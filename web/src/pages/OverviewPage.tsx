import { AlertTriangle } from 'lucide-react'
import { Fragment, useState } from 'react'
import { Link } from 'react-router'

import type { OverviewBucket } from '@/api/client'
import { useOverview } from '@/api/queries'
import { NativeSelect } from '@/components/NativeSelect'
import { EmptyState, ErrorState, LoadingRows } from '@/components/states'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { categoryLabel, formatAmount, monthName } from '@/lib/format'

/** The group's currency (HUF) first, then the others alphabetically. */
const byCurrency = (a: OverviewBucket, b: OverviewBucket) =>
  Number(b.currency === 'HUF') - Number(a.currency === 'HUF') || a.currency.localeCompare(b.currency)

// The API sends positive sums; formatAmount shows a negative amount without a sign and a positive one with "+".
const money = (amount: string, currency: string) => formatAmount(`-${amount}`, currency)
const income = (amount: string, currency: string) => (Number(amount) === 0 ? '–' : formatAmount(amount, currency))

/**
 * W2: the month's totals per category and per member, counted on deduplicated events
 * (GET /v1/overview). Transfers within the group are left out; events waiting for review are
 * counted in and flagged, so the member sees how much of a total is not settled yet.
 */
export function OverviewPage() {
  const [month, setMonth] = useState<string | null>(null)
  const overview = useOverview(month)
  const data = overview.data
  const months = data ? [...new Set([data.month, ...data.months])].sort().reverse() : []

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-2xl font-semibold">Áttekintés</h1>
        {data && (
          <div className="space-y-1">
            <label htmlFor="o-month" className="block text-sm font-medium">
              Hónap
            </label>
            <NativeSelect id="o-month" value={data.month} onChange={(change) => setMonth(change.target.value)}>
              {months.map((item) => (
                <option key={item} value={item}>
                  {monthName(item)}
                </option>
              ))}
            </NativeSelect>
          </div>
        )}
      </div>

      {overview.isPending ? (
        <LoadingRows />
      ) : overview.isError ? (
        <ErrorState error={overview.error} />
      ) : data!.totals.length === 0 ? (
        <EmptyState>
          {monthName(data!.month)} hónapban még nincs egy esemény sem.
          {data!.transfer_count > 0 && ` (${data!.transfer_count} átvezetés nem számít bele.)`}
        </EmptyState>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            {[...data!.totals].sort(byCurrency).map((total) => (
              <TotalCard key={total.currency} total={total} />
            ))}
          </div>

          <ReviewNotice totals={data!.totals} />
          {data!.transfer_count > 0 && (
            <p className="text-sm text-muted-foreground">
              {data!.transfer_count} átvezetés a csoport saját számlái között nem számít bele az összegekbe.
            </p>
          )}

          <BucketTable title="Kategóriák szerint" column="Kategória" rows={data!.categories} label={categoryLabel} />
          <BucketTable title="Tagok szerint" column="Tag" rows={data!.members} label={(key) => key} />

          <p className="text-sm">
            <Link to="/esemenyek" className="underline underline-offset-4">
              Az összes esemény
            </Link>
          </p>
        </>
      )}
    </section>
  )
}

function TotalCard({ total }: { total: OverviewBucket }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">Kiadás ({total.currency})</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        <p className="text-3xl font-semibold tabular-nums">{money(total.expense, total.currency)}</p>
        <p className="text-sm text-muted-foreground">
          Bevétel: <span className="tabular-nums">{income(total.income, total.currency)}</span> · {total.event_count}{' '}
          esemény
        </p>
      </CardContent>
    </Card>
  )
}

function ReviewNotice({ totals }: { totals: OverviewBucket[] }) {
  const flagged = totals.filter((total) => total.review_count > 0)
  if (flagged.length === 0) return null
  const count = flagged.reduce((sum, total) => sum + total.review_count, 0)
  const amounts = flagged.map((total) => money(total.review_amount, total.currency)).join(' + ')
  return (
    <div role="status" className="flex items-start gap-2 rounded-lg bg-warning p-3 text-sm text-warning-foreground">
      <AlertTriangle className="mt-0.5 size-4 shrink-0" />
      <p>
        Ellenőrzésre vár: {count} esemény ({amounts}). Az összegek tartalmazzák; ha egy már rögzített vásárlás másik
        példányának bizonyul, a kiadás ennyivel kevesebb.{' '}
        <Link to="/ellenorzes" className="font-medium underline underline-offset-4">
          Ellenőrzés
        </Link>
      </p>
    </div>
  )
}

function BucketTable({
  title,
  column,
  rows,
  label,
}: {
  title: string
  column: string
  rows: OverviewBucket[]
  label: (key: string) => string
}) {
  const largest: Record<string, number> = {}
  for (const row of rows) largest[row.currency] = Math.max(largest[row.currency] ?? 0, Number(row.expense))
  // Stable sort: within a currency the API's order (largest spending first) stays.
  const sorted = [...rows].sort(byCurrency)
  const several = new Set(rows.map((row) => row.currency)).size > 1
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{column}</TableHead>
              <TableHead className="text-right">Kiadás</TableHead>
              <TableHead className="hidden text-right sm:table-cell">Bevétel</TableHead>
              <TableHead className="hidden text-right sm:table-cell">Esemény</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.map((row, index) => (
              <Fragment key={`${row.key}-${row.currency}`}>
                {several && row.currency !== sorted[index - 1]?.currency && (
                  <TableRow>
                    <TableCell colSpan={4} className="pt-4 text-xs font-medium text-muted-foreground">
                      {row.currency}
                    </TableCell>
                  </TableRow>
                )}
                <TableRow>
                  <TableCell>
                    <div className="flex flex-wrap items-center gap-2">
                      <span>{label(row.key)}</span>
                      {row.review_count > 0 && (
                        <span
                          className="rounded bg-warning px-1.5 text-xs text-warning-foreground"
                          title="Ellenőrzésre váró események"
                        >
                          {row.review_count} ellenőrzésre vár
                        </span>
                      )}
                    </div>
                    <div className="mt-1 h-1.5 rounded bg-muted" aria-hidden="true">
                      <div
                        className="h-1.5 rounded bg-primary"
                        style={{
                          width: `${largest[row.currency] ? (100 * Number(row.expense)) / largest[row.currency] : 0}%`,
                        }}
                      />
                    </div>
                  </TableCell>
                  <TableCell className="text-right align-top tabular-nums">
                    {money(row.expense, row.currency)}
                  </TableCell>
                  <TableCell className="hidden text-right align-top tabular-nums sm:table-cell">
                    {income(row.income, row.currency)}
                  </TableCell>
                  <TableCell className="hidden text-right align-top tabular-nums sm:table-cell">
                    {row.event_count}
                  </TableCell>
                </TableRow>
              </Fragment>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
