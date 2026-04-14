import React, { useEffect, useRef, useState } from 'react'
import {
  fetchDoctors,
  fetchBookingStatus,
  submitBooking,
  checkExistingBooking,
  cancelBooking,
  Doctor,
  Slot,
  BookingConfirmation,
} from '../api/bookingClient'
import { useSessionStore } from '../store/sessionStore'

interface Props {
  department: string
  onClose: () => void
  onBooked: () => void
}

type Step = 'email' | 'checking' | 'already_booked' | 'doctor' | 'slot' | 'details' | 'pending' | 'confirmed'

export default function BookingModal({ department, onClose, onBooked }: Props) {
  const sessionId = useSessionStore((s) => s.sessionId)
  const { setPendingAppointmentId } = useSessionStore()

  const [step, setStep] = useState<Step>('email')

  // ── Email step ────────────────────────────────────────────────
  const [emailInput, setEmailInput]         = useState('')
  const [emailInputError, setEmailInputError] = useState('')

  // ── Doctor / slot / details ───────────────────────────────────
  const [doctors, setDoctors]               = useState<Doctor[]>([])
  const [loadingDoctors, setLoadingDoctors] = useState(false)
  const [doctorError, setDoctorError]       = useState('')
  const [selectedDoctor, setSelectedDoctor] = useState<Doctor | null>(null)
  const [selectedSlot, setSelectedSlot]     = useState<Slot | null>(null)

  const [patientName, setPatientName]   = useState('')
  const [patientPhone, setPatientPhone] = useState('03')
  const [formError, setFormError]       = useState('')
  const [submitting, setSubmitting]     = useState(false)

  const [touched, setTouched] = useState({ name: false, phone: false })

  // ── Existing booking (already_booked step) ────────────────────
  const [existingBooking, setExistingBooking]       = useState<BookingConfirmation | null>(null)
  const [cancellingExisting, setCancellingExisting] = useState(false)
  const [cancelError, setCancelError]               = useState('')

  // ── Confirmation / polling ────────────────────────────────────
  const [confirmation, setConfirmation] = useState<BookingConfirmation | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // ── Email validator ───────────────────────────────────────────
  const isValidEmail = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim())

  // ── Phone handlers ────────────────────────────────────────────
  function handlePhoneChange(raw: string) {
    const digits = raw.replace(/\D/g, '')
    let core = digits.startsWith('03') ? digits : '03' + digits.replace(/^0{0,1}3?/, '')
    core = core.slice(0, 11)
    setPatientPhone(core.length > 4 ? `${core.slice(0, 4)}-${core.slice(4)}` : core)
  }
  function handlePhoneKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    const el = e.currentTarget
    const start = el.selectionStart ?? 0
    const end   = el.selectionEnd   ?? 0
    if (e.key === 'Backspace' && start <= 2 && end <= 2) e.preventDefault()
    if (e.key === 'Delete'    && start < 2)              e.preventDefault()
  }
  function handlePhoneFocus(e: React.FocusEvent<HTMLInputElement>) {
    const el = e.currentTarget
    requestAnimationFrame(() => {
      const pos = el.selectionStart ?? 0
      if (pos < 2) el.setSelectionRange(2, 2)
    })
  }

  // ── Per-field validators ──────────────────────────────────────
  const nameError = (): string => {
    if (!patientName || patientName.trim().length === 0) return 'Full name is required.'
    if (patientName.trim().length < 2) return 'Name must be at least 2 characters.'
    return ''
  }
  const phoneError = (): string => {
    if (patientPhone === '03') return 'Phone number is required.'
    if (!/^03\d{2}-\d{7}$/.test(patientPhone)) return 'Enter all digits — format: 03XX-XXXXXXX.'
    return ''
  }

  const fieldValid = {
    name:  !nameError(),
    phone: /^03\d{2}-\d{7}$/.test(patientPhone),
  }

  // ── Step 0: check email against DB ───────────────────────────
  async function handleEmailContinue() {
    const email = emailInput.trim()
    if (!isValidEmail(email)) {
      setEmailInputError('Enter a valid email address.')
      return
    }
    setEmailInputError('')
    setStep('checking')
    try {
      const existing = await checkExistingBooking(email, department)
      if (existing) {
        setExistingBooking(existing)
        setStep('already_booked')
      } else {
        setStep('doctor')
      }
    } catch {
      setStep('doctor')   // on API error just proceed
    }
  }

  // ── Load doctors when we reach the doctor step ────────────────
  useEffect(() => {
    if (step !== 'doctor') return
    setLoadingDoctors(true)
    setDoctorError('')
    fetchDoctors(department)
      .then(setDoctors)
      .catch(() => setDoctorError('Could not load doctors. Please try again.'))
      .finally(() => setLoadingDoctors(false))
  }, [step, department])

  // ── Poll while pending (modal open) ──────────────────────────
  useEffect(() => {
    if (step === 'pending' && confirmation) {
      pollRef.current = setInterval(async () => {
        try {
          const status = await fetchBookingStatus(confirmation.appointment_id)
          if (status === 'confirmed') {
            clearInterval(pollRef.current!)
            setStep('confirmed')
          }
        } catch { /* silent */ }
      }, 4000)
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [step, confirmation])

  // ── Cancel existing appointment ───────────────────────────────
  async function handleCancelExisting() {
    if (!existingBooking) return
    setCancellingExisting(true)
    setCancelError('')
    try {
      await cancelBooking(existingBooking.appointment_id)
      setExistingBooking(null)
      setStep('doctor')
    } catch (e: unknown) {
      setCancelError(e instanceof Error ? e.message : 'Could not cancel. Please try again.')
    } finally {
      setCancellingExisting(false)
    }
  }

  // ── Submit booking ────────────────────────────────────────────
  async function handleBook() {
    setTouched({ name: true, phone: true })
    setFormError('')
    const ne = nameError(), pe = phoneError()
    if (ne || pe) return
    if (!selectedDoctor || !selectedSlot) return

    setSubmitting(true)
    try {
      const result = await submitBooking({
        session_id:            sessionId,
        department,
        doctor_id:             selectedDoctor.id,
        doctor_name:           selectedDoctor.name,
        doctor_specialization: selectedDoctor.specialization,
        slot_id:               selectedSlot.id,
        slot_date:             selectedSlot.date,
        slot_time:             selectedSlot.time,
        slot_label:            selectedSlot.label,
        patient_name:          patientName.trim(),
        patient_email:         emailInput.trim().toLowerCase(),
        patient_phone:         patientPhone.trim(),
      })
      setConfirmation(result)
      setPendingAppointmentId(result.appointment_id)
      setStep('pending')
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : 'Booking failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Helpers ───────────────────────────────────────────────────
  const slotsByDate = (slots: Slot[]) =>
    slots.reduce<Record<string, Slot[]>>((acc, s) => {
      acc[s.date] = acc[s.date] ? [...acc[s.date], s] : [s]
      return acc
    }, {})

  const STEPS: Array<'doctor' | 'slot' | 'details'> = ['doctor', 'slot', 'details']
  const stepIndex: Record<Step, number> = { email: -1, checking: -1, already_booked: -1, doctor: 0, slot: 1, details: 2, pending: 3, confirmed: 3 }

  const inputCls = 'w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 pl-3 pr-9 py-2.5 text-sm text-slate-800 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-600 focus:border-transparent shadow-sm'

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 dark:bg-black/70 backdrop-blur-sm px-0 sm:px-4">
      <div className="bg-white dark:bg-slate-900 w-full sm:max-w-lg rounded-t-2xl sm:rounded-2xl shadow-2xl flex flex-col max-h-[92vh] border border-slate-200 dark:border-slate-800">

        {/* ── Header ── */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-slate-800">
          <div>
            <h2 className="font-bold text-slate-800 dark:text-white text-base">Book Appointment</h2>
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">{department}</p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors text-sm"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* ── Step indicator (only for doctor/slot/details) ── */}
        {['doctor', 'slot', 'details'].includes(step) && (
          <div className="flex items-center gap-2 px-5 pt-3 pb-1">
            {STEPS.map((s, i) => {
              const current = stepIndex[step]
              const done    = i < current
              const active  = i === current
              return (
                <React.Fragment key={s}>
                  <div className={`flex items-center gap-1.5 text-xs font-medium ${
                    active ? 'text-indigo-600 dark:text-indigo-400'
                    : done  ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-slate-400 dark:text-slate-600'
                  }`}>
                    <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-semibold ${
                      active ? 'bg-indigo-600 text-white'
                      : done  ? 'bg-emerald-500 text-white'
                      : 'bg-slate-200 dark:bg-slate-800 text-slate-400 dark:text-slate-600'
                    }`}>
                      {done ? '✓' : i + 1}
                    </span>
                    <span className="hidden sm:inline">
                      {s === 'doctor' ? 'Doctor' : s === 'slot' ? 'Time Slot' : 'Your Details'}
                    </span>
                  </div>
                  {i < 2 && <div className="flex-1 h-px bg-slate-200 dark:bg-slate-800" />}
                </React.Fragment>
              )
            })}
          </div>
        )}

        {/* ── Body ── */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">

          {/* STEP 0 — Email entry */}
          {step === 'email' && (
            <div className="space-y-4">
              <div className="flex items-start gap-3 p-4 bg-indigo-50 dark:bg-indigo-950/40 rounded-xl border border-indigo-100 dark:border-indigo-900">
                <span className="text-xl flex-shrink-0 mt-0.5">📧</span>
                <div>
                  <p className="text-sm font-semibold text-indigo-700 dark:text-indigo-300">Enter your email to continue</p>
                  <p className="text-xs text-indigo-600 dark:text-indigo-400 mt-0.5 leading-relaxed">
                    We use your email to check existing bookings and send your confirmation &amp; PDF receipt.
                  </p>
                </div>
              </div>

              <FormField
                label="Email Address"
                error={emailInputError}
                valid={!emailInputError && isValidEmail(emailInput)}
              >
                <input
                  type="email"
                  value={emailInput}
                  onChange={(e) => { setEmailInput(e.target.value); setEmailInputError('') }}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleEmailContinue() }}
                  placeholder="e.g. ali@email.com"
                  className={inputCls}
                  autoFocus
                  autoComplete="email"
                />
              </FormField>
            </div>
          )}

          {/* Checking spinner */}
          {step === 'checking' && (
            <div className="flex flex-col items-center py-10 text-slate-400">
              <div className="w-7 h-7 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin mb-3" />
              <span className="text-sm">Checking your bookings…</span>
            </div>
          )}

          {/* Already booked — restrict + cancel flow */}
          {step === 'already_booked' && existingBooking && (
            <div className="py-2 space-y-4">
              <div className="text-center">
                <div className="w-14 h-14 bg-amber-50 dark:bg-amber-950/40 rounded-full flex items-center justify-center text-3xl mx-auto mb-3">
                  📅
                </div>
                <h3 className="font-bold text-slate-800 dark:text-white text-base">Appointment Already Scheduled</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                  <strong className="text-slate-700 dark:text-slate-200">{emailInput.trim().toLowerCase()}</strong>{' '}
                  already has an active appointment for{' '}
                  <strong className="text-slate-700 dark:text-slate-200">{department}</strong>{' '}
                  this week. Only one booking per department per week is allowed.
                </p>
              </div>

              <div className="p-3 bg-slate-100 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 space-y-2 text-sm">
                <Row label="Doctor"      value={existingBooking.doctor_name} />
                <Row label="Appointment" value={existingBooking.slot_label} />
                <Row label="Status"      value={
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    existingBooking.status === 'confirmed'
                      ? 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-400'
                      : 'bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-400'
                  }`}>
                    {existingBooking.status === 'confirmed' ? 'Confirmed' : 'Pending confirmation'}
                  </span>
                } />
                <Row label="Code"        value={
                  <span className="font-mono font-bold text-indigo-700 dark:text-indigo-400">
                    {existingBooking.confirmation_code}
                  </span>
                } />
              </div>

              <div className="rounded-xl border border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-950/30 p-3 text-xs text-amber-700 dark:text-amber-400 leading-relaxed">
                To book a different slot, cancel your existing appointment first. This action cannot be undone.
              </div>

              {cancelError && (
                <p className="text-xs text-red-500 font-medium text-center">{cancelError}</p>
              )}

              <button
                onClick={handleCancelExisting}
                disabled={cancellingExisting}
                className="w-full py-2.5 rounded-xl border border-red-200 dark:border-red-900 text-sm font-semibold text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {cancellingExisting ? (
                  <>
                    <span className="w-4 h-4 border-2 border-red-400 border-t-transparent rounded-full animate-spin" />
                    Cancelling…
                  </>
                ) : '✕  Cancel Existing Appointment & Book New Slot'}
              </button>
            </div>
          )}

          {/* STEP 1 — Doctor */}
          {step === 'doctor' && (
            <>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Select a doctor from <strong className="text-slate-700 dark:text-slate-200">{department}</strong>
              </p>

              {loadingDoctors && (
                <div className="flex flex-col items-center py-8 text-slate-400">
                  <div className="w-6 h-6 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin mb-2" />
                  <span className="text-sm">Loading doctors…</span>
                </div>
              )}

              {doctorError && (
                <p className="text-sm text-red-500 text-center py-4">{doctorError}</p>
              )}

              {!loadingDoctors && !doctorError && doctors.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => { setSelectedDoctor(doc); setSelectedSlot(null); setStep('slot') }}
                  className="w-full text-left p-4 rounded-xl border border-slate-200 dark:border-slate-800 hover:border-indigo-200 dark:hover:border-indigo-800 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 bg-slate-50 dark:bg-slate-800/50 shadow-sm transition-all group"
                >
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 flex items-center justify-center text-xl flex-shrink-0 group-hover:bg-indigo-100 dark:group-hover:bg-indigo-900/60 transition-colors">
                      👨‍⚕️
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-slate-800 dark:text-white text-sm">{doc.name}</p>
                      <p className="text-xs text-indigo-600 dark:text-indigo-400 mt-0.5">{doc.specialization}</p>
                      <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                        {doc.slots.length > 0 ? `${doc.slots.length} slots available` : 'No slots — walk-ins accepted'}
                      </p>
                    </div>
                    <span className="text-slate-300 dark:text-slate-600 group-hover:text-indigo-400 dark:group-hover:text-indigo-500 text-base mt-1 transition-colors">›</span>
                  </div>
                </button>
              ))}
            </>
          )}

          {/* STEP 2 — Slot */}
          {step === 'slot' && selectedDoctor && (
            <>
              <button
                onClick={() => setStep('doctor')}
                className="flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 hover:underline font-medium"
              >
                ← Back
              </button>

              <div className="flex items-center gap-3 p-3 bg-indigo-50 dark:bg-indigo-950/40 rounded-xl border border-indigo-100 dark:border-indigo-900">
                <span className="text-2xl">👨‍⚕️</span>
                <div>
                  <p className="font-semibold text-sm text-slate-800 dark:text-white">{selectedDoctor.name}</p>
                  <p className="text-xs text-indigo-600 dark:text-indigo-400">{selectedDoctor.specialization}</p>
                </div>
              </div>

              <p className="text-sm text-slate-500 dark:text-slate-400">
                Choose a time slot{' '}
                <span className="text-xs text-slate-400 dark:text-slate-600">(next 7 working days)</span>:
              </p>

              {selectedDoctor.slots.length === 0 ? (
                <p className="text-sm text-slate-400 dark:text-slate-500 text-center py-4">
                  No slots available online. Please visit reception.
                </p>
              ) : (
                Object.entries(slotsByDate(selectedDoctor.slots)).map(([date, daySlots]) => (
                  <div key={date}>
                    <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">
                      {new Date(date + 'T00:00:00').toLocaleDateString('en-US', {
                        weekday: 'long', month: 'long', day: 'numeric',
                      })}
                    </p>
                    <div className="grid grid-cols-4 gap-2">
                      {daySlots.map((slot) => (
                        <button
                          key={slot.id}
                          onClick={() => { setSelectedSlot(slot); setStep('details') }}
                          className={`py-2 rounded-lg border text-xs font-medium transition-all ${
                            selectedSlot?.id === slot.id
                              ? 'bg-indigo-600 text-white border-indigo-600'
                              : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-300 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-700 hover:text-indigo-600 dark:hover:text-indigo-400'
                          }`}
                        >
                          {slot.time}
                        </button>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </>
          )}

          {/* STEP 3 — Details */}
          {step === 'details' && selectedDoctor && selectedSlot && (
            <>
              <button
                onClick={() => setStep('slot')}
                className="flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 hover:underline font-medium"
              >
                ← Back
              </button>

              {/* Summary */}
              <div className="p-3 bg-slate-100 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 space-y-2 text-sm">
                {[
                  { label: 'Doctor',     value: selectedDoctor.name },
                  { label: 'Department', value: department },
                  { label: 'Time',       value: selectedSlot.label },
                  { label: 'Email',      value: emailInput.trim().toLowerCase() },
                ].map(({ label, value }) => (
                  <div key={label} className="flex justify-between">
                    <span className="text-slate-400 dark:text-slate-500">{label}</span>
                    <span className="font-medium text-slate-800 dark:text-white text-right max-w-[60%] truncate">{value}</span>
                  </div>
                ))}
              </div>

              <div className="space-y-3">

                {/* Full Name */}
                <FormField
                  label="Full Name"
                  error={touched.name ? nameError() : ''}
                  valid={fieldValid.name}
                >
                  <input
                    type="text"
                    value={patientName}
                    onChange={(e) => setPatientName(e.target.value.replace(/[^a-zA-Z ]/g, '').replace(/^ +/, ''))}
                    onBlur={() => setTouched(t => ({ ...t, name: true }))}
                    placeholder="e.g. Ali Hassan"
                    maxLength={60}
                    className={inputCls}
                    autoComplete="name"
                  />
                </FormField>

                {/* Phone — masked input with ghost placeholder */}
                <FormField
                  label="Phone Number"
                  error={touched.phone ? phoneError() : ''}
                  valid={fieldValid.phone}
                  hint="03 is fixed — type the remaining 9 digits"
                >
                  <div className="relative rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus-within:ring-2 focus-within:ring-indigo-400 dark:focus-within:ring-indigo-600 focus-within:border-transparent overflow-hidden shadow-sm">
                    <div
                      aria-hidden
                      className="absolute inset-0 flex items-center pl-3 pr-9 pointer-events-none select-none font-mono text-sm"
                    >
                      <span className="text-transparent whitespace-pre">{patientPhone}</span>
                      <span className="text-slate-300 dark:text-slate-600 whitespace-pre">
                        {'03__-_______'.slice(patientPhone.length)}
                      </span>
                    </div>
                    <input
                      type="tel"
                      value={patientPhone}
                      onChange={(e) => handlePhoneChange(e.target.value)}
                      onKeyDown={handlePhoneKeyDown}
                      onFocus={handlePhoneFocus}
                      onBlur={() => setTouched(t => ({ ...t, phone: true }))}
                      maxLength={12}
                      className="relative w-full bg-transparent pl-3 pr-9 py-2.5 text-sm font-mono text-slate-800 dark:text-slate-100 focus:outline-none"
                      autoComplete="tel"
                      inputMode="numeric"
                      spellCheck={false}
                    />
                  </div>
                </FormField>
              </div>

              {formError && (
                <p className="text-xs text-red-500 font-medium">{formError}</p>
              )}
            </>
          )}

          {/* STEP 4 — Pending */}
          {step === 'pending' && confirmation && (
            <div className="py-2 space-y-5">
              <div className="text-center">
                <div className="w-16 h-16 bg-amber-50 dark:bg-amber-950/40 rounded-full flex items-center justify-center text-4xl mx-auto mb-3 animate-pulse">
                  📧
                </div>
                <h3 className="font-bold text-slate-800 dark:text-white text-lg">Check Your Email</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                  We sent a confirmation email to{' '}
                  <strong className="text-slate-700 dark:text-slate-300">{confirmation.patient_email}</strong>
                </p>
              </div>

              <div className="rounded-xl border border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-950/30 p-4 space-y-2 text-sm">
                <p className="font-semibold text-amber-800 dark:text-amber-400">Action required to finalise booking</p>
                <ol className="list-decimal list-inside space-y-1 text-amber-700 dark:text-amber-500">
                  <li>Open the email from City Hospital Triage</li>
                  <li>Click <strong>"Confirm My Appointment"</strong></li>
                  <li>This page will update automatically</li>
                </ol>
              </div>

              <div className="p-3 bg-slate-100 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 space-y-2 text-sm">
                <Row label="Slot reserved" value={confirmation.slot_label} />
                <Row label="Doctor"        value={confirmation.doctor_name} />
                <Row label="Code"          value={
                  <span className="font-mono font-bold text-indigo-700 dark:text-indigo-400">
                    {confirmation.confirmation_code}
                  </span>
                } />
              </div>

              <div className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
                <span className="w-3 h-3 border-2 border-indigo-400 dark:border-indigo-600 border-t-transparent rounded-full animate-spin" />
                Waiting for email confirmation…
              </div>
            </div>
          )}

          {/* STEP 5 — Confirmed */}
          {step === 'confirmed' && confirmation && (
            <div className="py-2 space-y-4">
              <div className="text-center">
                <div className="w-14 h-14 bg-emerald-50 dark:bg-emerald-950/40 rounded-full flex items-center justify-center text-3xl mx-auto mb-3">
                  ✅
                </div>
                <h3 className="font-bold text-slate-800 dark:text-white text-lg">Appointment Confirmed!</h3>
                <p className="text-sm text-slate-400 dark:text-slate-500 mt-1">
                  Please arrive 10 minutes early with your PDF receipt.
                </p>
              </div>

              <div className="rounded-xl border-2 border-emerald-200 dark:border-emerald-900 bg-emerald-50 dark:bg-emerald-950/30 p-4 space-y-2">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wide">Confirmation Code</span>
                  <span className="font-mono font-bold text-emerald-700 dark:text-emerald-400 text-lg tracking-widest">
                    {confirmation.confirmation_code}
                  </span>
                </div>
                <hr className="border-emerald-200 dark:border-emerald-900" />
                <div className="space-y-2 text-sm">
                  <Row label="Patient"        value={confirmation.patient_name} />
                  <Row label="Department"     value={confirmation.department} />
                  <Row label="Doctor"         value={confirmation.doctor_name} />
                  <Row label="Specialization" value={confirmation.doctor_specialization} />
                  <Row label="Appointment"    value={confirmation.slot_label} />
                  <Row label="Status"         value={
                    <span className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-400 rounded-full text-xs font-medium">
                      Confirmed
                    </span>
                  } />
                </div>
              </div>

              <p className="text-xs text-slate-400 dark:text-slate-500 text-center">
                PDF receipt emailed to{' '}
                <strong className="text-slate-600 dark:text-slate-400">{confirmation.patient_email}</strong>.
                Show it at reception.
              </p>
            </div>
          )}
        </div>

        {/* ── Footer ── */}
        <div className="border-t border-slate-200 dark:border-slate-800 px-5 py-3 flex gap-2">

          {/* Email step — continue button */}
          {step === 'email' && (
            <button
              onClick={handleEmailContinue}
              className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold transition-colors shadow-sm"
            >
              Continue →
            </button>
          )}

          {/* Details step */}
          {step === 'details' && (
            <>
              <button
                onClick={() => setStep('slot')}
                className="flex-1 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleBook}
                disabled={submitting}
                className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2 shadow-sm"
              >
                {submitting ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Sending…
                  </>
                ) : '📅 Reserve & Send Confirmation'}
              </button>
            </>
          )}

          {/* Confirmed */}
          {step === 'confirmed' && (
            <button
              onClick={() => { onBooked(); onClose() }}
              className="flex-1 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold transition-colors shadow-sm"
            >
              Done
            </button>
          )}

          {/* Cancel/close for all other steps */}
          {['checking', 'already_booked', 'doctor', 'slot', 'pending'].includes(step) && (
            <button
              onClick={onClose}
              className="flex-1 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              {step === 'pending' ? 'Close (check email later)' : 'Cancel'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-400 dark:text-slate-500">{label}</span>
      <span className="font-medium text-slate-800 dark:text-white text-right">{value}</span>
    </div>
  )
}

function FormField({
  label,
  error,
  valid,
  hint,
  children,
}: {
  label: string
  error: string
  valid: boolean
  hint?: string
  children: React.ReactNode
}) {
  const showError = !!error
  const showValid = valid && !error

  return (
    <div>
      <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
        {label} <span className="text-red-400">*</span>
      </label>
      <div className="relative">
        {children}
        <span className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
          {showValid && (
            <svg className="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
            </svg>
          )}
          {showError && (
            <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          )}
        </span>
      </div>
      {showError && (
        <p className="mt-1 text-xs text-red-500 flex items-center gap-1">
          <svg className="w-3 h-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          {error}
        </p>
      )}
      {hint && !showError && !showValid && (
        <p className="mt-1 text-xs text-slate-400 dark:text-slate-600">{hint}</p>
      )}
    </div>
  )
}
