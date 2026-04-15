import { useEffect, useState, useCallback } from 'react'
import {
  fetchAppointments, cancelAppointment, bulkCancelAppointments,
  type Appointment, type BulkCancelFilters,
} from '../api/adminClient'
import { useAuthStore } from '../store/authStore'

const DEPARTMENTS = [
  'Emergency Room','Cardiology','Neurology','ENT','Dermatology',
  'Gastroenterology','Pulmonology','Orthopedics','Ophthalmology',
  'Gynecology','Urology','Psychiatry','General Medicine','Pediatrics',
]

const STATUS_BADGE: Record<string, string> = {
  confirmed:            'bg-emerald-100 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800',
  pending_confirmation: 'bg-yellow-100 dark:bg-yellow-950/50 text-yellow-700 dark:text-yellow-300 border-yellow-200 dark:border-yellow-800',
  cancelled:            'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700',
}

const STATUS_LABEL: Record<string, string> = {
  confirmed:            '✅ Confirmed',
  pending_confirmation: '⏳ Pending',
  cancelled:            '❌ Cancelled',
}

// ── Date helpers ──────────────────────────────────────────────────────────────

function isoToday() { return new Date().toISOString().slice(0, 10) }

function addDays(base: string, n: number) {
  const d = new Date(base); d.setDate(d.getDate() + n)
  return d.toISOString().slice(0, 10)
}

function startOfWeek(base: string) {
  const d = new Date(base); d.setDate(d.getDate() - d.getDay())
  return d.toISOString().slice(0, 10)
}

function endOfWeek(base: string) { return addDays(startOfWeek(base), 6) }

function startOfMonth(base: string) { return base.slice(0, 8) + '01' }

function endOfMonth(base: string) {
  const [y, m] = base.split('-').map(Number)
  return `${base.slice(0, 8)}${String(new Date(y, m, 0).getDate()).padStart(2, '0')}`
}

type Preset = 'today' | 'week' | 'month'

function applyPreset(preset: Preset): { from: string; to: string } {
  const today = isoToday()
  if (preset === 'today') return { from: today, to: today }
  if (preset === 'week')  return { from: startOfWeek(today), to: endOfWeek(today) }
  return { from: startOfMonth(today), to: endOfMonth(today) }
}

// ── Date range bar (shared sub-component) ────────────────────────────────────

interface DateRangeBarProps {
  dateFrom: string; dateTo: string
  onFromChange: (v: string) => void; onToChange: (v: string) => void
  onPreset: (p: Preset) => void; onClear: () => void
  activePreset: Preset | null
}

