// The category line editor's arithmetic (W4, docs/design/categorization.md#mixed-baskets). The member types
// every line's amount but the last; the last line takes the remainder, so the lines always add up to the
// event's amount. Amounts are typed as positive numbers and sent with the event's sign.

import type { CategoryLineInput, FinSyncEvent } from '@/api/client'
import { parseAmount } from '@/lib/format'

export interface DraftLine {
  category: string
  /** As typed ("9 000"); ignored for the last line, which shows the remainder. */
  amount: string
}

/** Whole fillér (hundredths), so 0.1 + 0.2 never adds up to 0.30000000000000004. */
const toCents = (value: string) => Math.round(Number(value) * 100)
const fromCents = (cents: number) => (cents % 100 === 0 ? String(cents / 100) : (cents / 100).toFixed(2))

/** The editor's starting lines: the saved ones, or the whole amount under the current category plus an empty line. */
export function initialLines(event: FinSyncEvent): DraftLine[] {
  if (event.lines.length > 0) {
    return event.lines.map((line) => ({ category: line.category, amount: fromCents(Math.abs(toCents(line.amount))) }))
  }
  const total = fromCents(Math.abs(toCents(event.amount)))
  return [
    { category: event.category, amount: total },
    { category: '', amount: '0' },
  ]
}

/** The remainder left for the last line, in the event's currency units (positive), or null if a typed amount is invalid. */
export function remainder(event: FinSyncEvent, lines: DraftLine[]): string | null {
  let cents = Math.abs(toCents(event.amount))
  for (const line of lines.slice(0, -1)) {
    const parsed = parseAmount(line.amount)
    if (parsed === null) return null
    cents -= toCents(parsed)
  }
  return fromCents(cents)
}

/** The lines to send, with the event's sign; or a Hungarian reason why they cannot be saved yet. */
export function linesToSave(event: FinSyncEvent, lines: DraftLine[]): CategoryLineInput[] | string {
  if (lines.length < 2) return 'Legalább két sor kell.'
  const rest = remainder(event, lines)
  if (rest === null) return 'Minden sorhoz adj meg pozitív összeget.'
  if (Number(rest) <= 0) return 'Az utolsó sorra nem marad összeg: csökkentsd a többi sort.'
  const categories = lines.map((line) => line.category)
  if (categories.some((category) => category === '')) return 'Minden sorhoz válassz kategóriát.'
  if (new Set(categories).size !== categories.length) return 'Egy kategória csak egy sorban szerepelhet.'
  const sign = event.amount.startsWith('-') ? '-' : ''
  return lines.map((line, index) => ({
    category: line.category,
    amount: sign + (index === lines.length - 1 ? rest : (parseAmount(line.amount) as string)),
  }))
}
