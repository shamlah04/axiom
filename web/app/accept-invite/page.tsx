'use client'
// web/app/accept-invite/page.tsx
// Landing page for team invite deep links from email.
// URL: /accept-invite?token=<invite_token>
//
// Flow:
//   A) User already logged in → immediately POST /team/invites/accept
//   B) User not logged in → show register/login form, then accept on success

import { useEffect, useState, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { authApi } from '@/lib/api/auth'
import { teamApi } from '@/lib/api/modules'
import { getToken } from '@/lib/api/client'
import { Button, Input } from '@/components/ui'

type Step = 'loading' | 'login' | 'accepting' | 'done' | 'error'

export default function AcceptInvitePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="w-10 h-10 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <AcceptInviteContent />
    </Suspense>
  )
}

function AcceptInviteContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const token = searchParams.get('token') ?? ''

  const [step, setStep] = useState<Step>('loading')
  const [errorMsg, setErrorMsg] = useState('')
  const [isNewUser, setIsNewUser] = useState(true)
  const [form, setForm] = useState({ email: '', password: '', full_name: '' })
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!token) {
      setErrorMsg('Invalid or missing invitation token.')
      setStep('error')
      return
    }
    // If already logged in, accept immediately
    if (getToken()) {
      acceptInvite()
    } else {
      setStep('login')
    }
  }, [token]) // eslint-disable-line react-hooks/exhaustive-deps

  async function acceptInvite() {
    setStep('accepting')
    try {
      await teamApi.acceptInvite(token)
      setStep('done')
      setTimeout(() => router.push('/dashboard'), 2000)
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to accept invitation')
      setStep('error')
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setErrorMsg('')
    try {
      if (isNewUser) {
        await authApi.register({ email: form.email, password: form.password, full_name: form.full_name })
      }
      await authApi.login(form.email, form.password)
      await acceptInvite()
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Authentication failed')
      setSubmitting(false)
    }
  }

  const Logo = () => (
    <div className="flex items-center gap-2 mb-8">
      <div className="w-8 h-8 bg-cyan-500 rounded-lg flex items-center justify-center">
        <span className="text-slate-900 text-xs font-black">A</span>
      </div>
      <div>
        <p className="text-sm font-bold text-slate-100">Axiom</p>
        <p className="text-[10px] text-slate-500">Fleet Intelligence</p>
      </div>
    </div>
  )

  // Loading / Accepting spinner
  if (step === 'loading' || step === 'accepting') {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-10 h-10 border-2 border-cyan-500 border-t-transparent
                          rounded-full animate-spin mx-auto" />
          <p className="text-slate-400 text-sm">
            {step === 'accepting' ? 'Joining fleet…' : 'Loading…'}
          </p>
        </div>
      </div>
    )
  }

  // Success
  if (step === 'done') {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center
                          justify-center mx-auto border border-emerald-500/20">
            <span className="text-2xl">✓</span>
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-100">You're in!</h2>
            <p className="text-sm text-slate-400 mt-1">Redirecting to your dashboard…</p>
          </div>
        </div>
      </div>
    )
  }

  // Error
  if (step === 'error') {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="w-full max-w-sm text-center space-y-4">
          <Logo />
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6">
            <p className="text-red-400 font-semibold mb-2">Invitation error</p>
            <p className="text-sm text-slate-400">{errorMsg}</p>
          </div>
          <p className="text-xs text-slate-600">
            Ask your fleet owner to send a new invitation link.
          </p>
        </div>
      </div>
    )
  }

  // Login / Register form
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <Logo />

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-5">
          <div>
            <h1 className="text-lg font-bold text-slate-100">Accept your invitation</h1>
            <p className="text-xs text-slate-500 mt-1">
              {isNewUser
                ? 'Create your Axiom account to join the fleet'
                : 'Sign in to accept the invitation'}
            </p>
          </div>

          {/* Toggle new / existing user */}
          <div className="flex bg-slate-800 rounded-lg p-0.5">
            {[{ label: 'New user', value: true }, { label: 'Existing user', value: false }].map(opt => (
              <button
                key={String(opt.value)}
                onClick={() => setIsNewUser(opt.value)}
                className={`flex-1 py-1.5 rounded-md text-xs font-medium transition-all ${isNewUser === opt.value
                    ? 'bg-slate-700 text-slate-100'
                    : 'text-slate-500 hover:text-slate-400'
                  }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-3">
            {isNewUser && (
              <Input
                label="Full name"
                value={form.full_name}
                onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
                required
                placeholder="Your name"
              />
            )}
            <Input
              label="Email"
              type="email"
              value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
              required
              placeholder="you@example.com"
            />
            <Input
              label="Password"
              type="password"
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
              required
              placeholder={isNewUser ? 'Create a password' : 'Your password'}
            />

            {errorMsg && (
              <p className="text-xs text-red-400 bg-red-400/10 border border-red-400/20
                            rounded-lg px-3 py-2">{errorMsg}</p>
            )}

            <Button
              type="submit"
              loading={submitting}
              className="w-full justify-center"
            >
              {isNewUser ? 'Create account & join fleet' : 'Sign in & join fleet'}
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}
