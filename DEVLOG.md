# Development Log — Healthcare Triage System

## Overview

This document is a chronological journal of everything built in this project — from the initial scaffold to the final tooling. The system is an AI-powered hospital triage and appointment platform built with FastAPI, LangGraph, ChromaDB, SQLite, and two React frontends (patient-facing and nurse/admin dashboard).

---

## Phase 1 — Foundation
**Date:** 2026-04-13 · **Commit:** `6619fce`

### What was built

**Backend (FastAPI)**
- Full FastAPI application scaffold with startup/shutdown lifecycle events
- SQLite database via SQLModel — `TriageSession` (audit log) and initial `NurseUser` tables
- Health check endpoint (`GET /health`) reporting ChromaDB and SQLite status

**AI Triage Engine (LangGraph)**
- `StateGraph` with `MemorySaver` checkpointer — keyed by `session_id` as `thread_id`
- 9 graph nodes:
  - `start_session` — initialise state on first turn only
  - `symptom_collector` — conversational LLM node to gather symptoms and duration
  - `rag_retrieval` — query ChromaDB for relevant triage protocols
  - `urgency_assessor` — classify urgency (EMERGENCY / URGENT / NON_URGENT / SELF_CARE)
  - `emergency_node` — static EMERGENCY response template, no LLM
  - `escalation_node` — bump low-confidence results to URGENT
  - `department_router` — route to correct hospital department
  - `response_composer` — write patient-facing message (streams tokens)
  - `audit_node` — write triage record via MCP
- Conditional routing edges: `route_after_collection` and `route_after_urgency`
- `interrupt_after=["collect_symptoms"]` — graph pauses after each patient turn

**LLM**
- Groq API client (`llama-3.3-70b-versatile`) with `@lru_cache` singleton
- `structured_output.py` — JSON extraction from LLM text with markdown fence fallback

**RAG System**
- `sentence-transformers` (`all-MiniLM-L6-v2`) for local CPU embeddings
- ChromaDB persistent vector store (`data/chroma_db/`) with collection `triage_protocols`
- Ingestion pipeline: reads 11 markdown protocol files from `data/raw/`, chunks (~400 tokens, 75 overlap), upserts by content hash
- 11 triage protocol files added: chest pain, abdominal, respiratory, neurological, ENT, dermatology, orthopedic, pediatric, emergency red flags, self-care guide, and department symptom map

**MCP Server & Client**
- `FastMCP` server (`src/mcp/server.py`) running as a subprocess over `PythonStdioTransport`
- 6 MCP tools: `write_audit_record`, `get_session_history`, `get_er_wait_time`, `get_opd_wait_time`, `get_department_info`, `send_emergency_alert`
- `MCPClient` with `start()`/`stop()` lifecycle wired into FastAPI startup/shutdown

**Safety Layer**
- `detect_red_flags()` — 45+ hard-coded emergency keyword patterns (chest pain, stroke, seizure, severe bleeding, etc.) — run BEFORE the LLM, bypass confidence scoring
- `is_gibberish()` — reject meaningless input before touching the LLM
- `sanitize_llm_response()` — strip accidental diagnosis language from LLM output
- `DISCLAIMER` constant appended to every patient-facing message

**Config & Prompts**
- Pydantic `BaseSettings` loading `.env` with all required vars
- 5 system prompts: symptom collector, urgency assessor, department router, response composer, and triage-only variant
- All prompts explicitly forbid diagnosis language

**Patient Frontend (React, basic version)**
- React 18 + Zustand + TailwindCSS + Vite on port 5173
- `sessionStore.ts` — Zustand store with session state, messages, triage result
- `triageClient.ts` — SSE client streaming from `POST /api/v1/chat`
- Components: `ChatWindow`, `MessageBubble`, `RoutingCard`, `UrgencyBadge`, `DisclaimerBanner`

### Key technical decisions
- **LangGraph `MemorySaver` in-process** — all session state lives in memory, keyed by `session_id`. Fast, zero DB overhead. Tradeoff: state lost on restart.
- **ChromaDB HNSW index** — approximate nearest-neighbour for sub-10ms retrieval at scale.
- **MCP over `PythonStdioTransport`** — subprocess communication avoids network overhead for the audit write path; `PYTHONPATH` explicitly injected so server script resolves `src.*` imports.
- **Groq only** — Ollama was considered but removed; Groq's 70B model provides sufficient quality with lower local resource requirements.

