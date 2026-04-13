import json
from langchain_core.messages import HumanMessage, AIMessage
from src.models.state import TriageState
from src.mcp.client import get_mcp_client
import logging

logger = logging.getLogger(__name__)


async def audit_node(state: TriageState) -> dict:
    """Write the triage session audit record via MCP tool."""
    session_id = state.get("session_id", "unknown")

    # Serialize conversation messages
    messages = state.get("messages", [])
    convo = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            convo.append({"role": "patient", "content": msg.content})
        elif isinstance(msg, AIMessage):
            convo.append({"role": "assistant", "content": msg.content})

    # Serialize RAG chunks used (IDs only for traceability)
    rag_chunks = state.get("rag_context", [])
    rag_ids = [c.get("id", "unknown") for c in rag_chunks]

    payload = {
        "session_id": session_id,
        "age_group": state.get("patient_age_group"),
        "gender": state.get("patient_gender"),
        "symptoms_extracted": json.dumps(state.get("extracted_symptoms", [])),
        "red_flags": json.dumps(state.get("red_flags_detected", [])),
        "urgency_level": state.get("urgency_level"),
        "urgency_confidence": state.get("urgency_confidence"),
        "urgency_reasoning": state.get("urgency_reasoning"),
        "routed_department": state.get("routed_department"),
        "routing_reasoning": state.get("routing_reasoning"),
        "rag_chunks_used": json.dumps(rag_ids),
        "estimated_wait_minutes": state.get("estimated_wait_minutes"),
        "emergency_flag": state.get("urgency_level") == "EMERGENCY",
        "human_review_flag": state.get("human_review_flag", False),
        "llm_model_used": state.get("llm_model_used"),
        "conversation_turns": state.get("conversation_turns", 0),
        "full_conversation": json.dumps(convo),
    }

    try:
        client = get_mcp_client()
        result = await client.call_tool("write_audit_record", {"payload": payload})
        logger.info(f"Audit record written: {result.get('record_id')}")

        # Send emergency alert via MCP if needed
        if payload["emergency_flag"]:
            await client.call_tool("send_emergency_alert", {
                "session_id": session_id,
                "symptoms": state.get("extracted_symptoms", []),
            })

    except Exception as e:
        logger.error(f"audit_node MCP call failed: {e}")

    return {"audit_written": True}
