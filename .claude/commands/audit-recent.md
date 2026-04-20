Show recent triage audit records from the SQLite database at d:/AI_project/data/triage_audit.db.

$ARGUMENTS

If a number is provided as the argument, show that many recent sessions. Default to 10 if no argument.

Run:
```bash
cd d:/AI_project && .venv/Scripts/python.exe -c "
import sqlite3, json, sys

n = int('$ARGUMENTS'.strip()) if '$ARGUMENTS'.strip().isdigit() else 10
conn = sqlite3.connect('data/triage_audit.db')
conn.row_factory = sqlite3.Row
rows = conn.execute('''
    SELECT session_id, urgency_level, ROUND(urgency_confidence, 2) as confidence,
           routed_department, age_group, conversation_turns,
           emergency_flag, human_review_flag, llm_model_used,
           symptoms_extracted, created_at
    FROM triage_sessions
    ORDER BY created_at DESC
    LIMIT ?
''', (n,)).fetchall()
print(f'Last {n} triage sessions ({len(rows)} found):')
print('-' * 80)
for r in rows:
    symptoms = json.loads(r['symptoms_extracted'] or '[]')
    flags = []
    if r['emergency_flag']: flags.append('EMERGENCY')
    if r['human_review_flag']: flags.append('HUMAN_REVIEW')
    print(f\"Session: {r['session_id'][:8]}...  Urgency: {r['urgency_level']}  Confidence: {r['confidence']}\")
    print(f\"  Dept: {r['routed_department']}  Age: {r['age_group']}  Turns: {r['conversation_turns']}\")
    print(f\"  Symptoms: {', '.join(symptoms[:4])}\")
    if flags: print(f\"  FLAGS: {', '.join(flags)}\")
    print(f\"  At: {r['created_at']}\")
    print()
conn.close()
"
```

Then show appointment status summary:
```bash
cd d:/AI_project && sqlite3 data/triage_audit.db "SELECT status, COUNT(*) as count FROM appointments GROUP BY status;"
```

After showing output, offer to look up a specific session in full detail using `/session-lookup <session_id>`.
