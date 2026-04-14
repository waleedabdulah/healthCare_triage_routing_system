"""
Appointment booking endpoints.
GET  /api/v1/appointments/doctors/{department}  — list doctors + available slots
POST /api/v1/appointments/book                  — create a pending appointment, send confirmation email
GET  /api/v1/appointments/confirm/{token}       — confirm appointment via email link (returns HTML)
GET  /api/v1/appointments/{appointment_id}      — fetch booking details
"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr

from src.config.settings import get_settings
from src.data.doctors import get_doctors_for_department
from src.database.repository import (
    create_appointment,
    get_appointment,
    confirm_appointment,
    get_booked_slot_ids,
    cancel_appointment_by_id,
    get_active_appointment_for_department,
)
from src.utils.email_service import send_appointment_email, send_cancellation_email

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


# ── Schemas ───────────────────────────────────────────────────────────────────

class BookingRequest(BaseModel):
    session_id: str
    department: str
    doctor_id: str
    doctor_name: str
    doctor_specialization: str
    slot_id: str
    slot_date: str
    slot_time: str
    slot_label: str
    patient_name: str
    patient_email: str
    patient_phone: str


class BookingResponse(BaseModel):
    appointment_id: str
    confirmation_code: str
    department: str
    doctor_name: str
    doctor_specialization: str
    slot_label: str
    patient_name: str
    patient_email: str
    status: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/appointments/doctors/{department}")
async def list_doctors(department: str):
    """Return doctors with available (unbooked) slots for the next 7 working days."""
    booked = await asyncio.to_thread(get_booked_slot_ids)
    doctors = get_doctors_for_department(department, booked_slot_ids=booked)
    return {"department": department, "doctors": doctors}


@router.post("/appointments/book", response_model=BookingResponse)
async def book_appointment(request: BookingRequest):
    """
    Create a pending appointment and send a confirmation email with PDF receipt.
    The slot is reserved immediately but status stays 'pending_confirmation' until
    the patient clicks the link in the email.
    """
    # Prevent double-booking the same slot
    booked = await asyncio.to_thread(get_booked_slot_ids)
    if request.slot_id in booked:
        raise HTTPException(
            status_code=409,
            detail="This slot was just booked by another patient. Please choose a different time."
        )

    try:
        appt = await asyncio.to_thread(create_appointment, request.model_dump())
    except Exception as e:
        logger.error(f"Appointment creation failed: {e}")
        raise HTTPException(status_code=500, detail="Could not save appointment. Please try again.")

    logger.info(
        f"Appointment pending — id={appt.id} dept={appt.department} "
        f"doctor={appt.doctor_name} slot={appt.slot_label} email={appt.patient_email}"
    )

    # Send confirmation email in background (don't block the response)
    confirm_url = f"{settings.app_base_url}/api/v1/appointments/confirm/{appt.confirmation_token}"
    appt_dict = {
        "patient_name":          appt.patient_name,
        "patient_email":         appt.patient_email,
        "patient_phone":         appt.patient_phone,
        "department":            appt.department,
        "doctor_name":           appt.doctor_name,
        "doctor_specialization": appt.doctor_specialization,
        "slot_label":            appt.slot_label,
        "confirmation_code":     appt.confirmation_code,
        "status":                appt.status,
    }
    asyncio.create_task(
        asyncio.to_thread(send_appointment_email, appt_dict, confirm_url)
    )

    return BookingResponse(
        appointment_id=appt.id,
        confirmation_code=appt.confirmation_code,
        department=appt.department,
        doctor_name=appt.doctor_name,
        doctor_specialization=appt.doctor_specialization,
        slot_label=appt.slot_label,
        patient_name=appt.patient_name,
        patient_email=appt.patient_email,
        status=appt.status,
    )


@router.get("/appointments/confirm/{token}", response_class=HTMLResponse)
async def confirm_booking(token: str):
    """
    Email confirmation link handler.
    Returns a styled HTML page matching one of four states.
    """
    appt, result_code = await asyncio.to_thread(confirm_appointment, token)

    if result_code == "not_found":
        return HTMLResponse(
            content=_html_page(
                title="Invalid Link",
                icon="❌",
                color="#dc2626",
                message="This confirmation link is invalid.",
                sub="If you believe this is an error, please contact reception.",
            ),
            status_code=404,
        )

    if result_code == "expired":
        return HTMLResponse(
            content=_html_page(
                title="Confirmation Link Expired",
                icon="⏰",
                color="#d97706",
                message=(
                    f"The confirmation link for your appointment with "
                    f"<strong>{appt.doctor_name}</strong> ({appt.department}) "
                    f"has expired. Confirmation links are valid for <strong>15 minutes</strong> only."
                ),
                sub="Please book a new appointment or contact reception for assistance.",
            ),
            status_code=410,
        )

    if result_code == "cancelled":
        return HTMLResponse(
            content=_html_page(
                title="Appointment Cancelled",
                icon="🚫",
                color="#6b7280",
                message=(
                    f"This appointment with <strong>{appt.doctor_name}</strong> "
                    f"({appt.department}) has already been cancelled."
                ),
                sub="Please book a new appointment if you still require care.",
            ),
            status_code=410,
        )

    if result_code == "already_confirmed":
        return HTMLResponse(
            content=_html_page(
                title="Appointment Already Confirmed",
                icon="✅",
                color="#16a34a",
                message=(
                    f"Your appointment with <strong>{appt.doctor_name}</strong> "
                    f"({appt.department}) on <strong>{appt.slot_label}</strong> "
                    f"is already confirmed."
                ),
                sub=(
                    f"Confirmation code: <strong>{appt.confirmation_code}</strong> — "
                    "no further action needed. Please show your PDF receipt at reception."
                ),
            ),
            status_code=200,
        )

    # result_code == "confirmed" — just confirmed now
    return HTMLResponse(
        content=_html_page(
            title="Appointment Confirmed!",
            icon="✅",
            color="#16a34a",
            message=(
                f"Your appointment with <strong>{appt.doctor_name}</strong> "
                f"({appt.department}) on <strong>{appt.slot_label}</strong> "
                f"has been confirmed."
            ),
            sub=(
                f"Confirmation code: <strong>{appt.confirmation_code}</strong> — "
                "please show your PDF receipt at reception on arrival."
            ),
        ),
        status_code=200,
    )


@router.get("/appointments/check")
async def check_existing_booking(email: str, department: str):
    """
    Check if this patient email already has an active appointment for the given
    department within the last 7 days. Returns the appointment or null.
    """
    appt = await asyncio.to_thread(
        get_active_appointment_for_department, email, department
    )
    if not appt:
        return {"exists": False, "appointment": None}
    return {
        "exists": True,
        "appointment": {
            "appointment_id": appt.id,
            "confirmation_code": appt.confirmation_code,
            "department": appt.department,
            "doctor_name": appt.doctor_name,
            "doctor_specialization": appt.doctor_specialization,
            "slot_label": appt.slot_label,
            "patient_name": appt.patient_name,
            "patient_email": appt.patient_email,
            "status": appt.status,
        },
    }


@router.post("/appointments/{appointment_id}/cancel")
async def cancel_booking(appointment_id: str):
    """Cancel an existing appointment by ID and send a cancellation email."""
    appt = await asyncio.to_thread(cancel_appointment_by_id, appointment_id)
    if not appt:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found or already cancelled/completed."
        )

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
    asyncio.create_task(
        asyncio.to_thread(send_cancellation_email, appt_dict)
    )

    return {"cancelled": True, "appointment_id": appointment_id}


@router.get("/appointments/{appointment_id}/status")
async def get_booking_status(appointment_id: str):
    """Poll endpoint so the frontend can check confirmation status."""
    appt = await asyncio.to_thread(get_appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    return {"appointment_id": appointment_id, "status": appt.status}


@router.get("/appointments/{appointment_id}")
async def get_booking(appointment_id: str):
    """Fetch a previously booked appointment."""
    appt = await asyncio.to_thread(get_appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    return appt


# ── HTML template helper ──────────────────────────────────────────────────────

def _html_page(title: str, icon: str, color: str, message: str, sub: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — City Hospital</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Segoe UI',Arial,sans-serif;background:#f1f5f9;min-height:100vh;
         display:flex;align-items:center;justify-content:center;padding:24px}}
    .card{{background:#fff;border-radius:16px;box-shadow:0 4px 24px rgba(0,0,0,.08);
           padding:48px 40px;max-width:480px;width:100%;text-align:center}}
    .icon{{font-size:56px;margin-bottom:20px}}
    h1{{font-size:22px;color:#0f172a;margin-bottom:12px}}
    .msg{{font-size:15px;color:#334155;line-height:1.6;margin-bottom:12px}}
    .sub{{font-size:13px;color:#64748b;line-height:1.6}}
    .badge{{display:inline-block;margin-top:20px;padding:8px 20px;
            border-radius:8px;font-size:13px;font-weight:600;color:#fff;
            background:{color}}}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">{icon}</div>
    <h1>{title}</h1>
    <p class="msg">{message}</p>
    <p class="sub">{sub}</p>
    <span class="badge">City Hospital Triage System</span>
  </div>
</body>
</html>"""
