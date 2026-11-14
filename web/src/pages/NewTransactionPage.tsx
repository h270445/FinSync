import { useState } from 'react'
import { Link } from 'react-router'

import { ApiError, type StoreResult } from '@/api/client'
import { useCreateTransaction } from '@/api/queries'
import { useSession } from '@/auth/session'
import { NativeSelect } from '@/components/NativeSelect'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { parseAmount } from '@/lib/format'

// W6 manual entry (docs/design/user-interface.md#web-app) on POST /v1/transactions.
// The member is the signed-in one: the API takes identity from the session only.
// A time without an offset is Budapest wall-clock time on the server (ADR 0008), so the form
// sends "2026-11-14T18:30" as typed; without a time the entry is a calendar day.

const CURRENCIES = ['HUF', 'EUR', 'USD']

type Fields = {
  direction: 'expense' | 'income'
  amount: string
  currency: string
  date: string
  time: string
  merchant: string
  description: string
}
type Errors = Partial<Record<'amount' | 'date' | 'description', string>>

/** Today in Budapest as "2026-11-14", the date input's default. */
function today(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Budapest' }).format(new Date())
}

const empty = (): Fields => ({
  direction: 'expense',
  amount: '',
  currency: 'HUF',
  date: today(),
  time: '',
  merchant: '',
  description: '',
})

function validate(fields: Fields): Errors {
  const errors: Errors = {}
  if (!fields.amount.trim()) errors.amount = 'Add meg az összeget.'
  else if (parseAmount(fields.amount) === null) errors.amount = 'Az összegnek pozitív számnak kell lennie, legfeljebb két tizedesjeggyel.'
  if (!fields.date) errors.date = 'Add meg a dátumot.'
  if (!fields.description.trim()) errors.description = 'Add meg a leírást.'
  return errors
}

