// W4 event detail: the category card. Confirm or change the category (optionally remembered for the
// merchant), mark the purchase as mixed, split it into category lines, mark it as a transfer, and read
// the change log (docs/design/categorization.md#review-in-the-web-app).

import { Plus, Trash2, TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import type { CategoryChange, CategoryLineInput, FinSyncEvent } from '@/api/client'
import {
  useCategoryChanges,
  useSetCategory,
  useSetCategoryLines,
  useSetMixed,
  useSetTransfer,
  useSuggestCategory,
} from '@/api/queries'
import { CategoryBadge } from '@/components/category'
import { NativeSelect } from '@/components/NativeSelect'
import { ErrorState, LoadingRows } from '@/components/states'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { type DraftLine, initialLines, linesToSave, remainder } from '@/lib/categoryLines'
import { categoryCertainty, llmDueText, refusal, ruleMessage } from '@/lib/categoryText'
import { CATEGORY_CHOICES, categoryLabel, formatAmount, formatDateTime } from '@/lib/format'

export function CategoryPanel({ event }: { event: FinSyncEvent }) {
  const isTransfer = event.direction === 'transfer'
  const [editingLines, setEditingLines] = useState(false)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2 text-base">
          Kategória: <CategoryBadge event={event} />
        </CardTitle>
        <CardDescription>{categoryCertainty(event)}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {isTransfer ? (
          <p>Átvezetés a csoport saját számlái között: kimarad a kiadások és bevételek összegéből.</p>
        ) : editingLines ? (
          <LineEditor event={event} onDone={() => setEditingLines(false)} />
        ) : (
          <>
            {event.lines.length === 0 ? <CategoryChooser key={event.category} event={event} /> : <SavedLines event={event} />}
            {llmDueText(event) && <p className="text-muted-foreground">{llmDueText(event)}</p>}
            <div className="flex flex-wrap items-center gap-2">
              <MixedToggle event={event} />
              <SuggestButton event={event} />
              <Button variant="outline" size="sm" onClick={() => setEditingLines(true)}>
                {event.lines.length > 0 ? 'Felosztás módosítása' : 'Felosztás kategóriákra'}
              </Button>
            </div>
          </>
        )}
        {!editingLines && <TransferButton event={event} />}
        <CategoryHistory event={event} />
      </CardContent>
    </Card>
  )
}

