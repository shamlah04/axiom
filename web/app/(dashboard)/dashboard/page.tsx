'use client'
// app/(dashboard)/dashboard/page.tsx
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { dashboardApi } from '@/lib/api/dashboard'
import { analyticsApi } from '@/lib/api/analytics'
import { StatCard, Card, CardHeader, CardContent, Button } from '@/components/ui'
import { ProfitTrendChart } from '@/components/charts/ProfitTrendChart'
import { formatCurrency, formatPercent } from '@/lib/utils'
import type { DashboardSummary, MonthlyTrend } from '@/types/api'

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [trends, setTrends] = useState<MonthlyTrend[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([dashboardApi.summary(), analyticsApi.trends(6)])
      .then(([s, t]) => { setSummary(s); setTrends(t) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <PageSkeleton />

  const acceptRate = summary && summary.total_jobs > 0
    ? Math.round((summary.accepted_jobs / summary.total_jobs) * 100)
    : 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-slate-100">Dashboard</h1>
          <p className="text-xs text-slate-500 mt-0.5">Fleet performance overview</p>
        </div>
        <Link href="/jobs/new">
          <Button size="sm">+ New job</Button>
        </Link>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total revenue"
          value={formatCurrency(summary?.total_revenue)}
          sub={`${summary?.total_jobs ?? 0} jobs`}
        />
        <StatCard
          label="Net profit"
          value={formatCurrency(summary?.total_profit)}
          accent={summary && summary.total_profit > 0 ? 'text-emerald-400' : 'text-red-400'}
        />
        <StatCard
          label="Avg margin"
          value={formatPercent(summary?.avg_margin_pct)}
          accent={
            summary?.avg_margin_pct == null ? undefined :
            summary.avg_margin_pct >= 15 ? 'text-emerald-400' :
            summary.avg_margin_pct >= 5  ? 'text-amber-400' : 'text-red-400'
          }
        />
        <StatCard
          label="Accept rate"
          value={`${acceptRate}%`}
          sub={`${summary?.accepted_jobs ?? 0} accepted · ${summary?.rejected_jobs ?? 0} rejected`}
        />
      </div>

      {/* Profit Trend Chart */}
      <Card>
        <CardHeader>
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Profit trend — last 6 months
          </h2>
        </CardHeader>
        <CardContent>
          {trends.length === 0 ? (
            <div className="h-48 flex items-center justify-center text-slate-600 text-sm">
              No data yet — submit and accept some jobs first
            </div>
          ) : (
            <ProfitTrendChart data={trends} />
          )}
        </CardContent>
      </Card>

      {/* Bottom row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Job mix */}
        <Card>
          <CardHeader>
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Job status mix</h2>
          </CardHeader>
          <CardContent>
            {summary && summary.total_jobs > 0 ? (
              <div className="space-y-3">
                {[
                  { label: 'Accepted', count: summary.accepted_jobs, color: 'bg-emerald-500' },
                  { label: 'Rejected', count: summary.rejected_jobs, color: 'bg-red-500' },
                  { label: 'Pending',
                    count: summary.total_jobs - summary.accepted_jobs - summary.rejected_jobs - (summary.completed_jobs ?? 0),
                    color: 'bg-slate-600' },
                ].map(row => (
                  <div key={row.label}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-400">{row.label}</span>
                      <span className="text-slate-300 font-mono">{row.count}</span>
                    </div>
                    <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${row.color}`}
                        style={{ width: `${(row.count / summary.total_jobs) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-600 py-4 text-center">No jobs yet</p>
            )}
          </CardContent>
        </Card>

        {/* Quick actions */}
        <Card>
          <CardHeader>
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Quick actions</h2>
          </CardHeader>
          <CardContent className="space-y-2">
            {[
              { href: '/jobs/new',   icon: '⟁', label: 'Submit a new job',         sub: 'Get instant profit prediction' },
              { href: '/trucks',     icon: '⬡', label: 'Manage trucks & drivers',   sub: 'Add or edit fleet resources' },
              { href: '/analytics',  icon: '◉', label: 'View analytics',            sub: 'Trends, routes, fuel impact' },
              { href: '/scenarios',  icon: '◎', label: 'Run a scenario',            sub: 'What-if fleet simulations' },
            ].map(a => (
              <Link key={a.href} href={a.href}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-slate-700/50 transition-all group">
                <span className="text-lg text-slate-500 group-hover:text-cyan-400 transition-colors">{a.icon}</span>
                <div>
                  <p className="text-xs font-medium text-slate-300">{a.label}</p>
                  <p className="text-[11px] text-slate-600">{a.sub}</p>
                </div>
                <span className="ml-auto text-slate-700 group-hover:text-slate-500 text-xs">→</span>
              </Link>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function PageSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 w-48 bg-slate-800 rounded"/>
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <div key={i} className="h-24 bg-slate-800 rounded-xl"/>)}
      </div>
      <div className="h-64 bg-slate-800 rounded-xl"/>
    </div>
  )
}
