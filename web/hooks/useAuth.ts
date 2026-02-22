'use client'
// hooks/useAuth.ts
import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { authApi } from '@/lib/api/auth'
import type { UserOut } from '@/types/api'

export function useAuth() {
  const [user, setUser] = useState<UserOut | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    authApi.me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    await authApi.login(email, password)
    const me = await authApi.me()
    setUser(me)
    router.push('/dashboard')
  }, [router])

  const logout = useCallback(() => {
    authApi.logout()
    setUser(null)
    router.push('/login')
  }, [router])

  return { user, loading, login, logout }
}
