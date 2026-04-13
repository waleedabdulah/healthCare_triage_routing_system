from src.models.state import TriageState
from src.mcp.client import get_mcp_client
import logging

logger = logging.getLogger(__name__)

# Fallback wait times when MCP is unavailable
FALLBACK_WAIT_TIMES = {
    "Emergency Room": {"minutes": 0, "slot": "Immediate"},
    "Cardiology": {"minutes": 45, "slot": "Next available"},
    "Neurology": {"minutes": 60, "slot": "Next available"},
    "ENT": {"minutes": 35, "slot": "Next available"},
    "Dermatology": {"minutes": 120, "slot": "Next available"},
    "Gastroenterology": {"minutes": 50, "slot": "Next available"},
    "Pulmonology": {"minutes": 40, "slot": "Next available"},
    "Orthopedics": {"minutes": 55, "slot": "Next available"},
    "General Medicine": {"minutes": 30, "slot": "Next available"},
    "Pediatrics": {"minutes": 25, "slot": "Next available"},
}


async def wait_time_node(state: TriageState) -> dict:
    """Fetch estimated wait times via MCP tools."""
    department = state.get("routed_department", "General Medicine")
    urgency = state.get("urgency_level", "NON_URGENT")

    try:
        client = get_mcp_client()

        if urgency == "EMERGENCY" or department == "Emergency Room":
            result = await client.call_tool("get_er_wait_time", {})
            return {
                "estimated_wait_minutes": result.get("wait_minutes", 0),
                "next_available_slot": "Immediate",
            }
        else:
            result = await client.call_tool("get_opd_wait_time", {"department": department})
            return {
                "estimated_wait_minutes": result.get("wait_minutes", 30),
                "next_available_slot": result.get("next_slot", "Next available"),
            }

    except Exception as e:
        logger.warning(f"MCP wait time fetch failed: {e} — using fallback values")
        fallback = FALLBACK_WAIT_TIMES.get(department, {"minutes": 30, "slot": "Next available"})
        return {
            "estimated_wait_minutes": fallback["minutes"],
            "next_available_slot": fallback["slot"],
        }
