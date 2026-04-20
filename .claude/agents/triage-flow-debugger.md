---
name: triage-flow-debugger
description: Debug LangGraph triage flow issues — pass 1/pass 2 SSE streaming, interrupt_after state, routing edge decisions, node errors, and symptom checklist logic
tools: [Read, Grep, Bash, Glob]
---

You are a specialist debugger for the LangGraph-based hospital triage system at d:/AI_project.

---

## Graph Architecture

```
START
  └─► start_session  (runs ONCE — first turn only)
        └─► collect_symptoms ◄─────────────────────┐
              │                                      │
              ▼ (route_after_collection)             │
         [ready?] ──No──► [still here] ─────────────┘
              │
              Yes
              ▼
         rag_retrieval
              └─► urgency_assessment
                    │
                    ▼ (route_after_urgency)
              ┌─────┴──────────────┐
              ▼                    ▼                 ▼
       emergency_node      escalation_node    department_routing
              │                    │                 │
              └────────────────────┴─────────────────┘
                                   │
                                   ▼
                            compose_response
                                   │
                                   ▼
                              audit_node
                                   │
                                   ▼
                                  END
```

**Interrupt policy**: `interrupt_after=["collect_symptoms"]` — graph pauses after each patient turn. Resumed on next message via `graph.update_state()` + `None` input.

**Checkpointer**: `MemorySaver` (in-memory, keyed by `thread_id = session_id`). All state is lost on process restart.

---

## SSE Streaming — Two-Pass Pattern (`src/api/routes/chat.py`)

The `/chat` endpoint streams Server-Sent Events. **Four event types**:

```
data: {"type": "token", "content": "..."}
  → Streaming LLM token (compose_response node only)

data: {"type": "message", "content": "..."}
  → Complete conversational message from symptom_collector

data: {"type": "options", "question": "...", "options": [...], "multi_select": true}
  → Impact checklist form — frontend renders checkboxes instead of a text bubble

data: {"type": "triage_complete", "urgency_level": "URGENT", "routed_department": "Cardiology",
        "final_response": "...", "is_emergency": false}
  → Final triage result

data: [DONE]
  → Stream complete
```

**Two-pass streaming per request:**
- **Pass 1**: Resume/run `collect_symptoms` (pauses at interrupt). Emits `message` or `options` event.
- **Pass 2**: If `_should_proceed_to_triage()` returns True, resume graph to run full triage pipeline. Emits `token` + `triage_complete`.

### Critical LangGraph Resume Pattern

Passing a non-None dict to `graph.astream_events()` on an interrupted graph **restarts execution from the entry point** (re-runs `start_session`, wiping all accumulated state). To correctly resume:

```python
snapshot = graph.get_state(config)
is_fresh = not snapshot or not snapshot.values.get("session_id")

if is_fresh:
    # First turn — start graph from scratch
    input_data = {"messages": [HumanMessage(content=message)], "session_id": ..., "patient_age_group": ...}
else:
    # Subsequent turns — inject new message, then resume with None
    graph.update_state(config, {"messages": [HumanMessage(content=message)]})
    input_data = None
```

This ensures `start_session` only runs once per session, and all accumulated state (`symptom_duration`, `extracted_symptoms`, etc.) persists correctly across turns.

---

## TriageState Fields (`src/models/state.py`)

