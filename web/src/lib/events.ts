import type { FinSyncEvent, Transaction } from '@/api/client'

/** An event's records without re-deliveries, each with how many times it arrived. */
export function originalRecords(event: FinSyncEvent): { record: Transaction; deliveries: number }[] {
  return event.transactions
    .filter((record) => record.duplicate_of_id === null)
    .map((record) => ({
      record,
      deliveries: 1 + event.transactions.filter((other) => other.duplicate_of_id === record.id).length,
    }))
}

export function primaryRecord(event: FinSyncEvent): Transaction | undefined {
  return event.transactions.find((record) => record.id === event.primary_transaction_id) ?? event.transactions[0]
}

/** "2026-10" from the API's timestamp: close enough for a month filter. */
export function monthOf(event: FinSyncEvent): string {
  return event.happened_at.slice(0, 7)
}
