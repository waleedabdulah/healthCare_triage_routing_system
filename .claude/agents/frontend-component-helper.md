---
name: frontend-component-helper
description: Build and debug React components for the patient triage frontend (port 5173) and admin dashboard (port 5174) — Zustand stores, SSE event handling, SymptomOptionsForm logic, booking flow, and admin appointments table
tools: [Read, Grep, Glob, Edit]
---

You are a frontend specialist for the healthcare triage system's two React apps at d:/AI_project.

---

## App Locations and Ports

| App | Path | Port | Purpose |
|---|---|---|---|
| Patient frontend | `d:/AI_project/frontend/` | 5173 | Symptom chat + booking flow |
| Admin frontend | `d:/AI_project/admin_frontend/` | 5174 | Nurse/admin dashboard |

Both use: React 18, Zustand, TailwindCSS, Vite. Proxy: `/api → http://localhost:8000`.

---

## Patient Frontend (`frontend/`)

### Zustand Store (`frontend/src/store/sessionStore.ts`)

```typescript
interface SessionState {
  sessionId: string
  messages: Message[]
  triageResult: TriageResult | null
  isLoading: boolean
  streamingContent: string
  appointmentBooked: boolean
  pendingAppointmentId: string | null
  pendingOptions: OptionsPayload | null   // set when severity checklist is active
}

interface OptionsPayload {
  question: string
  options: string[]
  multi_select: boolean
}

interface TriageResult {
  urgencyLevel: string | null       // EMERGENCY / URGENT / NON_URGENT / SELF_CARE
  routedDepartment: string | null
  isEmergency: boolean
  finalResponse: string | null
}
```

Key actions:
- `setPendingOptions(opts | null)` — sets/clears the active checklist form
- `addMessage(msg)` — appends to chat history
- `setTriageResult(result)` — stores final triage result
- `finalizeStreamingMessage()` — called when SSE stream ends
- `resetSession()` — clears all state for a new session

### SSE Client (`frontend/src/api/triageClient.ts`)

`sendMessage(sessionId, message, ageGroup?)` streams SSE from `/api/v1/chat`.

**SSE event types and their store actions:**

| Backend event type | Frontend action |
|---|---|
| `token` | **Discarded** — triage result shown in RoutingCard, NOT as a chat bubble. Do not change this. |
| `message` | `store.addMessage({ role: 'assistant', content })` |
| `options` | `store.setPendingOptions({ question, options, multi_select })` → renders `SymptomOptionsForm` |
| `triage_complete` | `store.setTriageResult(result)` — EMERGENCY also adds a chat message |
| `[DONE]` | `store.finalizeStreamingMessage()` + `store.setLoading(false)` |

**Adding a new SSE event type**: add a new `else if (event.type === 'your_type')` branch in the `for (const line of lines)` loop in `triageClient.ts`.

### Booking Flow (`frontend/src/api/bookingClient.ts`)

1. `fetchDoctors(dept)` → `GET /api/v1/appointments/doctors/{dept}` — returns doctors with available (unbooked) slots for next 7 working days
2. `submitBooking(payload)` → `POST /api/v1/appointments/book` — returns `{appointment_id, confirmation_code, status: "pending_confirmation"}`
3. `fetchBookingStatus(id)` → `GET /api/v1/appointments/{id}/status` — **poll every 4 seconds** until status is `"confirmed"`
4. `checkExistingBooking(email, dept)` → `GET /api/v1/appointments/check` — prevents duplicate bookings
5. `cancelBooking(id)` → `POST /api/v1/appointments/{id}/cancel`

`BookingModal` uses `pendingAppointmentId` from the store to decide whether to show the "waiting for email confirmation" polling state.

### Key Components

| Component | Purpose |
|---|---|
| `ChatWindow.tsx` | Main chat interface; disables text input while `pendingOptions !== null` |
| `MessageBubble.tsx` | Patient / assistant message rendering |
| `SymptomOptionsForm.tsx` | Impact checklist — checkboxes, mutual exclusion for "None", Submit button |
| `RoutingCard.tsx` | Triage result card — urgency, department, booking button |
| `UrgencyBadge.tsx` | Color-coded EMERGENCY / URGENT / NON_URGENT / SELF_CARE badge |
| `BookingModal.tsx` | Doctor selection + slot picker + patient details form |
| `DisclaimerBanner.tsx` | "Not a medical diagnosis" banner |

### `SymptomOptionsForm.tsx` Behaviour

