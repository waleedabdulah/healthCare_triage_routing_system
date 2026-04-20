import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'

export type UrgencyLevel = 'EMERGENCY' | 'URGENT' | 'NON_URGENT' | 'SELF_CARE' | null

export interface OptionsPayload {
  question: string
  options: string[]
  multi_select: boolean
}

export interface Message {
  role: 'patient' | 'assistant'
  content: string
  timestamp: Date
  isStreaming?: boolean
}

export interface TriageResult {
  urgencyLevel: UrgencyLevel
  routedDepartment: string | null
  isEmergency: boolean
  finalResponse: string | null
}

interface SessionState {
  sessionId: string
  messages: Message[]
  triageResult: TriageResult | null
  isLoading: boolean
  streamingContent: string
  appointmentBooked: boolean        // true once appointment is confirmed this session
  pendingAppointmentId: string | null  // set after booking created, cleared on confirm
  pendingOptions: OptionsPayload | null  // set when severity checkbox form is active

  // Actions
  addMessage: (msg: Omit<Message, 'timestamp'>) => void
  updateStreamingContent: (chunk: string) => void
  finalizeStreamingMessage: () => void
  setTriageResult: (result: TriageResult) => void
  setLoading: (v: boolean) => void
  setAppointmentBooked: () => void
  setPendingAppointmentId: (id: string | null) => void
  setPendingOptions: (opts: OptionsPayload | null) => void
  resetSession: () => void
}

const defaultResult: TriageResult = {
  urgencyLevel: null,
  routedDepartment: null,
  isEmergency: false,
  finalResponse: null,
}

export const useSessionStore = create<SessionState>((set, get) => ({
  sessionId: uuidv4(),
  messages: [],
  triageResult: null,
  isLoading: false,
  streamingContent: '',
  appointmentBooked: false,
  pendingAppointmentId: null,
  pendingOptions: null,

  addMessage: (msg) =>
    set((state) => ({
      messages: [...state.messages, { ...msg, timestamp: new Date() }],
    })),

  updateStreamingContent: (chunk) =>
    set((state) => ({ streamingContent: state.streamingContent + chunk })),

  finalizeStreamingMessage: () => {
    const content = get().streamingContent
    if (content) {
      set((state) => ({
        messages: [
          ...state.messages,
          { role: 'assistant', content, timestamp: new Date() },
        ],
        streamingContent: '',
      }))
    }
  },

  setTriageResult: (result) => set({ triageResult: result }),

  setLoading: (v) => set({ isLoading: v }),

  setAppointmentBooked: () => set({ appointmentBooked: true, pendingAppointmentId: null }),

  setPendingAppointmentId: (id) => set({ pendingAppointmentId: id }),

  setPendingOptions: (opts) => set({ pendingOptions: opts }),

  resetSession: () =>
    set({
      sessionId: uuidv4(),
      messages: [],
      triageResult: null,
      isLoading: false,
      streamingContent: '',
      appointmentBooked: false,
      pendingAppointmentId: null,
      pendingOptions: null,
    }),
}))
