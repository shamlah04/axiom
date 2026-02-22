// lib/api/auth.ts
import { api, setToken, clearToken } from './client'
import type { Token, UserOut, UserRegister } from '@/types/api'

export const authApi = {
  register: (data: UserRegister) =>
    api.post<UserOut>('/api/v1/auth/register', data),

  login: async (email: string, password: string): Promise<Token> => {
    const body = new URLSearchParams({ username: email, password })
    const token = await api.postForm<Token>('/api/v1/auth/login', body)
    setToken(token.access_token)
    return token
  },

  me: () => api.get<UserOut>('/api/v1/auth/me'),

  refresh: () => api.post<Token>('/api/v1/auth/refresh', {}),

  logout: () => clearToken(),
}