function CategoryChooser({ event }: { event: FinSyncEvent }) {
  const [category, setCategory] = useState(
    CATEGORY_CHOICES.includes(event.category as (typeof CATEGORY_CHOICES)[number]) ? event.category : '',
  )
  const [remember, setRemember] = useState(false)
  const save = useSetCategory()

  function submit(chosen: string) {
    save.mutate(
      { eventId: event.id, category: chosen, remember: remember && event.remember_merchant !== null },
      {
        onSuccess: (result) => {
          toast.success(`Kategória mentve: ${categoryLabel(chosen)}`, { description: ruleMessage(result) ?? undefined })
          setRemember(false)
        },
        onError: (error) => toast.error(refusal(error, 'A kategória mentése nem sikerült.')),
      },
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-2">
        <div className="flex flex-col gap-1">
          <Label htmlFor="category-choice" className="text-xs text-muted-foreground">
            Kategória
          </Label>
          <NativeSelect id="category-choice" value={category} onChange={(change) => setCategory(change.target.value)}>
            {category === '' && <option value="">Válassz…</option>}
            {CATEGORY_CHOICES.map((choice) => (
              <option key={choice} value={choice}>
                {categoryLabel(choice)}
              </option>
            ))}
          </NativeSelect>
        </div>
        <Button size="lg" disabled={category === '' || save.isPending} onClick={() => submit(category)}>
          {event.uncertain && category === event.category ? 'Javaslat elfogadása' : 'Mentés'}
        </Button>
      </div>
      {event.remember_merchant !== null && (
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={remember} onChange={(change) => setRemember(change.target.checked)} />
          Mindig ezt használd: {event.remember_merchant}
        </label>
      )}
    </div>
  )
}

function SavedLines({ event }: { event: FinSyncEvent }) {
  return (
    <div className="space-y-2">
      {event.lines_match_amount === false && (
        <Alert>
          <TriangleAlert />
          <AlertDescription>
            A sorok már nem adják ki az esemény összegét (közben egy tételt leválasztottak). Amíg nem javítod, az
            összesítő a teljes összeget a fő kategóriánál számolja.
          </AlertDescription>
        </Alert>
      )}
      <ul className="divide-y rounded-md border">
        {event.lines.map((line) => (
          <li key={line.category} className="flex justify-between gap-2 px-3 py-2">
            <span>{categoryLabel(line.category)}</span>
            <span className="tabular-nums">{formatAmount(line.amount, event.currency)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function MixedToggle({ event }: { event: FinSyncEvent }) {
  const setMixed = useSetMixed()
  if (event.lines.length > 0) return null
  return (
    <label className="flex items-center gap-2">
      <input
        type="checkbox"
        checked={event.mixed}
        disabled={setMixed.isPending}
        onChange={(change) =>
          setMixed.mutate(
            { eventId: event.id, mixed: change.target.checked },
            { onError: (error) => toast.error(refusal(error, 'A mentés nem sikerült.')) },
          )
        }
      />
      Vegyes vásárlás (több kategória, összeg nélkül)
    </label>
  )
}

/** Every line's amount is typed except the last, which takes the remainder, so the lines always add up. */
function LineEditor({ event, onDone }: { event: FinSyncEvent; onDone: () => void }) {
  const [lines, setLines] = useState<DraftLine[]>(() => initialLines(event))
  const save = useSetCategoryLines()
  const rest = remainder(event, lines)
  const result = linesToSave(event, lines)
  const update = (index: number, change: Partial<DraftLine>) =>
    setLines(lines.map((line, at) => (at === index ? { ...line, ...change } : line)))

  function submit(toSend: CategoryLineInput[]) {
    save.mutate(
      { eventId: event.id, lines: toSend },
      {
        onSuccess: () => {
          toast.success(toSend.length > 0 ? 'Felosztás mentve.' : 'Felosztás törölve.')
          onDone()
        },
        onError: (error) => toast.error(refusal(error, 'A felosztás mentése nem sikerült.')),
      },
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-muted-foreground">
        Teljes összeg: <span className="tabular-nums">{formatAmount(event.amount, event.currency)}</span>. Az utolsó sor
        a maradékot kapja.
      </p>
      <ul className="space-y-2">
        {lines.map((line, index) => {
          const last = index === lines.length - 1
          return (
            <li key={index} className="flex flex-wrap items-center gap-2">
              <NativeSelect
                aria-label={`${index + 1}. sor kategóriája`}
                value={line.category}
                onChange={(change) => update(index, { category: change.target.value })}
              >
                <option value="">Válassz…</option>
                {CATEGORY_CHOICES.map((choice) => (
                  <option key={choice} value={choice}>
                    {categoryLabel(choice)}
                  </option>
                ))}
              </NativeSelect>
              {last ? (
                <span className="w-32 tabular-nums" aria-label={`${index + 1}. sor összege (maradék)`}>
                  {rest === null ? '–' : formatAmount(rest, event.currency)}
                </span>
              ) : (
                <Input
                  aria-label={`${index + 1}. sor összege`}
                  inputMode="decimal"
                  value={line.amount}
                  onChange={(change) => update(index, { amount: change.target.value })}
                  className="h-9 w-32"
                />
              )}
              {lines.length > 2 && (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={`${index + 1}. sor törlése`}
                  onClick={() => setLines(lines.filter((_, at) => at !== index))}
                >
                  <Trash2 aria-hidden />
                </Button>
              )}
            </li>
          )
        })}
      </ul>
      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setLines([...lines.slice(0, -1), { category: '', amount: '0' }, lines[lines.length - 1]])}
        >
          <Plus aria-hidden /> Sor hozzáadása
        </Button>
      </div>
      {typeof result === 'string' && <p className="text-muted-foreground">{result}</p>}
      <div className="flex flex-wrap gap-2">
        <Button disabled={typeof result === 'string' || save.isPending} onClick={() => typeof result !== 'string' && submit(result)}>
          Felosztás mentése
        </Button>
        {event.lines.length > 0 && (
          <Button variant="outline" disabled={save.isPending} onClick={() => submit([])}>
            Felosztás törlése
          </Button>
        )}
        <Button variant="ghost" onClick={onDone}>
          Mégse
        </Button>
      </div>
    </div>
  )
}

/**
 * "Kérj javaslatot most": only for a suggestion nobody settled. The server answers 409 with the reason when
 * it has no model or the group's monthly budget is used up; the toast shows it.
 */
function SuggestButton({ event }: { event: FinSyncEvent }) {
  const suggest = useSuggestCategory()
  if (!event.uncertain || event.lines.length > 0) return null
  return (
    <Button
      variant="outline"
      size="sm"
      disabled={suggest.isPending}
      title="Csak a kereskedő, a leírás és az összeg kerül a modellhez."
      onClick={() =>
        suggest.mutate(event.id, {
          onSuccess: (answer) =>
            answer.uncertain
              ? toast.info('A modell sem biztos benne; a javaslat maradt.')
              : toast.success(`A modell javaslata: ${categoryLabel(answer.category)}`),
          onError: (error) => toast.error(refusal(error, 'A modell most nem érhető el.')),
        })
      }
    >
      {suggest.isPending ? 'A modell gondolkodik…' : 'Kérj javaslatot a modelltől'}
    </Button>
  )
}

function TransferButton({ event }: { event: FinSyncEvent }) {
  const setTransfer = useSetTransfer()
  const isTransfer = event.direction === 'transfer'
  if (!isTransfer && event.lines.length > 0) return null
  return (
    <Button
      variant="outline"
      size="sm"
      disabled={setTransfer.isPending}
      onClick={() =>
        setTransfer.mutate(
          { eventId: event.id, transfer: !isTransfer },
          {
            onSuccess: () => toast.success(isTransfer ? 'Már nem átvezetés.' : 'Átvezetésként megjelölve.'),
            onError: (error) => toast.error(refusal(error, 'A mentés nem sikerült.')),
          },
        )
      }
    >
      {isTransfer ? 'Mégsem átvezetés' : 'Átvezetés saját számlák között'}
    </Button>
  )
}

const KIND_LABELS: Record<string, string> = {
  category: 'Kategória',
  mixed: 'Vegyes jelölés',
  lines: 'Felosztás',
  transfer: 'Átvezetés',
}

function describeChange(change: CategoryChange): string {
  const value = change.new_value as Record<string, unknown> | boolean | { category: string; amount: string }[] | null
  switch (change.kind) {
    case 'category':
      return categoryLabel(String((value as Record<string, unknown>).category))
    case 'mixed':
      return value ? 'bekapcsolva' : 'kikapcsolva'
    case 'lines': {
      const lines = value as { category: string; amount: string }[]
      return lines.length === 0 ? 'törölve' : lines.map((line) => categoryLabel(line.category)).join(' + ')
    }
    case 'transfer':
      return (value as Record<string, unknown>).direction === 'transfer' ? 'megjelölve' : 'visszavonva'
    default:
      return ''
  }
}

function CategoryHistory({ event }: { event: FinSyncEvent }) {
  const changes = useCategoryChanges(event.id)
  if (changes.isPending) return <LoadingRows rows={1} />
  if (changes.isError) return <ErrorState error={changes.error} />
  if (changes.data.length === 0) return <p className="text-muted-foreground">A kategóriát még senki nem módosította.</p>
  return (
    <div className="space-y-1">
      <h3 className="font-medium">Kategória-előzmények</h3>
      <ol className="space-y-1 border-l pl-4">
        {changes.data.map((change) => (
          <li key={change.id}>
            <span className="font-medium">{KIND_LABELS[change.kind] ?? change.kind}:</span> {describeChange(change)}
            <span className="text-xs text-muted-foreground">
              {' · '}
              {change.changed_by} · <span className="tabular-nums">{formatDateTime(change.created_at)}</span>
            </span>
          </li>
        ))}
      </ol>
    </div>
  )
}
