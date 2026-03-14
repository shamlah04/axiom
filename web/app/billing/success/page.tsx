'use client'
// web/app/billing/success/page.tsx
// Stripe redirects here after a successful checkout session.
// URL: /billing/success?session_id=cs_...

import { useEffect, useState, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { fleetsApi } from '@/lib/api/modules'
import type { PlanSummary } from '@/types/api'

export default function BillingSuccessPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="w-10 h-10 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <BillingSuccessContent />
    </Suspense>
  )
}

function BillingSuccessContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const sessionId = searchParams.get('session_id')

  const [plan, setPlan] = useState<PlanSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [attempts, setAttempts] = useState(0)

  useEffect(() => {
    if (!sessionId) {
      router.replace('/dashboard')
      return
    }

    // Poll the plan endpoint for up to 10s — the webhook may take a moment
    // to fire and upgrade the tier before we read it back.
    let timer: ReturnType<typeof setTimeout>

    async function checkPlan() {
      try {
        const summary = await fleetsApi.plan()
        // Keep polling until tier is no longer tier1 or we've tried 5 times
        if (summary.subscription_tier === 'tier1' && attempts < 5) {
          setAttempts(a => a + 1)
          timer = setTimeout(checkPlan, 2000)
        } else {
          setPlan(summary)
          setLoading(false)
        }
      } catch {
        setLoading(false)
      }
    }

    checkPlan()
    return () => clearTimeout(timer)
  }, [sessionId, attempts]) // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-12 h-12 border-2 border-cyan-500 border-t-transparent
                          rounded-full animate-spin mx-auto" />
          <p className="text-slate-400 text-sm">Confirming your upgrade…</p>
        </div>
      </div>
    )
  }

  const tierLabel = plan?.plan_label ?? 'Growth'
  const tierFeatures: Record<string, string[]> = {
    tier2: [
      'ML-powered profit predictions',
      'Intelligence dashboard',
      'Trend & anomaly detection',
      'Team invites (up to 5 members)',
      'Cross-fleet benchmarking',
    ],
    tier3: [
      'Everything in Growth',
      'Unlimited team members',
      'Priority support',
      'Custom integrations',
      'Dedicated account manager',
    ],
  }
  const features = tierFeatures[plan?.subscription_tier ?? 'tier2'] ?? tierFeatures.tier2

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-6">

        {/* Success card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center space-y-4">
          {/* Animated check */}
          <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center
                          justify-center mx-auto border border-emerald-500/30">
            <span className="text-3xl">✓</span>
          </div>

          <div>
            <h1 className="text-xl font-bold text-slate-100">You're on {tierLabel}</h1>
            <p className="text-sm text-slate-400 mt-1">Payment confirmed — your plan is now active</p>
          </div>

          {/* Feature list */}
          <ul className="text-left space-y-2 pt-2">
            {features.map(f => (
              <li key={f} className="flex items-start gap-2 text-sm text-slate-300">
                <span className="text-cyan-400 mt-0.5 shrink-0">◈</span>
                {f}
              </li>
            ))}
          </ul>
        </div>

        {/* Actions */}
        <div className="space-y-2">
          <Link
            href="/intelligence"
            className="block w-full text-center bg-cyan-500 hover:bg-cyan-400
                       text-slate-900 font-semibold py-3 rounded-xl text-sm transition-colors"
          >
            Open Intelligence Dashboard →
          </Link>
          <Link
            href="/dashboard"
            className="block w-full text-center text-slate-400 hover:text-slate-300
                       py-3 text-sm transition-colors"
          >
            Back to dashboard
          </Link>
        </div>
      </div>
    </div>
  )
}
