'use client'
// app/(dashboard)/scenarios/page.tsx
import { useState } from 'react'
import { Button, Input, Card, CardHeader, CardContent } from '@/components/ui'
import { formatCurrency, formatPercent } from '@/lib/utils'

interface SimInput {
  monthly_revenue: string
  monthly_cost: string
  fuel_change_pct: string
  rate_change_pct: string
  add_trucks: string
  truck_monthly_fixed: string
}

interface SimResult {
  label: string
  revenue: number
  cost: number
  profit: number
  margin: number
  note: string
  color: string
}

function simulate(base: { revenue: number; cost: number }, inputs: SimInput): SimResult[] {
  const results: SimResult[] = []

  const baseProfit = base.revenue - base.cost
  const baseMargin = base.revenue > 0 ? (baseProfit / base.revenue) * 100 : 0

  // Baseline
  results.push({
    label: 'Baseline',
    revenue: base.revenue,
    cost: base.cost,
    profit: baseProfit,
    margin: baseMargin,
    note: 'Current situation',
    color: 'text-slate-300',
  })

  // Fuel price change
  const fuelPct = Number(inputs.fuel_change_pct) / 100
  if (fuelPct !== 0) {
    const fuelCostShare = 0.35 // assume 35% of costs are fuel
    const newCost = base.cost * (1 + fuelCostShare * fuelPct)
    const p = base.revenue - newCost
    results.push({
      label: `Fuel ${fuelPct > 0 ? '+' : ''}${inputs.fuel_change_pct}%`,
      revenue: base.revenue,
      cost: newCost,
      profit: p,
      margin: (p / base.revenue) * 100,
      note: `Fuel costs ${fuelPct > 0 ? 'increase' : 'decrease'} by ${Math.abs(Number(inputs.fuel_change_pct))}%`,
      color: fuelPct > 0 ? 'text-red-400' : 'text-emerald-400',
    })
  }

  // Rate change
  const ratePct = Number(inputs.rate_change_pct) / 100
  if (ratePct !== 0) {
    const newRevenue = base.revenue * (1 + ratePct)
    const p = newRevenue - base.cost
    results.push({
      label: `Rates ${ratePct > 0 ? '+' : ''}${inputs.rate_change_pct}%`,
      revenue: newRevenue,
      cost: base.cost,
      profit: p,
      margin: (p / newRevenue) * 100,
      note: `Average job rate ${ratePct > 0 ? 'increases' : 'decreases'} by ${Math.abs(Number(inputs.rate_change_pct))}%`,
      color: ratePct > 0 ? 'text-emerald-400' : 'text-red-400',
    })
  }

  // Additional trucks
  const addTrucks = Number(inputs.add_trucks)
  if (addTrucks > 0) {
    const truckFixed = Number(inputs.truck_monthly_fixed) || 2500
    const extraCost = addTrucks * truckFixed
    const extraRevenue = base.revenue > 0 ? (base.revenue / Math.max(1, base.cost / 500)) * addTrucks * 500 : 0
    const newRevenue = base.revenue + extraRevenue
    const newCost = base.cost + extraCost
    const p = newRevenue - newCost
    results.push({
      label: `+${addTrucks} truck${addTrucks > 1 ? 's' : ''}`,
      revenue: newRevenue,
      cost: newCost,
      profit: p,
      margin: newRevenue > 0 ? (p / newRevenue) * 100 : 0,
      note: `${addTrucks} additional truck${addTrucks > 1 ? 's' : ''} at ${formatCurrency(truckFixed)}/mo fixed cost each`,
      color: p > baseProfit ? 'text-emerald-400' : 'text-amber-400',
    })
  }

  // Combined scenario
  if (fuelPct !== 0 || ratePct !== 0 || addTrucks > 0) {
    const fuelCostShare = 0.35
    const combinedRevenue = base.revenue * (1 + ratePct) + (addTrucks > 0 ? base.revenue * 0.3 * addTrucks : 0)
    const combinedCost = base.cost * (1 + fuelCostShare * fuelPct) + (addTrucks * (Number(inputs.truck_monthly_fixed) || 2500))
    const p = combinedRevenue - combinedCost
    results.push({
      label: 'Combined',
      revenue: combinedRevenue,
      cost: combinedCost,
      profit: p,
      margin: combinedRevenue > 0 ? (p / combinedRevenue) * 100 : 0,
      note: 'All changes applied simultaneously',
      color: p > baseProfit ? 'text-emerald-400' : 'text-red-400',
    })
  }

  return results
}