- Rendered inside `ChatWindow` when `pendingOptions !== null`
- Last option is always "None of the above — symptoms are mild and manageable"
- Selecting "None of the above" clears all other selections (mutual exclusion)
- Selecting any non-None option removes "None of the above" from the selection
- Submit disabled until `selected.size > 0`
- On submit: joins selected labels with `, ` → sends as text message via `sendMessage()` → calls `setPendingOptions(null)`
- The submitted text is what the backend stores as `symptom_impact` in `TriageState`

---

## Admin Frontend (`admin_frontend/`)

### Routes
- `/login` — Login page
- `/dashboard` — Protected dashboard (ProtectedRoute)
- `*` → redirect to `/dashboard`

### Auth Store (`admin_frontend/src/store/authStore.ts`)

```typescript
interface AuthUser {
  id: string
  email: string
  fullName: string
  department: string | null   // null = admin (unrestricted); string = nurse (locked to that dept)
  role: 'nurse' | 'admin'
}
```

- `login(email, password)` → `POST /api/v1/auth/login` → stores `admin_token` + `admin_user` in `localStorage`
- `logout()` → clears localStorage + Zustand state
- `loadFromStorage()` → called in `App.tsx` on mount to restore session after page refresh
- `isAdmin()` → `user?.role === 'admin'`

### Admin API Client (`admin_frontend/src/api/adminClient.ts`)

```typescript
fetchAppointments(token, {department?, status?, date_from?, date_to?, doctor?})
cancelAppointment(token, appointmentId)
bulkCancelAppointments(token, {department?, doctor?, date_from?, date_to?, target_status?})
fetchAuditLogs(token, limit?)
fetchStats(token)
```

**Global 401 interceptor** — any 401 response → `useAuthStore.getState().logout()` + `window.location.replace('/login')`. Fires automatically for all authenticated calls — no per-component handling needed.

### Key Components

| Component | Purpose |
|---|---|
| `StatsCards.tsx` | Total sessions, by urgency, by department, emergency count |
| `AuditLogTable.tsx` | Triage session history with urgency badges |
| `AppointmentsTable.tsx` | Filtered appointments + per-row cancel + mass cancellation panel |
| `ProtectedRoute.tsx` | Redirect to /login if not authenticated |

### `AppointmentsTable.tsx` Features

- **View filters**: department (locked for nurses), doctor partial match, status, date range
- **Date presets**: Today / This Week / This Month — set `date_from` + `date_to`
- **Per-row cancel**: confirmation modal → `cancelAppointment()` → row updates in-place
- **Mass Cancel panel**: independent filter state → preview count → bulk confirm → `bulkCancelAppointments()`
- Both single and bulk cancel trigger backend email sends automatically
- Nurses have their `department` locked — the backend enforces this via JWT even if frontend is bypassed

---

## Auth System (`src/api/dependencies.py`)

### JWT Flow

```
POST /api/v1/auth/login  {email, password}
  └─► get_nurse_by_email(email) — case-insensitive lookup
  └─► bcrypt.checkpw(password, stored_hash)
  └─► jwt.encode({sub: id, email, department, role, exp: now+8h}, JWT_SECRET, HS256)
  └─► Returns {access_token, token_type: "bearer", user: {...}}

Protected endpoints:
  Authorization: Bearer <token>
  └─► dependencies.get_current_user() decodes JWT
  └─► Returns {id, email, department, role}
```

### Department Scoping (Security Layer)

```python
effective_department = department   # from query param
if user.department is not None:     # nurse (not admin)
    effective_department = user.department   # override — cannot be bypassed
```

- **Admin** (`department=None`): sees all departments, unrestricted
- **Nurse** (`department="Cardiology"`): locked to Cardiology only — enforced server-side

### Password Hashing

Uses `bcrypt` directly (not `passlib` — passlib 1.7.4 incompatible with bcrypt 4.x+):
```python
import bcrypt
hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
bcrypt.checkpw(password.encode(), stored_hash.encode())
```

---

## Development Patterns

**Adding a new Zustand store slice** (patient frontend):
1. Add field to `SessionState` interface in `sessionStore.ts`
2. Add to initial state object
3. Add setter/action in the store

**Adding a new admin API call**:
1. Add function to `adminClient.ts` alongside existing functions
2. Always pass `token` as first argument
3. The 401 interceptor handles expired tokens automatically

**Adding a new SSE event type** (backend + frontend):
1. Backend: emit `data: {"type": "your_type", ...}\n\n` from `chat.py`
2. Frontend: add `else if (event.type === 'your_type')` branch in `triageClient.ts`
3. Add store action in `sessionStore.ts` if state needs updating

**Tailwind conventions**: both apps use dark mode with `dark:` variants. Follow existing color patterns — indigo for primary actions, emerald for success, red for emergency/cancel, amber for warnings.
