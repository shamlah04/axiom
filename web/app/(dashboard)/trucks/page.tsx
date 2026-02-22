'use client'
// app/(dashboard)/trucks/page.tsx
import { useEffect, useState } from 'react'
import { trucksApi } from '@/lib/api/trucks'
import { driversApi } from '@/lib/api/drivers'
import { Button, Card, Modal, Input, Select, Badge, EmptyState } from '@/components/ui'
import { formatCurrency } from '@/lib/utils'
import type { TruckOut, DriverOut, TruckCreate, DriverCreate } from '@/types/api'

type Tab = 'trucks' | 'drivers'

export default function FleetPage() {
  const [tab, setTab] = useState<Tab>('trucks')
  const [trucks, setTrucks] = useState<TruckOut[]>([])
  const [drivers, setDrivers] = useState<DriverOut[]>([])
  const [loading, setLoading] = useState(true)
  const [showTruckModal, setShowTruckModal] = useState(false)
  const [showDriverModal, setShowDriverModal] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const [truckForm, setTruckForm] = useState<TruckCreate>({
    name: '', fuel_type: 'diesel',
    fuel_consumption_per_100km: 0, maintenance_cost_per_km: 0,
    insurance_monthly: 0, leasing_monthly: 0,
  })
  const [driverForm, setDriverForm] = useState<DriverCreate>({
    name: '', hourly_rate: 0, monthly_fixed_cost: 0,
  })

  function loadData() {
    setLoading(true)
    Promise.all([trucksApi.list(), driversApi.list()])
      .then(([t, d]) => { setTrucks(t); setDrivers(d) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadData() }, [])

  async function saveTruck(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setSaving(true)
    try {
      await trucksApi.create(truckForm)
      setShowTruckModal(false)
      loadData()
    } catch (err: any) { setError(err.message) }
    finally { setSaving(false) }
  }

  async function saveDriver(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setSaving(true)
    try {
      await driversApi.create(driverForm)
      setShowDriverModal(false)
      loadData()
    } catch (err: any) { setError(err.message) }
    finally { setSaving(false) }
  }

  async function deleteTruck(id: string) {
    if (!confirm('Soft-delete this truck? Jobs remain intact.')) return
    await trucksApi.delete(id)
    loadData()
  }

  async function deleteDriver(id: string) {
    if (!confirm('Soft-delete this driver? Jobs remain intact.')) return
    await driversApi.delete(id)
    loadData()
  }

  const activeTrucks = trucks.filter(t => t.is_active)
  const activeDrivers = drivers.filter(d => d.is_active)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-slate-100">Fleet</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            {activeTrucks.length} truck{activeTrucks.length !== 1 ? 's' : ''} · {activeDrivers.length} driver{activeDrivers.length !== 1 ? 's' : ''}
          </p>
        </div>
        <Button size="sm" onClick={() => tab === 'trucks' ? setShowTruckModal(true) : setShowDriverModal(true)}>
          + Add {tab === 'trucks' ? 'truck' : 'driver'}
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-700/50">
        {(['trucks', 'drivers'] as Tab[]).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-xs font-medium capitalize transition-all border-b-2 -mb-px
              ${tab === t ? 'border-cyan-500 text-cyan-400' : 'border-transparent text-slate-500 hover:text-slate-300'}`}>
            {t}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-2 animate-pulse">
          {[...Array(3)].map((_, i) => <div key={i} className="h-16 bg-slate-800 rounded-xl"/>)}
        </div>
      ) : tab === 'trucks' ? (
        activeTrucks.length === 0 ? (
          <Card>
            <EmptyState icon="⬡" title="No trucks" description="Add your first truck to start submitting jobs."
              action={<Button size="sm" onClick={() => setShowTruckModal(true)}>Add truck</Button>} />
          </Card>
        ) : (
          <Card>
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-700/50">
                  {['Name', 'Fuel type', 'Consumption', 'Maintenance/km', 'Insurance/mo', 'Leasing/mo', ''].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-slate-500 font-medium uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/30">
                {activeTrucks.map(t => (
                  <tr key={t.id} className="hover:bg-slate-700/20 transition-colors">
                    <td className="px-4 py-3">
                      <p className="text-slate-200 font-medium">{t.name}</p>
                      {t.license_plate && <p className="text-slate-500">{t.license_plate}</p>}
                    </td>
                    <td className="px-4 py-3"><Badge className="bg-slate-700/50 text-slate-400 border-slate-600">{t.fuel_type}</Badge></td>
                    <td className="px-4 py-3 font-mono text-slate-300">{t.fuel_consumption_per_100km}L/100km</td>
                    <td className="px-4 py-3 font-mono text-slate-300">€{t.maintenance_cost_per_km}/km</td>
                    <td className="px-4 py-3 font-mono text-slate-300">{formatCurrency(t.insurance_monthly)}</td>
                    <td className="px-4 py-3 font-mono text-slate-300">{formatCurrency(t.leasing_monthly ?? 0)}</td>
                    <td className="px-4 py-3">
                      <Button variant="ghost" size="sm" onClick={() => deleteTruck(t.id)}>Delete</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )
      ) : (
        activeDrivers.length === 0 ? (
          <Card>
            <EmptyState icon="◈" title="No drivers" description="Add your first driver to start submitting jobs."
              action={<Button size="sm" onClick={() => setShowDriverModal(true)}>Add driver</Button>} />
          </Card>
        ) : (
          <Card>
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-700/50">
                  {['Name', 'Hourly rate', 'Monthly fixed cost', ''].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-slate-500 font-medium uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/30">
                {activeDrivers.map(d => (
                  <tr key={d.id} className="hover:bg-slate-700/20 transition-colors">
                    <td className="px-4 py-3 text-slate-200 font-medium">{d.name}</td>
                    <td className="px-4 py-3 font-mono text-slate-300">€{d.hourly_rate}/hr</td>
                    <td className="px-4 py-3 font-mono text-slate-300">{formatCurrency(d.monthly_fixed_cost)}</td>
                    <td className="px-4 py-3">
                      <Button variant="ghost" size="sm" onClick={() => deleteDriver(d.id)}>Delete</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )
      )}

      {/* Add Truck Modal */}
      <Modal open={showTruckModal} onClose={() => setShowTruckModal(false)} title="Add truck">
        <form onSubmit={saveTruck} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Input label="Name" placeholder="Volvo FH16" value={truckForm.name}
              onChange={e => setTruckForm(p => ({ ...p, name: e.target.value }))} required />
            <Input label="License plate" placeholder="AB 12 345" value={truckForm.license_plate ?? ''}
              onChange={e => setTruckForm(p => ({ ...p, license_plate: e.target.value }))} />
          </div>
          <Select label="Fuel type" value={truckForm.fuel_type}
            onChange={e => setTruckForm(p => ({ ...p, fuel_type: e.target.value as any }))}
            options={[
              { value: 'diesel', label: 'Diesel' },
              { value: 'petrol', label: 'Petrol' },
              { value: 'electric', label: 'Electric' },
              { value: 'hybrid', label: 'Hybrid' },
            ]} />
          <Input label="Fuel consumption (L/100km)" type="number" step="0.1" placeholder="32"
            value={truckForm.fuel_consumption_per_100km || ''}
            onChange={e => setTruckForm(p => ({ ...p, fuel_consumption_per_100km: Number(e.target.value) }))} required />
          <Input label="Maintenance cost (€/km)" type="number" step="0.001" placeholder="0.08"
            value={truckForm.maintenance_cost_per_km || ''}
            onChange={e => setTruckForm(p => ({ ...p, maintenance_cost_per_km: Number(e.target.value) }))} required />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Insurance (€/month)" type="number" placeholder="1200"
              value={truckForm.insurance_monthly || ''}
              onChange={e => setTruckForm(p => ({ ...p, insurance_monthly: Number(e.target.value) }))} required />
            <Input label="Leasing (€/month)" type="number" placeholder="800"
              value={truckForm.leasing_monthly || ''}
              onChange={e => setTruckForm(p => ({ ...p, leasing_monthly: Number(e.target.value) }))} />
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <div className="flex gap-2 pt-2">
            <Button type="button" variant="secondary" className="flex-1 justify-center"
              onClick={() => setShowTruckModal(false)}>Cancel</Button>
            <Button type="submit" className="flex-1 justify-center" loading={saving}>Save truck</Button>
          </div>
        </form>
      </Modal>

      {/* Add Driver Modal */}
      <Modal open={showDriverModal} onClose={() => setShowDriverModal(false)} title="Add driver">
        <form onSubmit={saveDriver} className="space-y-4">
          <Input label="Name" placeholder="Lars Jensen" value={driverForm.name}
            onChange={e => setDriverForm(p => ({ ...p, name: e.target.value }))} required />
          <Input label="Hourly rate (€/hr)" type="number" step="0.01" placeholder="25.00"
            value={driverForm.hourly_rate || ''}
            onChange={e => setDriverForm(p => ({ ...p, hourly_rate: Number(e.target.value) }))} required />
          <Input label="Monthly fixed cost (€)" type="number" placeholder="200"
            value={driverForm.monthly_fixed_cost || ''}
            onChange={e => setDriverForm(p => ({ ...p, monthly_fixed_cost: Number(e.target.value) }))} />
          {error && <p className="text-xs text-red-400">{error}</p>}
          <div className="flex gap-2 pt-2">
            <Button type="button" variant="secondary" className="flex-1 justify-center"
              onClick={() => setShowDriverModal(false)}>Cancel</Button>
            <Button type="submit" className="flex-1 justify-center" loading={saving}>Save driver</Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