export default function ScenariosPage() {
  const [base, setBase] = useState({ monthly_revenue: '', monthly_cost: '' })
  const [inputs, setInputs] = useState<SimInput>({
    monthly_revenue: '', monthly_cost: '',
    fuel_change_pct: '10', rate_change_pct: '5',
    add_trucks: '1', truck_monthly_fixed: '2500',
  })
  const [results, setResults] = useState<SimResult[] | null>(null)

  function runSim(e: React.FormEvent) {
    e.preventDefault()
    const revenue = Number(inputs.monthly_revenue)
    const cost = Number(inputs.monthly_cost)
    if (!revenue || !cost) return
    setResults(simulate({ revenue, cost }, inputs))
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-lg font-bold text-slate-100">Scenario simulator</h1>
        <p className="text-xs text-slate-500 mt-0.5">What-if analysis for fleet decisions</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Inputs */}
        <div>
          <form onSubmit={runSim} className="space-y-4">
            <Card>
              <CardHeader><p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Current baseline</p></CardHeader>
              <CardContent className="space-y-4">
                <Input label="Monthly revenue (€)" type="number" placeholder="45000"
                  value={inputs.monthly_revenue}
                  onChange={e => setInputs(p => ({ ...p, monthly_revenue: e.target.value }))} required />
                <Input label="Monthly cost (€)" type="number" placeholder="38000"
                  value={inputs.monthly_cost}
                  onChange={e => setInputs(p => ({ ...p, monthly_cost: e.target.value }))} required />
              </CardContent>
            </Card>

            <Card>
              <CardHeader><p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">What-if changes</p></CardHeader>
              <CardContent className="space-y-4">
                <Input label="Fuel price change (%)" type="number" placeholder="10"
                  hint="Positive = fuel price rises, negative = falls"
                  value={inputs.fuel_change_pct}
                  onChange={e => setInputs(p => ({ ...p, fuel_change_pct: e.target.value }))} />
                <Input label="Rate change (%)" type="number" placeholder="5"
                  hint="Change in average job rates you can charge"
                  value={inputs.rate_change_pct}
                  onChange={e => setInputs(p => ({ ...p, rate_change_pct: e.target.value }))} />
                <div className="grid grid-cols-2 gap-3">
                  <Input label="Additional trucks" type="number" min="0" placeholder="1"
                    value={inputs.add_trucks}
                    onChange={e => setInputs(p => ({ ...p, add_trucks: e.target.value }))} />
                  <Input label="Fixed cost/truck (€/mo)" type="number" placeholder="2500"
                    value={inputs.truck_monthly_fixed}
                    onChange={e => setInputs(p => ({ ...p, truck_monthly_fixed: e.target.value }))} />
                </div>
              </CardContent>
            </Card>

            <Button type="submit" className="w-full justify-center" size="lg">Run scenarios</Button>
          </form>
        </div>

        {/* Results */}
        {results && (
          <div className="space-y-3 animate-in fade-in slide-in-from-right-4 duration-300">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Results</p>
            {results.map((r, i) => (
              <Card key={i} className={i === 0 ? 'border-slate-600' : ''}>
                <CardContent className="py-4">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <p className="text-xs font-semibold text-slate-300">{r.label}</p>
                      <p className="text-[11px] text-slate-600 mt-0.5">{r.note}</p>
                    </div>
                    <div className="text-right">
                      <p className={`text-sm font-bold font-mono ${r.color}`}>{formatPercent(r.margin)}</p>
                      <p className="text-[11px] text-slate-500">margin</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div>
                      <p className="text-[10px] text-slate-600 uppercase tracking-wider">Revenue</p>
                      <p className="text-xs font-mono text-slate-300">{formatCurrency(r.revenue)}</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-slate-600 uppercase tracking-wider">Cost</p>
                      <p className="text-xs font-mono text-slate-400">{formatCurrency(r.cost)}</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-slate-600 uppercase tracking-wider">Profit</p>
                      <p className={`text-xs font-mono font-semibold ${r.profit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {formatCurrency(r.profit)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}

            <p className="text-[11px] text-slate-600 px-1">
              Note: These are estimates based on your inputs. Fuel cost share assumed at 35% of total cost.
              Use actual job data for more accurate projections.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
