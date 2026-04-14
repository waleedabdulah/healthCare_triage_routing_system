import uuid
from src.models.state import TriageState


def start_session_node(state: TriageState) -> dict:
    """Initialize session state. Entry point of the graph."""
    return {
        "session_id": state.get("session_id") or str(uuid.uuid4()),
        "conversation_turns": 0,
        "extracted_symptoms": [],
        "red_flags_detected": [],
        "ready_for_triage": False,
        "rag_context": [],
        "audit_written": False,
        "human_review_flag": False,
        "patient_age_group": state.get("patient_age_group"),
        "patient_gender": state.get("patient_gender"),
        # Always reset triage results — prevents stale values from a previous
        # completed session leaking into a new run on the same thread_id
        "urgency_level": None,
        "urgency_confidence": None,
        "urgency_reasoning": None,
        "routed_department": None,
        "routing_reasoning": None,
        "estimated_wait_minutes": None,
        "next_available_slot": None,
        "final_response": None,
        "symptom_duration": None,
        "symptom_severity": None,
    }
