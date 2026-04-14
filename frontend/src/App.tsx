import { useState, useEffect } from 'react'
import ChatWindow from './components/ChatWindow'
import RoutingCard from './components/RoutingCard'
import DisclaimerBanner from './components/DisclaimerBanner'
import { useSessionStore } from './store/sessionStore'

/* ── Dark-mode hook ──────────────────────────────────────────── */
function useDarkMode() {
  const [dark, setDark] = useState(() => {
    try {
      const saved = localStorage.getItem('theme')
      if (saved) return saved === 'dark'
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    } catch {
      return false
    }
  })

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])

  return { dark, toggle: () => setDark(d => !d) }
}

/* ── App ─────────────────────────────────────────────────────── */
export default function App() {
  const { dark, toggle } = useDarkMode()
  const { triageResult, resetSession } = useSessionStore()
  const [activeTab, setActiveTab] = useState<'chat' | 'result'>('chat')

  // Auto-switch to result tab on mobile when triage completes
  useEffect(() => {
    if (triageResult) setActiveTab('result')
  }, [triageResult])

  function handleNewSession() {
    resetSession()
    setActiveTab('chat')
  }

  return (
    <div className="flex flex-col h-screen bg-slate-100 dark:bg-slate-950">

      {/* ══ HEADER ══════════════════════════════════════════════ */}
      <header className="flex-shrink-0 bg-white dark:bg-slate-900 z-20">
        <div className="px-4 sm:px-6 h-14 flex items-center justify-between gap-4">

          {/* Logo */}
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center flex-shrink-0 shadow-sm shadow-indigo-200 dark:shadow-indigo-900">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
              </svg>
            </div>
            <div className="min-w-0">
              <p className="text-sm font-bold text-slate-900 dark:text-white leading-tight truncate">
                City Hospital
              </p>
              <p className="text-[10px] font-medium text-slate-400 dark:text-slate-500 uppercase tracking-widest leading-tight">
                Triage System
              </p>
            </div>
          </div>

          {/* Centre tagline — hidden on small screens */}
          <p className="hidden md:block text-[11px] font-medium text-slate-400 dark:text-slate-600 uppercase tracking-widest text-center flex-1">
            AI-Powered Symptom Assessment &amp; Routing
          </p>

          {/* Actions */}
          <div className="flex items-center gap-1.5 flex-shrink-0">
            {/* Dark mode toggle */}
            <button
              onClick={toggle}
              aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
              title={dark ? 'Light mode' : 'Dark mode'}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-700 dark:text-slate-500 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              {dark ? (
                /* Sun */
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
                </svg>
              ) : (
                /* Moon */
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                </svg>
              )}
            </button>

            {/* Divider */}
            <div className="w-px h-5 bg-slate-200 dark:bg-slate-700 mx-0.5" />

            {/* New session */}
            <button
              onClick={handleNewSession}
              className="text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-indigo-50 dark:hover:bg-indigo-950 hover:border-indigo-200 dark:hover:border-indigo-800 hover:text-indigo-700 dark:hover:text-indigo-400 transition-colors"
            >
              New Session
            </button>
          </div>
        </div>

        {/* Accent rule */}
        <div className="h-px bg-gradient-to-r from-transparent via-indigo-500 to-transparent opacity-50 dark:opacity-30" />
        <div className="h-px bg-slate-200 dark:bg-slate-800" />
      </header>

      {/* ══ MOBILE TAB BAR (visible only when triage is ready) ══ */}
      {triageResult && (
        <div className="flex-shrink-0 md:hidden flex bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
          {[
            { key: 'chat',   label: 'Chat',   icon: '💬' },
            { key: 'result', label: 'Result',  icon: '🏥' },
          ].map(({ key, label, icon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key as 'chat' | 'result')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
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
      )}

      {/* ══ MAIN ════════════════════════════════════════════════ */}
      <main className="flex flex-1 overflow-hidden">

        {/* Chat panel */}
        <div className={[
          'flex flex-col transition-all duration-300',
          triageResult ? 'w-full md:w-1/2 border-r border-slate-200 dark:border-slate-800' : 'w-full',
          triageResult && activeTab !== 'chat' ? 'hidden md:flex' : 'flex',
        ].join(' ')}>
          <ChatWindow />
        </div>

        {/* Triage result panel */}
        {triageResult && (
          <div className={[
            'flex-col w-full md:w-1/2 bg-slate-100 dark:bg-slate-900 overflow-y-auto',
            activeTab === 'result' ? 'flex' : 'hidden md:flex',
          ].join(' ')}>
            <div className="p-6 space-y-5 max-w-lg mx-auto w-full">

              {/* Panel heading */}
              <div className="pt-2 pb-4 border-b border-slate-200 dark:border-slate-800">
                <p className="text-[10px] font-semibold text-indigo-500 dark:text-indigo-400 uppercase tracking-widest mb-1">
                  Assessment Ready
                </p>
                <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">
                  Triage Result
                </h2>
                <p className="text-sm text-slate-400 dark:text-slate-500 mt-1">
                  Based on your symptoms, here is your routing recommendation.
                </p>
              </div>

              <RoutingCard result={triageResult} />

              {/* At reception */}
              <div className="flex gap-3 bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-100 dark:border-indigo-900 rounded-xl p-4">
                <span className="text-xl flex-shrink-0">📋</span>
                <div>
                  <p className="text-sm font-semibold text-indigo-700 dark:text-indigo-300 mb-0.5">At Reception</p>
                  <p className="text-sm text-indigo-600 dark:text-indigo-400 leading-relaxed">
                    Present the <strong>PDF receipt</strong> sent to your email when you booked the appointment. The reception desk will verify it and direct you to the correct department.
                  </p>
                </div>
              </div>

              {/* Emergency note */}
              <div className="flex gap-3 bg-red-50 dark:bg-red-950/50 border border-red-100 dark:border-red-900 rounded-xl p-4">
                <span className="text-xl flex-shrink-0">🚨</span>
                <div>
                  <p className="text-sm font-semibold text-red-700 dark:text-red-400 mb-0.5">If condition worsens</p>
                  <p className="text-sm text-red-600 dark:text-red-400 leading-relaxed">
                    Difficulty breathing, chest pain, or loss of consciousness — go to the Emergency Room immediately or call{' '}
                    <strong>115 / 1122</strong>.
                  </p>
                </div>
              </div>

            </div>
          </div>
        )}
      </main>

      {/* ══ FOOTER ══════════════════════════════════════════════ */}
      <DisclaimerBanner />
    </div>
  )
}
