import type { Lang } from '../data/types'

const IST = 'Asia/Kolkata'

export function hourLabel(epoch: number, lang: Lang, now = Date.now() / 1000): string {
  const d = new Date(epoch * 1000)
  const parts = new Intl.DateTimeFormat('en-GB', { timeZone: IST, hour: 'numeric', hour12: false, day: '2-digit', month: '2-digit', year: 'numeric' }).formatToParts(d)
  const hour = Number(parts.find(p => p.type === 'hour')!.value) % 24
  const dayKey = (e: number) => new Intl.DateTimeFormat('en-CA', { timeZone: IST }).format(new Date(e * 1000))
  const diff = Math.round((Date.parse(dayKey(epoch)) - Date.parse(dayKey(now))) / 86400000)
  const h12 = hour % 12 || 12
  if (lang === 'hi') {
    const part = hour >= 20 || hour < 5 ? 'रात' : hour < 12 ? 'सुबह' : hour < 16 ? 'दोपहर' : 'शाम'
    const day = diff === 0 ? 'आज' : diff === 1 ? 'कल' : new Intl.DateTimeFormat('hi-IN', { timeZone: IST, day: 'numeric', month: 'short' }).format(d)
    return `${day} ${part} ${h12} बजे`
  }
  const ampm = hour < 12 ? 'AM' : 'PM'
  const day = diff === 0 ? (hour >= 18 ? 'tonight' : 'today') : diff === 1 ? 'tomorrow' : new Intl.DateTimeFormat('en-IN', { timeZone: IST, day: 'numeric', month: 'short' }).format(d)
  return `${h12} ${ampm} ${day}`
}

export function clock(epoch: number): string {
  return new Intl.DateTimeFormat('en-IN', { timeZone: IST, hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(epoch * 1000)) + ' IST'
}

export function shortTime(epoch: number, lang: Lang): string {
  return new Intl.DateTimeFormat(lang === 'hi' ? 'hi-IN' : 'en-IN', { timeZone: IST, weekday: 'short', hour: 'numeric', hour12: true }).format(new Date(epoch * 1000))
}

export function compact(n: number): string {
  if (n >= 1e7) return `${(n / 1e7).toFixed(1)} crore`
  if (n >= 1e5) return `${(n / 1e5).toFixed(1)} lakh`
  return new Intl.NumberFormat('en-IN').format(Math.round(n))
}
