"""
MCP client used by LangGraph nodes to call MCP tools.
Uses stdio transport — spawns server.py as a subprocess and communicates
over stdin/stdout using the real MCP protocol via FastMCP Client.

Lifecycle:
  - Call get_mcp_client().start() once on app startup (on_startup event)
  - Call get_mcp_client().stop() once on app shutdown (on_shutdown event)
"""
import json
import logging
import os
from pathlib import Path
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class MCPClient:
    """
    Async MCP client that communicates with server.py over a real stdio subprocess.
    The subprocess stays alive for the lifetime of the application.
    """

    def __init__(self, server_script: str):
        self._server_script = str(Path(server_script).resolve())
        # Project root is 3 levels up: project/src/mcp/server.py
        self._project_root = str(Path(self._server_script).parent.parent.parent)
        self._client: Client | None = None

    async def start(self):
        """Spawn the MCP server subprocess and open the connection."""
        # Inherit the full parent environment, then ensure the project root is on
        # PYTHONPATH so the subprocess can resolve `src.*` imports.
        env = {**os.environ}
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            f"{self._project_root}{os.pathsep}{existing}" if existing else self._project_root
        )

        transport = PythonStdioTransport(
            script_path=self._server_script,
            env=env,
            # python_cmd defaults to the current venv Python — no override needed
        )
        self._client = Client(transport)
        await self._client.__aenter__()
        logger.info(f"MCP server subprocess started: {self._server_script}")

    async def stop(self):
        """Shut down the MCP server subprocess cleanly."""
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None
            logger.info("MCP server subprocess stopped")

    async def call_tool(self, tool_name: str, args: dict) -> dict:
        """
        Call a tool via MCP protocol.
        FastMCP returns List[TextContent]; tool results are JSON in result[0].text.
        Returns parsed dict, or {"error": ...} on failure.
        """
        if self._client is None:
            logger.error("MCP client not started — call start() on app startup")
            return {"error": "MCP client not initialized"}
        try:
            result = await self._client.call_tool(tool_name, args)
            if result and hasattr(result[0], "text"):
                return json.loads(result[0].text)
            return {}
        except Exception as e:
            logger.error(f"MCP tool call failed [{tool_name}]: {e}")
            return {"error": str(e)}


_mcp_client: MCPClient | None = None


def get_mcp_client() -> MCPClient:
    global _mcp_client
    if _mcp_client is None:
        settings = get_settings()
        _mcp_client = MCPClient(settings.mcp_server_script)
    return _mcp_client
