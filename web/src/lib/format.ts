// Hungarian display formats (docs/design/user-interface.md#screens): "12 990 Ft", "2026. 10. 09.", 24-hour times.

const TIME_ZONE = 'Europe/Budapest'

// useGrouping 'always': Hungarian CLDR leaves 4-digit numbers ungrouped, the design wants "2 000 Ft".
const money = (currency: string) =>
  new Intl.NumberFormat('hu-HU', { style: 'currency', currency, minimumFractionDigits: 0, maximumFractionDigits: 2, useGrouping: 'always' })
const huf = money('HUF')
const dateFormat = new Intl.DateTimeFormat('hu-HU', { year: 'numeric', month: '2-digit', day: '2-digit', timeZone: TIME_ZONE })
const dayFormat = new Intl.DateTimeFormat('hu-HU', { year: 'numeric', month: '2-digit', day: '2-digit', timeZone: 'UTC' })
const timeFormat = new Intl.DateTimeFormat('hu-HU', { hour: '2-digit', minute: '2-digit', timeZone: TIME_ZONE })
const decimal = new Intl.NumberFormat('hu-HU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

/** Expenses are shown without a sign, income with "+": a spending list reads naturally. */
export function formatAmount(amount: string, currency = 'HUF'): string {
  const value = Number(amount)
  const formatter = currency === 'HUF' ? huf : money(currency)
  const text = formatter.format(Math.abs(value))
  return value > 0 ? `+${text}` : text
}

/** A day-precision value (no time of day) keeps its calendar date; it is not shifted by time zone. */
export function formatDate(iso: string, precision = 'minute'): string {
  if (precision === 'day') return dayFormat.format(new Date(`${iso.slice(0, 10)}T00:00:00Z`))
  return dateFormat.format(new Date(iso))
}

export function formatTime(iso: string, precision = 'minute'): string | null {
  return precision === 'day' ? null : timeFormat.format(new Date(iso))
}

export function formatDateTime(iso: string, precision = 'minute'): string {
  const time = formatTime(iso, precision)
  return time ? `${formatDate(iso, precision)} ${time}` : formatDate(iso, precision)
}

/** Scores and feature values as "0,97". */
export function formatScore(value: number): string {
  return decimal.format(value)
}

/** The matcher's time difference ("0d", "2d", "0.07h") as a Hungarian phrase. */
export function describeDelta(delta: string): string {
  if (delta.endsWith('d')) {
    const days = Number(delta.slice(0, -1))
    return days === 0 ? 'ugyanaz a nap' : `${days} nap eltérés`
  }
  const hours = Number(delta.slice(0, -1))
  const minutes = Math.round(hours * 60)
  if (minutes < 60) return minutes === 0 ? 'azonos időpont' : `${minutes} perc eltérés`
  return `${new Intl.NumberFormat('hu-HU', { maximumFractionDigits: 1 }).format(hours)} óra eltérés`
}

const SOURCES: Record<string, string> = {
  android_notification: 'Értesítés',
  google_sheet: 'Táblázat',
  manual: 'Kézi',
  file_import: 'Fájl',
}

const CATEGORIES: Record<string, string> = {
  groceries: 'Élelmiszer',
  transport: 'Közlekedés',
  entertainment: 'Szórakozás',
  housing: 'Lakhatás',
  other: 'Egyéb',
}

const OUTCOMES: Record<string, string> = {
  separate: 'Új esemény',
  auto_linked: 'Automatikusan összekapcsolva',
  needs_review: 'Ellenőrzésre vár',
  exact_duplicate: 'Ismételt beküldés',
  confirmed: 'Megerősítve',
  rejected: 'Elutasítva',
  split: 'Szétválasztva',
}

export const sourceLabel = (source: string) => SOURCES[source] ?? source
export const categoryLabel = (category: string) => CATEGORIES[category] ?? category
export const outcomeLabel = (outcome: string) => OUTCOMES[outcome] ?? outcome
