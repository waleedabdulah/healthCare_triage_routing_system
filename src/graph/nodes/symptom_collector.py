from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.models.state import TriageState
from src.config.prompts import SYMPTOM_COLLECTOR_SYSTEM
from src.llm.client import get_llm
from src.llm.structured_output import extract_json
from src.utils.safety_filters import detect_red_flags, is_gibberish
import logging

logger = logging.getLogger(__name__)

# Error messages we've added to state on previous failed turns — don't show to LLM
_ERROR_PREFIXES = (
    "I'm sorry, I'm having trouble connecting",
    "I'm sorry, I wasn't able to understand that",
    "Please wait while I assist you further",
)


def _is_internal_error_msg(msg) -> bool:
    if isinstance(msg, AIMessage):
        return any(msg.content.startswith(p) for p in _ERROR_PREFIXES)
    return False


async def symptom_collector_node(state: TriageState) -> dict:
    """
    Conversational node: asks follow-up questions to collect symptom info.
    Loops back until sufficient info is gathered.
    """
    llm = get_llm()
    messages = state.get("messages", [])

    # Scan the latest patient message for hard-coded red flags first
    new_red_flags = list(state.get("red_flags_detected", []))
    for msg in messages:
        if hasattr(msg, "content") and isinstance(msg, HumanMessage):
            found = detect_red_flags(msg.content)
            for f in found:
                if f not in new_red_flags:
                    new_red_flags.append(f)

    # Reject gibberish before touching the LLM
    latest_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
    )
    if latest_human and is_gibberish(latest_human.content):
        return {
            "messages": [AIMessage(content=(
                "I'm sorry, I wasn't able to understand that. "
                "Could you please describe your symptoms in a few words? "
                "For example: \"I have a headache and fever\" or \"my chest hurts\"."
            ))],
            "conversation_turns": state.get("conversation_turns", 0) + 1,
            "red_flags_detected": new_red_flags,
        }

    # Filter internal error messages so the LLM doesn't see them in context
    clean_messages = [m for m in messages if not _is_internal_error_msg(m)]

    system_msg = SystemMessage(content=SYMPTOM_COLLECTOR_SYSTEM)
    llm_messages = [system_msg] + clean_messages

    # Step 1: call the LLM — if this fails, return a generic fallback
    try:
        response = await llm.ainvoke(llm_messages)
        raw = response.content
    except Exception as e:
        logger.error(f"symptom_collector LLM call failed: {e}")
        return {
            "messages": [AIMessage(content=(
                "I'm sorry, I'm having trouble connecting right now. "
                "Could you please try again in a moment?"
            ))],
            "conversation_turns": state.get("conversation_turns", 0) + 1,
            "red_flags_detected": new_red_flags,
        }

    # Step 2: try to parse JSON from the response — if missing, use raw text directly
    try:
        data = extract_json(raw)
    except Exception:
        logger.debug("symptom_collector: no JSON in LLM response, using raw text")
        data = {}

    patient_message = data.get("message") or raw

    # Merge extracted symptoms with any previously found
    existing = set(state.get("extracted_symptoms", []))
    new_symptoms = set(data.get("symptoms", []))
    merged_symptoms = list(existing | new_symptoms)

    # Merge red flags
    llm_red_flags = data.get("red_flags", [])
    for rf in llm_red_flags:
        if rf not in new_red_flags:
            new_red_flags.append(rf)

    return {
        "messages": [AIMessage(content=patient_message)],
        "extracted_symptoms": merged_symptoms,
        "symptom_duration": data.get("duration") or state.get("symptom_duration"),
        "symptom_severity": data.get("severity") or state.get("symptom_severity"),
        "patient_age_group": data.get("age_group") or state.get("patient_age_group"),
        "patient_gender": data.get("gender") or state.get("patient_gender"),
        "red_flags_detected": new_red_flags,
        "conversation_turns": state.get("conversation_turns", 0) + 1,
    }