export function NewTransactionPage() {
  const { session } = useSession()
  const create = useCreateTransaction()
  const [fields, setFields] = useState<Fields>(empty)
  const [errors, setErrors] = useState<Errors>({})
  const [result, setResult] = useState<StoreResult | null>(null)
  const [refused, setRefused] = useState<string | null>(null)

  const set = (name: keyof Fields) => (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setFields((current) => ({ ...current, [name]: event.target.value }))

  function submit(event: React.FormEvent) {
    event.preventDefault()
    const found = validate(fields)
    setErrors(found)
    setRefused(null)
    if (Object.keys(found).length > 0) return
    create
      .mutateAsync({
        amount: parseAmount(fields.amount)!,
        currency: fields.currency,
        direction: fields.direction,
        happened_at: fields.time ? `${fields.date}T${fields.time}` : fields.date,
        description: fields.description.trim(),
        merchant: fields.merchant.trim() || null,
      })
      .then(
        (stored) => {
          setResult(stored)
          setFields(empty())
        },
        (error: unknown) =>
          setRefused(error instanceof ApiError ? error.message : 'Nem sikerült elérni a szervert. Fut az API (python -m finsync.api)?'),
      )
  }

  const describedBy = (name: keyof Errors) => (errors[name] ? `${name}-error` : undefined)
  const fieldError = (name: keyof Errors) =>
    errors[name] && (
      <p id={`${name}-error`} className="text-sm text-destructive">
        {errors[name]}
      </p>
    )

  return (
    <section className="max-w-2xl space-y-4">
      <h1 className="text-2xl font-semibold">Új tétel</h1>
      {result && <Outcome result={result} onClose={() => setResult(null)} />}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Kézi rögzítés</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4" noValidate>
            <div className="grid gap-4 sm:grid-cols-[auto_1fr_auto]">
              <div className="space-y-2">
                <Label htmlFor="direction">Irány</Label>
                <NativeSelect id="direction" className="w-full" value={fields.direction} onChange={set('direction')}>
                  <option value="expense">Kiadás</option>
                  <option value="income">Bevétel</option>
                </NativeSelect>
              </div>
              <div className="space-y-2">
                <Label htmlFor="amount">Összeg</Label>
                <Input
                  id="amount"
                  inputMode="decimal"
                  autoComplete="off"
                  placeholder="pl. 4 990"
                  value={fields.amount}
                  onChange={set('amount')}
                  aria-invalid={errors.amount ? true : undefined}
                  aria-describedby={describedBy('amount')}
                />
                {fieldError('amount')}
              </div>
              <div className="space-y-2">
                <Label htmlFor="currency">Pénznem</Label>
                <NativeSelect id="currency" className="w-full" value={fields.currency} onChange={set('currency')}>
                  {CURRENCIES.map((code) => (
                    <option key={code} value={code}>
                      {code === 'HUF' ? 'Ft' : code}
                    </option>
                  ))}
                </NativeSelect>
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="date">Dátum</Label>
                <Input
                  id="date"
                  type="date"
                  value={fields.date}
                  onChange={set('date')}
                  aria-invalid={errors.date ? true : undefined}
                  aria-describedby={describedBy('date')}
                />
                {fieldError('date')}
              </div>
              <div className="space-y-2">
                <Label htmlFor="time">Időpont (nem kötelező)</Label>
                <Input id="time" type="time" value={fields.time} onChange={set('time')} aria-describedby="time-hint" />
                <p id="time-hint" className="text-xs text-muted-foreground">
                  Budapesti idő. Időpont nélkül a tétel a teljes napra vonatkozik.
                </p>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="merchant">Kereskedő (nem kötelező)</Label>
              <Input id="merchant" autoComplete="off" value={fields.merchant} onChange={set('merchant')} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Leírás</Label>
              <Input
                id="description"
                autoComplete="off"
                value={fields.description}
                onChange={set('description')}
                aria-invalid={errors.description ? true : undefined}
                aria-describedby={describedBy('description')}
              />
              {fieldError('description')}
            </div>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
              <dt className="text-muted-foreground">Kategória</dt>
              <dd>automatikus (az eseménynél javítható)</dd>
              <dt className="text-muted-foreground">Tag</dt>
              <dd>{session?.user_id}</dd>
            </dl>
            {refused && (
              <p role="alert" className="text-sm text-destructive">
                {refused}
              </p>
            )}
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? 'Mentés…' : 'Mentés'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </section>
  )
}

/** What the matcher did with the new record: a new event, a link to an existing one, or a question. */
function Outcome({ result, onClose }: { result: StoreResult; onClose: () => void }) {
  const eventLink = (
    <Link className="font-medium underline underline-offset-4" to={`/esemenyek/${result.event_id}`}>
      Esemény megnyitása
    </Link>
  )
  const content: Record<string, { title: string; body: React.ReactNode }> = {
    separate: { title: 'Mentve új eseményként.', body: eventLink },
    auto_linked: {
      title: 'Mentve, és egy meglévő eseményhez kapcsoltuk: ugyanaz a vásárlás.',
      body: <>{eventLink}. Ha tévedés, ott szétválaszthatod.</>,
    },
    needs_review: {
      title: 'Mentve, de hasonlít egy meglévő eseményre.',
      body: (
        <>
          Döntsd el az{' '}
          <Link className="font-medium underline underline-offset-4" to="/ellenorzes">
            Ellenőrzés
          </Link>{' '}
          oldalon, hogy ugyanaz a vásárlás-e.
        </>
      ),
    },
    exact_duplicate: { title: 'Ezt a tételt már korábban rögzítették.', body: eventLink },
  }
  const shown = content[result.match_outcome] ?? content.separate
  return (
    <Alert role="status">
      <AlertTitle>{shown.title}</AlertTitle>
      <AlertDescription>
        <p>{shown.body}</p>
        <Button variant="link" className="h-auto p-0" onClick={onClose}>
          Bezárás
        </Button>
      </AlertDescription>
    </Alert>
  )
}
