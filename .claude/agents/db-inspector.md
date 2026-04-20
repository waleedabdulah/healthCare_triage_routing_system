---
name: db-inspector
description: Inspect and query the SQLite triage database — audit logs, appointments, nurse users, session history, and appointment confirmation status
tools: [Bash, Read]
---

You are a database inspector for the healthcare triage system's SQLite database at d:/AI_project.

---

## Database Setup

- **File**: `data/triage_audit.db` (auto-created on backend startup)
- **Engine**: SQLite via SQLModel + SQLAlchemy (`check_same_thread=False` required for FastAPI async)
- **ORM**: `src/models/db_models.py` — SQLModel tables
- **Query functions**: `src/database/repository.py`

---

## Table Schemas

### `NurseUser` (auth)

| Column | Type | Notes |
|---|---|---|
| `id` | str (UUID) | PK |
| `email` | str | Unique, indexed, stored lowercase |
| `password_hash` | str | bcrypt (not passlib — passlib 1.7.4 incompatible with bcrypt 4.x+) |
| `full_name` | str | |
| `department` | str? | NULL = admin (all departments); string = nurse (locked to that dept) |
| `role` | str | "nurse" or "admin" |
| `created_at` | datetime | |
| `is_active` | bool | Default True |

### `TriageSession` (audit log — one row per completed triage)

| Column | Type | Notes |
|---|---|---|
| `id` | str (UUID) | PK |
| `session_id` | str | LangGraph thread_id, indexed |
| `created_at` | datetime | Row insert time |
| `completed_at` | datetime | When triage finished |
| `age_group` | str? | child / adult / elderly |
| `gender` | str? | |
| `symptoms_extracted` | str? | JSON list e.g. `["chest pain","sweating"]` |
| `red_flags` | str? | JSON list |
| `urgency_level` | str? | EMERGENCY / URGENT / NON_URGENT / SELF_CARE |
| `urgency_confidence` | float? | 0.0–1.0 |
| `urgency_reasoning` | str? | LLM reasoning text |
| `routed_department` | str? | e.g. "Cardiology" |
| `routing_reasoning` | str? | |
| `rag_chunks_used` | str? | JSON list of chunk IDs |
| `estimated_wait_minutes` | int? | |
| `emergency_flag` | bool | Indexed |
| `human_review_flag` | bool | Low-confidence cases |
| `llm_model_used` | str? | e.g. "llama-3.3-70b-versatile" |
| `total_llm_calls` | int | |
| `conversation_turns` | int | |
| `full_conversation` | str? | JSON message list |

### `Appointment`

| Column | Type | Notes |
|---|---|---|
| `id` | str (UUID) | PK |
| `session_id` | str | Indexed |
| `patient_name` | str | |
| `patient_email` | str | |
| `patient_phone` | str | |
| `department` | str | |
| `doctor_id` | str | |
| `doctor_name` | str | |
| `doctor_specialization` | str | |
| `slot_id` | str | **Unique** — prevents double-booking |
| `slot_date` | str | "YYYY-MM-DD" |
| `slot_time` | str | "09:00" |
| `slot_label` | str | Human-readable |
| `status` | str | `pending_confirmation` / `confirmed` / `cancelled` |
| `confirmation_code` | str | 6-char hex, unique |
| `confirmation_token` | str | 32-char URL-safe, used in email link (15-min expiry) |
| `created_at` | datetime | |

**15-minute confirmation window**: `(datetime.utcnow() - appt.created_at).total_seconds() > 900` → token expired. Implemented in `src/database/repository.py` → `confirm_appointment()`.

---

## Key Repository Functions (`src/database/repository.py`)

- `create_appointment(payload)` → `Appointment`
- `confirm_appointment(token)` → `(Appointment|None, result_code)` — result_code: `confirmed` / `already_confirmed` / `expired` / `cancelled` / `not_found`
- `cancel_appointment_by_id(id)` → `Appointment` (or None if not found/already cancelled)
- `bulk_cancel_appointments(dept, doctor, date_from, date_to, status)` → `list[dict]`
- `get_appointments_filtered(dept, status, date_from, date_to, doctor, limit)` → `list[dict]`
- `get_booked_slot_ids()` → `set[str]` — returns `pending_confirmation` + `confirmed` slot IDs (prevents double-booking)
- `write_audit_record(payload)` → `str` (record_id)
- `create_nurse_user(email, password_hash, full_name, dept, role)` → `NurseUser`
- `get_nurse_by_email(email)` → `NurseUser|None`
- `get_stats()` → `dict` (by_urgency, by_department, emergency_count)

---

## Appointment Booking Flow

