import uuid
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from src.models.schemas import ChatRequest
from src.graph.builder import get_compiled_graph

router = APIRouter()


async def _stream_graph(session_id: str, message: str, age_group: str | None):
    """
    Run the triage graph and stream SSE events to the client.
    Each event is a JSON line prefixed with 'data: '.
    """
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": session_id}}

    initial_input = {
        "messages": [HumanMessage(content=message)],
        "session_id": session_id,
        "patient_age_group": age_group,
    }

    # Track whether triage actually completed in THIS invocation
    triage_completed = False

    async for event in graph.astream_events(initial_input, config=config, version="v2"):
        kind = event.get("event")
        name = event.get("name", "")

        # Stream token-by-token ONLY from the final response composer.
        # collect_symptoms uses llm.invoke() which also fires on_chat_model_stream
        # but its output is raw JSON — we emit the clean message via on_chain_end instead.
        if kind == "on_chat_model_stream":
            node_name = event.get("metadata", {}).get("langgraph_node", "")
            if node_name == "compose_response":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"

        elif kind == "on_chain_end":
            if name == "collect_symptoms":
                # Emit the clean patient-facing message extracted by the node
                # (works for both normal LLM responses and gibberish rejections)
                output = event.get("data", {}).get("output", {}) or {}
                msgs = output.get("messages", [])
                if msgs:
                    last = msgs[-1]
                    content = last.content if hasattr(last, "content") else str(last)
                    if content:
                        yield f"data: {json.dumps({'type': 'message', 'content': content})}\n\n"

            elif name in ("compose_response", "emergency_node"):
                triage_completed = True

    # Only emit triage_complete if triage actually ran this invocation
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
        except Exception:
            pass

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
