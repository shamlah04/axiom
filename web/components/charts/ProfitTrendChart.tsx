'use client'
// components/charts/ProfitTrendChart.tsx
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend
} from 'recharts'
import { monthLabel } from '@/lib/utils'
import type { MonthlyTrend } from '@/types/api'

export function ProfitTrendChart({ data }: { data: MonthlyTrend[] }) {
  const chartData = data.map(d => ({
    month: monthLabel(d.year, d.month),
    Revenue: Math.round(d.total_revenue),
    Cost: Math.round(d.total_cost),
    Profit: Math.round(d.total_profit),
  }))

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false}
          tickFormatter={v => `€${(v/1000).toFixed(0)}k`} />
        <Tooltip
          contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: '#94a3b8' }}
          formatter={(value: number) => [`€${value.toLocaleString()}`, '']}
        />
        <Legend wrapperStyle={{ fontSize: 11, color: '#64748b' }} />
        <Line type="monotone" dataKey="Revenue" stroke="#06b6d4" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="Cost" stroke="#ef4444" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="Profit" stroke="#10b981" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}
