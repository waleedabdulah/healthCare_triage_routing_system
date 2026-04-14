import { UrgencyLevel } from '../store/sessionStore'

interface Props { level: UrgencyLevel }

const CONFIG: Record<NonNullable<UrgencyLevel>, {
  label: string; dot: string; bg: string; text: string; ring: string
}> = {
  EMERGENCY: {
    label: 'EMERGENCY',
    dot:  'bg-red-500',
    bg:   'bg-red-50 dark:bg-red-950/60',
    text: 'text-red-700 dark:text-red-400',
    ring: 'ring-red-200 dark:ring-red-900',
  },
  URGENT: {
    label: 'URGENT',
    dot:  'bg-orange-400',
    bg:   'bg-orange-50 dark:bg-orange-950/60',
    text: 'text-orange-700 dark:text-orange-400',
    ring: 'ring-orange-200 dark:ring-orange-900',
  },
  NON_URGENT: {
    label: 'NON-URGENT',
    dot:  'bg-amber-400',
    bg:   'bg-amber-50 dark:bg-amber-950/60',
    text: 'text-amber-700 dark:text-amber-400',
    ring: 'ring-amber-200 dark:ring-amber-900',
  },
  SELF_CARE: {
    label: 'SELF-CARE',
    dot:  'bg-emerald-500',
    bg:   'bg-emerald-50 dark:bg-emerald-950/60',
    text: 'text-emerald-700 dark:text-emerald-400',
    ring: 'ring-emerald-200 dark:ring-emerald-900',
  },
}

export default function UrgencyBadge({ level }: Props) {
  if (!level) return null
  const { label, dot, bg, text, ring } = CONFIG[level]
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold tracking-wide ring-1 ${bg} ${text} ${ring}`}>
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dot}`} />
      {label}
    </span>
  )
}
