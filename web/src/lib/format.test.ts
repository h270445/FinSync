import { describe, expect, it } from 'vitest'

import { describeDelta, formatAmount, formatDate, formatDateTime, formatScore } from './format'

// Intl uses no-break spaces as thousand separators; compare with plain spaces.
const plain = (text: string | null) => text?.replace(/\s/g, ' ')

describe('formatAmount', () => {
  it('shows expenses without a sign and income with +', () => {
    expect(plain(formatAmount('-12990'))).toBe('12 990 Ft')
    expect(plain(formatAmount('5000'))).toBe('+5 000 Ft')
  })

  it('keeps fractions the backend sends', () => {
    expect(plain(formatAmount('-1234.56'))).toBe('1 234,56 Ft')
  })
})

describe('formatDate', () => {
  it('uses the Hungarian date format in Budapest time', () => {
    // 23:30 UTC on Oct 8 is already Oct 9 in Budapest (CEST, UTC+2).
    expect(formatDate('2026-10-08T23:30:00+00:00')).toBe('2026. 10. 09.')
  })

  it('does not shift a day-precision value', () => {
    expect(formatDateTime('2026-09-05T00:00:00+00:00', 'day')).toBe('2026. 09. 05.')
  })

  it('adds a 24-hour time for minute precision', () => {
    expect(formatDateTime('2026-09-01T13:45:00+00:00')).toBe('2026. 09. 01. 15:45')
  })
})

describe('describeDelta', () => {
  it('words the matcher time differences', () => {
    expect(describeDelta('0d')).toBe('ugyanaz a nap')
    expect(describeDelta('2d')).toBe('2 nap eltérés')
    expect(describeDelta('0.07h')).toBe('4 perc eltérés')
    expect(describeDelta('1.50h')).toBe('1,5 óra eltérés')
  })
})

it('formats scores with a decimal comma', () => {
  expect(formatScore(0.8)).toBe('0,80')
})
