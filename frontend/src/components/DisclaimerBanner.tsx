import React from 'react'

export default function DisclaimerBanner() {
  return (
    <div className="bg-amber-50 border-t border-amber-200 px-4 py-2 text-center text-xs text-amber-800">
      ⚠️{' '}
      <strong>This is NOT a medical diagnosis.</strong> This is an automated triage routing assistant only.
      In an emergency, call <strong>115</strong> or <strong>1122</strong> immediately.
    </div>
  )
}
