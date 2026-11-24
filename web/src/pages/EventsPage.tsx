import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router'

import type { FinSyncEvent } from '@/api/client'
import { useEvents } from '@/api/queries'
import { ReviewTag, SourceBadge } from '@/components/badges'
import { QuickCategory } from '@/components/category'
import { NativeSelect } from '@/components/NativeSelect'
import { EmptyState, ErrorState, LoadingRows } from '@/components/states'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { monthOf, originalRecords, primaryRecord } from '@/lib/events'
import { categoryLabel, formatAmount, formatDate, formatTime, monthName, sourceLabel } from '@/lib/format'

const ALL = ''

interface Filters {
  month: string
  member: string
  category: string
  source: string
  search: string
  /** Only suggested categories nobody settled ("uncertain categories" filter of the design). */
  uncertain: boolean
}

function unique(values: string[]): string[] {
  return [...new Set(values)].sort()
}

function matches(event: FinSyncEvent, filters: Filters): boolean {
  const search = filters.search.trim().toLocaleLowerCase('hu')
  return (
    (filters.month === ALL || monthOf(event) === filters.month) &&
    (filters.member === ALL || event.transactions.some((record) => record.user_id === filters.member)) &&
    (filters.category === ALL || event.category === filters.category) &&
    (filters.source === ALL || event.transactions.some((record) => record.source === filters.source)) &&
    (!filters.uncertain || event.uncertain) &&
    (event.merchant ?? '').toLocaleLowerCase('hu').includes(search)
  )
}

