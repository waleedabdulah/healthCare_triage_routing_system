import React from 'react'
import { UrgencyLevel } from '../store/sessionStore'

interface Props {
  level: UrgencyLevel
}

const CONFIG: Record<NonNullable<UrgencyLevel>, { label: string; emoji: string; bg: string; text: string; border: string }> = {
  EMERGENCY: {
    label: 'EMERGENCY',
    emoji: '🔴',
    bg: 'bg-red-50',
    text: 'text-red-700',
    border: 'border-red-400',
  },
  URGENT: {
    label: 'URGENT',
    emoji: '🟠',
    bg: 'bg-orange-50',
    text: 'text-orange-700',
    border: 'border-orange-400',
  },
  NON_URGENT: {
    label: 'NON-URGENT',
    emoji: '🟡',
    bg: 'bg-yellow-50',
    text: 'text-yellow-700',
    border: 'border-yellow-400',
  },
  SELF_CARE: {
    label: 'SELF-CARE',
    emoji: '🟢',
    bg: 'bg-green-50',
    text: 'text-green-700',
    border: 'border-green-400',
  },
}

export default function UrgencyBadge({ level }: Props) {
  if (!level) return null
  const { label, emoji, bg, text, border } = CONFIG[level]

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border-2 ${bg} ${text} ${border} font-bold text-sm`}>
      <span>{emoji}</span>
      <span>{label}</span>
    </div>
  )
}
