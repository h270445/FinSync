import { ArrowLeft } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'

import { ApiError, type FinSyncEvent, type Transaction } from '@/api/client'
import { useEvents, useSplitEvent } from '@/api/queries'
import { ReviewTag, SourceBadge } from '@/components/badges'
import { EmptyState, ErrorState, LoadingRows } from '@/components/states'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { originalRecords, primaryRecord } from '@/lib/events'
import { categoryLabel, formatAmount, formatDateTime } from '@/lib/format'

/** W4: one event and the records behind it, with the split action. */
export function EventDetailPage() {
  const { eventId } = useParams()
  const events = useEvents()
  const event = events.data?.find((candidate) => String(candidate.id) === eventId)

  return (
    <section className="space-y-6">
      <Link to="/esemenyek" className="inline-flex items-center gap-1 text-sm text-primary hover:underline">
        <ArrowLeft className="size-4" aria-hidden />
        Vissza az eseményekhez
      </Link>
      {events.isPending ? (
        <LoadingRows rows={3} />
      ) : events.isError ? (
        <ErrorState error={events.error} />
      ) : !event ? (
        <EmptyState>Nincs ilyen esemény ebben a csoportban.</EmptyState>
      ) : (
        <EventDetail event={event} />
      )}
    </section>
  )
}

function EventDetail({ event }: { event: FinSyncEvent }) {
  const records = originalRecords(event)
  const precision = primaryRecord(event)?.happened_at_precision

  return (
    <>
      <header className="space-y-1">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold">{event.merchant ?? 'Ismeretlen kereskedő'}</h1>
          {event.review_state === 'needs_review' && (
            <Link to="/ellenorzes">
              <ReviewTag />
            </Link>
          )}
        </div>
        <p className="text-xl font-medium tabular-nums">{formatAmount(event.amount, event.currency)}</p>
        <p className="text-muted-foreground">
          {formatDateTime(event.happened_at, precision)} · {categoryLabel(event.category)}
        </p>
      </header>

      <section className="space-y-3" aria-labelledby="sources-heading">
        <h2 id="sources-heading" className="text-lg font-semibold">
          Források ({records.length})
        </h2>
        <div className="grid gap-3 lg:grid-cols-2">
          {records.map(({ record, deliveries }) => (
            <RecordCard
              key={record.id}
              event={event}
              record={record}
              deliveries={deliveries}
              canSplit={records.length > 1}
            />
          ))}
        </div>
      </section>

      <section className="space-y-3" aria-labelledby="history-heading">
        <h2 id="history-heading" className="text-lg font-semibold">
          Döntési előzmények
        </h2>
        {/* The decision log is stored but no endpoint returns it yet (planned with the M2 web screens). */}
        <EmptyState>A döntési előzmények megjelenítése még nem érhető el.</EmptyState>
      </section>
    </>
  )
}

function RecordCard(props: { event: FinSyncEvent; record: Transaction; deliveries: number; canSplit: boolean }) {
  const { event, record, deliveries, canSplit } = props
  const [showRaw, setShowRaw] = useState(false)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2 text-base">
          <SourceBadge source={record.source} />
          <span>{record.merchant ?? record.description}</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
          <dt className="text-muted-foreground">Beküldte</dt>
          <dd>{record.user_id}</dd>
          <dt className="text-muted-foreground">Összeg</dt>
          <dd className="tabular-nums">{formatAmount(record.amount, record.currency)}</dd>
          <dt className="text-muted-foreground">Időpont</dt>
          <dd className="tabular-nums">{formatDateTime(record.happened_at, record.happened_at_precision)}</dd>
          <dt className="text-muted-foreground">Beérkezett</dt>
          <dd className="tabular-nums">{formatDateTime(record.created_at)}</dd>
          <dt className="text-muted-foreground">Leírás</dt>
          <dd className="break-words">{record.description}</dd>
        </dl>
        {deliveries > 1 && <p className="text-muted-foreground">Ismételt beküldés ({deliveries}×)</p>}
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" aria-expanded={showRaw} onClick={() => setShowRaw(!showRaw)}>
            {showRaw ? 'Nyers adat elrejtése' : 'Nyers adat megjelenítése'}
          </Button>
          {canSplit && <SplitButton event={event} record={record} />}
        </div>
        {showRaw && (
          <pre className="overflow-x-auto rounded-md bg-muted p-3 font-mono text-xs">
            {JSON.stringify(record, null, 2)}
          </pre>
        )}
      </CardContent>
    </Card>
  )
}

function SplitButton({ event, record }: { event: FinSyncEvent; record: Transaction }) {
  const [open, setOpen] = useState(false)
  const split = useSplitEvent()
  const navigate = useNavigate()

  function confirm() {
    // mutateAsync: the refetch moves this record out of the event and unmounts this button, and
    // per-call mutate callbacks of an unmounted component never run.
    split.mutateAsync({ eventId: event.id, transactionId: record.id }).then(
      (result) => {
        setOpen(false)
        toast.success('Szétválasztva: a tétel külön eseménybe került.', {
          action: { label: 'Megnyitás', onClick: () => navigate(`/esemenyek/${result.event_id}`) },
        })
      },
      (error) => toast.error(error instanceof ApiError ? error.message : 'A szétválasztás nem sikerült.'),
    )
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        Szétválasztás
      </Button>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Szétválasztod a tételt?</DialogTitle>
          <DialogDescription>
            A(z) {record.merchant ?? record.description} tétel ({formatAmount(record.amount, record.currency)}) kikerül
            ebből az eseményből, és külön eseménnyé válik. A döntés a naplóba kerül.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose render={<Button variant="outline" />}>Mégse</DialogClose>
          <Button onClick={confirm} disabled={split.isPending}>
            Szétválasztás
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
