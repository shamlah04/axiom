'use client'
// web/app/billing/mock-checkout/page.tsx
// Only reachable in dev/test when STRIPE_SECRET_KEY is not set.
// Simulates the Stripe checkout UI so the frontend flow can be tested end-to-end.
// URL: /billing/mock-checkout?fleet_id=...&tier=tier2

import { useState, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { api } from '@/lib/api/client'

export default function MockCheckoutPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="w-10 h-10 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <MockCheckoutContent />
    </Suspense>
  )
}

function MockCheckoutContent() {
  const params = useSearchParams()
  const router = useRouter()
  const tier = params.get('tier') ?? 'tier2'
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const tierLabels: Record<string, { label: string; price: string }> = {
    tier2: { label: 'Growth', price: '€49 / month' },
    tier3: { label: 'Enterprise', price: '€149 / month' },
  }
  const { label, price } = tierLabels[tier] ?? tierLabels.tier2

  async function handleConfirm() {
    setLoading(true)
    setError('')
    try {
      // In mock mode, directly upgrade via the internal endpoint
      await api.post('/api/v1/fleets/me/upgrade', { new_tier: tier })
      router.push(`/billing/success?session_id=mock_${Date.now()}`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Upgrade failed')
      setLoading(false)
    }
  }

  function handleCancel() {
    router.push('/settings/billing?cancelled=1')
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-4">

        {/* Dev mode banner */}
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-2
                        text-xs text-amber-400 text-center">
          ⚠️ Mock checkout — Stripe is not configured in this environment
        </div>

        {/* Checkout card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-cyan-500 rounded-lg flex items-center justify-center">
              <span className="text-slate-900 font-black text-sm">A</span>
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-100">Axiom Fleet Intelligence</p>
              <p className="text-xs text-slate-500">Subscription upgrade</p>
            </div>
          </div>

          <div className="border-t border-slate-800 pt-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Plan</span>
              <span className="text-slate-100 font-medium">{label}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Amount</span>
              <span className="text-slate-100 font-medium">{price}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Billing</span>
              <span className="text-slate-100">Monthly, cancel anytime</span>
            </div>
          </div>

          {error && (
            <p className="text-xs text-red-400 bg-red-400/10 border border-red-400/20
                          rounded-lg px-3 py-2">{error}</p>
          )}

          <div className="space-y-2 pt-1">
            <button
              onClick={handleConfirm}
              disabled={loading}
              className="w-full bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50
                         text-slate-900 font-semibold py-3 rounded-xl text-sm
                         transition-colors flex items-center justify-center gap-2"
            >
              {loading && (
                <span className="w-4 h-4 border-2 border-slate-900 border-t-transparent
                                 rounded-full animate-spin" />
              )}
              {loading ? 'Processing…' : `Confirm — ${price}`}
            </button>
            <button
              onClick={handleCancel}
              disabled={loading}
              className="w-full text-slate-500 hover:text-slate-400 py-2 text-sm
                         transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
