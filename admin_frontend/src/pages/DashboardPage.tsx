import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import AppointmentsTable from '../components/AppointmentsTable'
import StatsCards from '../components/StatsCards'
import AuditLogTable from '../components/AuditLogTable'

type Tab = 'appointments' | 'stats' | 'audit'

const TABS: { key: Tab; label: string; icon: string }[] = [
  { key: 'appointments', label: 'Appointments', icon: '📅' },
  { key: 'stats',        label: 'Statistics',   icon: '📊' },
  { key: 'audit',        label: 'Audit Logs',   icon: '🗂️' },
]

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<Tab>('appointments')
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-950 flex flex-col">

      {/* Header */}
      <header className="flex-shrink-0 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">

          {/* Logo */}
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center flex-shrink-0 shadow-sm shadow-indigo-200 dark:shadow-indigo-900">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
              </svg>
            </div>
            <div className="min-w-0">
              <p className="text-sm font-bold text-slate-900 dark:text-white leading-tight truncate">City Hospital</p>
              <p className="text-[10px] font-medium text-slate-400 dark:text-slate-500 uppercase tracking-widest leading-tight">
                Staff Portal
              </p>
            </div>
          </div>

          {/* User info + logout */}
          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block">
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{user?.fullName}</p>
              <p className="text-xs text-slate-400 dark:text-slate-500">
                {user?.department ?? 'All Departments'} · {user?.role === 'admin' ? 'Admin' : 'Nurse'}
              </p>
            </div>
            <button
              onClick={handleLogout}
              className="text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-red-50 dark:hover:bg-red-950 hover:border-red-200 dark:hover:border-red-800 hover:text-red-700 dark:hover:text-red-400 transition-colors"
            >
              Logout
            </button>
          </div>
        </div>

        {/* Accent line */}
        <div className="h-px bg-gradient-to-r from-transparent via-indigo-500 to-transparent opacity-50 dark:opacity-30" />
      </header>

      {/* Tab bar */}
      <div className="flex-shrink-0 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex gap-1">
          {TABS.map(({ key, label, icon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`flex items-center gap-1.5 px-4 py-3 text-sm font-semibold border-b-2 transition-colors ${
                activeTab === key
                  ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                  : 'border-transparent text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-400'
              }`}
            >
              <span>{icon}</span>
              <span>{label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
          {activeTab === 'appointments' && <AppointmentsTable />}
          {activeTab === 'stats'        && <StatsCards />}
          {activeTab === 'audit'        && <AuditLogTable />}
        </div>
      </main>
    </div>
  )
}
