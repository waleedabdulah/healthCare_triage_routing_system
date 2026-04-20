import axios from 'axios'
import { useAuthStore } from '../store/authStore'

// Global 401 interceptor — clears auth and redirects to login on token expiry
axios.interceptors.response.use(
  res => res,
  err => {
    if (err?.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.replace('/login')
    }
    return Promise.reject(err)
  }
)

function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}` }
}

export interface Appointment {
  appointment_id: string
  patient_name: string
  patient_phone: string
  department: string
  doctor_name: string
  doctor_specialization: string
  slot_label: string
  slot_date: string
  slot_time: string
  status: 'pending_confirmation' | 'confirmed' | 'cancelled'
  confirmation_code: string
  created_at: string
}

export interface AuditRecord {
  id: string
  session_id: string
  created_at: string
  age_group: string | null
  urgency_level: string | null
  routed_department: string | null
  urgency_confidence: number | null
  emergency_flag: boolean
  human_review_flag: boolean
  conversation_turns: number
}

export interface Stats {
  total: number
  by_urgency: Record<string, number>
  by_department: Record<string, number>
  emergency_count: number
}

export async function fetchAppointments(
  token: string,
  params: {
    department?: string
    status?: string
    date_from?: string
    date_to?: string
    doctor?: string
  }
): Promise<{ appointments: Appointment[]; count: number }> {
  const res = await axios.get('/api/v1/admin/appointments', {
    headers: authHeaders(token),
    params,
  })
  return res.data
}

export async function cancelAppointment(
  token: string,
  appointmentId: string
): Promise<void> {
  await axios.post(
    `/api/v1/admin/appointments/${appointmentId}/cancel`,
    {},
    { headers: authHeaders(token) }
  )
}

export interface BulkCancelFilters {
  department?:    string
  doctor?:        string
  date_from?:     string
  date_to?:       string
  target_status?: string
}

export interface BulkCancelResult {
  cancelled_count: number
  cancelled: { appointment_id: string; patient_name: string }[]
}

export async function bulkCancelAppointments(
  token: string,
  filters: BulkCancelFilters
): Promise<BulkCancelResult> {
  const res = await axios.post('/api/v1/admin/appointments/bulk-cancel', filters, {
    headers: authHeaders(token),
  })
  return res.data
}

export async function fetchAuditLogs(
  token: string,
  limit = 100
): Promise<{ records: AuditRecord[]; count: number }> {
  const res = await axios.get('/api/v1/admin/audit-logs', {
    headers: authHeaders(token),
    params: { limit },
  })
  return res.data
}

export async function fetchStats(token: string): Promise<Stats> {
  const res = await axios.get('/api/v1/admin/stats', {
    headers: authHeaders(token),
  })
  return res.data
}
