"""
Emergency alert tool.
Phase 1: Writes EMERGENCY flag to audit system (stub).
Phase 3+: Webhook to nurse station / hospital alert system.
"""
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def send_emergency_alert(session_id: str, symptoms: list) -> dict:
    """
    Flag a session as an emergency in the audit system.
    Stub implementation — logs the alert.
    """
    alert_id = str(uuid.uuid4())
    logger.warning(
        f"🚨 EMERGENCY ALERT | alert_id={alert_id} | session={session_id} | "
        f"symptoms={symptoms} | time={datetime.utcnow().isoformat()}"
    )
    # Phase 3: POST to hospital nurse station webhook here
    return {
        "alerted": True,
        "alert_id": alert_id,
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