function DateRangeBar({ dateFrom, dateTo, onFromChange, onToChange, onPreset, onClear, activePreset }: DateRangeBarProps) {
  return (
    <div className="flex flex-wrap items-end gap-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
      <div>
        <label className="block text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Quick Range</label>
        <div className="flex gap-1">
          {(['today', 'week', 'month'] as const).map(p => (
            <button key={p} onClick={() => onPreset(p)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
                activePreset === p
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-indigo-400 hover:text-indigo-600'
              }`}>
              {p === 'today' ? 'Today' : p === 'week' ? 'This Week' : 'This Month'}
            </button>
          ))}
          {(dateFrom || dateTo) && (
            <button onClick={onClear}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-400 hover:text-red-500 hover:border-red-300 transition-colors">
              Clear
            </button>
          )}
        </div>
      </div>
      <div>
        <label className="block text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">From</label>
        <input type="date" value={dateFrom} max={dateTo || undefined} onChange={e => onFromChange(e.target.value)}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-700 dark:text-slate-200 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
      </div>
      <div>
        <label className="block text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">To</label>
        <input type="date" value={dateTo} min={dateFrom || undefined} onChange={e => onToChange(e.target.value)}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-700 dark:text-slate-200 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
      </div>
      <p className="text-xs self-end pb-2 text-indigo-600 dark:text-indigo-400 font-medium">
        {dateFrom && dateTo
          ? dateFrom === dateTo ? dateFrom : `${dateFrom} → ${dateTo}`
          : dateFrom ? `From ${dateFrom}` : dateTo ? `Up to ${dateTo}` : 'All dates'}
      </p>
    </div>
  )
}

// ── Single-cancel confirm modal ───────────────────────────────────────────────

interface SingleConfirmProps {
  appt: Appointment; onConfirm(): void; onClose(): void; cancelling: boolean
}

function SingleConfirmModal({ appt, onConfirm, onClose, cancelling }: SingleConfirmProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-700 p-6 max-w-sm w-full mx-4">
        <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100 mb-1">Cancel Appointment?</h3>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
          This will cancel <strong className="text-slate-700 dark:text-slate-200">{appt.patient_name}</strong>'s
          appointment with <strong className="text-slate-700 dark:text-slate-200">{appt.doctor_name}</strong> on{' '}
          <strong className="text-slate-700 dark:text-slate-200">{appt.slot_label}</strong>.
          A cancellation email will be sent to the patient.
        </p>
        <div className="flex gap-3 justify-end">
          <button onClick={onClose} disabled={cancelling}
            className="px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50">
            Keep
          </button>
          <button onClick={onConfirm} disabled={cancelling}
            className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-sm font-medium disabled:opacity-50">
            {cancelling ? 'Cancelling…' : 'Yes, Cancel'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Bulk-cancel confirm modal ─────────────────────────────────────────────────

interface BulkConfirmProps {
  previewCount: number; filters: BulkCancelFilters
  onConfirm(): void; onClose(): void; running: boolean
}

function BulkConfirmModal({ previewCount, filters, onConfirm, onClose, running }: BulkConfirmProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-700 p-6 max-w-md w-full mx-4">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">⚠️</span>
          <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100">Confirm Mass Cancellation</h3>
        </div>

        <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-xl p-4 mb-4 space-y-1">
          <p className="text-sm font-bold text-red-700 dark:text-red-400">
            {previewCount} appointment{previewCount !== 1 ? 's' : ''} will be cancelled
          </p>
          <p className="text-xs text-red-600 dark:text-red-500">A cancellation email will be sent to each patient.</p>
        </div>

        <div className="text-xs text-slate-500 dark:text-slate-400 space-y-1 mb-5">
          {filters.department   && <p><span className="font-semibold">Department:</span> {filters.department}</p>}
          {filters.doctor       && <p><span className="font-semibold">Doctor:</span> {filters.doctor}</p>}
          {filters.date_from    && <p><span className="font-semibold">From:</span> {filters.date_from}</p>}
          {filters.date_to      && <p><span className="font-semibold">To:</span> {filters.date_to}</p>}
          {filters.target_status && filters.target_status !== 'all' && (
            <p><span className="font-semibold">Status:</span> {filters.target_status}</p>
          )}
        </div>

        <div className="flex gap-3 justify-end">
          <button onClick={onClose} disabled={running}
            className="px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50">
            Go Back
          </button>
          <button onClick={onConfirm} disabled={running || previewCount === 0}
            className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-sm font-semibold disabled:opacity-50">
            {running ? 'Cancelling…' : `Cancel ${previewCount} Appointment${previewCount !== 1 ? 's' : ''}`}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Mass Cancel Panel ─────────────────────────────────────────────────────────

interface MassCancelPanelProps {
  token: string
  userDepartment: string | null
  isAdminUser: boolean
  onDone(): void
}

function MassCancelPanel({ token, userDepartment, isAdminUser, onDone }: MassCancelPanelProps) {
  const [dept,         setDept]         = useState(userDepartment ?? '')
  const [doctor,       setDoctor]       = useState('')
  const [dateFrom,     setDateFrom]     = useState('')
  const [dateTo,       setDateTo]       = useState('')
  const [targetStatus, setTargetStatus] = useState('all')

  const [previewing,   setPreviewing]   = useState(false)
  const [previewCount, setPreviewCount] = useState<number | null>(null)
  const [showConfirm,  setShowConfirm]  = useState(false)
  const [running,      setRunning]      = useState(false)
  const [result,       setResult]       = useState<{ count: number } | null>(null)
  const [error,        setError]        = useState('')

  const today = isoToday()

  function getActivePreset(): Preset | null {
    if (dateFrom === today && dateTo === today) return 'today'
    if (dateFrom === startOfWeek(today) && dateTo === endOfWeek(today)) return 'week'
    if (dateFrom === startOfMonth(today) && dateTo === endOfMonth(today)) return 'month'
    return null
  }

  function handlePreset(p: Preset) {
    const { from, to } = applyPreset(p)
    setDateFrom(from); setDateTo(to)
  }

  function buildFilters(): BulkCancelFilters {
    const f: BulkCancelFilters = {}
    if (dept)          f.department    = dept
    if (doctor.trim()) f.doctor        = doctor.trim()
    if (dateFrom)      f.date_from     = dateFrom
    if (dateTo)        f.date_to       = dateTo
    if (targetStatus && targetStatus !== 'all') f.target_status = targetStatus
    return f
  }

  async function handlePreview() {
    setPreviewing(true); setError(''); setPreviewCount(null); setResult(null)
    try {
      const params: Record<string, string> = {}
      if (dept)          params.department = dept
      if (doctor.trim()) params.doctor     = doctor.trim()
      if (dateFrom)      params.date_from  = dateFrom
      if (dateTo)        params.date_to    = dateTo
      if (targetStatus && targetStatus !== 'all') params.status = targetStatus
      const data = await fetchAppointments(token, params)
      // Count only cancellable ones
      const cancellable = data.appointments.filter(a => a.status !== 'cancelled')
      setPreviewCount(cancellable.length)
      setShowConfirm(true)
    } catch {
      setError('Could not preview. Please try again.')
    } finally {
      setPreviewing(false)
    }
  }

  async function handleConfirm() {
    setRunning(true); setError('')
    try {
      const res = await bulkCancelAppointments(token, buildFilters())
      setShowConfirm(false)
      setResult({ count: res.cancelled_count })
      onDone()
    } catch {
      setError('Mass cancellation failed. Please try again.')
      setShowConfirm(false)
    } finally {
      setRunning(false)
    }
  }

  return (
    <>
      {showConfirm && previewCount !== null && (
        <BulkConfirmModal
          previewCount={previewCount}
          filters={buildFilters()}
          onConfirm={handleConfirm}
          onClose={() => setShowConfirm(false)}
          running={running}
        />
      )}

      <div className="space-y-4 p-4 rounded-2xl border border-red-200 dark:border-red-900 bg-red-50/50 dark:bg-red-950/20">
        <div className="flex items-center gap-2">
          <span className="text-lg">🗑️</span>
          <h3 className="text-sm font-bold text-red-700 dark:text-red-400 uppercase tracking-wider">Mass Cancellation</h3>
          <span className="text-xs text-red-500 dark:text-red-600 ml-1">— cancellation emails sent automatically</span>
        </div>

        {/* Filters row */}
        <div className="flex flex-wrap gap-3 items-end">

          {/* Department */}
          <div>
            <label className="block text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Department</label>
            {isAdminUser ? (
              <select value={dept} onChange={e => setDept(e.target.value)}
                className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-700 dark:text-slate-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-400">
                <option value="">All Departments</option>
                {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            ) : (
              <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-sm text-slate-600 dark:text-slate-300 px-3 py-2 cursor-not-allowed">
                {userDepartment ?? '—'}
              </div>
            )}
          </div>

          {/* Doctor */}
          <div>
            <label className="block text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Doctor</label>
            <input type="text" value={doctor} onChange={e => setDoctor(e.target.value)} placeholder="Doctor name…"
              className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-700 dark:text-slate-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-400 w-40" />
          </div>

          {/* Target status */}
          <div>
            <label className="block text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Which Status</label>
            <select value={targetStatus} onChange={e => setTargetStatus(e.target.value)}
              className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-700 dark:text-slate-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-400">
              <option value="all">Pending + Confirmed</option>
              <option value="confirmed">Confirmed only</option>
              <option value="pending_confirmation">Pending only</option>
            </select>
          </div>
        </div>

        {/* Date range */}
        <DateRangeBar
          dateFrom={dateFrom} dateTo={dateTo}
          onFromChange={setDateFrom} onToChange={setDateTo}
          onPreset={handlePreset} onClear={() => { setDateFrom(''); setDateTo('') }}
          activePreset={getActivePreset()}
        />

        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

        {result && (
          <div className="flex items-center gap-2 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-xl px-4 py-3">
            <span className="text-emerald-600 dark:text-emerald-400 font-bold text-sm">
              ✅ {result.count} appointment{result.count !== 1 ? 's' : ''} cancelled — emails sent.
            </span>
          </div>
        )}

        <div className="flex justify-end">
          <button onClick={handlePreview} disabled={previewing || running}
            className="px-5 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-sm font-semibold transition-colors disabled:opacity-50 flex items-center gap-2">
            {previewing ? (
              <><span className="animate-spin">⟳</span> Previewing…</>
            ) : 'Preview & Cancel'}
          </button>
        </div>
      </div>
    </>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function AppointmentsTable() {
  const { token, user, isAdmin } = useAuthStore()

  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [loading, setLoading]           = useState(false)
  const [error, setError]               = useState('')

  // View filters
  const [department, setDepartment] = useState(user?.department ?? '')
  const [status, setStatus]         = useState('all')
  const [dateFrom, setDateFrom]     = useState('')
  const [dateTo, setDateTo]         = useState('')
  const [doctor, setDoctor]         = useState('')
  const [search, setSearch]         = useState('')

  // Panel toggle
  const [showMassCancel, setShowMassCancel] = useState(false)

  // Single-cancel state
  const [cancelTarget, setCancelTarget] = useState<Appointment | null>(null)
  const [cancelling,   setCancelling]   = useState(false)
  const [cancelError,  setCancelError]  = useState('')

  const today = isoToday()

  function getActivePreset(): Preset | null {
    if (dateFrom === today && dateTo === today) return 'today'
    if (dateFrom === startOfWeek(today) && dateTo === endOfWeek(today)) return 'week'
    if (dateFrom === startOfMonth(today) && dateTo === endOfMonth(today)) return 'month'
    return null
  }

  function handlePreset(p: Preset) {
    const { from, to } = applyPreset(p); setDateFrom(from); setDateTo(to)
  }

  // ── Load ────────────────────────────────────────────────────────────────────

  const load = useCallback(async () => {
    if (!token) return
    setLoading(true); setError('')
    try {
      const params: Record<string, string> = {}
      if (department)               params.department = department
      if (status && status !== 'all') params.status   = status
      if (dateFrom)                 params.date_from  = dateFrom
      if (dateTo)                   params.date_to    = dateTo
      if (doctor.trim())            params.doctor     = doctor.trim()
      const data = await fetchAppointments(token, params)
      setAppointments(data.appointments)
    } catch {
      setError('Could not load appointments. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [token, department, status, dateFrom, dateTo, doctor])

  useEffect(() => { load() }, [load])
  useEffect(() => { const id = setInterval(load, 60_000); return () => clearInterval(id) }, [load])

  // ── Single cancel ───────────────────────────────────────────────────────────

  async function handleCancel() {
    if (!cancelTarget || !token) return
    setCancelling(true); setCancelError('')
    try {
      await cancelAppointment(token, cancelTarget.appointment_id)
      setAppointments(prev =>
        prev.map(a => a.appointment_id === cancelTarget.appointment_id ? { ...a, status: 'cancelled' } : a)
      )
      setCancelTarget(null)
    } catch {
      setCancelError('Failed to cancel. Please try again.')
    } finally {
      setCancelling(false)
    }
  }

  // ── Filter ──────────────────────────────────────────────────────────────────

  const filtered = appointments.filter(a =>
    !search || a.patient_name.toLowerCase().includes(search.toLowerCase())
  )

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <>
      {cancelTarget && (
        <SingleConfirmModal
          appt={cancelTarget}
          onConfirm={handleCancel}
          onClose={() => { setCancelTarget(null); setCancelError('') }}
          cancelling={cancelling}
        />
      )}

      <div className="space-y-4">

        {/* ── View filter bar ─────────────────────────────────────────────── */}
        <div className="flex flex-wrap gap-3 items-end">
          {/* Department */}
          <div>
            <label className="block text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Department</label>
            {isAdmin() ? (
              <select value={department} onChange={e => setDepartment(e.target.value)}
                className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-700 dark:text-slate-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400">
                <option value="">All Departments</option>
                {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            ) : (
              <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-sm text-slate-600 dark:text-slate-300 px-3 py-2 cursor-not-allowed">
                {user?.department ?? '—'}
              </div>
            )}
          </div>

          {/* Doctor */}
          <div>
            <label className="block text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Doctor</label>
            <input type="text" value={doctor} onChange={e => setDoctor(e.target.value)} placeholder="Doctor name…"
              className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-700 dark:text-slate-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400 w-40" />
          </div>

          {/* Status */}
          <div>
            <label className="block text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Status</label>
            <select value={status} onChange={e => setStatus(e.target.value)}
              className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-700 dark:text-slate-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400">
              <option value="all">All</option>
              <option value="confirmed">Confirmed</option>
              <option value="pending_confirmation">Pending</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>

          {/* Patient search */}
          <div className="flex-1 min-w-[150px]">
            <label className="block text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Patient</label>
            <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Patient name…"
              className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-700 dark:text-slate-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          </div>

          <button onClick={load} disabled={loading}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition-colors disabled:opacity-50">
            {loading ? '…' : '↻ Refresh'}
          </button>
        </div>

        {/* ── Date range ──────────────────────────────────────────────────── */}
        <DateRangeBar
          dateFrom={dateFrom} dateTo={dateTo}
          onFromChange={setDateFrom} onToChange={setDateTo}
          onPreset={handlePreset} onClear={() => { setDateFrom(''); setDateTo('') }}
          activePreset={getActivePreset()}
        />

        {error      && <p className="text-sm text-red-500">{error}</p>}
        {cancelError && <p className="text-sm text-red-500">{cancelError}</p>}

        {/* ── Mass cancel toggle ──────────────────────────────────────────── */}
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-400 dark:text-slate-500">
            {filtered.length} appointment{filtered.length !== 1 ? 's' : ''} found
            {loading && ' · Refreshing…'}
          </p>
          <button
            onClick={() => setShowMassCancel(v => !v)}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
              showMassCancel
                ? 'bg-red-600 text-white border-red-600'
                : 'border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30'
            }`}>
            <span>🗑️</span>
            {showMassCancel ? 'Hide Mass Cancel' : 'Mass Cancellation'}
          </button>
        </div>

        {/* ── Mass cancel panel ───────────────────────────────────────────── */}
        {showMassCancel && token && (
          <MassCancelPanel
            token={token}
            userDepartment={user?.department ?? null}
            isAdminUser={isAdmin()}
            onDone={() => { load(); setShowMassCancel(false) }}
          />
        )}

        {/* ── Table ──────────────────────────────────────────────────────── */}
        <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
                {['Patient', 'Phone', 'Department', 'Doctor', 'Slot', 'Status', 'Code', 'Action'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-sm text-slate-400 dark:text-slate-500">
                    {loading ? 'Loading…' : 'No appointments found for the selected filters.'}
                  </td>
                </tr>
              ) : filtered.map(a => (
                <tr key={a.appointment_id} className="bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors">
                  <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-100 whitespace-nowrap">{a.patient_name}</td>
                  <td className="px-4 py-3 text-slate-500 dark:text-slate-400 whitespace-nowrap">{a.patient_phone}</td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-300 whitespace-nowrap">{a.department}</td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-300 whitespace-nowrap">
                    <div>{a.doctor_name}</div>
                    <div className="text-[11px] text-slate-400 dark:text-slate-500">{a.doctor_specialization}</div>
                  </td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-300 whitespace-nowrap">
                    <div className="font-medium">{a.slot_date}</div>
                    <div className="text-[11px] text-slate-400 dark:text-slate-500">{a.slot_time}</div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${STATUS_BADGE[a.status] ?? ''}`}>
                      {STATUS_LABEL[a.status] ?? a.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">{a.confirmation_code}</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {a.status !== 'cancelled' ? (
                      <button onClick={() => setCancelTarget(a)}
                        className="px-3 py-1 rounded-lg text-xs font-semibold border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors">
                        Cancel
                      </button>
                    ) : (
                      <span className="text-xs text-slate-300 dark:text-slate-600">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