---

## Phase 2 — Appointment Booking System
**Date:** 2026-04-14 · **Commit:** `43ec509`

### What was built

**Appointment Backend**
- `Appointment` SQLModel table with full booking lifecycle columns: `status` (pending_confirmation / confirmed / cancelled), `confirmation_token` (32-char URL-safe, 15-min expiry), `confirmation_code` (6-char hex), `slot_id` (unique constraint for double-booking prevention)
- Full `appointments.py` route file:
  - `POST /appointments/book` — creates pending appointment, fires background email task
  - `GET /appointments/confirm/{token}` — 15-min expiry check, idempotent (already_confirmed = 200)
  - `GET /appointments/{id}/status` — poll endpoint for frontend
  - `GET /appointments/{id}` — full booking details
  - `GET /appointments/doctors/{dept}` — available doctors + slots (7-day window, excludes booked)
  - `POST /appointments/{id}/cancel` — patient self-cancel
  - `GET /appointments/check` — check existing booking by session + department
- `doctors.py` data file — 14 departments × ~2 doctors each with slot schedules
- `repository.py` extended: `create_appointment`, `confirm_appointment`, `cancel_appointment_by_id`, `get_booked_slot_ids`, `get_active_appointment_for_department`

**Email System**
- `email_service.py` — full HTML email + PDF attachment via `reportlab`
- Two email types: booking confirmation (with 15-min link) and cancellation notice
- SMTP via Gmail App Password; silently skipped if `SMTP_*` vars absent

**Patient Frontend — fully built out**
- `BookingModal.tsx` — 3-step flow: department/doctor selection → slot picker → patient details form
- `RoutingCard.tsx` — redesigned with urgency colours, department info, and Book Appointment button
- `UrgencyBadge.tsx` — colour-coded EMERGENCY / URGENT / NON_URGENT / SELF_CARE
- `MessageBubble.tsx` — patient vs assistant styling
- `bookingClient.ts` — `fetchDoctors`, `submitBooking`, `fetchBookingStatus` (polls every 4s)
- `sessionStore.ts` extended — `appointmentBooked`, `pendingAppointmentId` state slices

### Key technical decisions
- **`slot_id` unique constraint** — the database-level uniqueness guarantee for double-booking prevention; no locking required.
- **Background email task** — `asyncio.create_task` fires the email send so the `/book` response returns immediately without waiting for SMTP.
- **15-minute confirmation window** — checked in `confirm_appointment()` using `(utcnow - created_at).total_seconds() > 900`; expired tokens return 410 Gone.

---

## Phase 3 — Appointment Status Fix
**Date:** 2026-04-15 · **Commit:** `8c3e3ad`

### What was fixed
- Frontend was not correctly reflecting appointment booked/confirmed status after SSE triage completion
- `ChatWindow.tsx` — refactored component structure, fixed status polling integration
- `App.tsx` — corrected routing state flow between triage result and booking
- `chat.py` — small fix to ensure triage completion event carries correct appointment context

---

## Phase 4 — Admin Dashboard
**Date:** 2026-04-15 · **Commit:** `30df1f9`

### What was built

**Auth System**
- `NurseUser` table extended with `role` (nurse / admin) and `department` (NULL = admin, unrestricted)
- `auth.py` route: `POST /auth/login` (bcrypt verify → JWT encode), `GET /auth/me`
- JWT HS256, 8-hour expiry, encoded with `{sub, email, department, role}`
- `dependencies.py` — `get_current_user()` and `require_admin()` FastAPI dependencies
- Password hashing uses `bcrypt` directly (not `passlib` — incompatible with bcrypt 4.x+)
- Auto-seed on startup: admin account (`admin@cityhospital.com` / `Admin@123`) + 14 nurse accounts (one per department)

**Admin Backend**
- `admin.py` routes (all JWT-protected):
  - `GET /admin/appointments` — filtered by dept/status/date/doctor; nurses auto-scoped to own dept
  - `POST /admin/appointments/{id}/cancel` — department check (403 if wrong dept)
  - `POST /admin/appointments/bulk-cancel` — atomic batch cancel with concurrent email sends
  - `GET /admin/audit-logs` — recent triage sessions
  - `GET /admin/stats` — aggregate counts by urgency and department
