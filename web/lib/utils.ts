// lib/utils.ts

export function formatCurrency(amount: number | null | undefined): string {
  if (amount == null) return '—'
  return new Intl.NumberFormat('da-DK', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return '—'
  return `${value.toFixed(1)}%`
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('da-DK', {
    day: 'numeric', month: 'short', year: 'numeric'
  })
}

export function monthLabel(year: number, month: number): string {
  return new Date(year, month - 1).toLocaleDateString('da-DK', {
    month: 'short', year: '2-digit'
  })
}

export function riskColor(risk: string | null): string {
  switch (risk) {
    case 'low':    return 'text-emerald-400'
    case 'medium': return 'text-amber-400'
    case 'high':   return 'text-red-400'
    default:       return 'text-slate-400'
  }
}

export function riskBg(risk: string | null): string {
  switch (risk) {
    case 'low':    return 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20'
    case 'medium': return 'bg-amber-400/10 text-amber-400 border-amber-400/20'
    case 'high':   return 'bg-red-400/10 text-red-400 border-red-400/20'
    default:       return 'bg-slate-400/10 text-slate-400 border-slate-400/20'
  }
}

export function recommendationBg(rec: string | null): string {
  switch (rec) {
    case 'accept': return 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20'
    case 'review': return 'bg-amber-400/10 text-amber-400 border-amber-400/20'
    case 'reject': return 'bg-red-400/10 text-red-400 border-red-400/20'
    default:       return 'bg-slate-400/10 text-slate-400 border-slate-400/20'
  }
}

export function statusBg(status: string): string {
  switch (status) {
    case 'accepted':  return 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20'
    case 'rejected':  return 'bg-red-400/10 text-red-400 border-red-400/20'
    case 'completed': return 'bg-blue-400/10 text-blue-400 border-blue-400/20'
    default:          return 'bg-slate-400/10 text-slate-400 border-slate-400/20'
  }
}

export function cn(...classes: (string | undefined | false)[]): string {
  return classes.filter(Boolean).join(' ')
}
