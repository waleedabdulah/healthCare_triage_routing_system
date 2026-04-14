export default function DisclaimerBanner() {
  return (
    <footer className="flex-shrink-0 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800">
      <div className="px-4 py-2.5 flex items-center justify-center gap-2">
        <svg className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd"
            d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
            clipRule="evenodd" />
        </svg>
        <p className="text-xs text-slate-400 dark:text-slate-500">
          <strong className="font-semibold text-slate-500 dark:text-slate-400">Not a medical diagnosis.</strong>{' '}
          Automated triage routing only. Emergency? Call{' '}
          <strong className="text-slate-600 dark:text-slate-300">115</strong> or{' '}
          <strong className="text-slate-600 dark:text-slate-300">1122</strong> immediately.
        </p>
      </div>
    </footer>
  )
}