- Department scoping enforced server-side: even if nurse bypasses frontend, the server overrides `effective_department = user.department`

**Admin Frontend (React)**
- Full React 18 + Zustand + react-router-dom + TailwindCSS app on port 5174
- `authStore.ts` — `login`, `logout`, `loadFromStorage` (persists to localStorage)
- `adminClient.ts` — all admin API functions + global 401 Axios interceptor (auto-logout)
- Pages: `LoginPage.tsx`, `DashboardPage.tsx`
- Components:
  - `StatsCards.tsx` — summary cards (total sessions, by urgency, emergency count)
  - `AuditLogTable.tsx` — triage history with urgency badges
  - `AppointmentsTable.tsx` — filters (dept, doctor, status, date range, presets), per-row cancel, mass-cancel panel
  - `ProtectedRoute.tsx` — redirect to /login if unauthenticated

### Key technical decisions
- **Department scoping is server-enforced** — the nurse's JWT `department` claim overrides any query parameter; nurses cannot see or cancel other departments even with direct API calls.
- **Bulk cancel is atomic** — single DB transaction updates all matching rows; emails sent with `asyncio.gather` concurrently after commit.
- **401 global interceptor** — one Axios response interceptor in `adminClient.ts` handles all expired/invalid tokens without per-component handling.

---

## Phase 5 — Symptom Impact Checklist + Documentation
**Date:** 2026-04-20 · **Commit:** `0fa1ec0`

### What was built

**Symptom Impact Checklist**
- Replaced numeric 1–10 severity scale with a 7-option descriptive checklist:
  1. My symptoms are constant (not coming and going)
  2. My symptoms are getting worse
  3. I cannot carry out my normal daily activities
  4. I am unable to sleep due to my symptoms
  5. The symptoms started suddenly (within the last few hours)
  6. I have tried medication but it has not helped
  7. None of the above — symptoms are mild and manageable
- "None of the above" is mutually exclusive (enforced in frontend + backend)
- `pending_options` state field added to `TriageState` — holds checklist payload while awaiting patient submission
- `symptom_impact` state field — stores selected labels as plain text, passed verbatim to urgency assessor LLM
- `SymptomOptionsForm.tsx` — checkbox form rendered in `ChatWindow` when `pendingOptions` is set; disables text input until submitted

**Two-Pass SSE Streaming**
- Rearchitected `chat.py` to run two `astream_events` passes per HTTP request:
  - **Pass 1**: resume/run `collect_symptoms` (pauses at interrupt); emits `message` or `options` event
  - **Pass 2**: if `_should_proceed_to_triage()` returns True, resume graph to run full triage pipeline; emits `token` + `triage_complete`
- `_should_proceed_to_triage()` — mirror of `route_after_collection` in the API layer; blocks if `pending_options` set or `symptoms+duration` present without `symptom_impact`
- Critical LangGraph resume pattern fixed: passing a non-None dict to `astream_events` on an interrupted graph restarts from the entry point (wipes state). Correct pattern: `graph.update_state(config, new_msg)` then `astream_events(None, config)`

**MCP Client Rewrite**
- Switched to `fastmcp.client.transports.PythonStdioTransport` (previous `StdioServerParameters` rejected by FastMCP)
- `PYTHONPATH` explicitly injected into subprocess env so `src.*` imports resolve inside server script

