import { AlertCircle, CheckCircle2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import { ApiError, type ColumnMapping, type ImportResult } from '@/api/client'
import { type ImportRequest, useImportFile } from '@/api/queries'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatAmount, formatDate, outcomeLabel } from '@/lib/format'
import { importMessage, MAX_REQUEST_BYTES, type ReadFile, readImportFile } from '@/lib/importFile'

// FinSync's generic headers, the API's defaults (docs/guides/api.md#post-v1imports).
const DEFAULT_MAPPING: ColumnMapping = {
  date: 'date',
  amount: 'amount',
  description: 'description',
  merchant: 'merchant',
  currency: 'currency',
  reference: 'reference',
  default_currency: 'HUF',
}

const FIELDS: { key: keyof ColumnMapping; label: string; required?: boolean }[] = [
  { key: 'date', label: 'Dátum', required: true },
  { key: 'amount', label: 'Összeg', required: true },
  { key: 'description', label: 'Leírás', required: true },
  { key: 'merchant', label: 'Kereskedő' },
  { key: 'currency', label: 'Pénznem' },
  { key: 'reference', label: 'Banki azonosító' },
]

// A member imports the same bank's export every month, so the last mapping is remembered in this browser.
const MAPPING_KEY = 'finsync.import.mapping'

function loadMapping(): ColumnMapping {
  try {
    const saved = localStorage.getItem(MAPPING_KEY)
    return saved ? { ...DEFAULT_MAPPING, ...(JSON.parse(saved) as Partial<ColumnMapping>) } : DEFAULT_MAPPING
  } catch {
    return DEFAULT_MAPPING
  }
}

function saveMapping(mapping: ColumnMapping) {
  try {
    localStorage.setItem(MAPPING_KEY, JSON.stringify(mapping))
  } catch {
    // Private windows may refuse storage; the mapping is then simply not remembered.
  }
}

/** W7: upload a spreadsheet export (CSV or XLSX), check it in a preview, then import every row or none. */
export function ImportPage() {
  const [file, setFile] = useState<ReadFile | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const [mapping, setMapping] = useState<ColumnMapping>(loadMapping)
  const [preview, setPreview] = useState<ImportResult | null>(null)
  const [done, setDone] = useState<ImportResult | null>(null)
  const upload = useImportFile()

  function reset() {
    setPreview(null)
    setDone(null)
    upload.reset()
  }

  async function choose(event: React.ChangeEvent<HTMLInputElement>) {
    reset()
    setFile(null)
    setFileError(null)
    const chosen = event.target.files?.[0]
    if (!chosen) return
    try {
      const read = await readImportFile(chosen)
      if (read.requestSize > MAX_REQUEST_BYTES) setFileError('A fájl túl nagy (legfeljebb kb. 1 MB). Bontsd több részre.')
      else setFile(read)
    } catch {
      setFileError('A fájlt nem sikerült beolvasni.')
    }
  }

  function request(dryRun: boolean): ImportRequest {
    const body: ImportRequest = { mapping: cleaned(mapping), dry_run: dryRun }
    if (file?.kind === 'xlsx') body.xlsx_base64 = file.base64
    else body.content = file?.content
    return body
  }

  function check(event: React.FormEvent) {
    event.preventDefault()
    if (!file) return
    reset()
    saveMapping(mapping)
    upload.mutate(request(true), { onSuccess: setPreview })
  }

  function importAll() {
    upload.mutate(request(false), { onSuccess: setDone })
  }

  const blocked = !preview || preview.errors.length > 0 || preview.already_imported || preview.rows.length === 0

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Importálás</h1>

      <Card>
        <CardHeader>
          <CardTitle>Bankszámla- vagy táblázatexport</CardTitle>
          <CardDescription>
            CSV vagy XLSX fájl, soronként egy tétel. Előbb ellenőrizd, utána importáld: a fájl minden sora bekerül,
            vagy egyik sem.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={check} className="space-y-4" noValidate>
            <div className="space-y-2">
              <Label htmlFor="import-file">Fájl</Label>
              <Input
                id="import-file"
                type="file"
                accept=".csv,.txt,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                onChange={(event) => void choose(event)}
                aria-describedby={fileError ? 'import-file-error' : undefined}
              />
              {fileError && (
                <p id="import-file-error" role="alert" className="text-sm text-destructive">
                  {fileError}
                </p>
              )}
            </div>

            <fieldset className="space-y-3">
              <legend className="text-sm font-medium">Oszlopok</legend>
              <p className="text-sm text-muted-foreground">
                Melyik oszlop fejléce mit tartalmaz. A nem kötelező mezőt hagyd üresen, ha a fájlban nincs ilyen oszlop.
                {file?.kind === 'csv' && file.header.length > 0 && <> A fájl oszlopai: {file.header.join(', ')}.</>}
              </p>
              <datalist id="import-columns">
                {file?.kind === 'csv' && file.header.map((name) => <option key={name} value={name} />)}
              </datalist>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {FIELDS.map(({ key, label, required }) => (
                  <div key={key} className="space-y-1">
                    <Label htmlFor={`map-${key}`}>
                      {label}
                      {!required && <span className="font-normal text-muted-foreground"> (nem kötelező)</span>}
                    </Label>
                    <Input
                      id={`map-${key}`}
                      list="import-columns"
                      autoCapitalize="none"
                      spellCheck={false}
                      value={mapping[key] ?? ''}
                      onChange={(event) => {
                        reset()
                        setMapping({ ...mapping, [key]: event.target.value })
                      }}
                    />
                  </div>
                ))}
                <div className="space-y-1">
                  <Label htmlFor="map-default-currency">Pénznem, ha nincs oszlop</Label>
                  <Input
                    id="map-default-currency"
                    maxLength={3}
                    autoCapitalize="characters"
                    value={mapping.default_currency}
                    onChange={(event) => {
                      reset()
                      setMapping({ ...mapping, default_currency: event.target.value.toUpperCase() })
                    }}
                  />
                </div>
              </div>
            </fieldset>

            <Button type="submit" disabled={!file || upload.isPending}>
              {upload.isPending && !preview ? 'Ellenőrzés…' : 'Ellenőrzés'}
            </Button>
          </form>
        </CardContent>
      </Card>

      {upload.isError && <RefusedAlert error={upload.error} />}

      {done ? (
        <Summary result={done} />
      ) : (
        preview && (
          <Preview result={preview}>
            <Button onClick={importAll} disabled={blocked || upload.isPending}>
              {upload.isPending ? 'Importálás…' : `${preview.rows.length} sor importálása`}
            </Button>
          </Preview>
        )
      )}
    </section>
  )
}

