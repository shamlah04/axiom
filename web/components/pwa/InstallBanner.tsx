'use client'
// components/pwa/InstallBanner.tsx
// Shows an install prompt for Android, and iOS instructions for iPhone

import { useState } from 'react'
import { usePWA } from '@/hooks/usePWA'

export function InstallBanner() {
  const { installPrompt, isInstalled, isIOS, promptInstall } = usePWA()
  const [dismissed, setDismissed] = useState(false)
  const [showIOSGuide, setShowIOSGuide] = useState(false)

  // Don't show if installed, dismissed, or nothing to show
  if (isInstalled || dismissed) return null
  if (!installPrompt && !isIOS) return null

  return (
    <>
      {/* Android / Desktop banner */}
      {installPrompt && (
        <div className="fixed bottom-0 left-0 right-0 z-50 p-4 bg-slate-800 border-t border-slate-700 flex items-center gap-3"
          style={{ paddingBottom: 'calc(env(safe-area-inset-bottom) + 1rem)' }}>
          <div className="w-9 h-9 bg-cyan-500 rounded-lg flex items-center justify-center shrink-0">
            <span className="text-slate-900 text-sm font-black">A</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-slate-100">Install Axiom</p>
            <p className="text-[11px] text-slate-400 truncate">Add to home screen for quick access</p>
          </div>
          <button
            onClick={() => promptInstall()}
            className="px-3 py-1.5 bg-cyan-500 text-slate-900 rounded-lg text-xs font-semibold shrink-0"
          >
            Install
          </button>
          <button
            onClick={() => setDismissed(true)}
            className="text-slate-500 hover:text-slate-300 text-lg leading-none shrink-0"
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>
      )}

      {/* iOS banner */}
      {isIOS && !installPrompt && (
        <div className="fixed bottom-0 left-0 right-0 z-50 p-4 bg-slate-800 border-t border-slate-700"
          style={{ paddingBottom: 'calc(env(safe-area-inset-bottom) + 1rem)' }}>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-9 h-9 bg-cyan-500 rounded-lg flex items-center justify-center shrink-0">
              <span className="text-slate-900 text-sm font-black">A</span>
            </div>
            <div className="flex-1">
              <p className="text-xs font-semibold text-slate-100">Install Axiom on iPhone</p>
              <button
                onClick={() => setShowIOSGuide(!showIOSGuide)}
                className="text-[11px] text-cyan-400 underline"
              >
                {showIOSGuide ? 'Hide instructions' : 'How to install →'}
              </button>
            </div>
            <button
              onClick={() => setDismissed(true)}
              className="text-slate-500 hover:text-slate-300 text-lg leading-none"
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
          {showIOSGuide && (
            <ol className="space-y-1 text-xs text-slate-400 pl-2">
              <li>1. Tap the <strong className="text-slate-300">Share</strong> button (↑) at the bottom of Safari</li>
              <li>2. Scroll down and tap <strong className="text-slate-300">&quot;Add to Home Screen&quot;</strong></li>
              <li>3. Tap <strong className="text-slate-300">&quot;Add&quot;</strong> in the top right</li>
            </ol>
          )}
        </div>
      )}
    </>
  )
}
