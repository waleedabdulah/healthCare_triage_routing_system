import { useState } from 'react'
import { useSessionStore, OptionsPayload } from '../store/sessionStore'
import { sendMessage } from '../api/triageClient'

interface Props {
  payload: OptionsPayload
  sessionId: string
  ageGroup: string | undefined
}

export default function SymptomOptionsForm({ payload, sessionId, ageGroup }: Props) {
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [submitting, setSubmitting] = useState(false)
  const { setPendingOptions, addMessage } = useSessionStore()

  const NONE_OPTION = payload.options[payload.options.length - 1] // last option is "None of the above"

  function toggle(option: string) {
    setSelected(prev => {
      const next = new Set(prev)
      if (option === NONE_OPTION) {
        // "None" is mutually exclusive — clear all others
        return next.has(option) ? new Set() : new Set([option])
      }
      // Selecting any other option clears "None"
      next.delete(NONE_OPTION)
      if (next.has(option)) next.delete(option)
      else next.add(option)
      return next
    })
  }

  async function handleSubmit() {
    if (selected.size === 0 || submitting) return
    setSubmitting(true)

    const selections = Array.from(selected)
    const messageText = selections.join(', ')

    // Show patient's selections as a chat bubble
    addMessage({ role: 'patient', content: messageText })
    setPendingOptions(null)

    try {
      await sendMessage(sessionId, messageText, ageGroup)
    } catch {
      useSessionStore.getState().addMessage({
        role: 'assistant',
        content: '⚠️ Connection error. Please try again.',
      })
      useSessionStore.getState().setLoading(false)
    }
  }

  return (
    <div className="flex items-end gap-2 mb-2">
      {/* Bot avatar */}
      <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0 self-start mt-1">
        <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
      </div>

      {/* Card */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm rounded-2xl rounded-bl-sm px-4 py-4 max-w-sm w-full">
        <p className="text-sm font-medium text-slate-700 dark:text-slate-200 mb-3">
          {payload.question}
        </p>

        <div className="space-y-2">
          {payload.options.map((option) => {
            const isSelected = selected.has(option)
            const isNone = option === NONE_OPTION
            return (
              <label
                key={option}
                className={`flex items-start gap-3 p-2.5 rounded-lg border cursor-pointer transition-all ${
                  isSelected
                    ? isNone
                      ? 'border-emerald-300 bg-emerald-50 dark:border-emerald-700 dark:bg-emerald-950/40'
                      : 'border-indigo-300 bg-indigo-50 dark:border-indigo-700 dark:bg-indigo-950/40'
                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-700/50'
                }`}
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => toggle(option)}
                  className="mt-0.5 flex-shrink-0 w-4 h-4 rounded accent-indigo-600"
                />
                <span className={`text-sm leading-snug ${
                  isSelected
                    ? isNone
                      ? 'text-emerald-700 dark:text-emerald-300 font-medium'
                      : 'text-indigo-700 dark:text-indigo-300 font-medium'
                    : 'text-slate-600 dark:text-slate-300'
                }`}>
                  {option}
                </span>
              </label>
            )
          })}
        </div>

        <button
          onClick={handleSubmit}
          disabled={selected.size === 0 || submitting}
          className="mt-4 w-full py-2.5 rounded-xl text-sm font-semibold transition-all
            bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white
            disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
        >
          {submitting ? 'Submitting…' : 'Submit'}
        </button>
      </div>
    </div>
  )
}
