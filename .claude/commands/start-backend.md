Start the FastAPI backend server for the healthcare triage system.

First, check that the `.env` file exists:
```bash
ls d:/AI_project/.env
```

If `.env` is missing, warn the user — the backend requires `GROQ_API_KEY` and will raise a `RuntimeError` without it.

Then start the backend:
```bash
cd d:/AI_project && source .venv/Scripts/activate && uvicorn src.api.main:app --reload --port 8000
```

Remind the user:
- Backend runs at http://localhost:8000
- Health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs
- On startup: (1) creates SQLite tables at `data/triage_audit.db`, (2) seeds default admin if no users exist (`admin@cityhospital.com` / `Admin@123`), (3) spawns MCP server subprocess from `src/mcp/server.py`
- **After code changes**: do a full stop + restart — do NOT rely on `--reload` alone. The `MemorySaver` checkpointer is in-process; a hot-reload wipes all active session state.
- If startup fails with `RuntimeError`: check `GROQ_API_KEY` is set in `.env`
- Ollama support has been removed — Groq is the only LLM provider
