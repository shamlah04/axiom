// lib/api/trucks.ts
import { api } from './client'
import type { TruckCreate, TruckUpdate, TruckOut } from '@/types/api'

export const trucksApi = {
  list: () => api.get<TruckOut[]>('/api/v1/trucks'),
  get: (id: string) => api.get<TruckOut>(`/api/v1/trucks/${id}`),
  create: (data: TruckCreate) => api.post<TruckOut>('/api/v1/trucks', data),
  update: (id: string, data: TruckUpdate) => api.patch<TruckOut>(`/api/v1/trucks/${id}`, data),
  delete: (id: string) => api.delete(`/api/v1/trucks/${id}`),
}
