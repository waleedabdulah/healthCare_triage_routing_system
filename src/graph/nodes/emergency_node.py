from src.models.state import TriageState
from src.config.prompts import EMERGENCY_RESPONSE_TEMPLATE


def emergency_escalation_node(state: TriageState) -> dict:
    """
    Handles EMERGENCY cases — routes to ER immediately.
    No LLM call needed: response is a fixed safe template.
    """
    return {
        "routed_department": "Emergency Room",
        "routing_reasoning": "Emergency symptoms detected — immediate ER routing",
        "estimated_wait_minutes": 0,
        "next_available_slot": "Immediate",
        "final_response": EMERGENCY_RESPONSE_TEMPLATE,
    }
