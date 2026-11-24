import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Overview, OverviewBucket } from '@/api/client'

import { OverviewPage } from './OverviewPage'

const bucket = (overrides: Partial<OverviewBucket>): OverviewBucket => ({
  key: 'all',
  currency: 'HUF',
  expense: '0',
  income: '0',
  event_count: 1,
  review_count: 0,
  review_amount: '0',
  uncertain_count: 0,
  uncertain_amount: '0',
  mixed_count: 0,
  mixed_amount: '0',
  ...overrides,
})

const november: Overview = {
  month: '2026-11',
  months: ['2026-11', '2026-10'],
  totals: [
    bucket({
      expense: '15490',
      income: '350000',
      event_count: 3,
      review_count: 1,
      review_amount: '4990',
    }),
  ],
  categories: [
    bucket({
      key: 'groceries',
      expense: '12000',
      event_count: 1,
      review_count: 1,
      review_amount: '4990',
    }),
    bucket({ key: 'transport', expense: '3490' }),
    bucket({ key: 'other', income: '350000' }),
  ],
  members: [
    bucket({ key: 'anna', expense: '12000', income: '350000', event_count: 2 }),
    bucket({ key: 'balint', expense: '3490' }),
  ],
  transfer_count: 2,
}

function serve(byMonth: Record<string, Overview>) {
  const fetchMock = vi.fn(async (request: Request) => {
    const month = new URL(request.url).searchParams.get('month') ?? '2026-11'
    return Response.json(byMonth[month])
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <OverviewPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('OverviewPage', () => {
  it('shows totals, flags review items and says how many transfers were left out', async () => {
    serve({ '2026-11': november })
    renderPage()

    expect(await screen.findByText('15 490 Ft')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Ellenőrzésre vár: 1 esemény (4 990 Ft)')
    expect(screen.getByText(/2 átvezetés a csoport saját számlái között/)).toBeInTheDocument()

    const categories = screen.getByText('Kategóriák szerint').closest('[data-slot="card"]') as HTMLElement
    const groceries = within(categories).getByText('Élelmiszer').closest('tr') as HTMLElement
    expect(groceries).toHaveTextContent('1 ellenőrzésre vár')
    expect(groceries).toHaveTextContent('12 000 Ft')
    expect(within(categories).getByText('+350 000 Ft')).toBeInTheDocument()
  })

  it('switches to another month', async () => {
    const fetchMock = serve({
      '2026-11': november,
      '2026-10': {
        ...november,
        month: '2026-10',
        totals: [],
        categories: [],
        members: [],
        transfer_count: 0,
      },
    })
    renderPage()

    await userEvent.selectOptions(await screen.findByLabelText('Hónap'), '2026-10')
    expect(await screen.findByText('2026. október hónapban még nincs egy esemény sem.')).toBeInTheDocument()
    const urls = fetchMock.mock.calls.map(([request]) => new URL(request.url).search)
    expect(urls).toContain('?month=2026-10')
  })

  it('says how much of the category split is only a suggestion or mixed', async () => {
    const totals = [bucket({ expense: '15490', uncertain_count: 2, uncertain_amount: '8480', mixed_count: 1, mixed_amount: '3490' })]
    serve({ '2026-11': { ...november, totals } })
    renderPage()

    expect(
      await screen.findByText(/2 esemény kategóriája csak javaslat \(8 480 Ft\), 1 vegyes vásárlás felosztás nélkül \(3 490 Ft\)/),
    ).toBeInTheDocument()
  })

  it('shows the backend error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => Response.json({ error: 'month must be YYYY-MM' }, { status: 400 })),
    )
    renderPage()
    expect(await screen.findByText('month must be YYYY-MM')).toBeInTheDocument()
  })
})
