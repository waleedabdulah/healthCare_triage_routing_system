from sqlmodel import Session, select, col
from src.models.db_models import TriageSession, Appointment
from src.database.connection import get_engine
from datetime import datetime, timedelta
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


def get_booked_slot_ids() -> set[str]:
    """Return slot IDs that are already taken (pending or confirmed)."""
    with Session(get_engine()) as db:
        rows = db.exec(
            select(Appointment.slot_id).where(
                col(Appointment.status).in_(["pending_confirmation", "confirmed"])
            )
        ).all()
        return set(rows)


def create_appointment(payload: dict) -> Appointment:
    """Insert a new appointment record and return it."""
    record = Appointment(
        session_id=payload["session_id"],
        patient_name=payload["patient_name"],
        patient_email=payload["patient_email"],
        patient_phone=payload["patient_phone"],
        department=payload["department"],
        doctor_id=payload["doctor_id"],
        doctor_name=payload["doctor_name"],
        doctor_specialization=payload["doctor_specialization"],
        slot_id=payload["slot_id"],
        slot_date=payload["slot_date"],
        slot_time=payload["slot_time"],
        slot_label=payload["slot_label"],
        status="pending_confirmation",
    )
    with Session(get_engine()) as db:
        db.add(record)
        db.commit()
        db.refresh(record)
    return record


CONFIRMATION_WINDOW_SECONDS = 15 * 60   # 15 minutes

def confirm_appointment(token: str) -> tuple[Appointment | None, str]:
    """
    Mark appointment as confirmed via email token.
    Returns (appointment, result_code) where result_code is one of:
      'confirmed'          — just confirmed successfully
      'already_confirmed'  — was already confirmed (duplicate click)
      'expired'            — pending but 15-min window has passed
      'cancelled'          — appointment was cancelled
      'not_found'          — token not found
    """
    with Session(get_engine()) as db:
        appt = db.exec(
            select(Appointment).where(Appointment.confirmation_token == token)
        ).first()

        if not appt:
            return None, "not_found"

        if appt.status == "confirmed":
            return appt, "already_confirmed"

        if appt.status == "cancelled":
            return appt, "cancelled"

        # pending_confirmation — check 15-min window
        elapsed = (datetime.utcnow() - appt.created_at).total_seconds()
        if elapsed > CONFIRMATION_WINDOW_SECONDS:
            return appt, "expired"

        appt.status = "confirmed"
        db.add(appt)
        db.commit()
        db.refresh(appt)
        return appt, "confirmed"


def get_appointment(appointment_id: str) -> Appointment | None:
    """Fetch a single appointment by ID."""
    with Session(get_engine()) as db:
        return db.get(Appointment, appointment_id)


def cancel_appointment_by_id(appointment_id: str) -> Appointment | None:
    """
    Cancel an appointment. Returns the cancelled Appointment record so
    the caller can send a cancellation email, or None if not found/already done.
    """
    with Session(get_engine()) as db:
        appt = db.get(Appointment, appointment_id)
        if appt and appt.status in ("pending_confirmation", "confirmed"):
            appt.status = "cancelled"
            db.add(appt)
            db.commit()
            db.refresh(appt)
            return appt
        return None


def get_active_appointment_for_department(patient_email: str, department: str) -> Appointment | None:
    """
    Return the most recent active (pending/confirmed) appointment for this
    patient email + department created within the last 7 days, or None.
    Email comparison is case-insensitive.
    """
    cutoff = datetime.utcnow() - timedelta(days=7)
    email_lower = patient_email.strip().lower()
    with Session(get_engine()) as db:
        results = db.exec(
            select(Appointment)
            .where(
                Appointment.department == department,
                col(Appointment.status).in_(["pending_confirmation", "confirmed"]),
                Appointment.created_at >= cutoff,
            )
            .order_by(Appointment.created_at.desc())
        ).all()
        # Filter case-insensitively in Python (SQLite LIKE is case-insensitive for ASCII only)
        for appt in results:
            if appt.patient_email.strip().lower() == email_lower:
                return appt
        return None


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
