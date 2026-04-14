from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.models.state import TriageState
from src.config.prompts import SYMPTOM_COLLECTOR_SYSTEM
from src.llm.client import get_llm
from src.llm.structured_output import extract_json
from src.utils.safety_filters import detect_red_flags, is_gibberish
import logging
import re

logger = logging.getLogger(__name__)

# Phrases that mean "I have no more symptoms to report"
_NO_MORE_SYMPTOMS_PATTERNS = re.compile(
    r'\b(nope|no+|nothing|nah|none|that\'?s?\s*(all|it)|no\s*(more|other|else|additional)|'
    r'i\s*(am|\'m)\s*(fine|okay|ok|good)|not\s*(really|anything)|nothing\s*(else|more|other))\b',
    re.IGNORECASE
)

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

    # Hard-coded check: if patient says "no/nope/nothing else" and we already have
    # at least one symptom, stop asking and proceed to triage immediately.
    existing_symptoms = list(state.get("extracted_symptoms", []))
    if (
        latest_human
        and existing_symptoms
        and len(latest_human.content.strip()) < 80  # short denial, not a new symptom description
        and _NO_MORE_SYMPTOMS_PATTERNS.search(latest_human.content)
    ):
        logger.info("Patient denied more symptoms — forcing ready_for_triage=True")
        return {
            "messages": [AIMessage(content=(
                "Thank you. I have collected all the information I need. "
                "Please wait a moment while I route you to the right department."
            ))],
            "extracted_symptoms": existing_symptoms,
            "symptom_duration": state.get("symptom_duration"),
            "symptom_severity": state.get("symptom_severity"),
            "patient_age_group": state.get("patient_age_group"),
            "patient_gender": state.get("patient_gender"),
            "red_flags_detected": new_red_flags,
            "conversation_turns": state.get("conversation_turns", 0) + 1,
            "ready_for_triage": True,
        }

    # Filter internal error messages so the LLM doesn't see them in context
    clean_messages = [m for m in messages if not _is_internal_error_msg(m)]

    # Build dynamic system prompt — prepend already-known facts so the LLM
    # never asks for information the patient already provided upfront.
    age_group = state.get("patient_age_group")
    age_labels = {
        "child":   "Child (under 16)",
        "adult":   "Adult (16–60)",
        "elderly": "Elderly (over 60)",
    }
    if age_group:
        age_label = age_labels.get(age_group, age_group)
        known_prefix = (
            f"ALREADY COLLECTED — DO NOT ASK AGAIN:\n"
            f"- Patient age group: {age_label} ✓\n\n"
            f"Because age group is already known, SKIP step 4 in the conversation flow entirely.\n"
            f"In your JSON response always set \"age_group\": \"{age_group}\" — never null.\n"
            f"For ready_for_triage condition 2, treat age_group as already satisfied.\n\n"
        )
        system_content = known_prefix + SYMPTOM_COLLECTOR_SYSTEM
    else:
        system_content = SYMPTOM_COLLECTOR_SYSTEM

    system_msg = SystemMessage(content=system_content)
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
    existing = set(existing_symptoms)
    new_symptoms = set(data.get("symptoms", []))
    merged_symptoms = list(existing | new_symptoms)

    # Merge red flags
    llm_red_flags = data.get("red_flags", [])
    for rf in llm_red_flags:
        if rf not in new_red_flags:
            new_red_flags.append(rf)

    # State-supplied age_group always wins — never let the LLM accidentally null it out
    resolved_age_group = state.get("patient_age_group") or data.get("age_group")

    return {
        "messages": [AIMessage(content=patient_message)],
        "extracted_symptoms": merged_symptoms,
        "symptom_duration": data.get("duration") or state.get("symptom_duration"),
        "symptom_severity": data.get("severity") or state.get("symptom_severity"),
        "patient_age_group": resolved_age_group,
        "patient_gender": data.get("gender") or state.get("patient_gender"),
        "red_flags_detected": new_red_flags,
        "conversation_turns": state.get("conversation_turns", 0) + 1,
        "ready_for_triage": bool(data.get("ready_for_triage", False)),
    }
