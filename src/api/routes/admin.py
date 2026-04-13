from fastapi import APIRouter, Query
from src.database.repository import get_recent_sessions, get_stats

router = APIRouter()


@router.get("/admin/audit-logs")
def list_audit_logs(limit: int = Query(default=50, le=200)):
    """Return recent triage audit records for the admin dashboard."""
    records = get_recent_sessions(limit=limit)
    # Sanitize for API response (datetime → str)
    safe = []
    for r in records:
        r_copy = dict(r)
        for k, v in r_copy.items():
            if hasattr(v, "isoformat"):
                r_copy[k] = v.isoformat()
        safe.append(r_copy)
    return {"records": safe, "count": len(safe)}


@router.get("/admin/stats")
def get_triage_stats():
    """Return aggregate statistics about triage sessions."""
    return get_stats()
