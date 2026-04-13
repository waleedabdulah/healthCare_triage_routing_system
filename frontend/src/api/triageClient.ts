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
          store.updateStreamingContent(event.content)
        } else if (event.type === 'message') {
          // Clean non-streaming message (e.g. symptom collector response or gibberish rejection)
          store.finalizeStreamingMessage()
          store.addMessage({ role: 'assistant', content: event.content })
        } else if (event.type === 'triage_complete') {
          // Finalize any streaming text first
          store.finalizeStreamingMessage()

          const result: TriageResult = {
            urgencyLevel: event.urgency_level ?? null,
            routedDepartment: event.routed_department ?? null,
            estimatedWaitMinutes: event.estimated_wait_minutes ?? null,
            nextAvailableSlot: event.next_available_slot ?? null,
            isEmergency: event.is_emergency ?? false,
            finalResponse: event.final_response ?? null,
          }
          store.setTriageResult(result)

          // Show the final response as a message if not already shown
          if (event.final_response && !store.messages.find(m => m.content === event.final_response)) {
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