/** Empty optional fields are sent as null: the server then does not look for that column. */
function cleaned(mapping: ColumnMapping): ColumnMapping {
  const optional = (value: string | null | undefined) => (value?.trim() ? value.trim() : null)
  return {
    date: mapping.date.trim(),
    amount: mapping.amount.trim(),
    description: mapping.description.trim(),
    merchant: optional(mapping.merchant),
    currency: optional(mapping.currency),
    reference: optional(mapping.reference),
    default_currency: mapping.default_currency.trim() || 'HUF',
  }
}

function RefusedAlert({ error }: { error: unknown }) {
  let text = 'Nem sikerült elérni a szervert. Fut az API (python -m finsync.api)?'
  if (error instanceof ApiError) {
    if (error.status === 409) text = 'Ezt a fájlt már importáltad, ezért most semmi sem került be.'
    else if (error.status === 413) text = 'A fájl túl nagy (legfeljebb 1 MB). Bontsd több részre.'
    else if (error.status === 401) text = 'A munkamenet lejárt. Jelentkezz be újra.'
    else text = importMessage(error.message)
  }
  return (
    <Alert variant="destructive">
      <AlertCircle />
      <AlertTitle>Nem sikerült</AlertTitle>
      <AlertDescription>{text}</AlertDescription>
    </Alert>
  )
}

function Preview({ result, children }: { result: ImportResult; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Előnézet</CardTitle>
        <CardDescription>
          {result.rows.length} rendben lévő sor
          {result.errors.length > 0 && `, ${result.errors.length} hibás sor`}. Még semmi sem került be.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {result.already_imported && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertTitle>Ezt a fájlt már importáltad</AlertTitle>
            <AlertDescription>Ugyanez a fájl egyszer már bekerült, ezért újra nem importálható.</AlertDescription>
          </Alert>
        )}
        {result.errors.length > 0 && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertTitle>Javítsd a hibás sorokat, mielőtt importálsz</AlertTitle>
            <AlertDescription>
              <ul className="list-disc pl-4">
                {result.errors.map((error) => (
                  <li key={error.line}>
                    {error.line}. sor: {importMessage(error.error)}
                  </li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}
        {result.rows.length > 0 && (
          <div className="max-h-96 overflow-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Sor</TableHead>
                  <TableHead>Dátum</TableHead>
                  <TableHead>Leírás</TableHead>
                  <TableHead>Kereskedő</TableHead>
                  <TableHead className="text-right">Összeg</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {result.rows.map((row) => (
                  <TableRow key={row.line}>
                    <TableCell className="text-muted-foreground">{row.line}</TableCell>
                    <TableCell className="whitespace-nowrap">{formatDate(row.happened_on, 'day')}</TableCell>
                    <TableCell>{row.description}</TableCell>
                    <TableCell>{row.merchant ?? '–'}</TableCell>
                    <TableCell className="text-right whitespace-nowrap tabular-nums">
                      {formatAmount(row.amount, row.currency)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
        {children}
      </CardContent>
    </Card>
  )
}

function Summary({ result }: { result: ImportResult }) {
  const waiting = result.summary.needs_review ?? 0
  return (
    <Alert>
      <CheckCircle2 />
      <AlertTitle>{result.results.length} sor importálva</AlertTitle>
      <AlertDescription>
        <ul className="list-disc pl-4">
          {Object.entries(result.summary).map(([outcome, count]) => (
            <li key={outcome}>
              {outcomeLabel(outcome)}: {count}
            </li>
          ))}
        </ul>
        <p className="mt-2 flex flex-wrap gap-4">
          {waiting > 0 && (
            <Link to="/ellenorzes" className="font-medium underline">
              {waiting} tétel ellenőrzése
            </Link>
          )}
          <Link to="/esemenyek" className="underline">
            Események megnyitása
          </Link>
        </p>
      </AlertDescription>
    </Alert>
  )
}
