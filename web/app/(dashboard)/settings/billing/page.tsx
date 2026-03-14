'use client'
// web/app/settings/billing/page.tsx
// The main billing management page.
// - Shows current plan, usage, feature matrix
// - Upgrade button → POST /billing/checkout → redirect to Stripe
// - Manage subscription → GET /billing/portal → redirect to Stripe portal
// - Handles ?cancelled=1 query param from Stripe cancel redirect

import { useEffect, useState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { fleetsApi, billingApi } from '@/lib/api/modules'
import { Card, CardHeader, CardContent, Button, Badge } from '@/components/ui'
import { formatCurrency } from '@/lib/utils'
import type { PlanSummary } from '@/types/api'

const TIER_CONFIG = {
  tier1: {
    label: 'Launch',
    color: 'text-slate-400',
    badge: 'bg-slate-700 text-slate-300',
    description: 'For solo operators getting started',
    monthlyPrice: null,
  },
  tier2: {
    label: 'Growth',
    color: 'text-cyan-400',
    badge: 'bg-cyan-500/10 text-cyan-400',
    description: 'For growing fleets that need intelligence',
    monthlyPrice: 49,
  },
  tier3: {
    label: 'Enterprise',
    color: 'text-violet-400',
    badge: 'bg-violet-500/10 text-violet-400',
    description: 'For large operations and teams',
    monthlyPrice: 149,
  },
} as const

type Tier = keyof typeof TIER_CONFIG

const FEATURE_ROWS: { label: string; tier1: boolean; tier2: boolean; tier3: boolean }[] = [
  { label: 'Profit prediction engine', tier1: true, tier2: true, tier3: true },
  { label: 'Scenario simulator', tier1: true, tier2: true, tier3: true },
  { label: 'Fleet dashboard & analytics', tier1: true, tier2: true, tier3: true },
  { label: 'Intelligence dashboard', tier1: false, tier2: true, tier3: true },
  { label: 'Trend & anomaly detection', tier1: false, tier2: true, tier3: true },
  { label: 'Cross-fleet benchmarking', tier1: false, tier2: true, tier3: true },
  { label: 'Team invites', tier1: false, tier2: true, tier3: true },
  { label: 'Unlimited team members', tier1: false, tier2: false, tier3: true },
  { label: 'Priority support', tier1: false, tier2: false, tier3: true },
]

export default function BillingPage() {
  return (
    <Suspense fallback={
      <div className="space-y-6 animate-pulse">
        <div className="h-7 w-40 bg-slate-800 rounded" />
        <div className="h-32 bg-slate-800 rounded-xl" />
        <div className="h-64 bg-slate-800 rounded-xl" />
      </div>
    }>
      <BillingPageContent />
    </Suspense>
  )
}

function BillingPageContent() {
  const searchParams = useSearchParams()
  const cancelled = searchParams.get('cancelled') === '1'

  const [plan, setPlan] = useState<PlanSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [upgrading, setUpgrading] = useState<Tier | null>(null)
  const [portalLoading, setPortalLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    fleetsApi.plan()
      .then(setPlan)
      .catch(() => setError('Failed to load plan details'))
      .finally(() => setLoading(false))
  }, [])

  async function handleUpgrade(tier: Tier) {
    setError('')
    setUpgrading(tier)
    try {
      const { checkout_url } = await billingApi.checkout(tier)
      window.location.href = checkout_url
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to start checkout')
      setUpgrading(null)
    }
  }

  async function handleManageSubscription() {
    setError('')
    setPortalLoading(true)
    try {
      const { portal_url } = await billingApi.portal()
      window.location.href = portal_url
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to open billing portal')
      setPortalLoading(false)
    }
  }

  const currentTier = (plan?.subscription_tier ?? 'tier1') as Tier
  const tierOrder = { tier1: 1, tier2: 2, tier3: 3 }

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-7 w-40 bg-slate-800 rounded" />
        <div className="h-32 bg-slate-800 rounded-xl" />
        <div className="h-64 bg-slate-800 rounded-xl" />
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-lg font-bold text-slate-100">Billing & Plan</h1>
        <p className="text-xs text-slate-500 mt-0.5">Manage your subscription and usage</p>
      </div>

      {/* Cancelled banner */}
      {cancelled && (
        <div className="bg-slate-800 border border-slate-700 rounded-xl px-4 py-3
                        text-sm text-slate-300 flex items-center gap-2">
          <span>↩</span>
          Checkout was cancelled — no changes were made to your plan.
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3
                        text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Current plan card */}
      <Card>
        <CardHeader>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Current plan</p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className={`text-xl font-bold ${TIER_CONFIG[currentTier].color}`}>
                  {TIER_CONFIG[currentTier].label}
                </span>
                {plan?.trial_active && (
                  <Badge className="bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    Trial — {plan.trial_days_remaining}d left
                  </Badge>
                )}
                {plan?.trial_expired && (
                  <Badge className="bg-red-500/10 text-red-400 border border-red-500/20">
                    Trial expired
                  </Badge>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                {TIER_CONFIG[currentTier].description}
              </p>
            </div>
            {currentTier !== 'tier1' && (
              <Button
                size="sm"
                variant="secondary"
                onClick={handleManageSubscription}
                loading={portalLoading}
              >
                Manage subscription
              </Button>
            )}
          </div>

          {/* Usage */}
          {plan && (
            <div className="grid grid-cols-2 gap-4 pt-2 border-t border-slate-800">
              {[
                { label: 'Trucks', used: plan.usage.trucks, max: plan.limits.max_trucks },
                { label: 'Drivers', used: plan.usage.drivers, max: plan.limits.max_drivers },
              ].map(item => (
                <div key={item.label}>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-slate-400">{item.label}</span>
                    <span className="text-slate-300 font-mono">
                      {item.used} / {item.max === 9999 ? '∞' : item.max}
                    </span>
                  </div>
                  <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${item.max === 9999
                          ? 'bg-cyan-500'
                          : item.used / item.max > 0.8
                            ? 'bg-red-500'
                            : item.used / item.max > 0.6
                              ? 'bg-amber-500'
                              : 'bg-cyan-500'
                        }`}
                      style={{ width: `${Math.min(100, (item.used / Math.min(item.max, 9999)) * 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Upgrade options */}
      {currentTier !== 'tier3' && (
        <Card>
          <CardHeader>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Upgrade plan</p>
          </CardHeader>
          <CardContent className="space-y-3">
            {(['tier2', 'tier3'] as Tier[])
              .filter(t => tierOrder[t] > tierOrder[currentTier])
              .map(tier => {
                const cfg = TIER_CONFIG[tier]
                return (
                  <div
                    key={tier}
                    className="flex items-center justify-between p-4 rounded-xl
                               border border-slate-700 hover:border-slate-600 transition-colors"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-bold ${cfg.color}`}>{cfg.label}</span>
                        <span className="text-xs text-slate-400">
                          €{cfg.monthlyPrice}/mo
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">{cfg.description}</p>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => handleUpgrade(tier)}
                      loading={upgrading === tier}
                      disabled={upgrading !== null && upgrading !== tier}
                    >
                      Upgrade →
                    </Button>
                  </div>
                )
              })}
          </CardContent>
        </Card>
      )}

      {/* Feature comparison table */}
      <Card>
        <CardHeader>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Plan comparison
          </p>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto -mx-1">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-800">
                  <th className="text-left py-2 pr-4 text-slate-500 font-normal w-1/2">Feature</th>
                  {(['tier1', 'tier2', 'tier3'] as Tier[]).map(t => (
                    <th key={t} className="text-center py-2 px-3 font-semibold">
                      <span className={currentTier === t ? TIER_CONFIG[t].color : 'text-slate-500'}>
                        {TIER_CONFIG[t].label}
                        {currentTier === t && ' ←'}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {FEATURE_ROWS.map(row => (
                  <tr key={row.label} className="border-b border-slate-800/50">
                    <td className="py-2 pr-4 text-slate-400">{row.label}</td>
                    {(['tier1', 'tier2', 'tier3'] as Tier[]).map(t => (
                      <td key={t} className="text-center py-2 px-3">
                        {row[t]
                          ? <span className="text-emerald-400">✓</span>
                          : <span className="text-slate-700">—</span>
                        }
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
