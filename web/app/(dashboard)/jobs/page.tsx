'use client'
// app/(dashboard)/jobs/page.tsx
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { jobsApi } from '@/lib/api/modules'
import { Button, Badge, Card, EmptyState } from '@/components/ui'
import { formatCurrency, formatPercent, formatDate, riskBg, statusBg, recommendationBg } from '@/lib/utils'
import type { JobOut, JobStatus } from '@/types/api'

const STATUS_FILTERS: { label: string; value: JobStatus | 'all' }[] = [
  { label: 'All', value: 'all' },
  { label: 'Pending', value: 'pending' },
  { label: 'Accepted', value: 'accepted' },
  { label: 'Rejected', value: 'rejected' },
  { label: 'Completed', value: 'completed' },
]

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobOut[]>([])
  const [filter, setFilter] = useState<JobStatus | 'all'>('all')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    jobsApi.list(100, 0).then(setJobs).catch(console.error).finally(() => setLoading(false))
  }, [])

  const filtered = filter === 'all' ? jobs : jobs.filter(j => j.status === filter)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-slate-100">Jobs</h1>
          <p className="text-xs text-slate-500 mt-0.5">{jobs.length} total</p>
        </div>
        <Link href="/jobs/new"><Button size="sm">+ New job</Button></Link>
      </div>

      {/* Filters */}
      <div className="flex gap-1.5">
        {STATUS_FILTERS.map(f => (
          <button key={f.value} onClick={() => setFilter(f.value)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all
              ${filter === f.value
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                : 'text-slate-500 hover:text-slate-300 border border-transparent'}`}>
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => <div key={i} className="h-14 bg-slate-800 rounded-xl animate-pulse"/>)}
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <EmptyState icon="⟁" title="No jobs yet"
            description="Submit a job to get an instant profit prediction."
            action={<Link href="/jobs/new"><Button size="sm">Submit first job</Button></Link>} />
        </Card>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-700/50">
                  {['Route', 'Rate', 'Margin', 'Risk', 'Rec.', 'Status', 'Date'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-slate-500 font-medium uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/30">
                {filtered.map(job => (
                  <tr key={job.id} className="hover:bg-slate-700/20 transition-colors">
                    <td className="px-4 py-3">
                      <p className="text-slate-200 font-medium">{job.origin}</p>
                      <p className="text-slate-500">→ {job.destination}</p>
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-300">{formatCurrency(job.offered_rate)}</td>
                    <td className="px-4 py-3 font-mono text-slate-300">{formatPercent(job.margin_pct)}</td>
                    <td className="px-4 py-3">
                      <Badge className={riskBg(job.risk_level)}>{job.risk_level ?? '—'}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge className={recommendationBg(job.recommendation)}>{job.recommendation ?? '—'}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge className={statusBg(job.status)}>{job.status}</Badge>
                    </td>
                    <td className="px-4 py-3 text-slate-500">{formatDate(job.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}
