import { useEffect, useState } from 'react'
import { fetchAuditLogs, type AuditRecord } from '../api/adminClient'
import { useAuthStore } from '../store/authStore'

const URGENCY_STYLE: Record<string, string> = {
  EMERGENCY:  'bg-red-100 dark:bg-red-950/50 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800',
  URGENT:     'bg-orange-100 dark:bg-orange-950/50 text-orange-700 dark:text-orange-300 border-orange-200 dark:border-orange-800',
  NON_URGENT: 'bg-yellow-100 dark:bg-yellow-950/50 text-yellow-700 dark:text-yellow-300 border-yellow-200 dark:border-yellow-800',
  SELF_CARE:  'bg-emerald-100 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800',
}

const URGENCY_EMOJI: Record<string, string> = {
  EMERGENCY: '🔴', URGENT: '🟠', NON_URGENT: '🟡', SELF_CARE: '🟢',
}

export default function AuditLogTable() {
  const { token } = useAuthStore()
  const [records, setRecords] = useState<AuditRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')

  useEffect(() => {
    if (!token) return
    setLoading(true)
    fetchAuditLogs(token, 100)
      .then(d => setRecords(d.records))
      .catch(() => setError('Could not load audit logs.'))
      .finally(() => setLoading(false))
  }, [token])

  if (loading) return <p className="text-sm text-slate-400 dark:text-slate-500">Loading audit logs…</p>
  if (error)   return <p className="text-sm text-red-500">{error}</p>

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-400 dark:text-slate-500">{records.length} triage sessions (most recent first)</p>

      <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
              {['Time', 'Age Group', 'Urgency', 'Department', 'Confidence', 'Turns', 'Flags'].map(h => (
                <th key={h} className="px-4 py-3 text-left text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider whitespace-nowrap">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {records.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-sm text-slate-400 dark:text-slate-500">
                  No triage sessions recorded yet.
                </td>
              </tr>
            ) : (
              records.map(r => (
                <tr key={r.id} className="bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors">
                  <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
                    {r.created_at ? new Date(r.created_at).toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-300 capitalize">{r.age_group ?? '—'}</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {r.urgency_level ? (
                      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${URGENCY_STYLE[r.urgency_level] ?? ''}`}>
                        {URGENCY_EMOJI[r.urgency_level]} {r.urgency_level}
                      </span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-300 whitespace-nowrap">{r.routed_department ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                    {r.urgency_confidence != null ? `${Math.round(r.urgency_confidence * 100)}%` : '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-300 text-center">{r.conversation_turns}</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {r.emergency_flag && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-100 dark:bg-red-950/50 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800 mr-1">
                        🚨 EMERG
                      </span>
                    )}
                    {r.human_review_flag && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-yellow-100 dark:bg-yellow-950/50 text-yellow-700 dark:text-yellow-300 border border-yellow-200 dark:border-yellow-800">
                        👁 REVIEW
                      </span>
                    )}
                    {!r.emergency_flag && !r.human_review_flag && (
                      <span className="text-slate-300 dark:text-slate-600">—</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
