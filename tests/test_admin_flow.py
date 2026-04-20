"""
Flow 6 — Bulk Appointment Cancellation
=======================================
Covers:
  - Admin bulk-cancels all appointments in a department
  - Bulk cancel with date range filters only cancels matching rows
  - Bulk cancel with doctor name filter (partial match)
  - Nurse bulk cancel is scoped to their own department
  - Nurse cannot bulk cancel another department's appointments
  - target_status filter: only confirmed / only pending / all active
  - Response includes correct cancelled_count and appointment list
  - Already-cancelled appointments are not re-cancelled or counted
  - Admin single-cancel via admin route returns 200
  - Admin can view stats (returns aggregate counts)
"""
import copy
import pytest
from src.database.repository import create_appointment


# ── Helper ────────────────────────────────────────────────────────────────────

def _make_appt(
    department: str,
    doctor_id: str,
    doctor_name: str,
    slot_suffix: str,
    slot_date: str = "2026-06-01",
    status_override: str | None = None,
) -> str:
    """Create an appointment directly via repository and return its ID."""
    appt = create_appointment({
        "session_id": f"test-admin-{slot_suffix}",
        "patient_name": "Admin Test Patient",
        "patient_email": "admin_test@test.com",
        "patient_phone": "0300-9999999",
        "department": department,
        "doctor_id": doctor_id,
        "doctor_name": doctor_name,
        "doctor_specialization": department,
        "slot_id": f"{doctor_id}_{slot_date}_{slot_suffix}",
        "slot_date": slot_date,
        "slot_time": "09:00",
        "slot_label": "Morning – 9:00 AM",
    })
    if status_override:
        from sqlmodel import Session
        from src.database.connection import get_engine
        from src.models.db_models import Appointment
        with Session(get_engine()) as session:
            a = session.get(Appointment, appt.id)
            a.status = status_override
            session.add(a)
            session.commit()
    return appt.id


# ── Flow 6a: Basic Bulk Cancel ────────────────────────────────────────────────

