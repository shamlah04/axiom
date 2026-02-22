// lib/api/jobs.ts
import { api } from './client'
import type { JobCreate, JobOut, JobPredictionResult } from '@/types/api'

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
