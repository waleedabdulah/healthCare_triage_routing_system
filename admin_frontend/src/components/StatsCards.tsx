import { useEffect, useState } from 'react'
import { fetchStats, type Stats } from '../api/adminClient'
import { useAuthStore } from '../store/authStore'

export default function StatsCards() {
  const { token } = useAuthStore()
  const [stats, setStats] = useState<Stats | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    fetchStats(token)
      .then(setStats)
      .catch(() => setError('Could not load statistics.'))
  }, [token])

  if (error) return <p className="text-sm text-red-500">{error}</p>
  if (!stats) return <p className="text-sm text-slate-400 dark:text-slate-500">Loading statistics…</p>

  const cards = [
    {
      label: 'Total Sessions',
      value: stats.total,
      icon: '🗂️',
      bg: 'bg-indigo-50 dark:bg-indigo-950/40',
      border: 'border-indigo-100 dark:border-indigo-900',
      text: 'text-indigo-700 dark:text-indigo-300',
    },
    {
      label: 'Emergencies',
      value: stats.emergency_count,
      icon: '🚨',
      bg: 'bg-red-50 dark:bg-red-950/40',
      border: 'border-red-100 dark:border-red-900',
      text: 'text-red-700 dark:text-red-300',
    },
    {
      label: 'URGENT Cases',
      value: stats.by_urgency['URGENT'] ?? 0,
      icon: '🟠',
      bg: 'bg-orange-50 dark:bg-orange-950/40',
      border: 'border-orange-100 dark:border-orange-900',
      text: 'text-orange-700 dark:text-orange-300',
    },
    {
      label: 'Self-Care',
      value: stats.by_urgency['SELF_CARE'] ?? 0,
      icon: '🟢',
      bg: 'bg-emerald-50 dark:bg-emerald-950/40',
      border: 'border-emerald-100 dark:border-emerald-900',
      text: 'text-emerald-700 dark:text-emerald-300',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map(c => (
          <div key={c.label} className={`rounded-2xl border p-5 ${c.bg} ${c.border}`}>
            <span className="text-2xl">{c.icon}</span>
            <p className={`text-3xl font-bold mt-2 ${c.text}`}>{c.value}</p>
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mt-1">{c.label}</p>
          </div>
        ))}
      </div>

      {/* By department */}
      {Object.keys(stats.by_department).length > 0 && (
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5">
          <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-4">
            Triage Sessions by Department
          </p>
          <div className="space-y-2">
            {Object.entries(stats.by_department)
              .sort((a, b) => b[1] - a[1])
              .map(([dept, count]) => (
                <div key={dept} className="flex items-center gap-3">
                  <span className="text-sm text-slate-700 dark:text-slate-200 w-44 truncate">{dept}</span>
                  <div className="flex-1 bg-slate-100 dark:bg-slate-800 rounded-full h-2">
                    <div
                      className="bg-indigo-500 h-2 rounded-full"
                      style={{ width: `${Math.round((count / stats.total) * 100)}%` }}
                    />
                  </div>
                  <span className="text-sm font-semibold text-slate-600 dark:text-slate-300 w-8 text-right">{count}</span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  )
}
