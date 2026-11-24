import { useState } from 'react'
import { toast } from 'sonner'

import { ApiError, type LlmSettings, type LlmSettingsInput } from '@/api/client'
import { useLlmSettings, useSaveLlmSettings } from '@/api/queries'
import { NativeSelect } from '@/components/NativeSelect'
import { ErrorState, LoadingRows } from '@/components/states'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { formatDateTime } from '@/lib/format'

const MODE_LABELS: Record<string, string> = {
  never: 'Soha (alapértelmezés)',
  after_arrival: 'A tétel beérkezése után megadott órával',
  daily: 'Naponta, megadott időpontban',
  weekly: 'Hetente, megadott napon és időpontban',
}

const WEEKDAYS = ['hétfő', 'kedd', 'szerda', 'csütörtök', 'péntek', 'szombat', 'vasárnap']

const usd = (value: string) =>
  `${Number(value).toLocaleString('hu-HU', { minimumFractionDigits: 2, maximumFractionDigits: 4 })} USD`

/** One line in Hungarian about when the model is asked under the saved setting. */
function scheduleSummary(settings: Pick<LlmSettings, 'mode' | 'hours_after' | 'run_time' | 'weekday'>): string {
  switch (settings.mode) {
    case 'after_arrival':
      return `A bizonytalan tételekről ${settings.hours_after} órával a beérkezésük után kérdezzük a modellt.`
    case 'daily':
      return `A bizonytalan tételekről naponta ${settings.run_time}-kor kérdezzük a modellt.`
    case 'weekly':
      return `A bizonytalan tételekről hetente, ${WEEKDAYS[settings.weekday] ?? ''} ${settings.run_time}-kor kérdezzük a modellt.`
    default:
      return 'A modellt csak akkor kérdezzük, ha egy tag egy tételnél a „Kérj javaslatot most” gombot választja.'
  }
}

function formFrom(settings: LlmSettings): LlmSettingsInput {
  return {
    mode: settings.mode,
    hours_after: settings.hours_after,
    run_time: settings.run_time,
    weekday: settings.weekday,
    monthly_budget_usd: settings.monthly_budget_usd,
  }
}

/**
 * W8 LLM setting (docs/design/categorization.md#when-the-llm-is-called-proposed-by-the-author-2026-11-19):
 * when the model is asked about uncertain categories, the monthly budget and what was spent. Every member
 * sees it; only an admin changes it, and the API also accepts the change only from a web session.
 */
