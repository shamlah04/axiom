// lib/api/dashboard.ts
import { api } from './client'
import type { DashboardSummary } from '@/types/api'

export const dashboardApi = {
  summary: () => api.get<DashboardSummary>('/api/v1/dashboard'),
}
