import React, { useState, useRef, useEffect } from 'react'
import { useSessionStore } from '../store/sessionStore'
import { sendMessage } from '../api/triageClient'
import MessageBubble from './MessageBubble'

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

  const isComplete       = triageResult !== null
  const needsAgeGroup    = !selectedAgeGroup && !isComplete
  const hasPatientSentMsg = messages.some(m => m.role === 'patient')

  return (
    <div className="flex flex-col h-full bg-slate-100 dark:bg-slate-950">

      {/* ── Messages ─────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-5 space-y-1 bg-slate-100 dark:bg-slate-950">

        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {/* ── Age group selection card ─────────────────────────── */}
        {/* Shown after welcome message, until triage is complete  */}
        {!isComplete && (
          <div className="flex items-end gap-2 mb-3">
            {/* Avatar to match assistant bubble style */}
            <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0 mb-0.5 shadow-sm opacity-0">
              {/* invisible spacer so card aligns with chat bubbles */}
            </div>

            <div className={`w-full max-w-[78%] rounded-2xl rounded-bl-sm border shadow-sm transition-all duration-200 ${
              selectedAgeGroup
                ? 'bg-white dark:bg-slate-800 border-emerald-200 dark:border-emerald-800'
                : ageGroupError
                  ? 'bg-white dark:bg-slate-800 border-red-300 dark:border-red-700'
                  : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700'
            }`}>

              {/* Card header */}
              <div className={`flex items-center justify-between px-4 pt-3 pb-2 border-b ${
                selectedAgeGroup
                  ? 'border-emerald-100 dark:border-emerald-900'
                  : ageGroupError
                    ? 'border-red-100 dark:border-red-900'
                    : 'border-slate-100 dark:border-slate-700'
              }`}>
                <div className="flex items-center gap-1.5">
                  {selectedAgeGroup && hasPatientSentMsg ? (
                    <svg className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd"/>
                    </svg>
                  ) : selectedAgeGroup ? (
                    <svg className="w-3.5 h-3.5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    <svg className={`w-3.5 h-3.5 ${ageGroupError ? 'text-red-400' : 'text-indigo-400'}`} fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                  )}
                  <p className={`text-xs font-semibold uppercase tracking-wider ${
                    selectedAgeGroup && hasPatientSentMsg
                      ? 'text-slate-400 dark:text-slate-500'
                      : selectedAgeGroup
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : ageGroupError
                        ? 'text-red-500 dark:text-red-400'
                        : 'text-slate-500 dark:text-slate-400'
                  }`}>
                    {selectedAgeGroup && hasPatientSentMsg ? 'Age Group Locked' : selectedAgeGroup ? 'Age Group Selected' : 'Select Age Group'}
                  </p>
                  {!selectedAgeGroup && (
                    <span className="text-[10px] font-bold text-red-400 bg-red-50 dark:bg-red-950/50 px-1.5 py-0.5 rounded-full">
                      Required
                    </span>
                  )}
                </div>

                {/* Selected confirmation label */}
                {selectedAgeGroup && (
                  <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">
                    {AGE_GROUPS.find(g => g.value === selectedAgeGroup)?.icon}{' '}
                    {AGE_GROUPS.find(g => g.value === selectedAgeGroup)?.label}
                  </span>
                )}
              </div>

              {/* Chips */}
              <div className="px-4 py-3 flex gap-2 flex-wrap">
                {AGE_GROUPS.map(({ label, value, icon }) => {
                  const isSelected = selectedAgeGroup === value
                  const isLocked   = hasPatientSentMsg
                  return (
                    <button
                      key={value}
                      onClick={() => !isLocked && selectAgeGroup(value)}
                      disabled={isLocked}
                      className={`flex items-center gap-1.5 px-3 py-2 rounded-xl border text-xs font-medium transition-all ${
                        isSelected && isLocked
                          ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm opacity-80 cursor-not-allowed'
                          : isSelected
                          ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm scale-105'
                          : isLocked
                          ? 'bg-slate-50 dark:bg-slate-800 text-slate-300 dark:text-slate-600 border-slate-200 dark:border-slate-700 cursor-not-allowed opacity-40'
                          : 'bg-slate-50 dark:bg-slate-700 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-600 hover:border-indigo-300 dark:hover:border-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 hover:text-indigo-700 dark:hover:text-indigo-300'
                      }`}
                    >
                      <span className="text-sm">{icon}</span>
                      <span>{label}</span>
                    </button>
                  )
                })}
                {hasPatientSentMsg && (
                  <span className="flex items-center gap-1 text-[10px] text-slate-400 dark:text-slate-500 ml-1 self-center">
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd"/>
                    </svg>
                    Locked
                  </span>
                )}
              </div>

              {/* Error message */}
              {ageGroupError && !selectedAgeGroup && (
                <div className="mx-4 mb-3 flex items-center gap-1.5 text-xs text-red-500 font-medium bg-red-50 dark:bg-red-950/30 border border-red-100 dark:border-red-900 rounded-lg px-3 py-2">
                  <svg className="w-3.5 h-3.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                  </svg>
                  Please select your age group before sending a message.
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Streaming token ──────────────────────────────────── */}
        {streamingContent && (
          <MessageBubble
            message={{ role: 'assistant', content: streamingContent, timestamp: new Date() }}
            isStreaming
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
            disabled={isLoading || isComplete}
            placeholder={
              isComplete
                ? 'Triage complete — start a new session above'
                : needsAgeGroup && !hasPatientSentMsg
                  ? 'Select your age group above to begin…'
                  : 'Describe your symptoms…'
            }
            rows={2}
            className="flex-1 resize-none rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-2.5 text-sm text-slate-800 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-600 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim() || isComplete}
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
