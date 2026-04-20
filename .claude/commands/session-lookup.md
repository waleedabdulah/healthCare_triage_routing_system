Look up the full details of a specific triage session by session ID (or partial prefix).

$ARGUMENTS

Use the session ID (or partial prefix) provided as the argument. If no argument is given, ask the user to provide one.

Run:
```bash
cd d:/AI_project && .venv/Scripts/python.exe -c "
import sqlite3, json

session_id = '$ARGUMENTS'.strip()
if not session_id:
    print('Error: provide a session_id or prefix as argument')
    exit(1)

conn = sqlite3.connect('data/triage_audit.db')
conn.row_factory = sqlite3.Row

rows = conn.execute(
    'SELECT * FROM triage_sessions WHERE session_id LIKE ? ORDER BY created_at DESC',
    (session_id + '%',)
).fetchall()

if not rows:
    print(f'No triage session found matching: {session_id}')
    exit(0)

r = rows[0]
print('=' * 70)
print(f'Session ID:  {r[\"session_id\"]}')
print(f'Created:     {r[\"created_at\"]}')
print(f'Completed:   {r[\"completed_at\"]}')
print()
print(f'Patient:     age_group={r[\"age_group\"]}  gender={r[\"gender\"]}')
symptoms = json.loads(r['symptoms_extracted'] or '[]')
red_flags = json.loads(r['red_flags'] or '[]')
print(f'Symptoms:    {symptoms}')
if red_flags: print(f'Red flags:   {red_flags}')
print()
print(f'URGENCY:     {r[\"urgency_level\"]}  (confidence={r[\"urgency_confidence\"]})')
print(f'Reasoning:   {r[\"urgency_reasoning\"]}')
print(f'Department:  {r[\"routed_department\"]}')
print(f'Dept reason: {r[\"routing_reasoning\"]}')
print()
print(f'Turns: {r[\"conversation_turns\"]}  |  Model: {r[\"llm_model_used\"]}')
print(f'Emergency flag: {bool(r[\"emergency_flag\"])}  |  Human review: {bool(r[\"human_review_flag\"])}')
rag_ids = json.loads(r['rag_chunks_used'] or '[]')
if rag_ids: print(f'RAG chunks used: {rag_ids}')
print()
print('FULL CONVERSATION:')
print('-' * 70)
convo = json.loads(r['full_conversation'] or '[]')
for msg in convo:
    role_label = 'PATIENT  ' if msg.get('role') == 'patient' else 'ASSISTANT'
    print(f'[{role_label}] {msg.get(\"content\", \"\")}')
    print()

appts = conn.execute(
    'SELECT id, patient_name, department, doctor_name, slot_label, status FROM appointments WHERE session_id = ?',
    (r['session_id'],)
).fetchall()
if appts:
    print('LINKED APPOINTMENTS:')
    for a in appts:
        print(f'  {a[\"id\"][:8]}... | {a[\"patient_name\"]} | {a[\"department\"]} | {a[\"doctor_name\"]} | {a[\"slot_label\"]} | {a[\"status\"]}')
conn.close()
"
```

After showing the output, offer to check the live graph state (if the backend is running):
```bash
curl -s http://localhost:8000/api/v1/session/$ARGUMENTS | python -m json.tool
```