class TestBulkCancelBasic:
    def test_admin_bulk_cancel_all_in_department(self, client, admin_token):
        """Admin cancels every active appointment in Cardiology."""
        ids = [
            _make_appt("Cardiology", "dr_cardio_01", "Dr. Heart", f"bulk-{i}")
            for i in range(3)
        ]

        resp = client.post(
            "/api/v1/admin/appointments/bulk-cancel",
            json={"department": "Cardiology"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["cancelled_count"] == 3

        cancelled_ids = [a["appointment_id"] for a in body["cancelled"]]
        for appt_id in ids:
            assert appt_id in cancelled_ids

    def test_bulk_cancel_response_shape(self, client, admin_token):
        """Each item in 'cancelled' has the required fields."""
        _make_appt("Cardiology", "dr_cardio_01", "Dr. Heart", "shape-check")

        resp = client.post(
            "/api/v1/admin/appointments/bulk-cancel",
            json={"department": "Cardiology"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        item = resp.json()["cancelled"][0]
        for field in ("appointment_id", "patient_name"):
            assert field in item

    def test_bulk_cancel_zero_matches_returns_empty(self, client, admin_token):
        """Bulk cancel with a filter that matches nothing — 0 cancelled."""
        resp = client.post(
            "/api/v1/admin/appointments/bulk-cancel",
            json={"department": "Dermatology"},  # no appointments created
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["cancelled_count"] == 0

    def test_already_cancelled_not_recounted(self, client, admin_token):
        """Already-cancelled rows must not appear in the cancelled_count."""
        _make_appt("Cardiology", "dr_cardio_01", "Dr. Heart", "pre-cancelled",
                   status_override="cancelled")
        _make_appt("Cardiology", "dr_cardio_01", "Dr. Heart", "active-one")

        resp = client.post(
            "/api/v1/admin/appointments/bulk-cancel",
            json={"department": "Cardiology"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        # Only the active appointment should be counted
        assert resp.json()["cancelled_count"] == 1


# ── Flow 6b: Filters ──────────────────────────────────────────────────────────

class TestBulkCancelFilters:
    def test_date_range_filter_only_cancels_matching_dates(self, client, admin_token):
        """Appointments outside the date range must not be cancelled."""
        in_range_id = _make_appt(
            "Neurology", "dr_neuro_01", "Dr. Brain", "in-range",
            slot_date="2026-07-10",
        )
        out_of_range_id = _make_appt(
            "Neurology", "dr_neuro_01", "Dr. Brain", "out-range",
            slot_date="2026-08-20",
        )

        resp = client.post(
            "/api/v1/admin/appointments/bulk-cancel",
            json={
                "department": "Neurology",
                "date_from": "2026-07-01",
                "date_to": "2026-07-31",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        cancelled_ids = [a["appointment_id"] for a in body["cancelled"]]

        assert in_range_id in cancelled_ids
        assert out_of_range_id not in cancelled_ids

    def test_doctor_partial_name_filter(self, client, admin_token):
        """Partial doctor name match should cancel only matching appointments."""
        smith_id = _make_appt("ENT", "dr_ent_01", "Dr. Smith", "ent-smith")
        jones_id = _make_appt("ENT", "dr_ent_02", "Dr. Jones", "ent-jones")

        resp = client.post(
            "/api/v1/admin/appointments/bulk-cancel",
            json={"department": "ENT", "doctor": "Smith"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        cancelled_ids = [a["appointment_id"] for a in body["cancelled"]]

        assert smith_id in cancelled_ids
        assert jones_id not in cancelled_ids

    def test_target_status_confirmed_only(self, client, admin_token):
        """target_status='confirmed' must not cancel pending_confirmation rows."""
        pending_id = _make_appt(
            "Orthopedics", "dr_ortho_01", "Dr. Bones", "ortho-pending"
        )  # default = pending_confirmation
        confirmed_id = _make_appt(
            "Orthopedics", "dr_ortho_01", "Dr. Bones", "ortho-confirmed",
            status_override="confirmed",
        )

        resp = client.post(
            "/api/v1/admin/appointments/bulk-cancel",
            json={"department": "Orthopedics", "target_status": "confirmed"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        cancelled_ids = [a["appointment_id"] for a in body["cancelled"]]

        assert confirmed_id in cancelled_ids
        assert pending_id not in cancelled_ids

    def test_target_status_all_cancels_both_pending_and_confirmed(
        self, client, admin_token
    ):
        """target_status=None (or 'all') cancels both pending and confirmed rows."""
        pending_id = _make_appt("Psychiatry", "dr_psy_01", "Dr. Mind", "psy-pending")
        confirmed_id = _make_appt(
            "Psychiatry", "dr_psy_01", "Dr. Mind", "psy-confirmed",
            status_override="confirmed",
        )

        resp = client.post(
            "/api/v1/admin/appointments/bulk-cancel",
            json={"department": "Psychiatry"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        cancelled_ids = [a["appointment_id"] for a in resp.json()["cancelled"]]

        assert pending_id in cancelled_ids
        assert confirmed_id in cancelled_ids


# ── Flow 6c: Department Scoping ───────────────────────────────────────────────

class TestBulkCancelScoping:
    def test_nurse_bulk_cancel_own_department(self, client, nurse_user, nurse_token):
        """Nurse can bulk-cancel within their own department (Cardiology)."""
        ids = [
            _make_appt("Cardiology", "dr_cardio_01", "Dr. Heart", f"nurse-own-{i}")
            for i in range(2)
        ]

        resp = client.post(
            "/api/v1/admin/appointments/bulk-cancel",
            json={"department": "Cardiology"},
            headers={"Authorization": f"Bearer {nurse_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["cancelled_count"] == 2

    def test_nurse_bulk_cancel_other_department_returns_empty(
        self, client, nurse_user, nurse_token
    ):
        """Nurse bulk-cancelling another department gets 0 results (dept scoped)."""
        # Create appointments in Neurology (nurse is Cardiology)
        _make_appt("Neurology", "dr_neuro_01", "Dr. Brain", "neuro-for-nurse")

        # Nurse requests cancellation of Neurology — server overrides to Cardiology
        resp = client.post(
            "/api/v1/admin/appointments/bulk-cancel",
            json={"department": "Neurology"},
            headers={"Authorization": f"Bearer {nurse_token}"},
        )
        # Should succeed but cancel 0 (Cardiology has none)
        assert resp.status_code == 200
        assert resp.json()["cancelled_count"] == 0

    def test_admin_bulk_cancel_across_departments(self, client, admin_token):
        """Admin without department filter cancels across all departments."""
        _make_appt("Cardiology", "dr_cardio_01", "Dr. Heart", "cross-cardio")
        _make_appt("Neurology", "dr_neuro_01", "Dr. Brain", "cross-neuro")

        resp = client.post(
            "/api/v1/admin/appointments/bulk-cancel",
            json={"date_from": "2026-06-01", "date_to": "2026-06-30"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["cancelled_count"] >= 2

    def test_bulk_cancel_without_token_returns_401(self, client):
        resp = client.post(
            "/api/v1/admin/appointments/bulk-cancel",
            json={"department": "Cardiology"},
        )
        assert resp.status_code == 401


# ── Flow 6d: Admin Single Cancel via Admin Route ──────────────────────────────

class TestAdminSingleCancel:
    def test_admin_can_cancel_any_department(self, client, admin_token):
        appt_id = _make_appt("Gastroenterology", "dr_gastro_01", "Dr. Gut", "admin-cancel")

        resp = client.post(
            f"/api/v1/admin/appointments/{appt_id}/cancel",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

        # Verify status changed
        list_resp = client.get(
            "/api/v1/admin/appointments",
            params={"department": "Gastroenterology"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        appt = next(a for a in list_resp.json()["appointments"] if a["appointment_id"] == appt_id)
        assert appt["status"] == "cancelled"

    def test_cancel_nonexistent_returns_404(self, client, admin_token):
        resp = client.post(
            "/api/v1/admin/appointments/00000000-0000-0000-0000-000000000000/cancel",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404


# ── Flow 6e: Stats Endpoint ───────────────────────────────────────────────────

class TestAdminStats:
    def test_stats_returns_expected_shape(self, client, admin_token):
        resp = client.get(
            "/api/v1/admin/stats",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "total" in body
        assert "by_urgency" in body
        assert "by_department" in body
        assert "emergency_count" in body

    def test_stats_without_token_returns_401(self, client):
        resp = client.get("/api/v1/admin/stats")
        assert resp.status_code == 401
