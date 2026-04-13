import React from 'react'
import ChatWindow from './components/ChatWindow'
import RoutingCard from './components/RoutingCard'
import DisclaimerBanner from './components/DisclaimerBanner'
import { useSessionStore } from './store/sessionStore'

export default function App() {
  const triageResult = useSessionStore((s) => s.triageResult)

  return (
    <div className="flex flex-col h-screen">
      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Chat (always visible) */}
        <div className={`flex flex-col ${triageResult ? 'w-full md:w-1/2' : 'w-full'} border-r border-gray-200 transition-all duration-300`}>
          <ChatWindow />
        </div>

        {/* Right: Triage result card (visible after triage completes) */}
        {triageResult && (
          <div className="hidden md:flex flex-col w-1/2 bg-gray-50 overflow-y-auto">
            <div className="p-6 space-y-6">
              {/* Header */}
              <div>
                <h1 className="text-xl font-bold text-gray-800">Triage Assessment</h1>
                <p className="text-sm text-gray-500 mt-1">
                  Based on the symptoms you described, here is your routing recommendation.
                </p>
              </div>

              <RoutingCard result={triageResult} />

              {/* Instructions */}
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-800">
                <strong>📍 At Reception:</strong> Show this screen to the reception desk.
                They will guide you to the correct department.
              </div>

              {/* Safety reminder */}
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
                <strong>⚠️ Important:</strong> If your condition worsens at any point —
                especially difficulty breathing, chest pain, or loss of consciousness —
                go to the Emergency Room immediately or call <strong>115 / 1122</strong>.
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Persistent disclaimer banner */}
      <DisclaimerBanner />
    </div>
  )
}
