"""
Conditional edge functions for the LangGraph triage workflow.
Each function reads state and returns the name of the next node.
"""
from src.models.state import TriageState


def route_after_collection(state: TriageState) -> str:
    """
    Decide whether to collect more symptoms or proceed to RAG retrieval.
    Proceeds immediately if any hard-coded red flag is detected.
    """
    red_flags = state.get("red_flags_detected", [])
    ready = state.get("ready_for_triage", False)
    turns = state.get("conversation_turns", 0)

    # Immediate proceed if emergency red flag found
    if red_flags:
        return "rag_retrieval"

    # LLM explicitly signalled it has enough info (symptoms + duration + severity + age)
    if ready:
        return "rag_retrieval"

    # Safety guardrail — prevent infinite collection loops.
    # If symptoms have been captured, proceed after 6 turns.
    # If no symptoms have been captured yet, allow 2 extra turns (up to 8)
    # so the patient gets another chance rather than silently receiving a
    # vacuous "General Medicine / NON_URGENT" result with empty context.
    symptoms = state.get("extracted_symptoms", [])
    max_turns = 6 if symptoms else 8
    if turns >= max_turns:
        return "rag_retrieval"

    # Ask for more information
    return "collect_symptoms"


def route_after_urgency(state: TriageState) -> str:
    """
    Route based on urgency level and confidence.
    - EMERGENCY → immediate ER escalation
    - Low confidence → conservative human-review escalation
    - Other → department routing
    """
    urgency = state.get("urgency_level")
    confidence = state.get("urgency_confidence", 1.0)

    if urgency == "EMERGENCY":
        return "emergency_node"

    # Low confidence on any level → escalate conservatively
    if confidence is not None and confidence < 0.65:
        return "escalation_node"

    return "department_routing"
