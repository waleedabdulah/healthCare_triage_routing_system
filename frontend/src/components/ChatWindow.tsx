import React, { useState, useRef, useEffect } from 'react'
import { useSessionStore } from '../store/sessionStore'
import { sendMessage } from '../api/triageClient'
import MessageBubble from './MessageBubble'
import SymptomOptionsForm from './SymptomOptionsForm'

const AGE_GROUPS = [
  { label: 'Child (< 16)',   value: 'child',   icon: '🧒' },
  { label: 'Adult (16–60)', value: 'adult',   icon: '🧑' },
  { label: 'Elderly (60+)', value: 'elderly', icon: '🧓' },
]

const WELCOME =
  "Hello! I'm the **Hospital Triage Assistant**.\n\nI'll help assess your symptoms and guide you to the right department.\n\nPlease tell me: **What is your main symptom today?**"

export default function ChatWindow() {
  const [input, setInput]                   = useState('')
  const [selectedAgeGroup, setSelectedAgeGroup] = useState<string | undefined>(undefined)
  const [ageGroupError, setAgeGroupError]   = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const {
    sessionId,
    messages,
    streamingContent,
    isLoading,
    triageResult,
    pendingOptions,
    addMessage,
    resetSession,
  } = useSessionStore()

  // ── Scroll to bottom ──────────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  // ── Welcome message — re-runs every time a new session starts ─
  useEffect(() => {
    if (useSessionStore.getState().messages.length === 0) {
      useSessionStore.getState().addMessage({ role: 'assistant', content: WELCOME })
    }
    // Reset local state for the new session
    setSelectedAgeGroup(undefined)
    setAgeGroupError(false)
    setInput('')
  }, [sessionId])  // sessionId changes on every resetSession()

  // ── Send ──────────────────────────────────────────────────────
  async function handleSend() {
    const text = input.trim()
    if (!text || isLoading) return

    // Age group is required before sending the first message
    if (!selectedAgeGroup) {
      setAgeGroupError(true)
      return
    }

    setInput('')
    addMessage({ role: 'patient', content: text })

    try {
      await sendMessage(sessionId, text, selectedAgeGroup)
    } catch {
      useSessionStore.getState().addMessage({
        role: 'assistant',
        content: '⚠️ Connection error. Please check that the server is running and try again.',
      })
      useSessionStore.getState().setLoading(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function selectAgeGroup(value: string) {
    setSelectedAgeGroup(value)
    setAgeGroupError(false)
  }

  const isComplete        = triageResult !== null
  const needsAgeGroup     = !selectedAgeGroup && !isComplete
  const hasPatientSentMsg = messages.some(m => m.role === 'patient')

  return (
    <div className="flex flex-col h-full bg-slate-100 dark:bg-slate-950">

      {/* ── Age group sticky strip (above scroll area) ────────────── */}
      {!isComplete && (
        <div className={`flex-shrink-0 border-b px-4 py-2.5 bg-white dark:bg-slate-900 transition-colors ${
          ageGroupError && !selectedAgeGroup
            ? 'border-red-200 dark:border-red-800'
            : selectedAgeGroup
            ? 'border-emerald-100 dark:border-emerald-900'
            : 'border-slate-200 dark:border-slate-800'
        }`}>
          <div className="flex items-center gap-3 flex-wrap">

            {/* Label */}
            <div className="flex items-center gap-1.5 flex-shrink-0">
              {selectedAgeGroup ? (
                <svg className="w-3.5 h-3.5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <svg className={`w-3.5 h-3.5 ${ageGroupError ? 'text-red-400' : 'text-indigo-400'}`} fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
              )}
              <span className={`text-xs font-semibold uppercase tracking-wider ${
                selectedAgeGroup
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : ageGroupError
                    ? 'text-red-500 dark:text-red-400'
                    : 'text-slate-500 dark:text-slate-400'
              }`}>
                {selectedAgeGroup ? 'Age Group' : ageGroupError ? 'Required' : 'Age Group'}
              </span>
              {!selectedAgeGroup && (
                <span className="text-[10px] font-bold text-red-400 bg-red-50 dark:bg-red-950/50 px-1.5 py-0.5 rounded-full">
                  Required
                </span>
              )}
            </div>

            {/* Chips */}
            <div className="flex items-center gap-1.5">
              {AGE_GROUPS.map(({ label, value, icon }) => {
                const isSelected = selectedAgeGroup === value
                const isLocked   = hasPatientSentMsg
                return (
                  <button
                    key={value}
                    onClick={() => !isLocked && selectAgeGroup(value)}
                    disabled={isLocked}
                    title={isLocked ? 'Age group locked after first message' : `Select ${label}`}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded-lg border text-xs font-medium transition-all ${
                      isSelected && isLocked
                        ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm cursor-default'
                        : isSelected
                        ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
                        : isLocked
                        ? 'bg-slate-50 dark:bg-slate-800 text-slate-300 dark:text-slate-600 border-slate-200 dark:border-slate-700 cursor-not-allowed opacity-40'
                        : ageGroupError
                        ? 'bg-red-50 dark:bg-red-950/30 text-slate-600 dark:text-slate-300 border-red-200 dark:border-red-800 hover:border-indigo-300 dark:hover:border-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 hover:text-indigo-700 dark:hover:text-indigo-300'
                        : 'bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 hover:text-indigo-700 dark:hover:text-indigo-300'
                    }`}
                  >
                    <span>{icon}</span>
                    <span>{label}</span>
                  </button>
                )
              })}

              {/* Locked indicator */}
              {hasPatientSentMsg && selectedAgeGroup && (
                <span className="flex items-center gap-1 text-[10px] text-slate-400 dark:text-slate-500 ml-1">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd"/>
                  </svg>
                  Locked
                </span>
              )}
            </div>

            {/* Inline error */}
            {ageGroupError && !selectedAgeGroup && (
              <span className="text-xs text-red-500 font-medium">
                Please select your age group before sending.
              </span>
            )}
          </div>
        </div>
      )}

      {/* ── Messages ─────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-5 space-y-1 bg-slate-100 dark:bg-slate-950">

        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {/* ── Streaming token ──────────────────────────────────── */}
        {streamingContent && (
          <MessageBubble
            message={{ role: 'assistant', content: streamingContent, timestamp: new Date() }}
            isStreaming
          />
        )}

        {/* ── Severity checkbox form ───────────────────────────── */}
        {pendingOptions && (
          <SymptomOptionsForm
            payload={pendingOptions}
            sessionId={sessionId}
            ageGroup={selectedAgeGroup}
          />
        )}

        {/* ── Typing indicator ─────────────────────────────────── */}
        {isLoading && !streamingContent && (
          <div className="flex items-end gap-2 mb-2">
            <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0">
              <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm rounded-2xl rounded-bl-sm px-4 py-3">
              <div className="flex gap-1.5 items-center">
                <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:160ms]" />
                <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:320ms]" />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ── Input area ───────────────────────────────────────────── */}
      <div className="flex-shrink-0 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-4 py-3">

        {isComplete && (
          <div className="mb-3 text-center text-xs text-slate-400 dark:text-slate-500">
            Triage complete.{' '}
            <button
              onClick={resetSession}
              className="text-indigo-600 dark:text-indigo-400 hover:underline font-medium"
            >
              Start a new session
            </button>{' '}
            to assess another concern.
          </div>
        )}

        <div className="flex items-end gap-2.5">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading || isComplete || !!pendingOptions}
            placeholder={
              isComplete
                ? 'Triage complete — start a new session above'
                : pendingOptions
                  ? 'Please complete the form above…'
                  : needsAgeGroup && !hasPatientSentMsg
                    ? 'Select your age group above to begin…'
                    : 'Describe your symptoms…'
            }
            rows={2}
            className="flex-1 resize-none rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-2.5 text-sm text-slate-800 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-600 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim() || isComplete || !!pendingOptions}
            aria-label="Send"
            className="flex-shrink-0 w-10 h-10 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center shadow-sm"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        <p className="text-[11px] text-slate-300 dark:text-slate-700 mt-2 text-center tracking-wide">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
