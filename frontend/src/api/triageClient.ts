import { useSessionStore, TriageResult } from '../store/sessionStore'

const API_BASE = '/api/v1'

export async function sendMessage(
  sessionId: string,
  message: string,
  ageGroup?: string
): Promise<void> {
  const store = useSessionStore.getState()
  store.setLoading(true)

  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message, age_group: ageGroup }),
  })

  if (!response.ok || !response.body) {
    store.setLoading(false)
    throw new Error(`API error: ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const data = line.slice(6).trim()

      if (data === '[DONE]') {
        store.finalizeStreamingMessage()
        store.setLoading(false)
        return
      }

      try {
        const event = JSON.parse(data)

        if (event.type === 'token') {
          // Triage result tokens are displayed in the right-panel card, not in the chat.
          // Discard them here so no duplicate streaming bubble appears in chat.
        } else if (event.type === 'message') {
          // Conversational message from symptom collector (question / acknowledgment)
          store.finalizeStreamingMessage()
          store.addMessage({ role: 'assistant', content: event.content })
        } else if (event.type === 'triage_complete') {
          store.finalizeStreamingMessage()   // clear any residual streaming content

          const result: TriageResult = {
            urgencyLevel: event.urgency_level ?? null,
            routedDepartment: event.routed_department ?? null,
            estimatedWaitMinutes: event.estimated_wait_minutes ?? null,
            nextAvailableSlot: event.next_available_slot ?? null,
            isEmergency: event.is_emergency ?? false,
            finalResponse: event.final_response ?? null,
          }
          store.setTriageResult(result)

          // Only add a chat message for emergencies — the result card handles all other cases.
          if (event.is_emergency && event.final_response) {
            store.addMessage({ role: 'assistant', content: event.final_response })
          }
        }
      } catch {
        // Non-JSON line — ignore
      }
    }
  }

  store.finalizeStreamingMessage()
  store.setLoading(false)
}
