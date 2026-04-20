"""
Flow 1 — Full Non-Emergency Triage (Happy Path)
Flow 2 — Emergency Bypass (no checklist)
=================================================
Flow 1 turn sequence:
  Turn 1: patient sends symptoms         → SSE message event (asks for duration)
  Turn 2: patient sends duration         → SSE message event (asks for more symptoms)
  Turn 3: patient sends any message      → SSE options event (checklist shown)
  Turn 4: patient submits checklist      → SSE message + triage_complete events

Flow 2 turn sequence:
  Turn 1: patient sends emergency phrase → SSE message + triage_complete (EMERGENCY)
           checklist is NEVER shown
"""
import uuid
import pytest
from tests.conftest import parse_sse


SESSION = str(uuid.uuid4())


class TestFullNonEmergencyTriage:
    """Flow 1 — happy path with checklist."""

    def _chat(self, client, session_id: str, message: str) -> list[dict]:
        resp = client.post("/api/v1/chat", json={
            "session_id": session_id,
            "message": message,
            "age_group": "adult",
        })
        assert resp.status_code == 200
        return parse_sse(resp.text)

    def test_full_triage_flow(self, client, mock_llm_triage):
        session_id = str(uuid.uuid4())

        # ── Turn 1: patient describes symptoms ───────────────────────────────
        events_t1 = self._chat(client, session_id, "I have a headache and fever")
        types_t1 = [e["type"] for e in events_t1]
        assert "message" in types_t1, "Turn 1 should emit a message event"
        assert "options" not in types_t1, "Turn 1 should NOT show checklist"
        assert "triage_complete" not in types_t1

        # ── Turn 2: patient gives duration ────────────────────────────────────
        events_t2 = self._chat(client, session_id, "For about 2 days")
        types_t2 = [e["type"] for e in events_t2]
        assert "message" in types_t2, "Turn 2 should emit a message event"
        assert "options" not in types_t2, "Checklist should not fire yet (no 'any other symptoms' turn)"
        assert "triage_complete" not in types_t2

        # ── Turn 3: any reply triggers the impact checklist ───────────────────
        events_t3 = self._chat(client, session_id, "No other symptoms")
        types_t3 = [e["type"] for e in events_t3]
        assert "options" in types_t3, "Turn 3 must emit the impact checklist options event"
        assert "triage_complete" not in types_t3, "No triage yet while checklist is pending"

        # Verify the options event structure
        options_event = next(e for e in events_t3 if e["type"] == "options")
        assert "question" in options_event
        assert isinstance(options_event["options"], list)
        assert len(options_event["options"]) == 7
        assert options_event["multi_select"] is True

        # ── Turn 4: patient submits checklist ─────────────────────────────────
        checklist_response = "My symptoms are getting worse, I cannot carry out my normal daily activities"
        events_t4 = self._chat(client, session_id, checklist_response)
        types_t4 = [e["type"] for e in events_t4]

        assert "message" in types_t4, "Turn 4 should confirm checklist receipt"
        assert "triage_complete" in types_t4, "Turn 4 must emit triage_complete"

        triage_event = next(e for e in events_t4 if e["type"] == "triage_complete")
        assert triage_event["urgency_level"] == "NON_URGENT"
        assert triage_event["routed_department"] == "General Medicine"
        assert triage_event["is_emergency"] is False
        assert triage_event["final_response"] is not None
        assert triage_event["session_id"] == session_id

    def test_triage_writes_audit_record_to_db(self, client, mock_llm_triage):
        """After a completed triage, the MCP client must have been called to write the audit."""
        import src.mcp.client as mcp_module
        mock_client = mcp_module._mcp_client

        session_id = str(uuid.uuid4())
        self._chat(client, session_id, "I have a headache and fever")
        self._chat(client, session_id, "2 days")
        self._chat(client, session_id, "Nothing else")
        self._chat(client, session_id, "My symptoms are getting worse")

        # The audit_node calls call_tool("write_audit_record", ...)
        assert mock_client.call_tool.called
        call_args = mock_client.call_tool.call_args_list
        tool_names = [c.args[0] for c in call_args if c.args]
        assert "write_audit_record" in tool_names

    def test_session_state_endpoint_reflects_triage_result(self, client, mock_llm_triage):
        """GET /session/{id} returns the urgency and department after triage."""
        session_id = str(uuid.uuid4())
        self._chat(client, session_id, "I have a headache and fever")
        self._chat(client, session_id, "2 days")
        self._chat(client, session_id, "Nothing else")
        self._chat(client, session_id, "My symptoms are getting worse")

        resp = client.get(f"/api/v1/session/{session_id}")
        assert resp.status_code == 200
        state = resp.json()
        assert state["urgency_level"] == "NON_URGENT"
        assert state["routed_department"] == "General Medicine"


