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
    symptoms = state.get("extracted_symptoms", [])
    turns = state.get("conversation_turns", 0)

    # Immediate proceed if emergency red flag found
    if red_flags:
        return "rag_retrieval"

    # Proceed if we have enough symptoms
    if len(symptoms) >= 2:
        return "rag_retrieval"

    # Safety guardrail — max 5 turns to prevent infinite loops
    if turns >= 5:
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
