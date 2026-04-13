from sqlmodel import Session, select
from src.models.db_models import TriageSession
from src.database.connection import get_engine
from datetime import datetime
import uuid


def write_audit_record(payload: dict) -> str:
    """Insert a triage session audit record. Returns the record ID."""
    record_id = str(uuid.uuid4())
    session_record = TriageSession(
        id=record_id,
        session_id=payload.get("session_id", "unknown"),
        completed_at=datetime.utcnow(),
        age_group=payload.get("age_group"),
        gender=payload.get("gender"),
        symptoms_extracted=payload.get("symptoms_extracted"),
        red_flags=payload.get("red_flags"),
        urgency_level=payload.get("urgency_level"),
        urgency_confidence=payload.get("urgency_confidence"),
        urgency_reasoning=payload.get("urgency_reasoning"),
        routed_department=payload.get("routed_department"),
        routing_reasoning=payload.get("routing_reasoning"),
        rag_chunks_used=payload.get("rag_chunks_used"),
        estimated_wait_minutes=payload.get("estimated_wait_minutes"),
        emergency_flag=payload.get("emergency_flag", False),
        human_review_flag=payload.get("human_review_flag", False),
        llm_model_used=payload.get("llm_model_used"),
        total_llm_calls=payload.get("total_llm_calls", 0),
        conversation_turns=payload.get("conversation_turns", 0),
        full_conversation=payload.get("full_conversation"),
    )
    with Session(get_engine()) as db:
        db.add(session_record)
        db.commit()
    return record_id


def get_session_history(session_id: str) -> list[dict]:
    """Retrieve all audit records for a session."""
    with Session(get_engine()) as db:
        results = db.exec(
            select(TriageSession).where(TriageSession.session_id == session_id)
        ).all()
        return [r.model_dump() for r in results]


def get_recent_sessions(limit: int = 50) -> list[dict]:
    """Retrieve recent triage sessions for the admin dashboard."""
    with Session(get_engine()) as db:
        results = db.exec(
            select(TriageSession).order_by(TriageSession.created_at.desc()).limit(limit)
        ).all()
        return [r.model_dump() for r in results]


def get_stats() -> dict:
    """Return summary statistics for the admin dashboard."""
    with Session(get_engine()) as db:
        all_records = db.exec(select(TriageSession)).all()
        total = len(all_records)
        if total == 0:
            return {"total": 0, "by_urgency": {}, "by_department": {}, "emergency_count": 0}

        by_urgency: dict[str, int] = {}
        by_dept: dict[str, int] = {}
        emergency_count = 0

        for r in all_records:
            if r.urgency_level:
                by_urgency[r.urgency_level] = by_urgency.get(r.urgency_level, 0) + 1
            if r.routed_department:
                by_dept[r.routed_department] = by_dept.get(r.routed_department, 0) + 1
            if r.emergency_flag:
                emergency_count += 1

        return {
            "total": total,
            "by_urgency": by_urgency,
            "by_department": by_dept,
            "emergency_count": emergency_count,
        }
