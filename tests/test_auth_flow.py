"""
Flow 5 — Admin Auth & Department Scoping
=========================================
Covers:
  - Successful admin login → JWT token returned
  - Wrong password → 401
  - Accessing protected endpoint without token → 401
  - Nurse token only sees their own department's appointments
  - Nurse cannot cancel an appointment from a different department
"""
import pytest
import bcrypt
from src.database.repository import create_nurse_user, create_appointment


class TestAdminLogin:
    def test_admin_login_success_returns_token(self, client):
        """Valid credentials return a JWT and user info."""
        resp = client.post("/api/v1/auth/login", json={
            "email": "admin@cityhospital.com",
            "password": "Admin@123",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["user"]["role"] == "admin"
        assert body["user"]["department"] is None   # admin = unrestricted

    def test_wrong_password_returns_401(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "email": "admin@cityhospital.com",
            "password": "WrongPassword!",
        })
        assert resp.status_code == 401

    def test_unknown_email_returns_401(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "email": "nobody@hospital.com",
            "password": "Admin@123",
        })
        assert resp.status_code == 401

    def test_case_insensitive_email_login(self, client):
        """Email lookup must be case-insensitive."""
        resp = client.post("/api/v1/auth/login", json={
            "email": "ADMIN@CITYHOSPITAL.COM",
            "password": "Admin@123",
        })
        assert resp.status_code == 200

    def test_get_me_returns_current_user(self, client, admin_token):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "admin@cityhospital.com"


class TestProtectedEndpoints:
    def test_admin_appointments_without_token_returns_401(self, client):
        resp = client.get("/api/v1/admin/appointments")
        assert resp.status_code == 401

    def test_admin_stats_without_token_returns_401(self, client):
        resp = client.get("/api/v1/admin/stats")
        assert resp.status_code == 401

    def test_admin_audit_logs_without_token_returns_401(self, client):
        resp = client.get("/api/v1/admin/audit-logs")
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client):
        resp = client.get(
            "/api/v1/admin/appointments",
            headers={"Authorization": "Bearer this.is.not.valid"},
        )
        assert resp.status_code == 401

    def test_admin_can_access_all_departments(self, client, admin_token):
        """Admin (department=None) gets results without department scoping."""
        resp = client.get(
            "/api/v1/admin/appointments",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200


class TestDepartmentScoping:
    def _make_appointment(self, dept: str, slot_suffix: str) -> str:
        """Helper — insert an appointment directly via repository, return its ID."""
        appt = create_appointment({
            "session_id": f"test-session-{slot_suffix}",
            "patient_name": "Scoping Patient",
            "patient_email": "scope@test.com",
            "patient_phone": "0300-0000000",
            "department": dept,
            "doctor_id": f"dr_{dept.lower()}_01",
            "doctor_name": f"Dr. {dept}",
            "doctor_specialization": dept,
            "slot_id": f"dr_{slot_suffix}_slot",
            "slot_date": "2026-05-10",
            "slot_time": "10:00",
            "slot_label": "Morning – 10:00 AM",
        })
        return appt.id

    def test_nurse_only_sees_own_department(self, client, nurse_user, nurse_token):
        """A Cardiology nurse must NOT see appointments from other departments."""
        cardio_id = self._make_appointment("Cardiology", "cardio")
        neurology_id = self._make_appointment("Neurology", "neuro")

        resp = client.get(
            "/api/v1/admin/appointments",
            headers={"Authorization": f"Bearer {nurse_token}"},
        )
        assert resp.status_code == 200
        appt_ids = [a["appointment_id"] for a in resp.json()["appointments"]]

        assert cardio_id in appt_ids
        assert neurology_id not in appt_ids

    def test_nurse_cannot_cancel_other_departments_appointment(
        self, client, nurse_user, nurse_token
    ):
        """Nurse cancelling a Neurology appointment must be rejected (403)."""
        neurology_id = self._make_appointment("Neurology", "neuro-cancel")

        resp = client.post(
            f"/api/v1/admin/appointments/{neurology_id}/cancel",
            headers={"Authorization": f"Bearer {nurse_token}"},
        )
        assert resp.status_code == 403

    def test_nurse_can_cancel_own_department_appointment(
        self, client, nurse_user, nurse_token
    ):
        """Nurse can cancel an appointment in their own department."""
        cardio_id = self._make_appointment("Cardiology", "cardio-cancel")

        resp = client.post(
            f"/api/v1/admin/appointments/{cardio_id}/cancel",
            headers={"Authorization": f"Bearer {nurse_token}"},
        )
        assert resp.status_code == 200

    def test_admin_sees_all_departments(self, client, admin_token):
        """Admin token has no department restriction."""
        cardio_id = self._make_appointment("Cardiology", "admin-cardio")
        neuro_id = self._make_appointment("Neurology", "admin-neuro")

        resp = client.get(
            "/api/v1/admin/appointments",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        appt_ids = [a["appointment_id"] for a in resp.json()["appointments"]]
        assert cardio_id in appt_ids
        assert neuro_id in appt_ids
