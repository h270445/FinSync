import { useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'

import { ApiError, type Review, type Transaction } from '@/api/client'
import { useConfirmMatch, useRejectMatch, useReviews, useSplitEvent } from '@/api/queries'
import { SourceBadge } from '@/components/badges'
import { EmptyState, ErrorState, LoadingRows } from '@/components/states'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { originalRecords } from '@/lib/events'
import { describeDelta, formatAmount, formatDate, formatDateTime, formatScore } from '@/lib/format'
import { cn } from '@/lib/utils'

/** The matcher's explanation of one review item (finsync/matching/scoring.py, core/service.py). */
interface Features {
  a?: number
  t?: number
  m?: number
  delta?: string
  score?: number
  runner_up?: number | null
  contested?: boolean
  identical_row_of_id?: number
}

const featuresOf = (review: Review) => (review.features ?? {}) as Features

/** W5: uncertain matches, one in focus at a time. */
export function ReviewPage() {
  const reviews = useReviews()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const items = reviews.data ?? []
  const selected = items.find((review) => review.decision_id === selectedId) ?? items[0]

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Ellenőrzés</h1>
      {reviews.isPending ? (
        <LoadingRows />
      ) : reviews.isError ? (
        <ErrorState error={reviews.error} />
      ) : !selected ? (
        <EmptyState>Nincs ellenőrzésre váró tétel.</EmptyState>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[18rem_1fr]">
          <nav aria-label="Ellenőrzésre váró tételek" className="space-y-2">
            <p className="text-sm text-muted-foreground">{items.length} ellenőrzésre vár</p>
            <ul className="space-y-1">
              {items.map((review) => (
                <li key={review.decision_id}>
                  <button
                    type="button"
                    aria-current={review === selected ? 'true' : undefined}
                    onClick={() => setSelectedId(review.decision_id)}
                    className={cn(
                      'flex w-full items-center justify-between gap-2 rounded-md border bg-card px-3 py-2 text-left text-sm hover:bg-muted',
                      'focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none',
                      review === selected && 'border-primary bg-accent',
                    )}
                  >
                    <span>
                      <span className="block font-medium">{merchantText(review.transaction)}</span>
                      <span className="text-muted-foreground tabular-nums">
                        {formatDate(review.transaction.happened_at, review.transaction.happened_at_precision)}
                      </span>
                    </span>
                    <span className="font-medium tabular-nums">
                      {formatAmount(review.transaction.amount, review.transaction.currency)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </nav>
          <ReviewItem key={selected.decision_id} review={selected} />
        </div>
      )}
    </section>
  )
}

function merchantText(record: Transaction): string {
  return record.merchant ?? record.description
}

function ReviewItem({ review }: { review: Review }) {
  const features = featuresOf(review)
  const event = review.candidate_event
  const confirm = useConfirmMatch()
  const reject = useRejectMatch()
  const split = useSplitEvent()
  const busy = confirm.isPending || reject.isPending

  const fail = (error: Error) =>
    toast.error(error instanceof ApiError ? error.message : 'A döntést nem sikerült elmenteni.')

  function same() {
    confirm.mutate(review.decision_id, {
      onSuccess: (result) =>
        toast.success('Összekapcsolva: ugyanaz a vásárlás.', {
          // Undo of a confirmation is a split of the record out of the event (logged as well).
          action: {
            label: 'Visszavonás',
            onClick: () =>
              split.mutate(
                { eventId: result.event_id, transactionId: result.transaction_id },
                { onSuccess: () => toast.success('Visszavonva: a tétel újra külön esemény.'), onError: fail },
              ),
          },
        }),
      onError: fail,
    })
  }

  function different() {
    reject.mutate(review.decision_id, {
      onSuccess: () => toast.success('Két külön vásárlásként rögzítve.'),
      onError: fail,
    })
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2">
        <RecordSide title="Új tétel" record={review.transaction} />
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              <Link to={`/esemenyek/${event.id}`} className="text-primary hover:underline">
                Meglévő esemény
              </Link>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {originalRecords(event).map(({ record }) => (
              <RecordFields key={record.id} record={record} />
            ))}
          </CardContent>
        </Card>
      </div>

      {features.identical_row_of_id !== undefined ? (
        <Alert>
          <AlertTitle>Azonos kézi tétel már rögzítve</AlertTitle>
          <AlertDescription>
            Ugyanez a tag ugyanezt a sort már rögzítette. Lehet elírás, de lehet két valódi vásárlás is (például két
            buszjegy).
          </AlertDescription>
        </Alert>
      ) : (
        <ScoreBreakdown review={review} features={features} />
      )}

      {typeof features.runner_up === 'number' && (
        <p className="text-sm text-muted-foreground">
          Másik lehetséges esemény is van (pontszám: {formatScore(features.runner_up)}).
        </p>
      )}

      {features.contested && (
        <Alert>
          <AlertTitle>Vitatott összekapcsolás</AlertTitle>
          <AlertDescription>
            Az eseményben már van egy hasonlóan valószínű tétel ugyanebből a forrásból, ezért a FinSync nem választ
            helyetted. Előbb válaszd le a másik tételt{' '}
            <Link to={`/esemenyek/${event.id}`} className="text-primary underline">
              az esemény oldalán
            </Link>
            .
          </AlertDescription>
        </Alert>
      )}

      <div className="flex flex-wrap gap-2">
        <Button size="lg" onClick={same} disabled={busy || features.contested}>
          Ugyanaz a vásárlás
        </Button>
        <Button size="lg" variant="outline" onClick={different} disabled={busy}>
          Két külön vásárlás
        </Button>
      </div>
    </div>
  )
}

function RecordSide({ title, record }: { title: string; record: Transaction }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <RecordFields record={record} />
      </CardContent>
    </Card>
  )
}

function RecordFields({ record }: { record: Transaction }) {
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
      <dt className="text-muted-foreground">Forrás</dt>
      <dd>
        <SourceBadge source={record.source} />
      </dd>
      <dt className="text-muted-foreground">Tag</dt>
      <dd>{record.user_id}</dd>
      <dt className="text-muted-foreground">Összeg</dt>
      <dd className="font-medium tabular-nums">{formatAmount(record.amount, record.currency)}</dd>
      <dt className="text-muted-foreground">Időpont</dt>
      <dd className="tabular-nums">{formatDateTime(record.happened_at, record.happened_at_precision)}</dd>
      <dt className="text-muted-foreground">Kereskedő</dt>
      {/* Exactly as received, so the member can judge the match. */}
      <dd className="font-mono text-xs break-words">{merchantText(record)}</dd>
    </dl>
  )
}

function ScoreBreakdown({ review, features }: { review: Review; features: Features }) {
  const rows = [
    {
      label: 'Összeg',
      value: features.a,
      note: features.a === 1 ? 'azonos összeg' : 'eltérő összeg',
    },
    {
      label: 'Időpont',
      value: features.t,
      note: features.delta ? describeDelta(features.delta) : '',
    },
    {
      label: 'Kereskedő',
      value: features.m,
      note: `${merchantText(review.transaction)} vs. ${review.candidate_event.merchant ?? '–'}`,
    },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Miért kérdezzük?</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {rows.map((row) =>
          row.value === undefined ? null : (
            <div key={row.label} className="grid grid-cols-[6rem_1fr_3rem] items-center gap-3 text-sm">
              <span>{row.label}</span>
              <div className="space-y-1">
                <Progress value={row.value * 100} aria-label={`${row.label}: ${formatScore(row.value)}`} />
                <span className="block text-xs text-muted-foreground">{row.note}</span>
              </div>
              <span className="text-right tabular-nums">{formatScore(row.value)}</span>
            </div>
          ),
        )}
        {review.score !== null && (
          <div className="flex justify-between border-t pt-3 text-sm font-medium">
            <span>Összpontszám</span>
            <span className="tabular-nums">{formatScore(review.score)}</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
