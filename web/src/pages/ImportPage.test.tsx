import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ImportResult } from '@/api/client'

import { ImportPage } from './ImportPage'

// Made-up rows in the generic format; no real shop or amount.
const CSV = 'date;amount;description;merchant\n2026-09-05;-4500;Heti bevásárlás;Mintabolt\n2026-09-05;-450;Buszjegy;Mintabusz\n'

const preview: ImportResult = {
  import_batch_id: 'file-abc',
  already_imported: false,
  rows: [
    { line: 2, happened_on: '2026-09-05', amount: '-4500', currency: 'HUF', description: 'Heti bevásárlás', merchant: 'Mintabolt', reference: null },
    { line: 3, happened_on: '2026-09-05', amount: '-450', currency: 'HUF', description: 'Buszjegy', merchant: 'Mintabusz', reference: null },
  ],
  errors: [],
  results: [],
  summary: {},
}

const imported: ImportResult = {
  ...preview,
  results: [
    { transaction_id: 1, event_id: 1, match_outcome: 'separate' },
    { transaction_id: 2, event_id: 2, match_outcome: 'needs_review' },
  ],
  summary: { separate: 1, needs_review: 1 },
}

function serve(answer: (body: Record<string, unknown>) => Response) {
  const bodies: Record<string, unknown>[] = []
  const fetchMock = vi.fn(async (request: Request) => {
    const body = (await request.json()) as Record<string, unknown>
    bodies.push(body)
    return answer(body)
  })
  vi.stubGlobal('fetch', fetchMock)
  return bodies
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ImportPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

async function chooseFile(content: BlobPart, name: string) {
  await userEvent.upload(screen.getByLabelText('Fájl'), new File([content], name))
}

beforeEach(() => localStorage.clear())
afterEach(() => vi.unstubAllGlobals())

describe('ImportPage', () => {
  it('previews the file, then imports it and links the review queue', async () => {
    const bodies = serve((body) => Response.json(body.dry_run ? preview : imported, { status: body.dry_run ? 200 : 201 }))
    renderPage()

    await chooseFile(CSV, 'export.csv')
    expect(await screen.findByText(/A fájl oszlopai: date, amount, description, merchant/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Ellenőrzés' }))

    expect(await screen.findByText('Heti bevásárlás')).toBeInTheDocument()
    expect(bodies[0]).toMatchObject({ content: CSV, dry_run: true, mapping: { date: 'date', merchant: 'merchant' } })

    await userEvent.click(screen.getByRole('button', { name: '2 sor importálása' }))
    expect(await screen.findByText('2 sor importálva')).toBeInTheDocument()
    expect(bodies[1]).toMatchObject({ dry_run: false })
    expect(screen.getByText('Ellenőrzésre vár: 1')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '1 tétel ellenőrzése' })).toHaveAttribute('href', '/ellenorzes')
  })

  it('blocks the import while a row is wrong', async () => {
    serve(() => Response.json({ ...preview, errors: [{ line: 4, error: "invalid amount 'sok'" }] }))
    renderPage()

    await chooseFile(CSV, 'export.csv')
    await userEvent.click(await screen.findByRole('button', { name: 'Ellenőrzés' }))

    const alert = await screen.findByText('Javítsd a hibás sorokat, mielőtt importálsz')
    expect(within(alert.parentElement!).getByText("4. sor: érvénytelen összeg: 'sok'")).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '2 sor importálása' })).toBeDisabled()
  })

  it('sends an XLSX file as base64 and sends an empty optional column as null', async () => {
    const bodies = serve(() => Response.json(preview))
    renderPage()

    await chooseFile(new Uint8Array([0x50, 0x4b, 3, 4]), 'export.xlsx')
    await userEvent.clear(screen.getByLabelText(/Banki azonosító/))
    await userEvent.click(await screen.findByRole('button', { name: 'Ellenőrzés' }))

    await screen.findByText('Heti bevásárlás')
    expect(bodies[0]).toMatchObject({ xlsx_base64: 'UEsDBA==', mapping: { reference: null } })
    expect(bodies[0]).not.toHaveProperty('content')
  })

  it('explains a file that was imported before', async () => {
    serve(() => Response.json({ error: 'This file was already imported' }, { status: 409 }))
    renderPage()

    await chooseFile(CSV, 'export.csv')
    await userEvent.click(await screen.findByRole('button', { name: 'Ellenőrzés' }))
    expect(await screen.findByText('Ezt a fájlt már importáltad, ezért most semmi sem került be.')).toBeInTheDocument()
  })
})
