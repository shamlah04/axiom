// lib/api/analytics.ts
import { api } from './client'
import type { MonthlyTrend, TopRoute, FuelVolatilityMonth } from '@/types/api'

export const analyticsApi = {
  trends: (months = 6) =>
    api.get<MonthlyTrend[]>(`/api/v1/dashboard/trends?months=${months}`),
  routes: (limit = 10, minJobs = 2) =>
    api.get<TopRoute[]>(`/api/v1/dashboard/routes?limit=${limit}&min_jobs=${minJobs}`),
  fuelVolatility: (months = 6) =>
    api.get<FuelVolatilityMonth[]>(`/api/v1/dashboard/fuel-volatility?months=${months}`),
}