class TestEmergencyBypass:
    """Flow 2 — emergency keywords skip the checklist entirely."""

    def _chat(self, client, session_id: str, message: str) -> list[dict]:
        resp = client.post("/api/v1/chat", json={
            "session_id": session_id,
            "message": message,
            "age_group": "adult",
        })
        assert resp.status_code == 200
        return parse_sse(resp.text)

    def test_emergency_keywords_trigger_immediate_routing(self, client, mock_llm_emergency):
        """Chest pain + difficulty breathing must produce EMERGENCY on turn 1."""
        session_id = str(uuid.uuid4())
        events = self._chat(
            client, session_id,
            "I have severe chest pain and I can't breathe properly"
        )
        types = [e["type"] for e in events]

        assert "options" not in types, "Checklist must NOT appear for emergency symptoms"
        assert "triage_complete" in types, "triage_complete must fire immediately"

        triage_event = next(e for e in events if e["type"] == "triage_complete")
        assert triage_event["urgency_level"] == "EMERGENCY"
        assert triage_event["is_emergency"] is True
        assert triage_event["routed_department"] == "Emergency Room"

    def test_emergency_response_contains_final_message(self, client, mock_llm_emergency):
        """The triage_complete event for emergencies must have a final_response."""
        session_id = str(uuid.uuid4())
        events = self._chat(
            client, session_id,
            "I'm having chest tightness and difficulty breathing"
        )
        triage_event = next(e for e in events if e["type"] == "triage_complete")
        assert triage_event["final_response"] is not None
        assert len(triage_event["final_response"]) > 10

    def test_different_emergency_phrases_all_bypass_checklist(self, client, mock_llm_emergency):
        """Multiple red-flag phrases should all produce EMERGENCY immediately."""
        phrases = [
            "I think I'm having a stroke, my face is drooping",
            "I feel unconscious and I am about to collapse",   # "unconscious" matches keyword
            "There is severe bleeding that won't stop",
        ]
        for phrase in phrases:
            # Need a fresh LLM mock for each phrase (each gets its own session).
            # Patch each node module directly — patching src.llm.client.get_llm
            # does not affect nodes that have already imported get_llm locally.
            from unittest.mock import AsyncMock, MagicMock, patch
            from contextlib import ExitStack
            from langchain_core.messages import AIMessage
            import json

            sc_resp = json.dumps({
                "message": "These are serious symptoms.",
                "symptoms": ["emergency symptom"],
                "duration": None,
                "ready_for_triage": False,
            })
            mock = MagicMock()
            mock.ainvoke = AsyncMock(side_effect=[
                AIMessage(content=sc_resp),
                AIMessage(content=sc_resp),
            ])

            _LLM_TARGETS = [
                "src.graph.nodes.symptom_collector.get_llm",
                "src.graph.nodes.urgency_assessor.get_llm",
                "src.graph.nodes.department_router.get_llm",
                "src.graph.nodes.response_composer.get_llm",
            ]
            with ExitStack() as stack:
                for target in _LLM_TARGETS:
                    stack.enter_context(patch(target, return_value=mock))
                session_id = str(uuid.uuid4())
                resp = client.post("/api/v1/chat", json={
                    "session_id": session_id,
                    "message": phrase,
                    "age_group": "adult",
                })
                assert resp.status_code == 200
                events = parse_sse(resp.text)
                types = [e["type"] for e in events]
                assert "options" not in types, f"Checklist shown for: {phrase!r}"
                assert "triage_complete" in types
                triage = next(e for e in events if e["type"] == "triage_complete")
                assert triage["urgency_level"] == "EMERGENCY", f"Not EMERGENCY for: {phrase!r}"