/** W3: the group's deduplicated events, newest first. */
export function EventsPage() {
  const events = useEvents()
  const navigate = useNavigate()
  const [filters, setFilters] = useState<Filters>({
    month: ALL,
    member: ALL,
    category: ALL,
    source: ALL,
    search: '',
    uncertain: false,
  })
  const set = (key: keyof Filters) => (change: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setFilters({ ...filters, [key]: change.target.value })

  const all = useMemo(
    () => [...(events.data ?? [])].sort((a, b) => b.happened_at.localeCompare(a.happened_at)),
    [events.data],
  )
  const options = useMemo(
    () => ({
      months: unique(all.map(monthOf)).reverse(),
      members: unique(all.flatMap((event) => event.transactions.map((record) => record.user_id))),
      categories: unique(all.map((event) => event.category)),
      sources: unique(all.flatMap((event) => event.transactions.map((record) => record.source))),
    }),
    [all],
  )
  const shown = all.filter((event) => matches(event, filters))

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Események</h1>

      <div className="flex flex-wrap items-end gap-3">
        <Filter label="Hónap" id="f-month">
          <NativeSelect id="f-month" value={filters.month} onChange={set('month')}>
            <option value={ALL}>Összes hónap</option>
            {options.months.map((month) => (
              <option key={month} value={month}>
                {monthName(month)}
              </option>
            ))}
          </NativeSelect>
        </Filter>
        <Filter label="Tag" id="f-member">
          <NativeSelect id="f-member" value={filters.member} onChange={set('member')}>
            <option value={ALL}>Mindenki</option>
            {options.members.map((member) => (
              <option key={member}>{member}</option>
            ))}
          </NativeSelect>
        </Filter>
        <Filter label="Kategória" id="f-category">
          <NativeSelect id="f-category" value={filters.category} onChange={set('category')}>
            <option value={ALL}>Összes kategória</option>
            {options.categories.map((category) => (
              <option key={category} value={category}>
                {categoryLabel(category)}
              </option>
            ))}
          </NativeSelect>
        </Filter>
        <Filter label="Forrás" id="f-source">
          <NativeSelect id="f-source" value={filters.source} onChange={set('source')}>
            <option value={ALL}>Összes forrás</option>
            {options.sources.map((source) => (
              <option key={source} value={source}>
                {sourceLabel(source)}
              </option>
            ))}
          </NativeSelect>
        </Filter>
        <Filter label="Kereskedő" id="f-search">
          <Input
            id="f-search"
            type="search"
            placeholder="Keresés…"
            value={filters.search}
            onChange={set('search')}
            className="h-9 w-48"
          />
        </Filter>
        <label className="flex h-9 items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={filters.uncertain}
            onChange={(change) => setFilters({ ...filters, uncertain: change.target.checked })}
          />
          Csak bizonytalan kategóriák ({all.filter((event) => event.uncertain).length})
        </label>
      </div>

      {events.isPending ? (
        <LoadingRows />
      ) : events.isError ? (
        <ErrorState error={events.error} />
      ) : shown.length === 0 ? (
        <EmptyState>{all.length === 0 ? 'Még nincs egy esemény sem.' : 'Nincs a szűrésnek megfelelő esemény.'}</EmptyState>
      ) : (
        <>
          <p className="text-sm text-muted-foreground">{shown.length} esemény</p>

          {/* Desktop: table. Phone (below md): card list. */}
          <div className="hidden rounded-lg border bg-card md:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Dátum</TableHead>
                  <TableHead>Kereskedő</TableHead>
                  <TableHead>Kategória</TableHead>
                  <TableHead className="text-right">Összeg</TableHead>
                  <TableHead>Tag</TableHead>
                  <TableHead>Források</TableHead>
                  <TableHead>Állapot</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {shown.map((event) => {
                  const primary = primaryRecord(event)
                  const precision = primary?.happened_at_precision
                  return (
                    <TableRow
                      key={event.id}
                      className="h-10 cursor-pointer"
                      onClick={() => navigate(`/esemenyek/${event.id}`)}
                    >
                      <TableCell className="tabular-nums">
                        {formatDate(event.happened_at, precision)}{' '}
                        <span className="text-muted-foreground">{formatTime(event.happened_at, precision)}</span>
                      </TableCell>
                      <TableCell>
                        <Link
                          to={`/esemenyek/${event.id}`}
                          className="font-medium hover:underline focus-visible:underline focus-visible:outline-none"
                          onClick={(click) => click.stopPropagation()}
                        >
                          {event.merchant ?? 'Ismeretlen kereskedő'}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <QuickCategory event={event} />
                      </TableCell>
                      <TableCell className="text-right font-medium tabular-nums">
                        {formatAmount(event.amount, event.currency)}
                      </TableCell>
                      <TableCell>{primary?.user_id}</TableCell>
                      <TableCell>
                        <Sources event={event} />
                      </TableCell>
                      <TableCell>
                        {event.review_state === 'needs_review' && (
                          <Link to="/ellenorzes" onClick={(click) => click.stopPropagation()}>
                            <ReviewTag />
                          </Link>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>

          <ul className="space-y-2 md:hidden">
            {shown.map((event) => {
              const precision = primaryRecord(event)?.happened_at_precision
              return (
                <li key={event.id} className="space-y-2 rounded-lg border bg-card p-3">
                  <Link
                    to={`/esemenyek/${event.id}`}
                    className="block space-y-2 rounded-md focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
                  >
                    <div className="flex justify-between gap-2">
                      <span className="font-medium">{event.merchant ?? 'Ismeretlen kereskedő'}</span>
                      <span className="font-medium tabular-nums">{formatAmount(event.amount, event.currency)}</span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                      <span className="tabular-nums">{formatDate(event.happened_at, precision)}</span>
                      <Sources event={event} />
                      {event.review_state === 'needs_review' && <ReviewTag />}
                    </div>
                  </Link>
                  {/* Outside the link: one tap confirms or changes the category without opening the event. */}
                  <div className="text-sm">
                    <QuickCategory event={event} />
                  </div>
                </li>
              )
            })}
          </ul>
        </>
      )}
    </section>
  )
}

function Filter({ label, id, children }: { label: string; id: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={id} className="text-xs text-muted-foreground">
        {label}
      </Label>
      {children}
    </div>
  )
}

function Sources({ event }: { event: FinSyncEvent }) {
  return (
    <span className="flex flex-wrap gap-1">
      {originalRecords(event).map(({ record }) => (
        <SourceBadge key={record.id} source={record.source} />
      ))}
    </span>
  )
}
