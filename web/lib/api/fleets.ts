// lib/api/fleets.ts
import { api } from './client'
import type { FleetCreate, FleetOut } from '@/types/api'

export const fleetsApi = {
  create: (data: FleetCreate) => api.post<FleetOut>('/api/v1/fleets', data),
  me: () => api.get<FleetOut>('/api/v1/fleets/me'),
}
