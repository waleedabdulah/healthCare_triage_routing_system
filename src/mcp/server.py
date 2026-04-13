"""
FastMCP server — all triage system tools.
Transport: stdio (runs as subprocess from the backend process).

Start manually: python src/mcp/server.py
"""
from fastmcp import FastMCP
from src.mcp.tools.wait_time_tool import get_er_wait_time, get_opd_wait_time
from src.mcp.tools.audit_tool import mcp_write_audit_record, mcp_get_session_history
from src.mcp.tools.department_tool import get_department_info
from src.mcp.tools.alert_tool import send_emergency_alert
from src.database.connection import create_db_and_tables

# Initialize DB on server startup
create_db_and_tables()

mcp = FastMCP("healthcare-triage")


@mcp.tool()
def get_er_wait_time_tool() -> dict:
    """Returns current Emergency Room estimated wait time and queue status."""
    return get_er_wait_time()


@mcp.tool()
def get_opd_wait_time_tool(department: str) -> dict:
    """
    Returns estimated OPD wait time for the specified department.
    Args:
        department: Department name (e.g. 'Cardiology', 'ENT', 'General Medicine')
    """
    return get_opd_wait_time(department)


@mcp.tool()
def write_audit_record(payload: dict) -> dict:
    """
    Writes a triage session audit record to the SQLite database.
    Args:
        payload: Audit payload dict containing session_id, symptoms, urgency, etc.
    """
    return mcp_write_audit_record(payload)


@mcp.tool()
def get_session_history(session_id: str) -> list:
    """
    Returns all audit records for a given session ID.
    Args:
        session_id: The session identifier
    """
    return mcp_get_session_history(session_id)


@mcp.tool()
def get_department_info_tool(department: str) -> dict:
    """
    Returns location, floor, and contact information for a hospital department.
    Args:
        department: Department name
    """
    return get_department_info(department)


@mcp.tool()
def send_emergency_alert_tool(session_id: str, symptoms: list) -> dict:
    """
    Sends an emergency alert for a session with critical symptoms.
    Args:
        session_id: The session identifier
        symptoms: List of symptom strings
    """
    return send_emergency_alert(session_id, symptoms)


if __name__ == "__main__":
    mcp.run(transport="stdio")
