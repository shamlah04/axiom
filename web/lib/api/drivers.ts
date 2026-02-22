// lib/api/drivers.ts
import { api } from './client'
import type { DriverCreate, DriverOut } from '@/types/api'

export const driversApi = {
  list: () => api.get<DriverOut[]>('/api/v1/drivers'),
  get: (id: string) => api.get<DriverOut>(`/api/v1/drivers/${id}`),
  create: (data: DriverCreate) => api.post<DriverOut>('/api/v1/drivers', data),
  delete: (id: string) => api.delete(`/api/v1/drivers/${id}`),
}
