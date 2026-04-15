import uuid
import json
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from src.models.schemas import ChatRequest
from src.graph.builder import get_compiled_graph
from src.graph.edges import route_after_collection

router = APIRouter()
logger = logging.getLogger(__name__)


def _should_proceed_to_triage(sv: dict) -> bool:
    """Mirror route_after_collection logic to decide if triage pipeline should run now."""
    return bool(
        sv.get("red_flags_detected")
        or sv.get("ready_for_triage")
        or len(sv.get("extracted_symptoms", [])) >= 2
        or sv.get("conversation_turns", 0) >= (6 if sv.get("extracted_symptoms") else 8)
    )


async def _run_pass(graph, config: dict, input_data, triage_only: bool = False):
    """
    Run one astream_events pass and yield SSE events.
    Returns (triage_completed: bool) via a mutable container so the caller can read it.
    This is a generator — yields SSE strings and finally yields a sentinel dict.
    """
    triage_completed = False

    async for event in graph.astream_events(input_data, config=config, version="v2"):
        kind = event.get("event")
        name = event.get("name", "")

        if kind == "on_chat_model_stream":
            node_name = event.get("metadata", {}).get("langgraph_node", "")
            if node_name == "compose_response":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"

        elif kind == "on_chain_end":
            logger.debug(f"on_chain_end: name={name!r}")

            if name == "collect_symptoms" and not triage_only:
                output = event.get("data", {}).get("output", {}) or {}
                # Suppress the collect_symptoms message when triage is firing
                # immediately — the LLM reply at that turn is just the internal
                # "ready" marker, not a real patient-facing question.
                if output.get("ready_for_triage"):
                    pass
                else:
                    msgs = output.get("messages", [])
                    if msgs:
                        last = msgs[-1]
                        content = last.content if hasattr(last, "content") else str(last)
                        if content:
                            yield f"data: {json.dumps({'type': 'message', 'content': content})}\n\n"

            elif name in ("compose_response", "emergency_node"):
                triage_completed = True

    # Yield a sentinel so caller can read triage_completed
    yield {"__triage_completed__": triage_completed}


async def _stream_graph(session_id: str, message: str, age_group: str | None):
    """
    Run the triage graph and stream SSE events to the client.

    Because the graph uses interrupt_after=["collect_symptoms"], each API call
    normally only runs collect_symptoms and then pauses.  When the LLM signals
    ready_for_triage (or the turn guardrail fires), we immediately resume the
    graph in a second astream_events pass so the triage result arrives in the
    same HTTP response — no extra user message needed.
    """
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": session_id}}

    initial_input = {
        "messages": [HumanMessage(content=message)],
        "session_id": session_id,
        "patient_age_group": age_group,
    }

    triage_completed = False

    # ── Pass 1: collect_symptoms turn ────────────────────────────────────────
    async for item in _run_pass(graph, config, initial_input, triage_only=False):
        if isinstance(item, dict) and "__triage_completed__" in item:
            triage_completed = item["__triage_completed__"]
        else:
            yield item

    logger.info(f"Pass 1 done — triage_completed={triage_completed}")

    # ── Pass 2: triage pipeline (if collect_symptoms finished collecting) ────
    if not triage_completed:
        try:
            snapshot = graph.get_state(config)
            sv = snapshot.values if snapshot else {}
            if _should_proceed_to_triage(sv):
                logger.info("Proceeding to triage pipeline (pass 2)")
                async for item in _run_pass(graph, config, None, triage_only=True):
                    if isinstance(item, dict) and "__triage_completed__" in item:
                        triage_completed = item["__triage_completed__"]
                    else:
                        yield item
                logger.info(f"Pass 2 done — triage_completed={triage_completed}")
        except Exception as e:
            logger.error(f"Triage pipeline pass failed: {e}")

    # ── Emit triage_complete ─────────────────────────────────────────────────
    if triage_completed:
        try:
            state = graph.get_state(config)
            if state and state.values:
                sv = state.values
                result = {
                    "type": "triage_complete",
                    "session_id": session_id,
                    "urgency_level": sv.get("urgency_level"),
                    "routed_department": sv.get("routed_department"),
                    "estimated_wait_minutes": sv.get("estimated_wait_minutes"),
                    "next_available_slot": sv.get("next_available_slot"),
                    "final_response": sv.get("final_response"),
                    "is_emergency": sv.get("urgency_level") == "EMERGENCY",
                }
                yield f"data: {json.dumps(result)}\n\n"
            else:
                logger.error("get_state() returned no values after triage_completed=True")
        except Exception as e:
            logger.error(f"get_state() failed: {e}")

    yield "data: [DONE]\n\n"


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Main chat endpoint — streams triage graph output as SSE.
    Client consumes 'data: ...' events line by line.
    """
    session_id = request.session_id or str(uuid.uuid4())

    return StreamingResponse(
        _stream_graph(session_id, request.message, request.age_group),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Return current state of an active session."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": session_id}}
    try:
        state = graph.get_state(config)
        if state and state.values:
            sv = state.values
            return {
                "session_id": session_id,
                "urgency_level": sv.get("urgency_level"),
                "routed_department": sv.get("routed_department"),
                "estimated_wait_minutes": sv.get("estimated_wait_minutes"),
                "conversation_turns": sv.get("conversation_turns", 0),
                "audit_written": sv.get("audit_written", False),
            }
    except Exception:
        pass
    return {"session_id": session_id, "status": "not_found"}
