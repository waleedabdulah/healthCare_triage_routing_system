const API_BASE = '/api/v1'

export interface Doctor {
  id: string
  name: string
  specialization: string
  slots: Slot[]
}

export interface Slot {
  id: string
  date: string
  time: string
  label: string
}

export interface BookingPayload {
  session_id: string
  department: string
  doctor_id: string
  doctor_name: string
  doctor_specialization: string
  slot_id: string
  slot_date: string
  slot_time: string
  slot_label: string
  patient_name: string
  patient_email: string
  patient_phone: string
}

export interface BookingConfirmation {
  appointment_id: string
  confirmation_code: string
  department: string
  doctor_name: string
  doctor_specialization: string
  slot_label: string
  patient_name: string
  patient_email: string
  status: string
}

export async function fetchDoctors(department: string): Promise<Doctor[]> {
  const res = await fetch(`${API_BASE}/appointments/doctors/${encodeURIComponent(department)}`)
  if (!res.ok) throw new Error(`Failed to load doctors: ${res.status}`)
  const data = await res.json()
  return data.doctors as Doctor[]
}

export async function submitBooking(payload: BookingPayload): Promise<BookingConfirmation> {
  const res = await fetch(`${API_BASE}/appointments/book`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `Booking failed: ${res.status}`)
  }
  return res.json()
}

export async function fetchBookingStatus(appointmentId: string): Promise<string> {
  const res = await fetch(`${API_BASE}/appointments/${appointmentId}/status`)
  if (!res.ok) throw new Error('Status check failed')
  const data = await res.json()
  return data.status as string
}

export async function checkExistingBooking(
  email: string,
  department: string,
): Promise<BookingConfirmation | null> {
  const params = new URLSearchParams({ email: email.trim().toLowerCase(), department })
  const res = await fetch(`${API_BASE}/appointments/check?${params}`)
  if (!res.ok) return null
  const data = await res.json()
  return data.exists ? (data.appointment as BookingConfirmation) : null
}

export async function cancelBooking(appointmentId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/appointments/${appointmentId}/cancel`, {
    method: 'POST',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `Cancel failed: ${res.status}`)
  }
}
