import React, { useState, useRef, useEffect } from 'react'
import { useSessionStore } from '../store/sessionStore'
import { sendMessage } from '../api/triageClient'
import MessageBubble from './MessageBubble'

export default function ChatWindow() {
  const [input, setInput] = useState('')
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

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  // Show welcome message on mount — read from getState() to avoid StrictMode double-run
  useEffect(() => {
    if (useSessionStore.getState().messages.length === 0) {
      useSessionStore.getState().addMessage({
        role: 'assistant',
        content:
          "Hello! I'm the **Hospital Triage Assistant**.\n\nI'll help assess your symptoms and guide you to the right department.\n\nPlease tell me: **What is your main symptom today?**",
      })
    }
  }, [])

  async function handleSend() {
    const text = input.trim()
    if (!text || isLoading) return

    setInput('')
    addMessage({ role: 'patient', content: text })

    try {
      await sendMessage(sessionId, text)
    } catch (err) {
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

  const isComplete = triageResult !== null

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-blue-700 text-white px-5 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">🏥</span>
          <div>
            <div className="font-bold text-sm">Hospital Triage Assistant</div>
            <div className="text-xs text-blue-200">Symptom Assessment & Routing</div>
          </div>
        </div>
        <button
          onClick={resetSession}
          className="text-xs bg-blue-600 hover:bg-blue-500 px-3 py-1.5 rounded-lg transition-colors"
        >
          New Session
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-1 bg-gray-50">
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {/* Streaming message */}
        {streamingContent && (
          <MessageBubble
            message={{ role: 'assistant', content: streamingContent, timestamp: new Date() }}
            isStreaming
          />
        )}

        {/* Loading indicator */}
        {isLoading && !streamingContent && (
          <div className="flex justify-start mb-3">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm mr-2 mt-1">
              🏥
            </div>
            <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-none px-4 py-3 shadow-sm">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:0ms]" />
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:150ms]" />
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 bg-white p-4">
        {isComplete && (
          <div className="mb-3 text-center text-sm text-gray-500">
            Triage complete.{' '}
            <button onClick={resetSession} className="text-blue-600 hover:underline font-medium">
              Start a new session
            </button>{' '}
            to assess another concern.
          </div>
        )}
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading || isComplete}
            placeholder={
              isComplete
                ? 'Triage complete — start a new session for another concern'
                : 'Describe your symptoms...'
            }
            rows={2}
            className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:text-gray-400"
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim() || isComplete}
            className="px-4 py-2.5 bg-blue-600 text-white rounded-xl font-medium text-sm hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
            Send
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-2 text-center">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
