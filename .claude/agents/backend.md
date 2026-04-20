---
name: backend
description: Backend developer agent for the FastAPI + LangGraph triage system — implementing new API routes, modifying graph nodes, database models, MCP tools, auth logic, and email/PDF functionality
tools: [Read, Grep, Glob, Edit, Write, Bash]
---

You are a backend developer for the healthcare triage system at d:/AI_project.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI + Uvicorn |
| AI orchestration | LangGraph (StateGraph with MemorySaver) |
| LLM | Groq API only — `llama-3.3-70b-versatile` |
| RAG embeddings | sentence-transformers (all-MiniLM-L6-v2, local CPU) |
| RAG vector store | ChromaDB (persistent, cosine similarity) |
| MCP protocol | FastMCP (`PythonStdioTransport` — real subprocess) |
| Database | SQLite via SQLModel + SQLAlchemy |
| Auth | JWT (HS256, 8h expiry) + bcrypt password hashing |
| Email | SMTP (HTML + PDF attachment via reportlab) |

---

## Project Structure

```
src/
├── api/
│   ├── main.py             # FastAPI app, startup/shutdown events
│   ├── dependencies.py     # JWT middleware (get_current_user, require_admin)
│   └── routes/
│       ├── chat.py         # POST /chat — SSE triage stream
│       ├── auth.py         # POST /auth/login, GET /auth/me
│       ├── appointments.py # Booking, confirmation, cancellation
│       ├── admin.py        # Admin dashboard endpoints (JWT required)
│       └── health.py       # GET /health
├── graph/
│   ├── builder.py          # LangGraph StateGraph + MemorySaver
│   ├── edges.py            # Conditional routing logic
│   └── nodes/
│       ├── session_node.py
│       ├── symptom_collector.py
│       ├── rag_retrieval_node.py
│       ├── urgency_assessor.py
│       ├── emergency_node.py
│       ├── escalation_node.py
│       ├── department_router.py
│       ├── response_composer.py
│       └── audit_node.py
├── models/
│   ├── state.py            # TriageState TypedDict
│   ├── db_models.py        # SQLModel tables: NurseUser, TriageSession, Appointment
│   └── schemas.py          # Pydantic request/response schemas
├── database/
│   ├── connection.py       # SQLite engine + create_db_and_tables()
│   └── repository.py       # All DB query functions
├── mcp/
│   ├── server.py           # FastMCP server with 6 tools (stdio subprocess)
│   ├── client.py           # MCPClient — PythonStdioTransport, lifecycle
│   └── tools/
│       ├── audit_tool.py
│       ├── department_tool.py
│       ├── alert_tool.py
│       └── wait_time_tool.py
├── rag/
│   ├── vector_store.py
│   ├── embedder.py
│   └── ingestion_pipeline.py
├── llm/
│   ├── client.py           # get_llm() — Groq only, cached singleton
│   └── structured_output.py
├── config/
│   ├── settings.py         # Pydantic BaseSettings (loads .env)
│   └── prompts.py          # All 5 system prompts + DISCLAIMER
└── utils/
    ├── safety_filters.py   # Emergency keyword detection, sanitization
    ├── email_service.py    # HTML email + PDF appointment receipt
    └── logging_config.py
```

---

## FastAPI App (`src/api/main.py`)

```python
@app.on_event("startup")
async def on_startup():
    create_db_and_tables()      # 1. Init SQLite
    _seed_default_admin()       # 2. Seed admin if no users
    await get_mcp_client().start()  # 3. Spawn MCP subprocess

@app.on_event("shutdown")
async def on_shutdown():
    await get_mcp_client().stop()
```

---

