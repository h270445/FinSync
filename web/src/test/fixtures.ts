// Synthetic events for the page tests (made-up shops and members only).
import type { FinSyncEvent, Transaction } from '@/api/client'

export const record = (overrides: Partial<Transaction> = {}): Transaction => ({
  id: 1,
  user_id: 'anna',
  group_id: 'lakas',
  amount: '-12000',
  currency: 'HUF',
  description: 'card_purchase:MINTA HIPERMARKET',
  merchant: 'MINTA HIPERMARKET',
  category: 'groceries',
  source: 'android_notification',
  happened_at: '2026-11-10T09:00:00+00:00',
  happened_at_precision: 'minute',
  created_at: '2026-11-10T09:00:05+00:00',
  event_id: 1,
  duplicate_of_id: null,
  category_source: 'dictionary',
  category_confidence: 'low',
  ...overrides,
})

export const event = (overrides: Partial<FinSyncEvent> = {}): FinSyncEvent => ({
  id: 1,
  amount: '-12000',
  currency: 'HUF',
  direction: 'expense',
  happened_at: '2026-11-10T09:00:00+00:00',
  merchant: 'MINTA HIPERMARKET',
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
  transactions: [record()],
  ...overrides,
})
