from src.models.state import TriageState
import logging

logger = logging.getLogger(__name__)


def escalation_node(state: TriageState) -> dict:
    """
    Handles low-confidence cases by conservatively escalating to URGENT.
    Flags for human review in the audit log.
    """
    logger.warning(
        f"Low-confidence triage (confidence={state.get('urgency_confidence')}) "
        f"— escalating to URGENT and flagging for human review"
    )
    return {
        "urgency_level": "URGENT",
        "urgency_reasoning": (
            (state.get("urgency_reasoning") or "") +
            " [Escalated: low confidence — flagged for human review]"
        ),
        "human_review_flag": True,
    }
