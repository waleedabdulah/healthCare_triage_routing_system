import React from 'react'
import { TriageResult } from '../store/sessionStore'
import UrgencyBadge from './UrgencyBadge'

interface Props {
  result: TriageResult
}

const DEPT_ICONS: Record<string, string> = {
  'Emergency Room': '🚨',
  'Cardiology': '❤️',
  'Neurology': '🧠',
  'ENT': '👂',
  'Dermatology': '🩹',
  'Gastroenterology': '🫁',
  'Pulmonology': '🫧',
  'Orthopedics': '🦴',
  'General Medicine': '🩺',
  'Pediatrics': '👶',
}

const URGENCY_ACTION: Record<string, string> = {
  EMERGENCY: 'Go to Emergency Room immediately',
  URGENT: 'Visit OPD today — urgent consultation',
  NON_URGENT: 'Schedule an OPD appointment',
  SELF_CARE: 'Monitor at home — visit OPD if worsens',
}

export default function RoutingCard({ result }: Props) {
  const { urgencyLevel, routedDepartment, estimatedWaitMinutes, nextAvailableSlot, isEmergency } = result
  const deptIcon = routedDepartment ? (DEPT_ICONS[routedDepartment] ?? '🏥') : '🏥'
  const action = urgencyLevel ? (URGENCY_ACTION[urgencyLevel] ?? '') : ''

  return (
    <div className={`rounded-xl border-2 p-5 space-y-4 ${isEmergency ? 'border-red-400 bg-red-50' : 'border-blue-200 bg-white'}`}>
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-gray-800">Triage Result</h2>
        {urgencyLevel && <UrgencyBadge level={urgencyLevel} />}
      </div>

      {isEmergency && (
        <div className="bg-red-600 text-white rounded-lg p-3 text-center font-bold animate-pulse">
          🚨 GO TO EMERGENCY ROOM NOW 🚨
        </div>
      )}

      {routedDepartment && (
        <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg border border-blue-100">
          <span className="text-2xl">{deptIcon}</span>
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide">Department</div>
            <div className="font-semibold text-gray-800">{routedDepartment}</div>
          </div>
        </div>
      )}

      {action && (
        <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Recommended Action</div>
          <div className="font-medium text-gray-700">{action}</div>
        </div>
      )}

      {(estimatedWaitMinutes !== null || nextAvailableSlot) && (
        <div className="flex gap-3">
          {estimatedWaitMinutes !== null && (
            <div className="flex-1 p-3 bg-gray-50 rounded-lg border border-gray-200 text-center">
              <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Wait Time</div>
              <div className="font-bold text-gray-800 text-lg">
                {estimatedWaitMinutes === 0 ? '⚡ Immediate' : `~${estimatedWaitMinutes} min`}
              </div>
            </div>
          )}
          {nextAvailableSlot && (
            <div className="flex-1 p-3 bg-gray-50 rounded-lg border border-gray-200 text-center">
              <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Next Slot</div>
              <div className="font-bold text-gray-800">{nextAvailableSlot}</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