**LLM Client Cleanup**
- Removed Ollama fallback — `GROQ_API_KEY` is now strictly required; raises `RuntimeError` with clear message if absent
- Removed `USE_OLLAMA`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` env vars

**CLAUDE.md — Full Developer Reference**
- 1,125-line comprehensive reference document covering all 18 sections: architecture, LangGraph graph, routing logic, checklist flow, MCP, RAG, database schemas, auth system, both frontends, all API endpoints, safety rules, environment variables, default credentials

---

## Phase 6 — Claude Code Tooling, Tests & CI Hook
**Date:** 2026-04-20 · **Commit:** `1c15fa9`

### What was built

**Claude Code Agents (`.claude/agents/`)**
8 specialist agents with embedded project knowledge:

| Agent | Purpose |
|---|---|
| `backend.md` | FastAPI, LangGraph, MCP, database — full backend reference |
| `frontend.md` | React patient app + admin dashboard, Zustand stores, SSE events |
| `team-lead.md` | Architecture decisions, cross-cutting concerns, delegation guide |
| `sqa.md` | Test categories, edge cases, urgency escalation safety rules |
| `triage-flow-debugger.md` | LangGraph routing/SSE debug — graph diagram, routing logic, checklist flow |
| `db-inspector.md` | SQLite queries, audit records, appointment inspection, credentials |
| `frontend-component-helper.md` | Zustand store slices, SSE event types, booking flow components |
| `rag-inspector.md` | ChromaDB chunk count, test retrieval queries, ingestion pipeline |

**Slash Command Skills (`.claude/commands/`)**
6 one-word developer commands:

| Command | What it does |
|---|---|
| `/start-backend` | Start uvicorn on port 8000 with env checks |
| `/start-frontends [patient\|admin\|both]` | Start React apps on ports 5173/5174 |
| `/audit-recent [N]` | Query last N triage sessions from SQLite |
| `/session-lookup <uuid>` | Full session dump with conversation history |
| `/ingest-rag [test]` | Re-run ChromaDB ingestion pipeline |
| `/run-tests [filter]` | Run pytest suite with optional test filter |

**PreToolUse Hook**
- `.claude/hooks/pre_start_tests.py` — fires before any Bash command containing `uvicorn src.api.main:app`
- Runs full pytest suite; exit code 2 blocks backend startup if any test fails
- `.claude/settings.json` registers the hook at project level

**End-to-End Test Suite (50 tests)**
- `pytest.ini` — test discovery config with `asyncio_mode = auto`
- `tests/conftest.py` — shared fixtures: isolated SQLite DB per test (`tmp_path`), LLM mock (patches each node module directly, not `src.llm.client`), MCP mock (`_mcp_client` singleton injection), ChromaDB mock, auth helpers
- 4 test files covering 6 flows:

| File | Flows | Tests |
|---|---|---|
| `test_triage_flow.py` | Flow 1: full non-emergency 4-turn triage; Flow 2: emergency bypass (no checklist) | 6 |
| `test_booking_flow.py` | Flow 3: email confirmation (15-min window, idempotent, expired, cancelled); Flow 4: double-booking prevention | 14 |
| `test_auth_flow.py` | Flow 5: admin auth + JWT + department scoping | 13 |
| `test_admin_flow.py` | Flow 6: bulk cancel (filters, scoping, status targeting) | 17 |

**Result: 50/50 passing in ~65 seconds**

### Key technical decisions
- **Patch LLM at usage site, not definition** — nodes do `from src.llm.client import get_llm` (local binding). Patching `src.llm.client.get_llm` does not affect those bindings. All fixtures patch each node module directly: `src.graph.nodes.symptom_collector.get_llm`, etc.
- **MCP mock via singleton injection** — `src.mcp.client._mcp_client` is set to an `AsyncMock` before `TestClient` starts; `get_mcp_client()` returns it because it checks `if _mcp_client is not None`.
- **`get_settings()` + `get_compiled_graph()` cache cleared per test** — both are `@lru_cache`; clearing between tests ensures each test gets a fresh SQLite path and fresh `MemorySaver`.

---

## Current State

| Area | Status |
|---|---|
| Backend API | Complete — 17 endpoints, all tested |
| LangGraph triage engine | Complete — 9 nodes, 6 routing conditions, emergency bypass |
| Symptom impact checklist | Complete — 7 options, SSE options event, mutual exclusion |
| RAG system | Complete — 11 protocol files, ChromaDB, cosine similarity |
| MCP integration | Complete — 6 tools, subprocess transport, lifecycle managed |
| Appointment booking | Complete — pending/confirmed/cancelled lifecycle, email + PDF |
| Admin dashboard | Complete — JWT, dept scoping, bulk cancel, audit logs |
| Patient frontend | Complete — chat, checklist form, booking modal |
| Auth system | Complete — bcrypt, JWT HS256, 14 nurse accounts + admin |
| Test suite | Complete — 50 tests, 100% passing, 6 flows covered |
| Claude Code tooling | Complete — 8 agents, 6 commands, 1 pre-start hook |
| Documentation | Complete — CLAUDE.md (1,125 lines), DEVLOG.md |
