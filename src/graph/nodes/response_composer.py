from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.models.state import TriageState
from src.config.prompts import RESPONSE_COMPOSER_SYSTEM, DISCLAIMER
from src.llm.client import get_llm
from src.utils.safety_filters import sanitize_llm_response
import logging

logger = logging.getLogger(__name__)

URGENCY_EMOJI = {
    "EMERGENCY": "🔴",
    "URGENT": "🟠",
    "NON_URGENT": "🟡",
    "SELF_CARE": "🟢",
}


async def response_composer_node(state: TriageState) -> dict:
    """Compose the final patient-facing triage result message."""
    urgency = state.get("urgency_level", "NON_URGENT")
    department = state.get("routed_department", "General Medicine")
    symptoms = state.get("extracted_symptoms", [])
    severity = state.get("symptom_severity")
    age_group = state.get("patient_age_group", "adult")

    # Emergency responses use the pre-built template (set by emergency_node)
    if state.get("final_response"):
        return {}   # Already set — nothing to do

    emoji = URGENCY_EMOJI.get(urgency, "🟡")

    prompt = (
        f"URGENCY: {urgency}\n"
        f"EMOJI: {emoji}\n"
        f"DEPARTMENT: {department}\n"
        f"PATIENT SYMPTOMS: {', '.join(symptoms)}\n"
        f"SELF-REPORTED SEVERITY: {f'{severity}/10' if severity else 'not specified'}\n"
        f"AGE GROUP: {age_group}\n\n"
        f"Compose the complete triage result message for the patient now."
    )

    llm = get_llm()
    try:
        response = await llm.ainvoke([
            SystemMessage(content=RESPONSE_COMPOSER_SYSTEM),
            HumanMessage(content=prompt),
        ])
        message = sanitize_llm_response(response.content) + DISCLAIMER

    except Exception as e:
        logger.error(f"response_composer error: {e} — using fallback template")
        message = _fallback_response(urgency, emoji, department)

    return {
        "messages": [AIMessage(content=message)],
        "final_response": message,
    }


def _fallback_response(urgency: str, emoji: str, department: str) -> str:
    action_map = {
        "EMERGENCY": "Go to the Emergency Room immediately.",
        "URGENT": "Visit the OPD today for urgent consultation.",
        "NON_URGENT": "Schedule an OPD appointment.",
        "SELF_CARE": "Monitor symptoms at home. Visit OPD if they persist.",
    }
    return (
        f"### 🧾 Triage Assessment\n\n"
        f"**Urgency Level:** {emoji} {urgency}\n"
        f"**Recommended Action:** {action_map.get(urgency, 'See a doctor.')}\n"
        f"**Department:** {department}\n\n"
        f"### 📍 Your Next Step\nProceed to {department}.\n\n"
        f"---\n*This is NOT a medical diagnosis. This is an automated triage routing tool.*"
    )
