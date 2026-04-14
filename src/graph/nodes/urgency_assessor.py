from langchain_core.messages import SystemMessage, HumanMessage
from src.models.state import TriageState
from src.models.schemas import UrgencyAssessment
from src.config.prompts import URGENCY_ASSESSOR_SYSTEM
from src.llm.client import get_llm, get_model_name
from src.llm.structured_output import parse_structured_output
import logging

logger = logging.getLogger(__name__)


def _build_urgency_prompt(state: TriageState) -> str:
    symptoms = state.get("extracted_symptoms", [])
    duration = state.get("symptom_duration", "unknown")
    severity = state.get("symptom_severity")
    age_group = state.get("patient_age_group", "unknown")
    red_flags = state.get("red_flags_detected", [])
    rag_context = state.get("rag_context", [])

    rag_text = ""
    if rag_context:
        rag_text = "\n\nRELEVANT TRIAGE PROTOCOLS:\n"
        for chunk in rag_context[:3]:
            text = chunk.get('text', '')[:600]
            rag_text += f"- {text}\n"

    severity_text = f"{severity}/10" if severity else "not specified"

    return (
        f"PATIENT SYMPTOMS:\n"
        f"- Symptoms: {', '.join(symptoms) if symptoms else 'not specified'}\n"
        f"- Duration: {duration}\n"
        f"- Self-reported severity: {severity_text}\n"
        f"- Age group: {age_group}\n"
        f"- Hard-coded red flags detected: {', '.join(red_flags) if red_flags else 'none'}\n"
        f"{rag_text}\n"
        f"Classify the urgency level now."
    )


async def urgency_assessor_node(state: TriageState) -> dict:
    """Classify symptom urgency using LLM + RAG context."""
    llm = get_llm()

    # Hard-coded safety override — red flags always = EMERGENCY
    red_flags = state.get("red_flags_detected", [])
    if red_flags:
        logger.info(f"Hard-coded emergency override triggered: {red_flags}")
        return {
            "urgency_level": "EMERGENCY",
            "urgency_confidence": 0.99,
            "urgency_reasoning": f"Hard-coded emergency red flags detected: {', '.join(red_flags)}",
        }

    prompt = _build_urgency_prompt(state)
    messages = [
        SystemMessage(content=URGENCY_ASSESSOR_SYSTEM),
        HumanMessage(content=prompt),
    ]

    try:
        response = await llm.ainvoke(messages)
        assessment = parse_structured_output(response.content, UrgencyAssessment)

        # Safety: escalate when confidence is low so under-triage risk is minimised.
        # NON_URGENT < 0.70 → URGENT (same-day review is safer than "see a GP whenever")
        # SELF_CARE  < 0.70 → NON_URGENT (schedule a visit rather than pure home monitoring)
        if assessment.urgency.value == "NON_URGENT" and assessment.confidence < 0.70:
            logger.warning("Low confidence NON_URGENT → escalating to URGENT")
            return {
                "urgency_level": "URGENT",
                "urgency_confidence": assessment.confidence,
                "urgency_reasoning": assessment.reasoning + " (escalated due to low confidence)",
                "llm_model_used": get_model_name(),
            }

        if assessment.urgency.value == "SELF_CARE" and assessment.confidence < 0.70:
            logger.warning("Low confidence SELF_CARE → escalating to NON_URGENT")
            return {
                "urgency_level": "NON_URGENT",
                "urgency_confidence": assessment.confidence,
                "urgency_reasoning": assessment.reasoning + " (escalated from SELF_CARE due to low confidence)",
                "llm_model_used": get_model_name(),
            }

        return {
            "urgency_level": assessment.urgency.value,
            "urgency_confidence": assessment.confidence,
            "urgency_reasoning": assessment.reasoning,
            "red_flags_detected": list(set(
                state.get("red_flags_detected", []) + assessment.red_flags
            )),
            "llm_model_used": get_model_name(),
        }

    except Exception as e:
        logger.error(f"urgency_assessor error: {e} — defaulting to URGENT")
        return {
            "urgency_level": "URGENT",
            "urgency_confidence": 0.5,
            "urgency_reasoning": "Assessment failed — defaulting to URGENT for safety",
            "llm_model_used": get_model_name(),
        }