export function LlmSettingsCard({ isAdmin }: { isAdmin: boolean }) {
  const settings = useLlmSettings()
  return (
    <Card>
      <CardHeader>
        <CardTitle>Kategória-javaslat nyelvi modellel</CardTitle>
        <CardDescription>
          Ha egy tétel kategóriája bizonytalan, egy nyelvi modell javasolhat kategóriát. A modellhez csak a tétel
          leírása, a kereskedő neve és az összeg jut el; név, számlaszám és a csoport más adata nem. Előbb mindig ti
          dönthettek: amit egy tag beállított, azt a modell soha nem írja felül.{' '}
          {isAdmin ? 'Adminként te módosíthatod.' : 'Csak a csoport adminja módosíthatja.'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {settings.isPending ? (
          <LoadingRows rows={3} />
        ) : settings.isError ? (
          <ErrorState error={settings.error} />
        ) : (
          <>
            {!settings.data.available && (
              <Alert>
                <AlertTitle>Ezen a szerveren nincs beállítva nyelvi modell</AlertTitle>
                <AlertDescription>
                  A beállítás elmenthető, de amíg nincs modell, senki nem kap javaslatot, és semmi nem hagyja el a
                  rendszert.
                </AlertDescription>
              </Alert>
            )}
            {settings.data.budget_exhausted && (
              <Alert variant="destructive" data-testid="budget-exhausted">
                <AlertTitle>Elfogyott a havi keret</AlertTitle>
                <AlertDescription>
                  Ebben a hónapban {usd(settings.data.spent_this_month_usd)} ment el, a havi keret{' '}
                  {usd(settings.data.monthly_budget_usd)}. A hónap végéig nem kérdezzük a modellt, a „Kérj
                  javaslatot most” gomb sem működik. A várakozó tételek a következő hónapban vagy magasabb kerettel
                  kerülnek sorra.
                </AlertDescription>
              </Alert>
            )}

            <dl className="grid gap-x-4 gap-y-1 text-sm sm:grid-cols-[auto_1fr]">
              <dt className="text-muted-foreground">Most érvényes</dt>
              <dd>{scheduleSummary(settings.data)}</dd>
              <dt className="text-muted-foreground">Ebben a hónapban</dt>
              <dd>
                {usd(settings.data.spent_this_month_usd)} elköltve, havi keret: {usd(settings.data.monthly_budget_usd)}
              </dd>
              {settings.data.model && (
                <>
                  <dt className="text-muted-foreground">Modell</dt>
                  <dd>
                    <code className="text-xs">{settings.data.model}</code>
                  </dd>
                </>
              )}
              {settings.data.updated_by && settings.data.updated_at && (
                <>
                  <dt className="text-muted-foreground">Utoljára módosította</dt>
                  <dd>
                    {settings.data.updated_by}, {formatDateTime(settings.data.updated_at)}
                  </dd>
                </>
              )}
            </dl>

            {isAdmin ? (
              <LlmSettingsForm key={settings.data.updated_at ?? 'default'} saved={settings.data} />
            ) : (
              !isAdmin && <Badge variant="outline">{MODE_LABELS[settings.data.mode] ?? settings.data.mode}</Badge>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}

/** The admin's form; it starts from the saved setting and is re-created when a save comes back. */
function LlmSettingsForm({ saved }: { saved: LlmSettings }) {
  const save = useSaveLlmSettings()
  const [form, setForm] = useState<LlmSettingsInput>(() => formFrom(saved))
  const update = (patch: Partial<LlmSettingsInput>) => setForm((current) => ({ ...current, ...patch }))

  function submit(event: React.FormEvent) {
    event.preventDefault()
    save.mutate(form, {
      onSuccess: () => toast.success('Az LLM-beállítás elmentve.'),
    })
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <div className="space-y-1">
        <Label htmlFor="llm-mode">Mikor kérdezzük a modellt?</Label>
        <NativeSelect id="llm-mode" value={form.mode} onChange={(event) => update({ mode: event.target.value })}>
          {Object.entries(MODE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </NativeSelect>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        {form.mode === 'after_arrival' && (
          <div className="space-y-1">
            <Label htmlFor="llm-hours">Hány óra múlva?</Label>
            <Input
              id="llm-hours"
              type="number"
              min={1}
              max={336}
              value={form.hours_after}
              onChange={(event) => update({ hours_after: Number(event.target.value) })}
              className="w-28"
            />
          </div>
        )}
        {form.mode === 'weekly' && (
          <div className="space-y-1">
            <Label htmlFor="llm-weekday">Melyik napon?</Label>
            <NativeSelect
              id="llm-weekday"
              value={String(form.weekday)}
              onChange={(event) => update({ weekday: Number(event.target.value) })}
            >
              {WEEKDAYS.map((day, index) => (
                <option key={day} value={index}>
                  {day}
                </option>
              ))}
            </NativeSelect>
          </div>
        )}
        {(form.mode === 'daily' || form.mode === 'weekly') && (
          <div className="space-y-1">
            <Label htmlFor="llm-time">Hánykor? (budapesti idő)</Label>
            <Input
              id="llm-time"
              type="time"
              value={form.run_time}
              onChange={(event) => update({ run_time: event.target.value })}
              className="w-32"
            />
          </div>
        )}
        <div className="space-y-1">
          <Label htmlFor="llm-budget">Havi keret (USD)</Label>
          <Input
            id="llm-budget"
            inputMode="decimal"
            value={String(form.monthly_budget_usd)}
            onChange={(event) =>
              update({
                monthly_budget_usd: event.target.value.replace(',', '.'),
              })
            }
            className="w-28"
          />
        </div>
      </div>
      <p className="text-xs text-muted-foreground">
        Mentéskor a most bizonytalan tételek is az új beállítás szerint kerülnek sorra. A keret elérésekor a hónap
        végéig nem kérdezzük a modellt.
      </p>
      <Button type="submit" disabled={save.isPending}>
        Mentés
      </Button>
      {save.isError && <p className="text-sm text-destructive">{saveRefusal(save.error)}</p>}
    </form>
  )
}

function saveRefusal(error: unknown): string {
  if (error instanceof ApiError && error.status === 403)
    return 'Ezt csak a csoport adminja módosíthatja, webes bejelentkezésből.'
  if (error instanceof ApiError && error.status === 400)
    return 'Valamelyik érték hibás: az óraszám 1 és 336 között, az időpont ÓÓ:PP alakban, a keret 0 és 100 USD között lehet.'
  return 'A mentés nem sikerült.'
}