| Field | Type | Description |
|---|---|---|
| `messages` | `Annotated[list, add_messages]` | Full chat history — uses reducer, **appends** rather than replaces. Never return all historical messages from a node — only the new one. |
| `session_id` | `str` | LangGraph thread_id |
| `conversation_turns` | `int` | Turn counter |
| `patient_age_group` | `Optional[str]` | child / adult / elderly |
| `patient_gender` | `Optional[str]` | |
| `extracted_symptoms` | `list[str]` | e.g. ["chest pain", "sweating"] |
| `symptom_duration` | `Optional[str]` | e.g. "2 hours" |
| `symptom_severity` | `Optional[int]` | Reserved field (not actively used) |
| `symptom_impact` | `Optional[str]` | Patient's selected checklist labels as plain text — passed to urgency assessor LLM |
| `pending_options` | `Optional[dict]` | Holds checkbox form payload while waiting for patient to submit; `None` otherwise |
| `red_flags_detected` | `list[str]` | Hard-coded emergency keywords found |
| `ready_for_triage` | `Optional[bool]` | Signals the triage pipeline should run now |
| `rag_context` | `list[dict]` | Retrieved protocol chunks |
| `urgency_level` | `Optional[str]` | EMERGENCY / URGENT / NON_URGENT / SELF_CARE |
| `urgency_confidence` | `Optional[float]` | 0.0–1.0 |
| `urgency_reasoning` | `Optional[str]` | |
| `routed_department` | `Optional[str]` | Target department name |
| `routing_reasoning` | `Optional[str]` | |
| `final_response` | `Optional[str]` | Patient-facing triage message |
| `audit_written` | `bool` | MCP audit call completed |
| `llm_model_used` | `Optional[str]` | e.g. "llama-3.3-70b-versatile" |
| `human_review_flag` | `bool` | Low-confidence escalation flag |

---

## Routing Logic (`src/graph/edges.py`)

### `route_after_collection(state)` — evaluated in this order:

1. `red_flags_detected` non-empty → `"rag_retrieval"` immediately (emergency bypass, skips checklist)
2. `ready_for_triage == True` → `"rag_retrieval"`
3. `pending_options` is set → `"collect_symptoms"` (wait for checklist submission)
4. **`extracted_symptoms` + `symptom_duration` known but `symptom_impact` not yet collected → `"collect_symptoms"`** (hold for checklist)
5. Turn guardrail: `turns >= 6` (with symptoms) or `turns >= 8` (no symptoms) → `"rag_retrieval"`
6. Otherwise → `"collect_symptoms"`

### `route_after_urgency(state)`:
- `EMERGENCY` → `emergency_node`
- Confidence < 0.65 → `escalation_node` (sets `human_review_flag=True`)
- Everything else → `department_routing`

### `_should_proceed_to_triage()` mirror in `chat.py`

This function must stay **in sync** with `route_after_collection`. If pass 2 never fires (or fires incorrectly), check this function first:

```python
def _should_proceed_to_triage(sv):
    if sv.get("pending_options"):
        return False
    if (sv.get("extracted_symptoms") and sv.get("symptom_duration")
            and not sv.get("symptom_impact") and not sv.get("red_flags_detected")):
        return False
    return bool(
        sv.get("red_flags_detected")
        or sv.get("ready_for_triage")
        or len(sv.get("extracted_symptoms", [])) >= 2
        or sv.get("conversation_turns", 0) >= (6 if sv.get("extracted_symptoms") else 8)
    )
```

---

## Node Summary

| Node | File | Type | Description |
|---|---|---|---|
| `start_session` | `session_node.py` | Sync | Initialise all state fields — runs first turn only |
| `collect_symptoms` | `symptom_collector.py` | Async LLM | Gather symptoms; trigger impact checklist; handle submission |
| `rag_retrieval` | `rag_retrieval_node.py` | Sync | Query ChromaDB |
| `urgency_assessment` | `urgency_assessor.py` | Async LLM | Classify urgency using symptoms + impact text + RAG |
| `emergency_node` | `emergency_node.py` | Sync | Static ER response template |
| `escalation_node` | `escalation_node.py` | Sync | Bump urgency + set review flag |
| `department_routing` | `department_router.py` | Async LLM | Select department |
| `compose_response` | `response_composer.py` | Async LLM | Write patient-facing message (streams tokens) |
| `audit_node` | `audit_node.py` | Async MCP | Write audit record to DB via MCP |

---

## Symptom Impact Assessment (§7)

### Why It Exists

Numeric self-rating (1–10) is clinically unreliable. The checklist replaces this with descriptive impact statements the LLM evaluates in clinical context.

### Conversation Flow

