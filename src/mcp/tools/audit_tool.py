from src.database.repository import write_audit_record, get_session_history
import uuid
import logging

logger = logging.getLogger(__name__)


def mcp_write_audit_record(payload: dict) -> dict:
    """Write a triage audit record to SQLite."""
    try:
        record_id = write_audit_record(payload)
        return {"success": True, "record_id": record_id}
    except Exception as e:
        logger.error(f"audit write failed: {e}")
        return {"success": False, "record_id": None, "error": str(e)}


def mcp_get_session_history(session_id: str) -> list:
    """Get audit history for a session."""
    try:
        return get_session_history(session_id)
    except Exception as e:
        logger.error(f"session history fetch failed: {e}")
        return []
