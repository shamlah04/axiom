'use client'
// app/(dashboard)/jobs/new/page.tsx
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { jobsApi } from '@/lib/api/jobs'
import { trucksApi } from '@/lib/api/trucks'
import { driversApi } from '@/lib/api/drivers'
import { Button, Input, Select, Card, CardHeader, CardContent, Badge } from '@/components/ui'
import { CostBreakdownChart } from '@/components/charts/CostBreakdownChart'
import { formatCurrency, formatPercent, riskBg, recommendationBg } from '@/lib/utils'
import type { TruckOut, DriverOut, JobPredictionResult } from '@/types/api'

export default function NewJobPage() {
  const router = useRouter()
  const [trucks, setTrucks] = useState<TruckOut[]>([])
  const [drivers, setDrivers] = useState<DriverOut[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [prediction, setPrediction] = useState<JobPredictionResult | null>(null)
  const [accepting, setAccepting] = useState(false)

  const [form, setForm] = useState({
    truck_id: '', driver_id: '',
    origin: '', destination: '',
    distance_km: '', estimated_duration_hours: '',
    offered_rate: '', toll_costs: '0',
    fuel_price_per_unit: '1.85', other_costs: '0',
  })

  useEffect(() => {
    Promise.all([trucksApi.list(), driversApi.list()]).then(([t, d]) => {
      const active_t = t.filter(x => x.is_active)
      const active_d = d.filter(x => x.is_active)
      setTrucks(active_t)
      setDrivers(active_d)
      if (active_t[0]) setForm(p => ({ ...p, truck_id: active_t[0].id }))
      if (active_d[0]) setForm(p => ({ ...p, driver_id: active_d[0].id }))
    }).catch(console.error)
  }, [])

  function set(key: string, value: string) {
    setForm(p => ({ ...p, [key]: value }))
    setPrediction(null)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const result = await jobsApi.create({
        truck_id: form.truck_id,
        driver_id: form.driver_id,
        origin: form.origin,
        destination: form.destination,
        distance_km: Number(form.distance_km),
        estimated_duration_hours: Number(form.estimated_duration_hours),
        offered_rate: Number(form.offered_rate),
        toll_costs: Number(form.toll_costs),
        fuel_price_per_unit: Number(form.fuel_price_per_unit),
        other_costs: Number(form.other_costs),
      })
      setPrediction(result)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleDecision(status: 'accepted' | 'rejected') {
    if (!prediction) return
    setAccepting(true)
    try {
      await jobsApi.updateStatus(prediction.job_id, status)
      router.push('/jobs')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setAccepting(false)
    }
  }

  const truckOptions = trucks.map(t => ({ value: t.id, label: `${t.name}${t.license_plate ? ` (${t.license_plate})` : ''}` }))
  const driverOptions = drivers.map(d => ({ value: d.id, label: d.name }))

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-lg font-bold text-slate-100">New job</h1>
        <p className="text-xs text-slate-500 mt-0.5">Enter job details to get an instant profit prediction</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form */}
        <div>
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Resources */}
            <Card>
              <CardHeader><p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Resources</p></CardHeader>
              <CardContent className="space-y-4">
                {trucks.length === 0 ? (
                  <p className="text-xs text-amber-400 bg-amber-400/10 border border-amber-400/20 rounded-lg px-3 py-2">
                    No trucks yet — <a href="/trucks" className="underline">add a truck first</a>
                  </p>
                ) : (
                  <Select label="Truck" value={form.truck_id} onChange={e => set('truck_id', e.target.value)} options={truckOptions} />
                )}
                {drivers.length === 0 ? (
                  <p className="text-xs text-amber-400 bg-amber-400/10 border border-amber-400/20 rounded-lg px-3 py-2">
                    No drivers yet — <a href="/trucks" className="underline">add a driver first</a>
                  </p>
                ) : (
                  <Select label="Driver" value={form.driver_id} onChange={e => set('driver_id', e.target.value)} options={driverOptions} />
                )}
              </CardContent>
            </Card>

            {/* Route */}
            <Card>
              <CardHeader><p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Route</p></CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <Input label="Origin" placeholder="Copenhagen" value={form.origin} onChange={e => set('origin', e.target.value)} required />
                  <Input label="Destination" placeholder="Aarhus" value={form.destination} onChange={e => set('destination', e.target.value)} required />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Input label="Distance (km)" type="number" placeholder="300" value={form.distance_km} onChange={e => set('distance_km', e.target.value)} required min="1" />
                  <Input label="Duration (hours)" type="number" step="0.5" placeholder="4.0" value={form.estimated_duration_hours} onChange={e => set('estimated_duration_hours', e.target.value)} required min="0.5" />
                </div>
              </CardContent>
            </Card>

            {/* Financials */}
            <Card>
              <CardHeader><p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Financials</p></CardHeader>
              <CardContent className="space-y-4">
                <Input label="Offered rate (€)" type="number" step="0.01" placeholder="1200.00" value={form.offered_rate} onChange={e => set('offered_rate', e.target.value)} required min="1" />
                <div className="grid grid-cols-3 gap-3">
                  <Input label="Fuel price (€/L)" type="number" step="0.01" placeholder="1.85" value={form.fuel_price_per_unit} onChange={e => set('fuel_price_per_unit', e.target.value)} required />
                  <Input label="Tolls (€)" type="number" step="0.01" placeholder="0" value={form.toll_costs} onChange={e => set('toll_costs', e.target.value)} />
                  <Input label="Other costs (€)" type="number" step="0.01" placeholder="0" value={form.other_costs} onChange={e => set('other_costs', e.target.value)} />
                </div>
              </CardContent>
            </Card>

            {error && <p className="text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">{error}</p>}

            {!prediction && (
              <Button type="submit" loading={loading} className="w-full justify-center" size="lg"
                disabled={!form.truck_id || !form.driver_id}>
                Get prediction
              </Button>
            )}
          </form>
        </div>

        {/* Prediction Result */}
        {prediction && (
          <div className="space-y-4 animate-in fade-in slide-in-from-right-4 duration-300">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Prediction result</p>
                  <div className="flex gap-2">
                    <Badge className={riskBg(prediction.risk_level)}>{prediction.risk_level} risk</Badge>
                    <Badge className={recommendationBg(prediction.recommendation)}>{prediction.recommendation}</Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Key numbers */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="text-center">
                    <p className="text-[11px] text-slate-500 uppercase tracking-wider mb-1">Total cost</p>
                    <p className="text-base font-bold font-mono text-slate-200">{formatCurrency(prediction.total_cost)}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-[11px] text-slate-500 uppercase tracking-wider mb-1">Net profit</p>
                    <p className={`text-base font-bold font-mono ${prediction.net_profit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {formatCurrency(prediction.net_profit)}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-[11px] text-slate-500 uppercase tracking-wider mb-1">Margin</p>
                    <p className={`text-base font-bold font-mono
                      ${prediction.margin_pct >= 15 ? 'text-emerald-400' :
                        prediction.margin_pct >= 5  ? 'text-amber-400' : 'text-red-400'}`}>
                      {formatPercent(prediction.margin_pct)}
                    </p>
                  </div>
                </div>

                {/* Cost breakdown */}
                <CostBreakdownChart prediction={prediction} />

                {/* Cost breakdown table */}
                <div className="space-y-1.5 pt-2 border-t border-slate-700/50">
                  {[
                    { label: 'Fuel', value: prediction.fuel_cost },
                    { label: 'Driver', value: prediction.driver_cost },
                    { label: 'Maintenance', value: prediction.maintenance_cost },
                    { label: 'Tolls', value: prediction.toll_costs },
                    { label: 'Fixed allocation', value: prediction.fixed_cost_allocation },
                    { label: 'Other', value: prediction.other_costs },
                  ].map(row => (
                    <div key={row.label} className="flex justify-between text-xs">
                      <span className="text-slate-500">{row.label}</span>
                      <span className="font-mono text-slate-300">{formatCurrency(row.value)}</span>
                    </div>
                  ))}
                  <div className="flex justify-between text-xs font-semibold pt-1.5 border-t border-slate-700/50">
                    <span className="text-slate-400">Total cost</span>
                    <span className="font-mono text-slate-200">{formatCurrency(prediction.total_cost)}</span>
                  </div>
                </div>

                {/* AI explanation */}
                <div className="bg-slate-900/50 rounded-lg px-3 py-2.5 text-xs text-slate-400 leading-relaxed">
                  {prediction.ai_explanation}
                </div>

                {/* Decision buttons */}
                <div className="grid grid-cols-2 gap-3 pt-1">
                  <Button variant="danger" onClick={() => handleDecision('rejected')} loading={accepting}
                    className="justify-center">
                    Reject job
                  </Button>
                  <Button onClick={() => handleDecision('accepted')} loading={accepting}
                    className="justify-center">
                    Accept job
                  </Button>
                </div>
                <button onClick={() => setPrediction(null)}
                  className="w-full text-xs text-slate-600 hover:text-slate-400 transition-colors">
                  ← Edit job details
                </button>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}
