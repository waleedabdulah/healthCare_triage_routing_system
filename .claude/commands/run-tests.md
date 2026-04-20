Run the end-to-end pytest test suite for the healthcare triage system.

$ARGUMENTS

Each test gets its own isolated SQLite DB — the backend does NOT need to be running.

Determine the test filter from $ARGUMENTS:
- If argument is empty → run full suite
- If argument contains "triage" → filter: `test_triage_flow`
- If argument contains "booking" → filter: `test_booking_flow`
- If argument contains "auth" → filter: `test_auth_flow`
- If argument contains "admin" or "bulk" → filter: `test_admin_flow`
- Otherwise → use $ARGUMENTS directly as `-k` filter expression

Run the full suite (no filter):
```bash
cd d:/AI_project && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short
```

Run with a filter (replace FILTER with the resolved filter name):
```bash
cd d:/AI_project && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short -k "FILTER"
```

After the run, summarise:
- Total passed / failed / errors
- Which test classes failed (if any) and the first error message
- If all pass: confirm all 6 flows are green

**Flow coverage reminder:**
| File | Flows |
|---|---|
| `test_triage_flow.py` | Flow 1 (non-emergency 4-turn) + Flow 2 (emergency bypass) |
| `test_booking_flow.py` | Flow 3 (email confirmation) + Flow 4 (double-booking prevention) |
| `test_auth_flow.py` | Flow 5 (admin auth + department scoping) |
| `test_admin_flow.py` | Flow 6 (bulk cancel) |

**Notes:**
- MCP subprocess is mocked — no real subprocess spawned
- LLM (Groq) is mocked — no API calls, no key needed
- ChromaDB is mocked — no vector store needed
- SMTP is disabled — no real emails sent
- Each test gets a fresh SQLite in `tmp_path` (pytest built-in)
