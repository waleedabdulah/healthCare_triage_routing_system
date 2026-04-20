"""
Flow 3 — Appointment Booking + Email Confirmation
Flow 4 — Double-Booking Prevention
====================================================
Flow 3:
  - POST /appointments/book → status=pending_confirmation
  - GET /appointments/confirm/{token} within 15 min → status=confirmed
  - Confirming again → already_confirmed (idempotent, 200)
  - Confirming expired token → 410
  - Confirming cancelled appointment → 410

Flow 4:
  - Booking an already-taken slot_id → 409 Conflict
"""
import pytest
from datetime import datetime, timedelta
from sqlmodel import Session
from src.database.connection import get_engine
from src.models.db_models import Appointment
from src.database.repository import create_appointment, cancel_appointment_by_id


class TestBookingCreation:
    def test_booking_creates_pending_appointment(self, client, sample_booking_payload):
        resp = client.post("/api/v1/appointments/book", json=sample_booking_payload)
        assert resp.status_code == 200
        body = resp.json()

        assert body["status"] == "pending_confirmation"
        assert "appointment_id" in body
        assert "confirmation_code" in body
        assert len(body["confirmation_code"]) == 6
        assert body["department"] == "General Medicine"
        assert body["doctor_name"] == "Dr. Test Doctor"

    def test_booking_reserves_slot_immediately(self, client, sample_booking_payload):
        """After booking, the slot must appear in get_booked_slot_ids."""
        resp = client.post("/api/v1/appointments/book", json=sample_booking_payload)
        assert resp.status_code == 200

        from src.database.repository import get_booked_slot_ids
        booked = get_booked_slot_ids()
        assert sample_booking_payload["slot_id"] in booked

    def test_booking_status_endpoint_returns_pending(self, client, sample_booking_payload):
        resp = client.post("/api/v1/appointments/book", json=sample_booking_payload)
        appt_id = resp.json()["appointment_id"]

        status_resp = client.get(f"/api/v1/appointments/{appt_id}/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "pending_confirmation"


class TestEmailConfirmation:
    def _book(self, client, payload: dict) -> dict:
        resp = client.post("/api/v1/appointments/book", json=payload)
        assert resp.status_code == 200
        return resp.json()

    def _get_token(self, appt_id: str) -> str:
        """Read the confirmation_token directly from the DB."""
        with Session(get_engine()) as session:
            appt = session.get(Appointment, appt_id)
            return appt.confirmation_token

    def test_confirm_within_window_sets_confirmed(self, client, sample_booking_payload):
        booking = self._book(client, sample_booking_payload)
        token = self._get_token(booking["appointment_id"])

        resp = client.get(f"/api/v1/appointments/confirm/{token}")
        assert resp.status_code == 200
        assert "confirmed" in resp.text.lower()

        # Verify DB status
        status_resp = client.get(f"/api/v1/appointments/{booking['appointment_id']}/status")
        assert status_resp.json()["status"] == "confirmed"

    def test_confirm_already_confirmed_is_idempotent(self, client, sample_booking_payload):
        """Clicking the email link twice must not error — 200 with 'already confirmed'."""
        booking = self._book(client, sample_booking_payload)
        token = self._get_token(booking["appointment_id"])

        # First confirm
        r1 = client.get(f"/api/v1/appointments/confirm/{token}")
        assert r1.status_code == 200

        # Second confirm — must still be 200 (idempotent)
        r2 = client.get(f"/api/v1/appointments/confirm/{token}")
        assert r2.status_code == 200
        assert "already confirmed" in r2.text.lower()

    def test_confirm_expired_token_returns_410(self, client, sample_booking_payload):
        """Tokens older than 15 minutes must be rejected with 410."""
        booking = self._book(client, sample_booking_payload)
        appt_id = booking["appointment_id"]
        token = self._get_token(appt_id)

        # Backdate the created_at by 20 minutes directly in the DB
        with Session(get_engine()) as session:
            appt = session.get(Appointment, appt_id)
            appt.created_at = datetime.utcnow() - timedelta(minutes=20)
            session.add(appt)
            session.commit()

        resp = client.get(f"/api/v1/appointments/confirm/{token}")
        assert resp.status_code == 410
        assert "expired" in resp.text.lower()

    def test_confirm_cancelled_appointment_returns_410(self, client, sample_booking_payload):
        """Confirming a cancelled appointment must return 410."""
        booking = self._book(client, sample_booking_payload)
        appt_id = booking["appointment_id"]
        token = self._get_token(appt_id)

        # Cancel the appointment first
        cancel_appointment_by_id(appt_id)

        resp = client.get(f"/api/v1/appointments/confirm/{token}")
        assert resp.status_code == 410
        assert "cancel" in resp.text.lower()

    def test_confirm_unknown_token_returns_404(self, client):
        resp = client.get("/api/v1/appointments/confirm/totally-fake-token-xyz")
        assert resp.status_code == 404


class TestDoubleBookingPrevention:
    """Flow 4 — same slot_id cannot be booked twice."""

    def test_duplicate_slot_id_returns_409(self, client, sample_booking_payload):
        # First booking succeeds
        r1 = client.post("/api/v1/appointments/book", json=sample_booking_payload)
        assert r1.status_code == 200

        # Second booking with the same slot_id must fail
        r2 = client.post("/api/v1/appointments/book", json=sample_booking_payload)
        assert r2.status_code == 409
        assert "slot" in r2.json()["detail"].lower()

    def test_different_slot_ids_can_both_be_booked(self, client, sample_booking_payload):
        import copy
        payload2 = copy.deepcopy(sample_booking_payload)
        payload2["slot_id"] = "dr_test_001_2026-05-01_10:00"
        payload2["slot_time"] = "10:00"
        payload2["slot_label"] = "Morning – 10:00 AM"

        r1 = client.post("/api/v1/appointments/book", json=sample_booking_payload)
        r2 = client.post("/api/v1/appointments/book", json=payload2)
        assert r1.status_code == 200
        assert r2.status_code == 200

    def test_cancelled_slot_can_be_rebooked(self, client, sample_booking_payload):
        """After cancellation the slot_id is freed and can be booked again."""
        r1 = client.post("/api/v1/appointments/book", json=sample_booking_payload)
        assert r1.status_code == 200
        appt_id = r1.json()["appointment_id"]

        # Cancel it
        cancel_appointment_by_id(appt_id)

        # Now booking the same slot must succeed
        r2 = client.post("/api/v1/appointments/book", json=sample_booking_payload)
        assert r2.status_code == 200


class TestPatientCancelBooking:
    def test_patient_can_cancel_own_booking(self, client, sample_booking_payload):
        booking = client.post("/api/v1/appointments/book", json=sample_booking_payload).json()
        appt_id = booking["appointment_id"]

        resp = client.post(f"/api/v1/appointments/{appt_id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["cancelled"] is True

        status = client.get(f"/api/v1/appointments/{appt_id}/status").json()
        assert status["status"] == "cancelled"

    def test_cancel_already_cancelled_returns_404(self, client, sample_booking_payload):
        booking = client.post("/api/v1/appointments/book", json=sample_booking_payload).json()
        appt_id = booking["appointment_id"]

        client.post(f"/api/v1/appointments/{appt_id}/cancel")
        resp = client.post(f"/api/v1/appointments/{appt_id}/cancel")
        assert resp.status_code == 404

    def test_cancel_nonexistent_returns_404(self, client):
        resp = client.post("/api/v1/appointments/00000000-0000-0000-0000-000000000000/cancel")
        assert resp.status_code == 404
