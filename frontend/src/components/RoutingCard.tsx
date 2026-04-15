import { useState, useEffect, useRef } from 'react'
import { useSessionStore, TriageResult } from '../store/sessionStore'
import { fetchBookingStatus } from '../api/bookingClient'
import UrgencyBadge from './UrgencyBadge'
import BookingModal from './BookingModal'

interface Props { result: TriageResult }

const DEPT_ICONS: Record<string, string> = {
  'Emergency Room':   '🚨',
  'Cardiology':       '❤️',
  'Neurology':        '🧠',
  'ENT':              '👂',
  'Dermatology':      '🩹',
  'Gastroenterology': '🩻',
  'Pulmonology':      '🫁',
  'Orthopedics':      '🦴',
  'Ophthalmology':    '👁️',
  'Gynecology':       '🌸',
  'Urology':          '💧',
  'Psychiatry':       '🧩',
  'General Medicine': '🩺',
  'Pediatrics':       '👶',
}

const URGENCY_ACTION: Record<string, string> = {
  EMERGENCY:  'Proceed to the Emergency Room immediately',
  URGENT:     'Visit OPD today — same-day consultation required',
  NON_URGENT: 'Schedule an OPD appointment at your earliest',
  SELF_CARE:  'Monitor at home — visit OPD if symptoms worsen',
}

const URGENCY_ACCENT: Record<string, { light: string; dark: string }> = {
  EMERGENCY:  { light: 'border-red-200 bg-red-50 text-red-700',     dark: 'dark:border-red-900 dark:bg-red-950/50 dark:text-red-400' },
  URGENT:     { light: 'border-orange-200 bg-orange-50 text-orange-700', dark: 'dark:border-orange-900 dark:bg-orange-950/50 dark:text-orange-400' },
  NON_URGENT: { light: 'border-amber-200 bg-amber-50 text-amber-700',  dark: 'dark:border-amber-900 dark:bg-amber-950/50 dark:text-amber-400' },
  SELF_CARE:  { light: 'border-emerald-200 bg-emerald-50 text-emerald-700', dark: 'dark:border-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-400' },
}

export default function RoutingCard({ result }: Props) {
  const { urgencyLevel, routedDepartment, isEmergency } = result
  const deptIcon = routedDepartment ? (DEPT_ICONS[routedDepartment] ?? '🏥') : '🏥'
  const action   = urgencyLevel ? (URGENCY_ACTION[urgencyLevel] ?? '') : ''
  const accent   = urgencyLevel && URGENCY_ACCENT[urgencyLevel]
    ? `${URGENCY_ACCENT[urgencyLevel].light} ${URGENCY_ACCENT[urgencyLevel].dark}`
    : 'border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300'

  const [showBooking, setShowBooking] = useState(false)
  const { appointmentBooked, setAppointmentBooked, pendingAppointmentId } = useSessionStore()
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Poll for confirmation even when the BookingModal is closed
  useEffect(() => {
    if (!pendingAppointmentId || appointmentBooked) return

    pollRef.current = setInterval(async () => {
      try {
        const status = await fetchBookingStatus(pendingAppointmentId)
        if (status === 'confirmed') {
          clearInterval(pollRef.current!)
          setAppointmentBooked()
        }
      } catch { /* silent — keep polling */ }
    }, 4000)

    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [pendingAppointmentId, appointmentBooked])

  return (
    <div className={`rounded-2xl border overflow-hidden shadow-sm ${
      isEmergency
        ? 'border-red-300 dark:border-red-800'
        : 'border-slate-200 dark:border-slate-800'
    }`}>

      {/* Emergency banner */}
      {isEmergency && (
        <div className="bg-red-600 text-white px-5 py-3 text-center font-bold text-sm tracking-wide animate-pulse">
          🚨 GO TO EMERGENCY ROOM IMMEDIATELY 🚨
        </div>
      )}

      <div className="bg-white dark:bg-slate-900 p-5 space-y-4">

        {/* Title + badge */}
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
            Routing Result
          </p>
          {urgencyLevel && <UrgencyBadge level={urgencyLevel} />}
        </div>

        {/* Department */}
        {routedDepartment && (
          <div className="flex items-center gap-4 p-4 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
            <span className="text-3xl">{deptIcon}</span>
            <div>
              <p className="text-xs text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-0.5">Department</p>
              <p className="font-bold text-slate-900 dark:text-white text-base">{routedDepartment}</p>
            </div>
          </div>
        )}

        {/* Recommended action */}
        {action && (
          <div className={`flex gap-3 p-4 rounded-xl border ${accent}`}>
            <span className="text-lg mt-0.5 flex-shrink-0">💡</span>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider mb-0.5 opacity-70">Recommended Action</p>
              <p className="text-sm font-medium">{action}</p>
            </div>
          </div>
        )}

        {/* Book appointment */}
        {!isEmergency && routedDepartment && (
          <button
            onClick={() => setShowBooking(true)}
            disabled={appointmentBooked}
            className={`w-full py-3 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-all shadow-sm ${
              appointmentBooked
                ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900 cursor-not-allowed'
                : 'bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white'
            }`}
          >
            <span>{appointmentBooked ? '✓' : '📅'}</span>
            {appointmentBooked ? 'Appointment Booked' : `Book Appointment — ${routedDepartment}`}
          </button>
        )}
      </div>

      {showBooking && routedDepartment && (
        <BookingModal
          department={routedDepartment}
          onClose={() => setShowBooking(false)}
          onBooked={() => { setAppointmentBooked(); setShowBooking(false) }}
        />
      )}
    </div>
  )
}
