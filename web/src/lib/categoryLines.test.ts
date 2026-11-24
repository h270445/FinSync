import { describe, expect, it } from 'vitest'

import type { FinSyncEvent } from '@/api/client'

import { initialLines, linesToSave, remainder } from './categoryLines'

const event = (overrides: Partial<FinSyncEvent> = {}): FinSyncEvent => ({
  id: 1,
  amount: '-12000',
  currency: 'HUF',
  direction: 'expense',
  happened_at: '2026-11-10T09:00:00+00:00',
  merchant: 'Minta Hipermarket',
  category: 'groceries',
  category_source: 'dictionary',
  category_confidence: 'low',
  uncertain: true,
  mixed: false,
  lines: [],
  lines_match_amount: null,
  remember_merchant: null,
  primary_transaction_id: 1,
  review_state: 'clear',
  transactions: [],
  ...overrides,
})

describe('category lines', () => {
  it('starts with the whole amount under the current category', () => {
    expect(initialLines(event())).toEqual([
      { category: 'groceries', amount: '12000' },
      { category: '', amount: '0' },
    ])
  })

  it('gives the last line the remainder and sends the event sign', () => {
    const lines = [
      { category: 'groceries', amount: '9 000' },
      { category: 'clothing', amount: 'ignored' },
    ]
    expect(remainder(event(), lines)).toBe('3000')
    expect(linesToSave(event(), lines)).toEqual([
      { category: 'groceries', amount: '-9000' },
      { category: 'clothing', amount: '-3000' },
    ])
  })

  it('keeps fillér exact', () => {
    const lines = [
      { category: 'groceries', amount: '0,10' },
      { category: 'clothing', amount: '' },
    ]
    expect(remainder(event({ amount: '-0.30' }), lines)).toBe('0.20')
  })

  it('explains why the lines cannot be saved yet', () => {
    expect(linesToSave(event(), initialLines(event()))).toMatch(/nem marad összeg/)
    expect(linesToSave(event(), [{ category: 'groceries', amount: '1' }, { category: '', amount: '' }])).toMatch(/kategóriát/)
    expect(
      linesToSave(event(), [
        { category: 'groceries', amount: '1' },
        { category: 'groceries', amount: '' },
      ]),
    ).toMatch(/egy sorban/)
    expect(linesToSave(event(), [{ category: 'groceries', amount: 'sok' }, { category: 'clothing', amount: '' }])).toMatch(
      /pozitív/,
    )
  })

  it('reopens saved lines as positive amounts', () => {
    const saved = event({
      lines: [
        { category: 'groceries', amount: '-9000', created_by: 'anna', created_at: '2026-11-10T10:00:00+00:00' },
        { category: 'clothing', amount: '-3000', created_by: 'anna', created_at: '2026-11-10T10:00:00+00:00' },
      ],
    })
    expect(initialLines(saved)).toEqual([
      { category: 'groceries', amount: '9000' },
      { category: 'clothing', amount: '3000' },
    ])
  })
})
