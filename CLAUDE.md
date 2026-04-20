# CLAUDE.md — Healthcare Symptom Triage System

Complete developer reference for the AI-powered hospital triage and appointment system.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [How to Run](#3-how-to-run)
4. [Project Structure](#4-project-structure)
5. [Backend Architecture](#5-backend-architecture)
6. [LangGraph Orchestration](#6-langgraph-orchestration)
7. [Symptom Impact Assessment (Checklist)](#7-symptom-impact-assessment-checklist)
8. [MCP System](#8-mcp-system)
9. [RAG System](#9-rag-system)
10. [Database](#10-database)
11. [Auth System](#11-auth-system)
12. [Patient Frontend](#12-patient-frontend)
13. [Admin Frontend](#13-admin-frontend)
14. [Key Data Flows](#14-key-data-flows)
15. [Safety Rules](#15-safety-rules)
16. [Environment Variables](#16-environment-variables)
17. [Default Credentials](#17-default-credentials)
18. [API Reference](#18-api-reference)

---

## 1. Project Overview

An AI-powered hospital triage system that:
- Collects patient symptoms via conversational chat
- Assesses severity through a structured impact checklist (no 1–10 scale)
- Classifies urgency (EMERGENCY / URGENT / NON_URGENT / SELF_CARE) using LLM + RAG
- Routes patients to the correct hospital department
- Allows patients to book appointments with available doctors
- Gives nurses and admins a dashboard to manage appointments and audit logs

**Three separate apps run together:**
- `backend` — FastAPI on port 8000
- `frontend` — React patient triage app on port 5173
- `admin_frontend` — React nurse/admin dashboard on port 5174

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI + Uvicorn |
| AI orchestration | LangGraph (StateGraph with MemorySaver) |
| LLM | Groq API only (llama-3.3-70b-versatile) |
| RAG embeddings | sentence-transformers (all-MiniLM-L6-v2, local CPU) |
| RAG vector store | ChromaDB (persistent, cosine similarity) |
| MCP protocol | FastMCP (`PythonStdioTransport` — real subprocess) |
| Database | SQLite via SQLModel + SQLAlchemy |
| Auth | JWT (HS256, 8h expiry) + bcrypt password hashing |
| Patient frontend | React 18 + Zustand + TailwindCSS + Vite |
| Admin frontend | React 18 + Zustand + react-router-dom + TailwindCSS + Vite |
| HTTP client | axios (both frontends) |
| Email | SMTP (HTML + PDF attachment) |
| PDF generation | reportlab |

---

## 3. How to Run

### Prerequisites
- Python 3.11+ with virtual environment at `.venv/`
- Node.js 18+
- `.env` file configured (see [Environment Variables](#16-environment-variables))
- RAG data ingested (one-time setup)

### One-time RAG ingestion
```bash
# From project root, with venv activated
python -m src.rag.ingestion_pipeline
# Processes data/raw/ → populates data/chroma_db/
```

### Backend
```bash
cd d:/AI_project
.venv/Scripts/activate
uvicorn src.api.main:app --reload --port 8000
```
Startup sequence:
1. Creates SQLite tables (`data/triage_audit.db`)
2. Seeds default admin account (if no users exist)
3. Spawns MCP server subprocess (`src/mcp/server.py` over stdio)

> **Important**: After code changes, do a **full restart** (stop + start) rather than relying on `--reload` alone. The `MemorySaver` checkpointer lives in-process; a reload wipes all active session state.

### Patient Frontend
```bash
cd d:/AI_project/frontend
npm install
npm run dev
# → http://localhost:5173
```

### Admin Frontend
```bash
cd d:/AI_project/admin_frontend
npm install
npm run dev
# → http://localhost:5174
```

### Health Check
```
GET http://localhost:8000/health
# Returns: {status: "ok"|"degraded", services: {chromadb, sqlite}}
```

---

## 4. Project Structure

```
d:/AI_project/
├── src/                        # Python backend
│   ├── api/
│   │   ├── main.py             # FastAPI app, startup/shutdown events
│   │   ├── dependencies.py     # JWT middleware (get_current_user, require_admin)
│   │   └── routes/
│   │       ├── chat.py         # POST /chat — SSE triage stream
│   │       ├── auth.py         # POST /auth/login, GET /auth/me
│   │       ├── appointments.py # Booking, confirmation, cancellation
│   │       ├── admin.py        # Admin dashboard endpoints (JWT required)
│   │       └── health.py       # GET /health
│   ├── graph/
│   │   ├── builder.py          # LangGraph StateGraph + MemorySaver
│   │   ├── edges.py            # Conditional routing logic
│   │   └── nodes/
│   │       ├── session_node.py          # Initialize state (first turn only)
│   │       ├── symptom_collector.py     # Collect symptoms + trigger impact checklist
│   │       ├── rag_retrieval_node.py    # Query ChromaDB
│   │       ├── urgency_assessor.py      # Classify urgency using LLM + impact text
│   │       ├── emergency_node.py        # Static ER template
│   │       ├── escalation_node.py       # Low-confidence escalation
│   │       ├── department_router.py     # Route to department
│   │       ├── response_composer.py     # Compose patient message
│   │       └── audit_node.py           # Write audit via MCP
│   ├── models/
│   │   ├── state.py            # TriageState TypedDict (LangGraph state)
│   │   ├── db_models.py        # SQLModel tables: NurseUser, TriageSession, Appointment
│   │   └── schemas.py          # Pydantic request/response schemas
│   ├── database/
│   │   ├── connection.py       # SQLite engine + create_db_and_tables()
│   │   └── repository.py       # All DB query functions
│   ├── mcp/
│   │   ├── server.py           # FastMCP server with 6 tools (stdio subprocess)
│   │   ├── client.py           # MCPClient — PythonStdioTransport, lifecycle
│   │   └── tools/
│   │       ├── audit_tool.py       # write_audit_record, get_session_history
│   │       ├── department_tool.py  # get_department_info (reads JSON)
│   │       ├── alert_tool.py       # send_emergency_alert
│   │       └── wait_time_tool.py   # get_er_wait_time, get_opd_wait_time
│   ├── rag/
│   │   ├── vector_store.py     # ChromaDB client + query wrapper
│   │   ├── embedder.py         # sentence-transformers embedding
│   │   └── ingestion_pipeline.py # One-time data loader
│   ├── llm/
│   │   ├── client.py           # get_llm() — Groq only, raises RuntimeError if key missing
│   │   └── structured_output.py # JSON extraction from LLM text
│   ├── config/
│   │   ├── settings.py         # Pydantic BaseSettings (loads .env)
│   │   └── prompts.py          # All 5 system prompts + DISCLAIMER
│   └── utils/
│       ├── safety_filters.py   # Emergency keyword detection, sanitization
│       ├── email_service.py    # HTML email + PDF appointment receipt
│       └── logging_config.py   # Logging setup
├── frontend/                   # Patient triage React app
│   └── src/
│       ├── store/sessionStore.ts
│       ├── api/triageClient.ts
│       ├── api/bookingClient.ts
│       └── components/
│           ├── ChatWindow.tsx
│           ├── MessageBubble.tsx
│           ├── SymptomOptionsForm.tsx   # Impact checklist checkbox form
│           ├── RoutingCard.tsx
│           ├── UrgencyBadge.tsx
│           ├── BookingModal.tsx
│           └── DisclaimerBanner.tsx
├── admin_frontend/             # Nurse/admin React dashboard
│   └── src/
│       ├── store/authStore.ts
│       ├── api/adminClient.ts  # Global 401 interceptor → auto logout
│       ├── pages/
│       │   ├── LoginPage.tsx
│       │   └── DashboardPage.tsx
│       └── components/
│           ├── ProtectedRoute.tsx
│           ├── StatsCards.tsx
│           ├── AuditLogTable.tsx
│           └── AppointmentsTable.tsx
├── data/
│   ├── raw/                    # 11 markdown protocol docs + department_symptom_map.json
│   ├── chroma_db/              # ChromaDB vector store (generated by ingestion)
│   └── triage_audit.db         # SQLite database (generated on first run)
├── scripts/                    # Utility scripts
├── tests/                      # Test suite
├── .env                        # Runtime configuration
└── requirements.txt            # Python dependencies
```

---

## 5. Backend Architecture

### FastAPI App (`src/api/main.py`)

```python
@app.on_event("startup")
async def on_startup():
    create_db_and_tables()      # 1. Init SQLite
    _seed_default_admin()       # 2. Seed admin if no users
    await get_mcp_client().start()  # 3. Spawn MCP subprocess

@app.on_event("shutdown")
async def on_shutdown():
    await get_mcp_client().stop()   # Clean MCP subprocess shutdown
```

### Route Summary

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/chat` | None | SSE triage stream |
| GET | `/api/v1/session/{session_id}` | None | Get session state |
| POST | `/api/v1/auth/login` | None | Get JWT token |
| GET | `/api/v1/auth/me` | JWT | Current user info |
| GET | `/api/v1/appointments/doctors/{dept}` | None | Available doctors + slots |
| POST | `/api/v1/appointments/book` | None | Book appointment |
| GET | `/api/v1/appointments/confirm/{token}` | None | Confirm via email link |
| GET | `/api/v1/appointments/check` | None | Check existing booking |
| POST | `/api/v1/appointments/{id}/cancel` | None | Cancel booking |
| GET | `/api/v1/appointments/{id}/status` | None | Poll status |
| GET | `/api/v1/appointments/{id}` | None | Get booking details |
| GET | `/api/v1/admin/audit-logs` | JWT | Triage session history |
| GET | `/api/v1/admin/stats` | JWT | Aggregate statistics |
| GET | `/api/v1/admin/appointments` | JWT | Filtered appointment list |
| POST | `/api/v1/admin/appointments/{id}/cancel` | JWT | Single cancel |
| POST | `/api/v1/admin/appointments/bulk-cancel` | JWT | Bulk cancel |
| GET | `/health` | None | Service health check |

### SSE Streaming (`src/api/routes/chat.py`)

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
- **Pass 2**: If ready for triage, resume graph to run the full triage pipeline. Emits `token` + `triage_complete`.

**LangGraph resume pattern** — critical implementation detail:

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

### State Model (`src/models/state.py`) — `TriageState` TypedDict

| Field | Type | Description |
|---|---|---|
| `messages` | `Annotated[list, add_messages]` | Full chat history — uses reducer, appends rather than replaces |
| `session_id` | `str` | LangGraph thread_id |
| `conversation_turns` | `int` | Turn counter |
| `patient_age_group` | `Optional[str]` | child / adult / elderly |
| `patient_gender` | `Optional[str]` | |
| `extracted_symptoms` | `list[str]` | e.g. ["chest pain", "sweating"] |
| `symptom_duration` | `Optional[str]` | e.g. "2 hours" |
| `symptom_severity` | `Optional[int]` | Reserved field (not actively used — severity assessed via checklist text) |
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

## 6. LangGraph Orchestration

### Graph Architecture (`src/graph/builder.py`)

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

**Interrupt policy**: `interrupt_after=["collect_symptoms"]` — graph pauses after each patient message turn. The chat endpoint resumes it on the next message via `graph.update_state()` + `None` input.

**Checkpointer**: `MemorySaver` (in-memory, keyed by `thread_id = session_id`). All state is lost on process restart.

### Routing Logic (`src/graph/edges.py`)

**`route_after_collection(state)`** — evaluated in this order:

1. `red_flags_detected` non-empty → `"rag_retrieval"` immediately (emergency bypass)
2. `ready_for_triage == True` → `"rag_retrieval"`
3. `pending_options` is set → `"collect_symptoms"` (wait for checklist submission)
4. **`extracted_symptoms` + `symptom_duration` known but `symptom_impact` not yet collected → `"collect_symptoms"`** (hold for checklist)
5. Turn guardrail: `turns >= 6` (with symptoms) or `turns >= 8` (no symptoms) → `"rag_retrieval"`
6. Otherwise → `"collect_symptoms"`

**`route_after_urgency(state)`**:
- `EMERGENCY` → `emergency_node`
- Confidence < 0.65 → `escalation_node` (sets `human_review_flag=True`)
- Everything else → `department_routing`

### `_should_proceed_to_triage()` (`src/api/routes/chat.py`)

Mirror of `route_after_collection` used to decide whether pass 2 should run:

```python
def _should_proceed_to_triage(sv):
    if sv.get("pending_options"):
        return False
    # Block while impact checklist is still needed
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

### Node Summary

| Node | File | Type | Description |
|---|---|---|---|
| `start_session` | `session_node.py` | Sync | Initialise all state fields — runs first turn only |
| `collect_symptoms` | `symptom_collector.py` | Async LLM | Gather symptoms; trigger impact checklist; handle submission |
| `rag_retrieval` | `rag_retrieval_node.py` | Sync | Query ChromaDB |
| `urgency_assessment` | `urgency_assessor.py` | Async LLM | Classify urgency using symptoms + impact text + RAG |
| `emergency_node` | `emergency_node.py` | Sync | Static ER response template |
| `escalation_node` | `escalation_node.py` | Sync | Bump urgency + set review flag |
| `department_routing` | `department_router.py` | Async LLM | Select department |
| `compose_response` | `response_composer.py` | Async LLM | Write patient-facing message |
| `audit_node` | `audit_node.py` | Async MCP | Write audit record to DB |

### LLM Configuration (`src/llm/client.py`)

- **Provider**: Groq only — Ollama fallback has been removed
- **Model**: from `settings.groq_model` (default `llama-3.3-70b-versatile`)
- **Settings**: temperature=0.1, max_tokens=1024, max_retries=5
- Raises `RuntimeError` with a clear message if `GROQ_API_KEY` is not set
- `get_llm()` returns a cached singleton

---

## 7. Symptom Impact Assessment (Checklist)

### Why It Exists

Numeric self-rating (1–10) is clinically unreliable — a stoic patient may rate a heart attack as 4, an anxious patient may rate a headache as 10. The checklist replaces this with descriptive impact statements that the LLM can evaluate in clinical context.

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

### The Seven Checklist Options (`symptom_collector.py`)

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

### How Severity Is Determined

The selected labels are **not scored hardcoded**. They are joined into a plain text string and stored as `symptom_impact`. The urgency assessor LLM receives this text alongside symptoms, duration, age group, and RAG-retrieved protocols and makes a holistic clinical judgement. Example prompt passed to LLM:

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

The LLM returns one of `EMERGENCY / URGENT / NON_URGENT / SELF_CARE` with a confidence score.

### Checklist Bypass Conditions

The form is **never shown** when:
- Emergency red flags are detected (triage fires immediately)
- The turn guardrail fires (too many turns without info — jumps to triage with what it has)

### SSE Protocol for Options Event

```json
{
  "type": "options",
  "question": "To help us understand how this is affecting you, please select all that apply:",
  "options": ["My symptoms are constant...", "..."],
  "multi_select": true
}
```

Frontend detects this → calls `store.setPendingOptions(payload)` → `ChatWindow` renders `SymptomOptionsForm` and disables the text input until submitted.

---

## 8. MCP System

### Architecture

```
FastAPI process (uvicorn)
  └─ on_startup: get_mcp_client().start()
       └─ spawns subprocess: python src/mcp/server.py
            [stdin/stdout — PythonStdioTransport]

LangGraph audit_node
  └─ get_mcp_client().call_tool("write_audit_record", {...})
       └─ sends MCP message over stdin
            └─ server.py receives, calls mcp_write_audit_record()
                 └─ returns JSON over stdout
                      └─ client parses json.loads(result[0].text)
```

### Transport: `PythonStdioTransport`

The client uses `fastmcp.client.transports.PythonStdioTransport` (not `mcp.client.stdio.StdioServerParameters` — FastMCP rejects that type). `PYTHONPATH` is explicitly injected into the subprocess environment so `src.*` imports resolve inside the server script:

```python
from fastmcp.client.transports import PythonStdioTransport

env = {**os.environ, "PYTHONPATH": project_root}
transport = PythonStdioTransport(script_path=server_script, env=env)
self._client = Client(transport)
await self._client.__aenter__()
```

### MCP Server Tools (`src/mcp/server.py`)

| Tool | Args | Returns |
|---|---|---|
| `get_er_wait_time_tool()` | none | `{wait_time_minutes, queue_status}` |
| `get_opd_wait_time_tool(department)` | department: str | `{department, wait_time_minutes, available_slots}` |
| `write_audit_record(payload)` | payload: dict | `{success, record_id}` |
| `get_session_history(session_id)` | session_id: str | `list[AuditRecord]` |
| `get_department_info_tool(department)` | department: str | `{location, floor, contact, accepts_walkins}` |
| `send_emergency_alert_tool(session_id, symptoms)` | session_id: str, symptoms: list | `{alerted, alert_id, timestamp}` |

### MCP Client (`src/mcp/client.py`)

```python
# Lifecycle — wired into FastAPI startup/shutdown
client = get_mcp_client()
await client.start()   # spawns server.py subprocess
await client.stop()    # clean shutdown

# Calling a tool
result = await client.call_tool("write_audit_record", {"payload": {...}})
# result is a parsed dict from json.loads(result[0].text)
```

---

## 9. RAG System

### How It Works

```
data/raw/*.md (11 protocol files)
  └─ ingestion_pipeline.py
       ├─ Parse YAML frontmatter (department, urgency_category, symptom_keywords)
       ├─ Chunk text (~400 tokens, 75 overlap)
       ├─ Embed with all-MiniLM-L6-v2 (local CPU)
       └─ Upsert into ChromaDB collection "triage_protocols"

At triage time (rag_retrieval_node.py):
  ├─ Build query: extracted_symptoms + red_flags
  ├─ If red_flags present: pre-filter where urgency_category=="EMERGENCY"
  │    └─ Falls back to unfiltered if no results
  └─ Return top 3 chunks with metadata → injected into urgency_assessor prompt
```

### Embedding Model
- **Model**: `all-MiniLM-L6-v2` (HuggingFace sentence-transformers)
- **Runs locally** — no API calls, no cost
- L2-normalized vectors, cosine similarity via ChromaDB HNSW index

### ChromaDB (`src/rag/vector_store.py`)
- **Collection**: `"triage_protocols"`
- **Persistent path**: `settings.chroma_db_path` (default `./data/chroma_db`)
- **Metadata per chunk**: `source_file`, `department`, `urgency_category`, `symptom_keywords`, `chunk_index`
- `get_vector_store()` — cached singleton

### Re-running Ingestion
```bash
# Wipes existing collection and re-ingests all files in data/raw/
python -m src.rag.ingestion_pipeline
```

---

## 10. Database

### SQLite via SQLModel + SQLAlchemy
- **File**: `data/triage_audit.db` (auto-created on startup)
- **Engine**: `check_same_thread=False` (required for FastAPI async)

### Tables

#### `NurseUser`
| Column | Type | Notes |
|---|---|---|
| `id` | str (UUID) | PK |
| `email` | str | Unique, indexed, case-insensitive lookup |
| `password_hash` | str | bcrypt |
| `full_name` | str | |
| `department` | str? | NULL = admin (all departments) |
| `role` | str | "nurse" or "admin" |
| `created_at` | datetime | |
| `is_active` | bool | Default True |

#### `TriageSession` (audit log)
| Column | Type | Notes |
|---|---|---|
| `id` | str (UUID) | PK |
| `session_id` | str | LangGraph thread_id, indexed |
| `created_at` | datetime | |
| `age_group, gender` | str? | |
| `symptoms_extracted` | str? | JSON list |
| `red_flags` | str? | JSON list |
| `urgency_level` | str? | EMERGENCY / URGENT / NON_URGENT / SELF_CARE |
| `urgency_confidence` | float? | |
| `routed_department` | str? | |
| `emergency_flag` | bool | Indexed |
| `human_review_flag` | bool | Low-confidence cases |
| `conversation_turns` | int | |
| `full_conversation` | str? | JSON message list |
| `llm_model_used` | str? | |

#### `Appointment`
| Column | Type | Notes |
|---|---|---|
| `id` | str (UUID) | PK |
| `session_id` | str | Indexed |
| `patient_name, patient_email, patient_phone` | str | |
| `department` | str | |
| `doctor_id, doctor_name, doctor_specialization` | str | |
| `slot_id` | str | Unique — prevents double-booking |
| `slot_date, slot_time, slot_label` | str | |
| `status` | str | pending_confirmation / confirmed / cancelled |
| `confirmation_code` | str | 6-char hex, unique |
| `confirmation_token` | str | 32-char URL-safe, for email link (15-min expiry) |
| `created_at` | datetime | |

### Key Repository Functions (`src/database/repository.py`)
- `create_appointment(payload)` → Appointment
- `confirm_appointment(token)` → (Appointment|None, result_code) — checks 15-min expiry
- `cancel_appointment_by_id(id)` → Appointment
- `bulk_cancel_appointments(dept, doctor, date_from, date_to, status)` → list[dict]
- `get_appointments_filtered(dept, status, date_from, date_to, doctor, limit)` → list[dict]
- `get_booked_slot_ids()` → set[str] — prevents double-booking
- `write_audit_record(payload)` → str (record_id)
- `create_nurse_user(email, password_hash, full_name, dept, role)` → NurseUser
- `get_nurse_by_email(email)` → NurseUser|None

---

## 11. Auth System

### JWT Flow

```
POST /api/v1/auth/login  {email, password}
  └─ get_nurse_by_email(email) — case-insensitive lookup
  └─ bcrypt.checkpw(password, stored_hash)
  └─ jwt.encode({sub: id, email, department, role, exp: now+8h}, JWT_SECRET, HS256)
  └─ Returns {access_token, token_type: "bearer", user: {...}}

Protected endpoints:
  Authorization: Bearer <token>
  └─ dependencies.get_current_user() decodes JWT
  └─ Returns {id, email, department, role}
```

### Department Scoping (Security Layer)

Every admin route reads `current_user["department"]`:
```python
effective_department = department   # from query param
if user.department is not None:     # nurse (not admin)
    effective_department = user.department   # override — cannot be bypassed
```

- **Admin** (`department=None`): sees all departments, unrestricted
- **Nurse** (`department="Cardiology"`): locked to Cardiology only — enforced server-side even if frontend is bypassed

### Password Hashing
Uses `bcrypt` directly (not `passlib`) — passlib 1.7.4 is incompatible with bcrypt 4.x+:
```python
import bcrypt
hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
bcrypt.checkpw(password.encode(), stored_hash.encode())
```

### 401 Auto-Logout (Admin Frontend)

A global Axios response interceptor in `admin_frontend/src/api/adminClient.ts` catches every 401 from the backend:

```typescript
axios.interceptors.response.use(
  res => res,
  err => {
    if (err?.response?.status === 401) {
      useAuthStore.getState().logout()   // clears localStorage + Zustand state
      window.location.replace('/login')
    }
    return Promise.reject(err)
  }
)
```

This fires for all authenticated requests — expired tokens, revoked sessions, tampered JWTs — without any per-component handling.

---

## 12. Patient Frontend

### Location: `frontend/`
**Port**: 5173 | **Proxy**: `/api → http://localhost:8000`

### Zustand Store (`src/store/sessionStore.ts`)

```typescript
interface SessionState {
  sessionId: string
  messages: Message[]
  triageResult: TriageResult | null
  isLoading: boolean
  streamingContent: string
  appointmentBooked: boolean
  pendingAppointmentId: string | null
  pendingOptions: OptionsPayload | null   // set when severity checklist is active
}

interface OptionsPayload {
  question: string
  options: string[]
  multi_select: boolean
}

interface TriageResult {
  urgencyLevel: string | null       // EMERGENCY / URGENT / NON_URGENT / SELF_CARE
  routedDepartment: string | null
  isEmergency: boolean
  finalResponse: string | null
}
```

Key actions: `setPendingOptions(opts | null)` — sets/clears the active checklist form.

### SSE Client (`src/api/triageClient.ts`)

`sendMessage(sessionId, message, ageGroup?)` streams SSE from `/api/v1/chat`:

| Event type | Action |
|---|---|
| `token` | Discarded — triage result shown in card, not chat bubble |
| `message` | Added to chat as assistant message |
| `options` | Calls `store.setPendingOptions({...})` → renders checklist form |
| `triage_complete` | Stored in `triageResult`; emergency message added to chat |

### Booking Flow (`src/api/bookingClient.ts`)
1. `fetchDoctors(dept)` → show available doctors/slots
2. `submitBooking(payload)` → creates appointment
3. `fetchBookingStatus(id)` → polls every 4s until `"confirmed"`

### Key Components

| Component | Purpose |
|---|---|
| `ChatWindow.tsx` | Main chat interface; disables text input while `pendingOptions` is set |
| `MessageBubble.tsx` | Patient / assistant message rendering |
| `SymptomOptionsForm.tsx` | Impact checklist — checkboxes, mutual exclusion for "None", Submit button |
| `RoutingCard.tsx` | Triage result card — urgency, department, booking button |
| `UrgencyBadge.tsx` | Color-coded EMERGENCY / URGENT / NON_URGENT / SELF_CARE badge |
| `BookingModal.tsx` | Doctor selection + slot picker + form |
| `DisclaimerBanner.tsx` | "Not a medical diagnosis" banner |

### `SymptomOptionsForm.tsx` Behaviour
- Renders in place of the text input when `pendingOptions !== null`
- "None of the above" is mutually exclusive with all other options
- Submit is disabled until at least one option is selected
- On submit: joins selected labels with `, ` → sends as a text message via `sendMessage()` → clears `pendingOptions`

---

## 13. Admin Frontend

### Location: `admin_frontend/`
**Port**: 5174 | **Proxy**: `/api → http://localhost:8000`

### Routes
- `/login` — Login page
- `/dashboard` — Protected dashboard (ProtectedRoute)
- `*` → redirect to `/dashboard`

### Auth Store (`src/store/authStore.ts`)

```typescript
interface AuthUser {
  id: string
  email: string
  fullName: string
  department: string | null   // null = admin
  role: 'nurse' | 'admin'
}
```

- `login(email, password)` → stores token + user in `localStorage` (keys: `admin_token`, `admin_user`)
- `logout()` → clears localStorage + Zustand state
- `loadFromStorage()` → called on app init to restore session

### Admin API Client (`src/api/adminClient.ts`)

```typescript
fetchAppointments(token, {department?, status?, date_from?, date_to?, doctor?})
cancelAppointment(token, appointmentId)
bulkCancelAppointments(token, {department?, doctor?, date_from?, date_to?, target_status?})
fetchAuditLogs(token, limit?)
fetchStats(token)
```

Global 401 interceptor: any 401 response → `logout()` + redirect to `/login` (see [Auth System](#11-auth-system)).

### Key Components

| Component | Purpose |
|---|---|
| `StatsCards.tsx` | Total sessions, by urgency, by department, emergency count |
| `AuditLogTable.tsx` | Triage session history with urgency badges |
| `AppointmentsTable.tsx` | Filtered appointments + per-row cancel + mass cancellation panel |
| `ProtectedRoute.tsx` | Redirect to /login if not authenticated |

### AppointmentsTable Features
- **View filters**: department (locked for nurses), doctor partial match, status, date range
- **Date presets**: Today / This Week / This Month
- **Per-row cancel**: confirmation modal → `cancelAppointment()` → row updates in-place
- **Mass Cancel panel**: independent filters → preview count → bulk confirm → `bulkCancelAppointments()`
- **Cancellation emails**: sent automatically on both single and bulk cancel

---

## 14. Key Data Flows

### Triage Flow (End-to-End)

```
Patient types message
  └─► POST /api/v1/chat  (SSE stream opens)
        └─► Turn 1: graph.astream_events(initial_input, config)
              └─► start_session → collect_symptoms → [interrupt]
              └─► SSE: message event (bot asks duration)

        └─► Turn 2: graph.update_state(new_msg) + astream_events(None)
              └─► route_after_collection → collect_symptoms → [interrupt]
              └─► SSE: message event (bot asks any other symptoms)
              [_should_proceed_to_triage blocked: symptoms+duration, no impact yet]

        └─► Turn 3: graph.update_state(new_msg) + astream_events(None)
              └─► route_after_collection → collect_symptoms
                    [form trigger fires: symptoms + duration in state, no impact]
              └─► SSE: options event → frontend shows checklist form
              [interrupt]

        └─► Turn 4: patient submits checklist → message = selected labels
              └─► collect_symptoms detects options response
              └─► symptom_impact = "My symptoms are getting worse, ..."
              └─► ready_for_triage = True
              └─► SSE: message event ("Thank you for completing the assessment…")
              [interrupt]
              [_should_proceed_to_triage = True → pass 2 fires]

        └─► Pass 2: astream_events(None)
              └─► route_after_collection → rag_retrieval
              └─► urgency_assessment (LLM reads symptoms + impact + RAG protocols)
                    ├─ EMERGENCY → emergency_node (static template)
                    ├─ low confidence → escalation_node (bump to URGENT)
                    └─ normal → department_routing (LLM)
              └─► compose_response (LLM — patient message, streams tokens)
              └─► audit_node (MCP → write_audit_record → SQLite)
              └─► SSE: triage_complete event

  └─► Frontend: RoutingCard shows urgency + department + Book button
```

### Appointment Booking Flow

```
Patient clicks "Book Appointment"
  └─► BookingModal opens
  └─► GET /appointments/doctors/{dept}  (7-day availability, excludes booked slots)
  └─► Patient selects doctor + slot
  └─► POST /appointments/book
        └─► Appointment created (status='pending_confirmation')
        └─► Background task: send HTML email with confirmation link + PDF attachment
  └─► Frontend polls GET /appointments/{id}/status every 4s
  └─► Patient clicks email link → GET /appointments/confirm/{token}
        └─► 15-min expiry check
        └─► status='confirmed'
  └─► Frontend shows "Appointment Booked" ✓
```

### Email System

Emails are sent via **SMTP** (Simple Mail Transfer Protocol) — the internet standard for mail delivery. Configure in `.env`:

```
SMTP_HOST=smtp.gmail.com    ← Gmail's outgoing mail server
SMTP_PORT=587               ← TLS submission port
SMTP_USER=your@gmail.com    ← sender account
SMTP_PASSWORD=app_password  ← Gmail App Password (not your login password)
```

Gmail requires an **App Password** (Settings → Security → 2FA → App Passwords) because standard login is blocked for scripts. If SMTP vars are absent, emails are silently skipped — the system does not crash.

Two email types:
- **Booking confirmation**: HTML email + PDF receipt with doctor/slot details + 15-minute confirmation link
- **Cancellation notice**: Sent on single cancel (per-row) or bulk cancel (`asyncio.gather` for concurrent sends)

### Admin Appointment Management Flow

```
Nurse logs in → JWT stored in localStorage
  └─► GET /admin/stats  (summary cards)
  └─► GET /admin/appointments  (filtered, dept-scoped by JWT)
  └─► Cancel row → POST /admin/appointments/{id}/cancel
        └─► Department check (nurse cannot cancel other depts)
        └─► status='cancelled'
        └─► asyncio.create_task: send cancellation email
  └─► Mass Cancel → POST /admin/appointments/bulk-cancel
        └─► Atomic DB transaction: update all matching rows
        └─► asyncio.gather: send emails concurrently
```

---

## 15. Safety Rules

These are **code-enforced rules** — not just prompts.

### No-Diagnosis Policy (enforced in 3 places)
1. **Prompts** (`src/config/prompts.py`) — All 5 system prompts explicitly forbid diagnosis language
2. **`sanitize_llm_response()`** (`src/utils/safety_filters.py`) — Replaces phrases like "you have X" → "symptoms suggest X" before showing to patient
3. **`DISCLAIMER`** — Appended to every patient-facing LLM message

### Emergency Detection (hard-coded, before LLM)
`src/utils/safety_filters.py` — `detect_red_flags(text)` scans for 45+ emergency patterns:
- Chest pain, chest pressure, chest tightness
- Difficulty breathing, shortness of breath
- Stroke signs (face drooping, arm weakness, speech difficulty)
- Severe bleeding, loss of consciousness
- Seizure, convulsions
- Severe allergic reaction, anaphylaxis

If detected → `red_flags_detected` set → checklist bypassed → graph skips further questioning → immediate EMERGENCY routing.

### Urgency Escalation (safety net)
- `urgency_assessor.py`: NON_URGENT + confidence < 0.70 → auto-escalate to URGENT
- `urgency_assessor.py`: SELF_CARE + confidence < 0.70 → auto-escalate to NON_URGENT
- `route_after_urgency()`: confidence < 0.65 → `escalation_node` → sets `human_review_flag=True`
- Rule: **always escalate when in doubt, never under-triage**

### Gibberish / Off-Topic Filtering
`is_gibberish(text)` — rejects meaningless input before LLM call.

### Department Scoping (auth security)
Nurses cannot access other departments even with direct API calls — enforced server-side in every admin endpoint.

---

## 16. Environment Variables

Create a `.env` file at project root:

```env
# ── LLM ───────────────────────────────────────────────
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
# Note: Ollama fallback has been removed. GROQ_API_KEY is required.

# ── App ───────────────────────────────────────────────
APP_ENV=development
LOG_LEVEL=INFO

# ── Paths ─────────────────────────────────────────────
CHROMA_DB_PATH=./data/chroma_db
SQLITE_DB_PATH=./data/triage_audit.db
MCP_SERVER_SCRIPT=./src/mcp/server.py

# ── CORS ──────────────────────────────────────────────
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174

# ── Email / SMTP (optional) ───────────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password   # Gmail App Password, not login password
SMTP_FROM_NAME=City Hospital Triage
APP_BASE_URL=http://localhost:8000

# ── Auth ──────────────────────────────────────────────
JWT_SECRET=change-this-to-a-secure-random-string-in-production
JWT_EXPIRE_MINUTES=480
```

**Notes:**
- If `SMTP_*` vars are absent, emails are silently skipped — no crash.
- If `GROQ_API_KEY` is not set, the backend raises `RuntimeError` on startup.
- Ollama variables (`USE_OLLAMA`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`) have been removed — do not add them.

---

## 17. Default Credentials

### Admin Account (auto-seeded on first startup)
| Field | Value |
|---|---|
| Email | `admin@cityhospital.com` |
| Password | `Admin@123` |
| Role | admin |
| Department | All (unrestricted) |

### Nurse Accounts (one per department — all password: `Nurse@123`)

| Department | Email |
|---|---|
| Emergency Room | `nurse.er@cityhospital.com` |
| Cardiology | `nurse.cardiology@cityhospital.com` |
| Neurology | `nurse.neurology@cityhospital.com` |
| ENT | `nurse.ent@cityhospital.com` |
| Dermatology | `nurse.dermatology@cityhospital.com` |
| Gastroenterology | `nurse.gastro@cityhospital.com` |
| Pulmonology | `nurse.pulmonology@cityhospital.com` |
| Orthopedics | `nurse.orthopedics@cityhospital.com` |
| Ophthalmology | `nurse.ophthalmology@cityhospital.com` |
| Gynecology | `nurse.gynecology@cityhospital.com` |
| Urology | `nurse.urology@cityhospital.com` |
| Psychiatry | `nurse.psychiatry@cityhospital.com` |
| General Medicine | `nurse.generalmedicine@cityhospital.com` |
| Pediatrics | `nurse.pediatrics@cityhospital.com` |

To create additional nurse accounts:
```bash
.venv/Scripts/python.exe -c "
import bcrypt
from src.database.connection import create_db_and_tables
from src.database.repository import create_nurse_user
create_db_and_tables()
pw = bcrypt.hashpw(b'YourPassword', bcrypt.gensalt()).decode()
create_nurse_user(email='nurse@example.com', password_hash=pw, full_name='Nurse Name', department='Cardiology', role='nurse')
"
```

---

## 18. API Reference

### Chat — POST `/api/v1/chat`
```json
// Request
{ "session_id": "uuid", "message": "I have chest pain", "age_group": "adult" }

// SSE Response (stream) — four possible event types:
data: {"type": "message", "content": "How long have you had this?"}
data: {"type": "options", "question": "To help us understand...", "options": ["My symptoms are constant...", "..."], "multi_select": true}
data: {"type": "triage_complete", "urgency_level": "EMERGENCY", "routed_department": "Emergency Room", "final_response": "...", "is_emergency": true}
data: [DONE]
```

### Auth — POST `/api/v1/auth/login`
```json
// Request
{ "email": "admin@cityhospital.com", "password": "Admin@123" }

// Response
{ "access_token": "eyJ...", "token_type": "bearer", "user": { "id": "...", "email": "...", "full_name": "...", "department": null, "role": "admin" } }
```

### Book Appointment — POST `/api/v1/appointments/book`
```json
// Request
{
  "session_id": "uuid",
  "department": "Cardiology",
  "doctor_id": "dr_001",
  "doctor_name": "Dr. Ahmed",
  "slot_id": "dr_001_2026-04-17_09:00",
  "slot_date": "2026-04-17",
  "slot_time": "09:00",
  "slot_label": "Morning – 9:00 AM",
  "patient_name": "John Doe",
  "patient_email": "john@example.com",
  "patient_phone": "0300-1234567",
  "doctor_specialization": "Cardiologist"
}

// Response
{ "appointment_id": "uuid", "confirmation_code": "A1B2C3", "department": "Cardiology", "doctor_name": "Dr. Ahmed", "slot_label": "Morning – 9:00 AM", "status": "pending_confirmation" }
```

### Admin Appointments — GET `/api/v1/admin/appointments`
```
Authorization: Bearer <token>
?department=Cardiology&status=confirmed&date_from=2026-04-01&date_to=2026-04-30&doctor=Ahmed&limit=100
```

### Bulk Cancel — POST `/api/v1/admin/appointments/bulk-cancel`
```json
// Request (Authorization: Bearer <token>)
{ "department": "Cardiology", "doctor": "Ahmed", "date_from": "2026-04-17", "date_to": "2026-04-17", "target_status": "confirmed" }

// Response
{ "cancelled_count": 5, "cancelled": [{ "appointment_id": "...", "patient_name": "..." }] }
```
