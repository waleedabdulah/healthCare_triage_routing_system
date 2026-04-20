Start the patient and/or admin React frontends for the healthcare triage system.

$ARGUMENTS

Based on the argument provided:

**`patient` or `5173`** — start only the patient triage app:
```bash
cd d:/AI_project/frontend && npm run dev
```
Runs at http://localhost:5173

**`admin` or `5174`** — start only the admin dashboard:
```bash
cd d:/AI_project/admin_frontend && npm run dev
```
Runs at http://localhost:5174

**`both` or no argument** — provide instructions for both (run each in a separate terminal):

Terminal 1 — Patient frontend (port 5173):
```bash
cd d:/AI_project/frontend && npm run dev
```

Terminal 2 — Admin frontend (port 5174):
```bash
cd d:/AI_project/admin_frontend && npm run dev
```

After starting, remind the user:
- The backend must be running on port 8000 first (`/start-backend`)
- Both apps proxy `/api` to `http://localhost:8000` via Vite config
- If `npm run dev` fails with module errors, run `npm install` first in the respective directory
- Admin login: `admin@cityhospital.com` / `Admin@123`
- Nurse accounts all use password `Nurse@123` (see CLAUDE.md §17 for department emails)
