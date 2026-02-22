'use client'
// app/(auth)/register/page.tsx
import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { authApi } from '@/lib/api/auth'
import { fleetsApi } from '@/lib/api/modules'
import { Button, Input, Select } from '@/components/ui'

export default function RegisterPage() {
  const router = useRouter()
  const [step, setStep] = useState<'account' | 'fleet'>('account')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [account, setAccount] = useState({ email: '', password: '', full_name: '' })
  const [fleet, setFleet] = useState({ name: '', country: 'DK', subscription_tier: 'tier1' as const })

  async function handleAccount(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await authApi.register(account)
      await authApi.login(account.email, account.password)
      setStep('fleet')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleFleet(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await fleetsApi.create(fleet)
      document.cookie = 'fcip_auth=1; path=/'
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-3 mb-10">
          <div className="w-9 h-9 bg-cyan-500 rounded-xl flex items-center justify-center">
            <span className="text-slate-900 text-sm font-black">A</span>
          </div>
          <div>
            <p className="text-base font-bold text-slate-100">Axiom</p>
            <p className="text-[11px] text-slate-500">Fleet Intelligence Platform</p>
          </div>
        </div>

        {/* Steps */}
        <div className="flex items-center gap-2 mb-8">
          {['Account', 'Fleet'].map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold
                ${(step === 'account' && i === 0) || (step === 'fleet' && i <= 1)
                  ? 'bg-cyan-500 text-slate-900' : 'bg-slate-700 text-slate-500'}`}>
                {i + 1}
              </div>
              <span className="text-xs text-slate-500">{s}</span>
              {i < 1 && <span className="text-slate-700">→</span>}
            </div>
          ))}
        </div>

        {step === 'account' ? (
          <>
            <h1 className="text-xl font-bold text-slate-100 mb-1">Create your account</h1>
            <p className="text-sm text-slate-500 mb-8">Step 1 of 2</p>
            <form onSubmit={handleAccount} className="space-y-4">
              <Input label="Full name" placeholder="Lars Jensen" value={account.full_name}
                onChange={e => setAccount(p => ({ ...p, full_name: e.target.value }))} required />
              <Input label="Email" type="email" placeholder="lars@fleet.dk" value={account.email}
                onChange={e => setAccount(p => ({ ...p, email: e.target.value }))} required />
              <Input label="Password" type="password" placeholder="••••••••" value={account.password}
                onChange={e => setAccount(p => ({ ...p, password: e.target.value }))}
                hint="Minimum 8 characters" required />
              {error && <p className="text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">{error}</p>}
              <Button type="submit" className="w-full justify-center" loading={loading} size="lg">Continue</Button>
            </form>
          </>
        ) : (
          <>
            <h1 className="text-xl font-bold text-slate-100 mb-1">Set up your fleet</h1>
            <p className="text-sm text-slate-500 mb-8">Step 2 of 2 — you can change this later</p>
            <form onSubmit={handleFleet} className="space-y-4">
              <Input label="Fleet name" placeholder="Jensen Transport ApS" value={fleet.name}
                onChange={e => setFleet(p => ({ ...p, name: e.target.value }))} required />
              <Select label="Country" value={fleet.country}
                onChange={e => setFleet(p => ({ ...p, country: e.target.value }))}
                options={[{ value: 'DK', label: 'Denmark' }, { value: 'SE', label: 'Sweden' }, { value: 'DE', label: 'Germany' }, { value: 'NL', label: 'Netherlands' }]} />
              <Select label="Plan" value={fleet.subscription_tier}
                onChange={e => setFleet(p => ({ ...p, subscription_tier: e.target.value as any }))}
                options={[
                  { value: 'tier1', label: 'Tier 1 — up to 2 trucks (free trial)' },
                  { value: 'tier2', label: 'Tier 2 — up to 10 trucks' },
                  { value: 'tier3', label: 'Tier 3 — enterprise' },
                ]} />
              {error && <p className="text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">{error}</p>}
              <Button type="submit" className="w-full justify-center" loading={loading} size="lg">Create fleet</Button>
            </form>
          </>
        )}

        <p className="text-xs text-slate-500 text-center mt-6">
          Already have an account?{' '}
          <Link href="/login" className="text-cyan-400 hover:text-cyan-300 transition-colors">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