```
Turn 1: Patient describes symptoms (text)
Turn 2: Bot asks duration (text)
Turn 3: Patient gives duration → bot asks any other symptoms
Turn 4: Patient replies (anything) →
         collect_symptoms form trigger fires:
           symptoms ✓ + duration in state ✓ + no impact yet ✓
         → returns pending_options payload
         → SSE emits options event
         → Frontend renders SymptomOptionsForm

Patient selects checkboxes → clicks Submit →
         Frontend sends selected labels as plain text message
         e.g. "My symptoms are getting worse, I cannot carry out my normal daily activities"

Turn N: collect_symptoms receives options response →
         stores text in symptom_impact
         sets ready_for_triage = True
         emits: "Thank you for completing the assessment…"
         → triage pipeline fires
```

### The Seven Checklist Options

```python
SEVERITY_OPTIONS = [
    "My symptoms are constant (not coming and going)",
    "My symptoms are getting worse",
    "I cannot carry out my normal daily activities",
    "I am unable to sleep due to my symptoms",
    "The symptoms started suddenly (within the last few hours)",
    "I have tried medication but it has not helped",
    "None of the above — symptoms are mild and manageable",
]
```

- "None of the above" is **mutually exclusive** — selecting it clears all others (enforced in `SymptomOptionsForm.tsx`)
- Selecting any other option automatically deselects "None of the above"

### How `symptom_impact` Is Used

Selected labels are joined into plain text and stored as `symptom_impact`. The urgency assessor LLM receives this text alongside symptoms, duration, age group, and RAG-retrieved protocols:

```
- Symptoms: fever, body aches, fatigue, cough
- Duration: 6 days
- Impact on daily life (patient-reported): My symptoms are getting worse,
  I cannot carry out my normal daily activities
- Age group: adult
- Hard-coded red flags: none
+ RELEVANT TRIAGE PROTOCOLS: [retrieved from ChromaDB]

Classify the urgency level now.
```

### Checklist Bypass Conditions

The form is **never shown** when:
- Emergency red flags are detected (triage fires immediately)
- The turn guardrail fires (too many turns — jumps to triage with what it has)

### SSE Protocol for Options Event

```json
{
  "type": "options",
  "question": "To help us understand how this is affecting you, please select all that apply:",
  "options": ["My symptoms are constant...", "..."],
  "multi_select": true
}
```

---

## `symptom_collector.py` Internal Execution Order

On each call, the node runs these checks in order (read the file at `src/graph/nodes/symptom_collector.py`):

1. **Hard-coded red flag scan** (pre-LLM) — populates `red_flags_detected`
2. **Gibberish rejection** (pre-LLM) — returns error message without LLM call
3. **Options response detection** — if latest patient message matches `SEVERITY_OPTIONS` text → stores `symptom_impact`, sets `ready_for_triage=True`, returns without LLM
4. **Checklist trigger** — if `extracted_symptoms` + `symptom_duration` present, no impact, no `pending_options`, no red flags → return `pending_options` payload without LLM
5. **"No more symptoms" short-circuit** — if patient says "nope/no/nothing else" + has ≥1 symptom → set `ready_for_triage=True` without LLM
6. **LLM call** — builds dynamic system prompt (prepends known `age_group` so LLM doesn't re-ask it)

---

## Common Bugs to Check

1. **Pass 2 never fires after checklist submission**: Check `_should_proceed_to_triage` — is `pending_options` still set in snapshot? Did `setPendingOptions(null)` run client-side before `sendMessage`?
2. **State wiped on turn 2**: Verify `is_fresh` detection — `snapshot.values.get("session_id")` must be non-None for existing sessions.
3. **Checklist shown twice**: `pending_options` returned when already set — check condition 4 in `symptom_collector` is guarded by `not state.get("pending_options")`.
4. **`add_messages` reducer misuse**: When returning `{"messages": [...]}` from a node, the list is *appended* (not replaced). Never return all historical messages — only the new one(s).
5. **MCP audit silently fails**: If the MCP subprocess died, `audit_written` becomes `True` but no DB record is written. Check backend logs for `MCP server subprocess` errors.
6. **LLM age_group null**: State-supplied `patient_age_group` must always win over re-asked values — check `resolved_age_group` logic in `symptom_collector_node`.

When debugging, always read backend logs first (INFO-level node names + `triage_completed` flag), then inspect graph state via `GET /api/v1/session/{session_id}`.
