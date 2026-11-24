// Category correction in the web app (docs/design/categorization.md#review-in-the-web-app). The supervisor's
// UX principles (2026-11-23): every suggestion shows its source and uncertainty, confirming or changing is
// one tap, and "always use this for …" is offered only where the API allows a rule (remember_merchant).

import { Check } from 'lucide-react'
import { toast } from 'sonner'

import type { FinSyncEvent } from '@/api/client'
import { useSetCategory } from '@/api/queries'
import { NativeSelect } from '@/components/NativeSelect'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { categoryCertainty, refusal } from '@/lib/categoryText'
import { CATEGORY_CHOICES, categoryLabel, categorySourceLabel } from '@/lib/format'

/** "Élelmiszer · javaslat": a suggested category is lighter and marked, with its source on hover. */
export function CategoryBadge({ event }: { event: FinSyncEvent }) {
  return (
    <span className="inline-flex flex-wrap items-center gap-1" title={`Forrás: ${categorySourceLabel(event.category_source)}`}>
      <span className={event.uncertain ? 'text-muted-foreground italic' : undefined}>{categoryLabel(event.category)}</span>
      {event.uncertain && (
        <Badge variant="outline" className="font-normal">
          javaslat
        </Badge>
      )}
      {event.lines.length > 0 && (
        <Badge variant="secondary" className="font-normal">
          {event.lines.length} kategóriára bontva
        </Badge>
      )}
      {event.mixed && event.lines.length === 0 && (
        <Badge variant="secondary" className="font-normal">
          vegyes
        </Badge>
      )}
    </span>
  )
}

/**
 * One-tap correction for a list row: a category select (changing it saves at once) and, for a
 * suggestion, a confirm button. Split events and transfers are corrected on the detail page.
 */
export function QuickCategory({ event }: { event: FinSyncEvent }) {
  const setCategory = useSetCategory()
  if (event.direction === 'transfer' || event.lines.length > 0) return <CategoryBadge event={event} />

  function save(category: string) {
    setCategory.mutate(
      { eventId: event.id, category },
      {
        onSuccess: () => toast.success(`Kategória mentve: ${categoryLabel(category)}`),
        onError: (error) => toast.error(refusal(error, 'A kategória mentése nem sikerült.')),
      },
    )
  }

  const label = event.merchant ?? 'esemény'
  return (
    <span className="inline-flex items-center gap-1" onClick={(click) => click.stopPropagation()}>
      <NativeSelect
        aria-label={`Kategória: ${label}`}
        value={event.category}
        disabled={setCategory.isPending}
        onChange={(change) => save(change.target.value)}
        className={event.uncertain ? 'h-8 text-muted-foreground italic' : 'h-8'}
        title={categoryCertainty(event)}
      >
        {!CATEGORY_CHOICES.includes(event.category as (typeof CATEGORY_CHOICES)[number]) && (
          <option value={event.category}>{categoryLabel(event.category)}</option>
        )}
        {CATEGORY_CHOICES.map((category) => (
          <option key={category} value={category}>
            {categoryLabel(category)}
          </option>
        ))}
      </NativeSelect>
      {event.uncertain && CATEGORY_CHOICES.includes(event.category as (typeof CATEGORY_CHOICES)[number]) && (
        <Button
          variant="outline"
          size="icon-sm"
          aria-label={`Javaslat elfogadása: ${categoryLabel(event.category)} (${label})`}
          title="Javaslat elfogadása"
          disabled={setCategory.isPending}
          onClick={() => save(event.category)}
        >
          <Check aria-hidden />
        </Button>
      )}
      {event.uncertain && (
        <Badge variant="outline" className="font-normal">
          javaslat
        </Badge>
      )}
      {event.mixed && (
        <Badge variant="secondary" className="font-normal">
          vegyes
        </Badge>
      )}
    </span>
  )
}
