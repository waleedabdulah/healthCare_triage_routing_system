"""
MCP client used by LangGraph nodes to call MCP tools.
Uses stdio transport — spawns the MCP server as a subprocess.

For simplicity in Phase 1, this client directly calls the tool functions
rather than spawning a subprocess. Swap to real stdio MCP client for production.
"""
from src.mcp.tools.wait_time_tool import get_er_wait_time, get_opd_wait_time
from src.mcp.tools.audit_tool import mcp_write_audit_record, mcp_get_session_history
from src.mcp.tools.department_tool import get_department_info
from src.mcp.tools.alert_tool import send_emergency_alert
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

# Tool registry — maps tool name to callable
TOOL_REGISTRY = {
    "get_er_wait_time": lambda _: get_er_wait_time(),
    "get_opd_wait_time": lambda args: get_opd_wait_time(args.get("department", "General Medicine")),
    "write_audit_record": lambda args: mcp_write_audit_record(args.get("payload", {})),
    "get_session_history": lambda args: mcp_get_session_history(args.get("session_id", "")),
    "get_department_info": lambda args: get_department_info(args.get("department", "General Medicine")),
    "send_emergency_alert": lambda args: send_emergency_alert(
        args.get("session_id", ""), args.get("symptoms", [])
    ),
}


class MCPClient:
    """
    Direct-call MCP client (Phase 1 — in-process).
    In production: replace call_tool with real MCP stdio client call.
    """

    async def call_tool(self, tool_name: str, args: dict) -> dict:
        """Call a registered MCP tool by name with given args."""
        if tool_name not in TOOL_REGISTRY:
            logger.error(f"Unknown MCP tool: {tool_name}")
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            result = TOOL_REGISTRY[tool_name](args)
            return result if isinstance(result, dict) else {"result": result}
        except Exception as e:
            logger.error(f"MCP tool '{tool_name}' failed: {e}")
            return {"error": str(e)}


@lru_cache()
def get_mcp_client() -> MCPClient:
    return MCPClient()
