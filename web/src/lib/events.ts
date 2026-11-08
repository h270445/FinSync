import type { FinSyncEvent, Transaction } from '@/api/client'
import { localMonth } from '@/lib/format'

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

/** The event's month ("2026-10") as the list shows its date: in Budapest time, a day-precision date as stored. */
export function monthOf(event: FinSyncEvent): string {
  return localMonth(event.happened_at, primaryRecord(event)?.happened_at_precision)
}
