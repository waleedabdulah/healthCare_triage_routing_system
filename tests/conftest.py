"""
Shared pytest fixtures for end-to-end tests.

Strategy:
- Each test gets an isolated SQLite DB (via tmp_path).
- The MCP subprocess is replaced with an AsyncMock (no real subprocess).
- ChromaDB is replaced with a MagicMock that returns empty results.
- The Groq LLM is replaced per-test with scripted AIMessage responses.
- The FastAPI TestClient triggers real startup/shutdown lifecycle events.
"""
import json
import pytest
import bcrypt
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage


# ── SSE Parsing Helper ────────────────────────────────────────────────────────

def parse_sse(response_text: str) -> list[dict]:
    """Parse raw SSE response text into a list of event dicts (skips [DONE])."""
    events = []
    for line in response_text.split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                continue
            try:
                events.append(json.loads(data))
            except json.JSONDecodeError:
                pass
    return events


# ── Settings Override (autouse — applies to every test) ───────────────────────

@pytest.fixture(autouse=True)
def override_settings(tmp_path, monkeypatch):
    """
    Give each test its own isolated SQLite DB and safe env vars.
    Clears lru_cache singletons so the new values take effect.
    """
    db_path = str(tmp_path / "test_triage.db")
    monkeypatch.setenv("SQLITE_DB_PATH", db_path)
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-at-least-32-chars!!")
    monkeypatch.setenv("SMTP_HOST", "")   # disable real email sending

    from src.config.settings import get_settings
    get_settings.cache_clear()

    from src.graph.builder import get_compiled_graph
    get_compiled_graph.cache_clear()

    yield db_path

    get_settings.cache_clear()
    get_compiled_graph.cache_clear()


# ── MCP Mock ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def mock_mcp():
    """
    Replace the global MCP client singleton with an AsyncMock.
    Works because get_mcp_client() returns _mcp_client if non-None.
    """
    mock_client = AsyncMock()
    mock_client.start = AsyncMock()
    mock_client.stop = AsyncMock()
    mock_client.call_tool = AsyncMock(
        return_value={"success": True, "record_id": "test-audit-record-id"}
    )

    import src.mcp.client as mcp_module
    original = mcp_module._mcp_client
    mcp_module._mcp_client = mock_client
    yield mock_client
    mcp_module._mcp_client = original  # restore after test


# ── Vector Store Mock ─────────────────────────────────────────────────────────

@pytest.fixture()
def mock_vector_store():
    """Replace ChromaDB with a mock that returns empty retrieval results."""
    from unittest.mock import patch

    mock_vs = MagicMock()
    mock_vs.query.return_value = []
    mock_vs.count.return_value = 0

    with patch("src.rag.vector_store.get_vector_store", return_value=mock_vs):
        yield mock_vs


# ── Scripted LLM Responses ────────────────────────────────────────────────────

def _ai(content: str) -> AIMessage:
    return AIMessage(content=content)


# symptom_collector turn 1 — extracts symptoms, asks for duration
_SC_TURN1 = json.dumps({
    "message": "How long have you been experiencing these symptoms?",
    "symptoms": ["headache", "fever"],
    "duration": None,
    "ready_for_triage": False,
    "age_group": "adult",
})

# symptom_collector turn 2 — extracts duration, asks for more symptoms
_SC_TURN2 = json.dumps({
    "message": "Do you have any other symptoms?",
    "symptoms": ["headache", "fever"],
    "duration": "2 days",
    "ready_for_triage": False,
    "age_group": "adult",
})

# urgency_assessor — NON_URGENT
_URGENCY = json.dumps({
    "urgency": "NON_URGENT",
    "confidence": 0.85,
    "red_flags": [],
    "reasoning": "Mild viral-type symptoms without emergency indicators.",
})

# department_router
_DEPARTMENT = json.dumps({
    "department": "General Medicine",
    "reasoning": "Symptoms consistent with a common viral illness.",
})

# response_composer — plain text (no JSON needed)
_COMPOSE = "Based on your symptoms, we recommend visiting General Medicine for a routine consultation."

# symptom_collector for emergency scenario
_SC_EMERGENCY = json.dumps({
    "message": "These are serious symptoms. Please seek immediate care.",
    "symptoms": ["chest pain", "shortness of breath"],
    "duration": None,
    "ready_for_triage": False,
    "age_group": "adult",
})


