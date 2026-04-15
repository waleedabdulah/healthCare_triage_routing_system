from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages


class TriageState(TypedDict):
    # ── Conversation ──────────────────────────────────────────────────────────
    messages: Annotated[list, add_messages]   # full chat history (appended, never replaced)
    session_id: str
    conversation_turns: int                   # how many collect_symptoms cycles ran

    # ── Patient context (never medically inferred) ────────────────────────────
    patient_age_group: Optional[str]          # "child" | "adult" | "elderly"
    patient_gender: Optional[str]

    # ── Extracted symptoms ────────────────────────────────────────────────────
    extracted_symptoms: list[str]             # e.g. ["chest pain", "shortness of breath"]
    symptom_duration: Optional[str]           # e.g. "2 hours", "3 days"
    symptom_severity: Optional[int]           # 1–10 self-reported scale
    red_flags_detected: list[str]             # hard-coded keyword triggers
    ready_for_triage: Optional[bool]          # LLM signals it has enough info to triage

    # ── RAG ───────────────────────────────────────────────────────────────────
    rag_context: list[dict]                   # retrieved chunks + metadata

    # ── Triage decisions (populated progressively) ────────────────────────────
    urgency_level: Optional[str]              # EMERGENCY | URGENT | NON_URGENT | SELF_CARE
    urgency_confidence: Optional[float]       # 0.0–1.0
    urgency_reasoning: Optional[str]
    routed_department: Optional[str]          # "Cardiology", "ER", "ENT", etc.
    routing_reasoning: Optional[str]

    # ── Output ────────────────────────────────────────────────────────────────
    final_response: Optional[str]

    # ── Audit ─────────────────────────────────────────────────────────────────
    audit_written: bool
    llm_model_used: Optional[str]      # e.g. "llama-3.3-70b-versatile"
    human_review_flag: bool             # True if escalated for human review
