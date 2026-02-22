'use client'
// app/(auth)/login/page.tsx
import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { authApi } from '@/lib/api/auth'
import { Button, Input } from '@/components/ui'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await authApi.login(email, password)
      document.cookie = 'fcip_auth=1; path=/'
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.message || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-10">
          <div className="w-9 h-9 bg-cyan-500 rounded-xl flex items-center justify-center">
            <span className="text-slate-900 text-sm font-black">A</span>
          </div>
          <div>
            <p className="text-base font-bold text-slate-100">Axiom</p>
            <p className="text-[11px] text-slate-500">Fleet Intelligence Platform</p>
          </div>
        </div>

        <h1 className="text-xl font-bold text-slate-100 mb-1">Welcome back</h1>
        <p className="text-sm text-slate-500 mb-8">Sign in to your fleet account</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Email"
            type="email"
            placeholder="operator@fleet.dk"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
          />
          <Input
            label="Password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
          />

          {error && (
            <div className="text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <Button type="submit" className="w-full justify-center" loading={loading} size="lg">
            Sign in
          </Button>
        </form>

        <p className="text-xs text-slate-500 text-center mt-6">
          No account?{' '}
          <Link href="/register" className="text-cyan-400 hover:text-cyan-300 transition-colors">
            Register your fleet
          </Link>
        </p>
      </div>
    </div>
  )
}
