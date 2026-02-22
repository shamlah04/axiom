import { api } from './client'
import type {
  FleetCreate, FleetOut,
  TruckCreate, TruckUpdate, TruckOut,
  DriverCreate, DriverOut,
  JobCreate, JobOut, JobPredictionResult,
  DashboardSummary,
  MonthlyTrend, TopRoute, FuelVolatilityMonth,
  ScenarioInput, ScenarioResult
} from '@/types/api'

// lib/api/fleets.ts
export const fleetsApi = {
  create: (data: FleetCreate) => api.post<FleetOut>('/api/v1/fleets', data),
  me: () => api.get<FleetOut>('/api/v1/fleets/me'),
}

// lib/api/trucks.ts
export const trucksApi = {
  list: () => api.get<TruckOut[]>('/api/v1/trucks'),
  get: (id: string) => api.get<TruckOut>(`/api/v1/trucks/${id}`),
  create: (data: TruckCreate) => api.post<TruckOut>('/api/v1/trucks', data),
  update: (id: string, data: TruckUpdate) => api.patch<TruckOut>(`/api/v1/trucks/${id}`, data),
  delete: (id: string) => api.delete(`/api/v1/trucks/${id}`),
}

// lib/api/drivers.ts
export const driversApi = {
  list: () => api.get<DriverOut[]>('/api/v1/drivers'),
  get: (id: string) => api.get<DriverOut>(`/api/v1/drivers/${id}`),
  create: (data: DriverCreate) => api.post<DriverOut>('/api/v1/drivers', data),
  delete: (id: string) => api.delete(`/api/v1/drivers/${id}`),
}

// lib/api/jobs.ts
export const jobsApi = {
  list: (limit = 50, offset = 0) =>
    api.get<JobOut[]>(`/api/v1/jobs?limit=${limit}&offset=${offset}`),
  get: (id: string) => api.get<JobOut>(`/api/v1/jobs/${id}`),
  create: (data: JobCreate) => api.post<JobPredictionResult>('/api/v1/jobs', data),
  updateStatus: (id: string, status: string) =>
    api.patch<JobOut>(`/api/v1/jobs/${id}/status`, { status }),
  updateActual: (id: string, actual_revenue: number, actual_cost: number) =>
    api.patch<JobOut>(`/api/v1/jobs/${id}/actual`, { actual_revenue, actual_cost }),
}

// lib/api/dashboard.ts
export const dashboardApi = {
  summary: () => api.get<DashboardSummary>('/api/v1/dashboard'),
}

// lib/api/analytics.ts
export const analyticsApi = {
  trends: (months = 6) =>
    api.get<MonthlyTrend[]>(`/api/v1/dashboard/trends?months=${months}`),
  routes: (limit = 10, minJobs = 2) =>
    api.get<TopRoute[]>(`/api/v1/dashboard/routes?limit=${limit}&min_jobs=${minJobs}`),
  fuelVolatility: (months = 6) =>
    api.get<FuelVolatilityMonth[]>(`/api/v1/dashboard/fuel-volatility?months=${months}`),
}

// lib/api/scenarios.ts
export const scenariosApi = {
  simulate: (data: ScenarioInput) =>
    api.post<ScenarioResult>('/api/v1/scenarios/simulate', data),
}