```
Patient clicks "Book Appointment"
  └─► POST /api/v1/appointments/book
        └─► DB: status = "pending_confirmation"  (slot reserved immediately)
        └─► Background task: send HTML email with confirmation link + PDF attachment
              confirmation_url = APP_BASE_URL + /api/v1/appointments/confirm/{token}

Patient clicks email link → GET /api/v1/appointments/confirm/{token}
  └─► confirm_appointment(token) in repository.py:
        1. Token not found → "not_found"
        2. status == "confirmed" → "already_confirmed" (idempotent)
        3. status == "cancelled" → "cancelled"
        4. elapsed > 900 seconds → "expired"
        5. All pass → status = "confirmed" ✓

Frontend polls GET /api/v1/appointments/{id}/status every 4 seconds
  └─► Sees "confirmed" → shows success UI
```

---

## Default Credentials

### Admin Account (auto-seeded on first startup)

| Field | Value |
|---|---|
| Email | `admin@cityhospital.com` |
| Password | `Admin@123` |
| Role | admin |
| Department | NULL (all departments, unrestricted) |

### Nurse Accounts (password: `Nurse@123`)

| Department | Email |
|---|---|
| Emergency Room | `nurse.er@cityhospital.com` |
| Cardiology | `nurse.cardiology@cityhospital.com` |
| Neurology | `nurse.neurology@cityhospital.com` |
| ENT | `nurse.ent@cityhospital.com` |
| Dermatology | `nurse.dermatology@cityhospital.com` |
| Gastroenterology | `nurse.gastro@cityhospital.com` |
| Pulmonology | `nurse.pulmonology@cityhospital.com` |
| Orthopedics | `nurse.orthopedics@cityhospital.com` |
| Ophthalmology | `nurse.ophthalmology@cityhospital.com` |
| Gynecology | `nurse.gynecology@cityhospital.com` |
| Urology | `nurse.urology@cityhospital.com` |
| Psychiatry | `nurse.psychiatry@cityhospital.com` |
| General Medicine | `nurse.generalmedicine@cityhospital.com` |
| Pediatrics | `nurse.pediatrics@cityhospital.com` |

### Create a New Nurse Account

```bash
cd d:/AI_project
.venv/Scripts/python.exe -c "
import bcrypt
from src.database.connection import create_db_and_tables
from src.database.repository import create_nurse_user
create_db_and_tables()
pw = bcrypt.hashpw(b'YourPassword', bcrypt.gensalt()).decode()
create_nurse_user(email='nurse@example.com', password_hash=pw, full_name='Nurse Name', department='Cardiology', role='nurse')
print('Done')
"
```

---

## Common SQL Queries

Open interactive shell:
```bash
cd d:/AI_project && sqlite3 data/triage_audit.db
```

Recent triage sessions:
```sql
SELECT session_id, urgency_level, ROUND(urgency_confidence,2), routed_department,
       conversation_turns, emergency_flag, human_review_flag, created_at
FROM triage_sessions ORDER BY created_at DESC LIMIT 20;
```

Emergency sessions only:
```sql
SELECT session_id, symptoms_extracted, urgency_reasoning, created_at
FROM triage_sessions WHERE emergency_flag = 1 ORDER BY created_at DESC;
```

Human-review flagged (low confidence):
```sql
SELECT session_id, urgency_level, urgency_confidence, routed_department
FROM triage_sessions WHERE human_review_flag = 1 ORDER BY created_at DESC;
```

Stats by urgency level:
```sql
SELECT urgency_level, COUNT(*) AS count FROM triage_sessions GROUP BY urgency_level;
```

Pending appointments (unconfirmed):
```sql
SELECT id, patient_name, department, doctor_name, slot_date, slot_time, status, created_at
FROM appointments WHERE status = 'pending_confirmation' ORDER BY created_at DESC LIMIT 20;
```

Appointments near expiry (pending > 10 min):
```sql
SELECT id, patient_name, department, slot_label, created_at,
       ROUND((julianday('now') - julianday(created_at)) * 1440, 1) AS minutes_elapsed
FROM appointments WHERE status = 'pending_confirmation'
AND (julianday('now') - julianday(created_at)) * 1440 > 10
ORDER BY created_at ASC;
```

Appointment status counts:
```sql
SELECT status, COUNT(*) FROM appointments GROUP BY status;
```

---

## Python One-liners for JSON Fields

Pretty-print the full conversation for the most recent session:
```bash
cd d:/AI_project && .venv/Scripts/python.exe -c "
import sqlite3, json
conn = sqlite3.connect('data/triage_audit.db')
row = conn.execute('SELECT full_conversation FROM triage_sessions ORDER BY created_at DESC LIMIT 1').fetchone()
if row: print(json.dumps(json.loads(row[0]), indent=2))
"
```

Show extracted symptoms for recent sessions:
```bash
cd d:/AI_project && .venv/Scripts/python.exe -c "
import sqlite3, json
conn = sqlite3.connect('data/triage_audit.db')
rows = conn.execute('SELECT session_id, symptoms_extracted, urgency_level FROM triage_sessions ORDER BY created_at DESC LIMIT 10').fetchall()
for r in rows:
    print(r[0][:8], r[2], json.loads(r[1] or '[]'))
"
```
