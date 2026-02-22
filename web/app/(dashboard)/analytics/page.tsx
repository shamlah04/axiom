'use client'
// app/(dashboard)/analytics/page.tsx
import { useEffect, useState } from 'react'
import { analyticsApi } from '@/lib/api/analytics'
import { Card, CardHeader, CardContent } from '@/components/ui'
import { ProfitTrendChart } from '@/components/charts/ProfitTrendChart'
import { FuelVolatilityChart } from '@/components/charts/FuelVolatilityChart'
import { formatCurrency, formatPercent } from '@/lib/utils'
import type { MonthlyTrend, TopRoute, FuelVolatilityMonth } from '@/types/api'

export default function AnalyticsPage() {
  const [trends, setTrends] = useState<MonthlyTrend[]>([])
  const [routes, setRoutes] = useState<TopRoute[]>([])
  const [fuel, setFuel] = useState<FuelVolatilityMonth[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      analyticsApi.trends(6),
      analyticsApi.routes(10, 1),
      analyticsApi.fuelVolatility(6),
    ]).then(([t, r, f]) => { setTrends(t); setRoutes(r); setFuel(f) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const empty = (msg: string) => (
    <div className="h-40 flex items-center justify-center text-xs text-slate-600">{msg}</div>
  )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-bold text-slate-100">Analytics</h1>
        <p className="text-xs text-slate-500 mt-0.5">Fleet performance deep-dive</p>
      </div>

      {/* Monthly profit trends */}
      <Card>
        <CardHeader>
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Monthly profit trends</h2>
        </CardHeader>
        <CardContent>
          {loading ? <div className="h-52 bg-slate-800/50 rounded animate-pulse"/> :
           trends.length === 0 ? empty('No trend data yet — accept some jobs first') :
           <ProfitTrendChart data={trends} />}
        </CardContent>
      </Card>

      {/* Top routes + Fuel volatility */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top routes */}
        <Card>
          <CardHeader>
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Most profitable routes</h2>
          </CardHeader>
          <CardContent>
            {loading ? <div className="h-40 bg-slate-800/50 rounded animate-pulse"/> :
             routes.length === 0 ? empty('Need 2+ jobs on the same route') : (
              <div className="space-y-2">
                {routes.map((r, i) => (
                  <div key={i} className="flex items-center gap-3 py-2 border-b border-slate-700/30 last:border-0">
                    <span className="text-xs font-mono text-slate-600 w-4">{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-slate-200 font-medium truncate">{r.origin} → {r.destination}</p>
                      <p className="text-[11px] text-slate-500">{r.job_count} jobs · avg {formatCurrency(r.avg_rate)}</p>
                    </div>
                    <div className="text-right">
                      <p className={`text-xs font-bold font-mono
                        ${r.avg_margin_pct >= 15 ? 'text-emerald-400' :
                          r.avg_margin_pct >= 5  ? 'text-amber-400' : 'text-red-400'}`}>
                        {formatPercent(r.avg_margin_pct)}
                      </p>
                      <p className="text-[11px] text-slate-500">{formatCurrency(r.avg_net_profit)} avg profit</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Fuel volatility */}
        <Card>
          <CardHeader>
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Fuel price vs margin</h2>
          </CardHeader>
          <CardContent>
            {loading ? <div className="h-52 bg-slate-800/50 rounded animate-pulse"/> :
             fuel.length === 0 ? empty('No fuel data yet') :
             <FuelVolatilityChart data={fuel} />}
          </CardContent>
        </Card>
      </div>

      {/* Fuel stats table */}
      {fuel.length > 0 && (
        <Card>
          <CardHeader>
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Fuel price detail</h2>
          </CardHeader>
          <CardContent>
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-700/50">
                  {['Month', 'Jobs', 'Avg fuel price', 'Price range', 'Avg margin'].map(h => (
                    <th key={h} className="py-2 text-left text-slate-500 font-medium uppercase tracking-wider pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/30">
                {fuel.map((f, i) => (
                  <tr key={i}>
                    <td className="py-2 pr-4 text-slate-300">{new Date(f.year, f.month - 1).toLocaleDateString('da-DK', { month: 'short', year: '2-digit' })}</td>
                    <td className="py-2 pr-4 text-slate-400 font-mono">{f.job_count}</td>
                    <td className="py-2 pr-4 font-mono text-slate-300">€{f.avg_fuel_price.toFixed(3)}</td>
                    <td className="py-2 pr-4 font-mono text-slate-400">±€{f.fuel_price_range.toFixed(3)}</td>
                    <td className={`py-2 font-mono font-semibold
                      ${f.avg_margin_pct >= 15 ? 'text-emerald-400' :
                        f.avg_margin_pct >= 5  ? 'text-amber-400' : 'text-red-400'}`}>
                      {formatPercent(f.avg_margin_pct)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