@pytest.fixture()
def mock_llm_triage():
    """
    Mock LLM for the full non-emergency triage flow.

    LLM call order across all 4 turns:
      1. collect_symptoms pass-1  (turn 1)
      2. collect_symptoms pass-2  (turn 1, triage_only — result not emitted)
      3. collect_symptoms pass-1  (turn 2)
      — turn 3 triggers checklist (pre-LLM, no call)
      — turn 4 checklist submission (pre-LLM, no call)
      4. urgency_assessor          (turn 4 pass-2)
      5. department_router         (turn 4 pass-2)
      6. response_composer         (turn 4 pass-2)
    """
    from unittest.mock import patch

    responses = [
        _ai(_SC_TURN1),    # 1. collect turn 1 pass 1
        _ai(_SC_TURN1),    # 2. collect turn 1 pass 2 (not emitted to client)
        _ai(_SC_TURN2),    # 3. collect turn 2
        _ai(_URGENCY),     # 4. urgency assessor
        _ai(_DEPARTMENT),  # 5. department router
        _ai(_COMPOSE),     # 6. response composer
    ]

    mock = MagicMock()
    mock.ainvoke = AsyncMock(side_effect=responses)

    # Patch get_llm where it is USED (each node imports it directly).
    # Patching src.llm.client.get_llm alone does not affect already-imported
    # references held by the node modules.
    _LLM_TARGETS = [
        "src.graph.nodes.symptom_collector.get_llm",
        "src.graph.nodes.urgency_assessor.get_llm",
        "src.graph.nodes.department_router.get_llm",
        "src.graph.nodes.response_composer.get_llm",
    ]
    from contextlib import ExitStack
    with ExitStack() as stack:
        for target in _LLM_TARGETS:
            stack.enter_context(patch(target, return_value=mock))
        yield mock


@pytest.fixture()
def mock_llm_emergency():
    """
    Mock LLM for the emergency bypass scenario.

    collect_symptoms runs twice (pass-1 + pass-2) but urgency_assessor
    is hardcoded for red flags, emergency_node is static, and
    response_composer is skipped (final_response already set).
    """
    from unittest.mock import patch
    from contextlib import ExitStack

    responses = [
        _ai(_SC_EMERGENCY),   # collect turn 1 pass 1
        _ai(_SC_EMERGENCY),   # collect turn 1 pass 2 (triage_only)
    ]

    mock = MagicMock()
    mock.ainvoke = AsyncMock(side_effect=responses)

    _LLM_TARGETS = [
        "src.graph.nodes.symptom_collector.get_llm",
        "src.graph.nodes.urgency_assessor.get_llm",
        "src.graph.nodes.department_router.get_llm",
        "src.graph.nodes.response_composer.get_llm",
    ]
    with ExitStack() as stack:
        for target in _LLM_TARGETS:
            stack.enter_context(patch(target, return_value=mock))
        yield mock


# ── App Client ────────────────────────────────────────────────────────────────

@pytest.fixture()
def client(mock_mcp, mock_vector_store):
    """
    FastAPI TestClient with MCP and vector store mocked.
    Startup event creates the test DB and seeds the default admin.
    """
    from src.api.main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ── Auth Helpers ──────────────────────────────────────────────────────────────

@pytest.fixture()
def admin_token(client):
    """Login as the auto-seeded admin and return the Bearer token."""
    resp = client.post("/api/v1/auth/login", json={
        "email": "admin@cityhospital.com",
        "password": "Admin@123",
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture()
def nurse_user(client):
    """Create a Cardiology nurse in the test DB and return credentials."""
    from src.database.repository import create_nurse_user
    pw_hash = bcrypt.hashpw(b"Nurse@123", bcrypt.gensalt()).decode()
    create_nurse_user(
        email="nurse.cardio@test.com",
        password_hash=pw_hash,
        full_name="Test Cardiology Nurse",
        department="Cardiology",
        role="nurse",
    )
    return {
        "email": "nurse.cardio@test.com",
        "password": "Nurse@123",
        "department": "Cardiology",
    }


@pytest.fixture()
def nurse_token(client, nurse_user):
    """Login as the test nurse and return the Bearer token."""
    resp = client.post("/api/v1/auth/login", json={
        "email": nurse_user["email"],
        "password": nurse_user["password"],
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


# ── Booking Helpers ───────────────────────────────────────────────────────────

@pytest.fixture()
def sample_booking_payload():
    """A valid booking request body."""
    return {
        "session_id": "test-session-booking-001",
        "department": "General Medicine",
        "doctor_id": "dr_test_001",
        "doctor_name": "Dr. Test Doctor",
        "doctor_specialization": "General Physician",
        "slot_id": "dr_test_001_2026-05-01_09:00",
        "slot_date": "2026-05-01",
        "slot_time": "09:00",
        "slot_label": "Morning – 9:00 AM",
        "patient_name": "Test Patient",
        "patient_email": "patient@test.com",
        "patient_phone": "0300-1234567",
    }
