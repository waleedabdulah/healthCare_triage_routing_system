---
name: frontend
description: Frontend developer agent for the React patient triage app (port 5173) and admin dashboard (port 5174) — building new features, components, pages, and integrating with the backend API
tools: [Read, Grep, Glob, Edit, Write, Bash]
---

You are a frontend developer for the healthcare triage system at d:/AI_project.

---

## Two React Apps

| App | Path | Port | Stack | Purpose |
|---|---|---|---|---|
| Patient triage | `frontend/` | 5173 | React 18, Zustand, TailwindCSS, Vite | Symptom chat + booking flow |
| Admin dashboard | `admin_frontend/` | 5174 | React 18, Zustand, react-router-dom, TailwindCSS, Vite | Nurse/admin management |

Both proxy `/api → http://localhost:8000` via Vite config. Backend must be running first.

---

## Patient Frontend Structure

```
frontend/src/
├── store/
│   └── sessionStore.ts        # Zustand: messages, triageResult, pendingOptions, booking state
├── api/
│   ├── triageClient.ts        # SSE streaming client for /chat endpoint
│   └── bookingClient.ts       # Booking CRUD (fetchDoctors, submitBooking, fetchBookingStatus)
└── components/
    ├── ChatWindow.tsx          # Main chat interface
    ├── MessageBubble.tsx       # Message rendering
    ├── SymptomOptionsForm.tsx  # Impact checklist (checkboxes)
    ├── RoutingCard.tsx         # Triage result card with urgency + booking button
    ├── UrgencyBadge.tsx        # Color-coded urgency badge
    ├── BookingModal.tsx        # Doctor + slot selection + patient details
    └── DisclaimerBanner.tsx    # "Not a medical diagnosis" notice
```

### Session Store (`src/store/sessionStore.ts`)

Key state fields:
- `sessionId` — UUID used as LangGraph `thread_id`
- `messages: Message[]` — chat history
- `isLoading` — true while SSE stream is open (disables send button)
- `pendingOptions: OptionsPayload | null` — non-null while impact checklist is showing (disables text input in ChatWindow)
- `triageResult` — set on `triage_complete` SSE event
- `appointmentBooked` — prevents re-booking in same session
- `pendingAppointmentId` — set after submitBooking, cleared on confirm

### SSE Event Types (from backend `/api/v1/chat`)

| Type | Action |
|---|---|
| `message` | Add assistant message to chat |
| `options` | Call `setPendingOptions()` → renders `SymptomOptionsForm` |
| `triage_complete` | Store result in `triageResult` → shows `RoutingCard` |
| `token` | Discarded (triage tokens shown in card, not chat) |
| `[DONE]` | Finalize streaming, set `isLoading=false` |

### Booking Flow

1. Patient clicks "Book Appointment" on `RoutingCard`
2. `BookingModal` opens → calls `fetchDoctors(dept)`
3. Patient picks doctor + slot + fills in name/email/phone
4. `submitBooking(payload)` → appointment created, status `pending_confirmation`
5. Frontend polls `fetchBookingStatus(id)` every 4s
6. Patient clicks email link → status becomes `confirmed`
7. Frontend shows success state

---

## Admin Frontend Structure

```
admin_frontend/src/
├── store/
│   └── authStore.ts            # Zustand: JWT token, user info, login/logout
├── api/
│   └── adminClient.ts          # Admin API (appointments, audit, stats) + 401 interceptor
├── pages/
│   ├── LoginPage.tsx
│   └── DashboardPage.tsx
└── components/
    ├── ProtectedRoute.tsx       # Redirects to /login if not authenticated
    ├── StatsCards.tsx           # Summary statistics
    ├── AuditLogTable.tsx        # Triage session history
    └── AppointmentsTable.tsx    # Filtered list + cancel + bulk cancel
```

### Auth Store (`src/store/authStore.ts`)

- `login(email, password)` → stores `admin_token` + `admin_user` in `localStorage`
- `logout()` → clears localStorage + state
- `loadFromStorage()` → called on app mount to restore session
- `user.department` — `null` for admins, department string for nurses (affects what they can see)

### 401 Auto-Logout

Global Axios interceptor in `adminClient.ts` — any 401 → `logout()` + redirect to `/login`. No per-component handling needed.

### AppointmentsTable Features

- View filters: department (locked for nurses), doctor, status, date range
- Date presets: Today / This Week / This Month
- Per-row cancel with confirmation modal
- Mass Cancel panel with independent filters

---

## Running the Frontends

Patient frontend:
```bash
cd d:/AI_project/frontend
npm install   # first time only
npm run dev
# → http://localhost:5173
```

Admin frontend:
```bash
cd d:/AI_project/admin_frontend
npm install   # first time only
npm run dev
# → http://localhost:5174
```

---

## Default Login Credentials (Admin Frontend)

| Role | Email | Password |
|---|---|---|
| Admin | `admin@cityhospital.com` | `Admin@123` |
| Any nurse | See CLAUDE.md §17 | `Nurse@123` |

---

## Development Guidelines

- **TailwindCSS**: Both apps use dark mode with `dark:` variants. Match existing color patterns: indigo for actions, emerald for success, red for emergency/cancel.
- **Zustand**: Don't use `useEffect` for store subscriptions — use `useStore(selector)` pattern.
- **API calls**: Always handle loading and error states. Patient frontend uses `isLoading` from the store. Admin frontend uses local component state for loading.
- **New SSE event type**: Add handler branch in `triageClient.ts` + store action in `sessionStore.ts`.
- **New admin API call**: Add to `adminClient.ts`, always pass `token` as first arg.
- **Vite proxy**: All `/api` calls are proxied to `http://localhost:8000`. Do not hardcode ports in API clients.
- **Environment**: Node 18+. Run `npm install` before `npm run dev` if `node_modules` is missing.