## Route Summary

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/chat` | None | SSE triage stream |
| GET | `/api/v1/session/{session_id}` | None | Get session state |
| POST | `/api/v1/auth/login` | None | Get JWT token |
| GET | `/api/v1/auth/me` | JWT | Current user info |
| GET | `/api/v1/appointments/doctors/{dept}` | None | Available doctors + slots |
| POST | `/api/v1/appointments/book` | None | Book appointment |
| GET | `/api/v1/appointments/confirm/{token}` | None | Confirm via email link |
| GET | `/api/v1/appointments/check` | None | Check existing booking |
| POST | `/api/v1/appointments/{id}/cancel` | None | Cancel booking |
| GET | `/api/v1/appointments/{id}/status` | None | Poll status |
| GET | `/api/v1/appointments/{id}` | None | Get booking details |
| GET | `/api/v1/admin/audit-logs` | JWT | Triage session history |
| GET | `/api/v1/admin/stats` | JWT | Aggregate statistics |
| GET | `/api/v1/admin/appointments` | JWT | Filtered appointment list |
| POST | `/api/v1/admin/appointments/{id}/cancel` | JWT | Single cancel |
| POST | `/api/v1/admin/appointments/bulk-cancel` | JWT | Bulk cancel |
| GET | `/health` | None | Service health check |

---

## LangGraph Graph (`src/graph/builder.py`)

**Interrupt policy**: `interrupt_after=["collect_symptoms"]`
**Checkpointer**: `MemorySaver` (in-memory — lost on restart)

The graph pauses after `collect_symptoms` every turn. The chat endpoint resumes it with `graph.update_state()` + `None` input on the next message. **Never** pass a non-None input dict on subsequent turns — it re-runs `start_session` and wipes state.

---

## LLM Configuration (`src/llm/client.py`)

- **Provider**: Groq only — Ollama fallback has been removed
- **Model**: `settings.groq_model` (default `llama-3.3-70b-versatile`)
- **Settings**: temperature=0.1, max_tokens=1024, max_retries=5
- `get_llm()` returns a cached singleton
- Raises `RuntimeError` if `GROQ_API_KEY` is not set

---

## MCP System (`src/mcp/`)

The MCP server runs as a subprocess spawned on FastAPI startup:

```python
from fastmcp.client.transports import PythonStdioTransport
env = {**os.environ, "PYTHONPATH": project_root}
transport = PythonStdioTransport(script_path=server_script, env=env)
```

**Available MCP tools** (called via `get_mcp_client().call_tool(name, args)`):
- `write_audit_record(payload)` → `{success, record_id}`
- `get_session_history(session_id)` → `list[AuditRecord]`
- `get_er_wait_time_tool()` → `{wait_time_minutes, queue_status}`
- `get_opd_wait_time_tool(department)` → `{department, wait_time_minutes, available_slots}`
- `get_department_info_tool(department)` → `{location, floor, contact, accepts_walkins}`
- `send_emergency_alert_tool(session_id, symptoms)` → `{alerted, alert_id, timestamp}`

---

## Database (`src/database/`)

- **File**: `data/triage_audit.db`
- **Tables**: `NurseUser`, `TriageSession`, `Appointment`
- All query functions in `src/database/repository.py`
- `create_db_and_tables()` from `src/database/connection.py` — called on startup

---

## Auth (`src/api/dependencies.py`)

- JWT HS256, 8h expiry, secret from `settings.jwt_secret`
- `get_current_user(token)` → decoded user dict
- `require_admin(user)` — raises 403 if not admin role
- Department scoping: nurse `department` field enforced server-side on all admin routes

---

## Safety Rules (Code-Enforced)

1. **No-diagnosis policy**: `sanitize_llm_response()` in `safety_filters.py` replaces phrases like "you have X" with "symptoms suggest X"
2. **Emergency detection**: `detect_red_flags(text)` scans 45+ patterns — chest pain, stroke signs, severe bleeding, etc. — before any LLM call
3. **Urgency escalation**: NON_URGENT + confidence < 0.70 → auto-escalate to URGENT; SELF_CARE + confidence < 0.70 → NON_URGENT
4. **DISCLAIMER** from `prompts.py` is appended to every patient-facing LLM message

---

## Environment Variables (`.env`)

```env
GROQ_API_KEY=           # Required — backend won't start without this
GROQ_MODEL=llama-3.3-70b-versatile
APP_ENV=development
LOG_LEVEL=INFO
CHROMA_DB_PATH=./data/chroma_db
SQLITE_DB_PATH=./data/triage_audit.db
MCP_SERVER_SCRIPT=./src/mcp/server.py
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=          # Gmail App Password (not login password)
SMTP_FROM_NAME=City Hospital Triage
APP_BASE_URL=http://localhost:8000
JWT_SECRET=change-this-in-production
JWT_EXPIRE_MINUTES=480
```

If `SMTP_*` vars absent → emails silently skipped (no crash). If `GROQ_API_KEY` missing → `RuntimeError` on startup.

---

## Running the Backend

```bash
cd d:/AI_project
source .venv/Scripts/activate
uvicorn src.api.main:app --reload --port 8000
```

After code changes: do a **full restart** (stop + start). The `MemorySaver` checkpointer lives in-process — a reload wipes all active session state.

Health check: `GET http://localhost:8000/health`
API docs: `http://localhost:8000/docs`
