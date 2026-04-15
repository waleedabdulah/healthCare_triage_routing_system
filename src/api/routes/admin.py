import asyncio
import logging
from fastapi import APIRouter, Query, Depends, HTTPException, status
from pydantic import BaseModel
from src.database.repository import (
    get_recent_sessions, get_stats, get_appointments_filtered,
    get_appointment, cancel_appointment_by_id, bulk_cancel_appointments,
)
from src.api.dependencies import get_current_user
from src.models.db_models import NurseUser
from src.utils.email_service import send_cancellation_email

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/admin/audit-logs")
def list_audit_logs(
    limit: int = Query(default=50, le=200),
    _user: NurseUser = Depends(get_current_user),
):
    """Return recent triage audit records. Requires JWT."""
    records = get_recent_sessions(limit=limit)
    safe = []
    for r in records:
        r_copy = dict(r)
        for k, v in r_copy.items():
            if hasattr(v, "isoformat"):
                r_copy[k] = v.isoformat()
        safe.append(r_copy)
    return {"records": safe, "count": len(safe)}


@router.get("/admin/stats")
def get_triage_stats(_user: NurseUser = Depends(get_current_user)):
    """Return aggregate statistics about triage sessions. Requires JWT."""
    return get_stats()


@router.get("/admin/appointments")
def list_appointments(
    department: str | None = Query(default=None),
    status: str | None = Query(default=None),
    date_from: str | None = Query(default=None, description="YYYY-MM-DD range start (inclusive)"),
    date_to: str | None = Query(default=None, description="YYYY-MM-DD range end (inclusive)"),
    doctor: str | None = Query(default=None, description="Partial doctor name search"),
    limit: int = Query(default=500, le=1000),
    user: NurseUser = Depends(get_current_user),
):
    """
    Return appointments filtered by department / status / date range / doctor.
    Nurses are always scoped to their own department.
    Admins can filter freely.
    Requires JWT.
    """
    # Department scoping — nurses cannot override their assigned department
    effective_department = department
    if user.department is not None:
        effective_department = user.department

    appointments = get_appointments_filtered(
        department=effective_department,
        status=status,
        date_from=date_from,
        date_to=date_to,
        doctor=doctor,
        limit=limit,
    )
    return {"appointments": appointments, "count": len(appointments)}


@router.post("/admin/appointments/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: str,
    user: NurseUser = Depends(get_current_user),
):
    """
    Cancel a specific appointment by ID.
    Nurses can only cancel appointments in their own department.
    Requires JWT.
    """
    # Fetch first so we can check department before mutating
    appt = await asyncio.to_thread(get_appointment, appointment_id)
    if appt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found.",
        )

    # Nurses are scoped to their department
    if user.department is not None and appt.department != user.department:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel appointments in your department.",
        )

    if appt.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appointment is already cancelled.",
        )

    await asyncio.to_thread(cancel_appointment_by_id, appointment_id)

    # Send cancellation email in background
    appt_dict = {
        "patient_name":          appt.patient_name,
        "patient_email":         appt.patient_email,
        "patient_phone":         appt.patient_phone,
        "department":            appt.department,
        "doctor_name":           appt.doctor_name,
        "doctor_specialization": appt.doctor_specialization,
        "slot_label":            appt.slot_label,
        "confirmation_code":     appt.confirmation_code,
    }
    asyncio.create_task(asyncio.to_thread(send_cancellation_email, appt_dict))

    return {"message": "Appointment cancelled.", "appointment_id": appointment_id}


# ── Bulk cancel schema ────────────────────────────────────────────────────────

class BulkCancelRequest(BaseModel):
    department:    str | None = None
    doctor:        str | None = None
    date_from:     str | None = None
    date_to:       str | None = None
    target_status: str | None = None   # None / "all" = pending+confirmed; or specific status


@router.post("/admin/appointments/bulk-cancel")
async def bulk_cancel(
    body: BulkCancelRequest,
    user: NurseUser = Depends(get_current_user),
):
    """
    Cancel all appointments matching the given filters and send
    cancellation emails to each affected patient.
    Nurses are locked to their own department.
    """
    # Department scoping
    effective_department = body.department
    if user.department is not None:
        effective_department = user.department

    cancelled = await asyncio.to_thread(
        bulk_cancel_appointments,
        department=effective_department,
        doctor=body.doctor,
        date_from=body.date_from,
        date_to=body.date_to,
        target_status=body.target_status,
    )

    # Fire cancellation emails concurrently in the background
    async def _send_all():
        tasks = [
            asyncio.to_thread(send_cancellation_email, appt)
            for appt in cancelled
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.error(f"Cancellation email failed for {cancelled[i]['patient_email']}: {r}")

    asyncio.create_task(_send_all())

    logger.info(
        f"Bulk cancel by {user.email}: {len(cancelled)} appointments cancelled "
        f"(dept={effective_department}, doctor={body.doctor}, "
        f"{body.date_from}→{body.date_to})"
    )

    return {
        "cancelled_count": len(cancelled),
        "cancelled": [{"appointment_id": a["appointment_id"], "patient_name": a["patient_name"]} for a in cancelled],
    }
