import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Review, Transaction } from '@/api/client'

import { ReviewPage } from './ReviewPage'

const record = (overrides: Partial<Transaction>): Transaction => ({
  id: 1,
  user_id: 'anna',
  group_id: 'lakas',
  amount: '-4990',
  currency: 'HUF',
  description: 'card_purchase:SPAR BUDAPEST',
  merchant: 'SPAR BUDAPEST',
  category: 'groceries',
  source: 'android_notification',
  happened_at: '2026-10-09T10:00:00+00:00',
  happened_at_precision: 'minute',
  created_at: '2026-10-09T10:00:05+00:00',
  event_id: 1,
  duplicate_of_id: null,
  ...overrides,
})

const review = (overrides: Partial<Review>): Review => {
  const existing = record({})
  return {
    decision_id: 7,
    score: 0.8,
    features: { a: 1, t: 1, m: 0.3333, delta: '0d', score: 0.8, runner_up: null },
    transaction: record({ id: 2, source: 'manual', merchant: 'Spar', user_id: 'balint', event_id: 2 }),
    candidate_event: {
      id: 1,
      amount: '-4990',
      currency: 'HUF',
      direction: 'expense',
      happened_at: existing.happened_at,
      merchant: 'SPAR BUDAPEST',
      category: 'groceries',
      primary_transaction_id: 1,
      review_state: 'needs_review',
      transactions: [existing],
    },
    ...overrides,
  }
}

function serve(reviews: Review[]) {
  const fetchMock = vi.fn(async (request: Request) => {
    if (request.url.endsWith('/v1/matches/review')) return Response.json({ reviews })
    return Response.json({ transaction_id: 2, event_id: 1, match_outcome: 'rejected' })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ReviewPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('ReviewPage', () => {
  it('shows the empty state', async () => {
    serve([])
    renderPage()
    expect(await screen.findByText('Nincs ellenőrzésre váró tétel.')).toBeInTheDocument()
  })

  it('explains the score and sends a rejection', async () => {
    const fetchMock = serve([review({})])
    renderPage()

    expect(await screen.findByText('1 ellenőrzésre vár')).toBeInTheDocument()
    expect(screen.getByText('azonos összeg')).toBeInTheDocument()
    expect(screen.getByText('ugyanaz a nap')).toBeInTheDocument()
    expect(screen.getByText('Spar vs. SPAR BUDAPEST')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Két külön vásárlás' }))
    const posted = fetchMock.mock.calls.map(([request]) => `${request.method} ${new URL(request.url).pathname}`)
    expect(posted).toContain('POST /v1/matches/7/reject')
  })

  it('blocks confirming while the event holds a record of the same channel', async () => {
    const base = review({ features: { a: 1, t: 0.9, m: 1, delta: '0.40h', score: 0.97, contested: true } })
    const sameChannel = record({ id: 3, source: 'manual', user_id: 'balint', merchant: 'Spar' })
    const event = { ...base.candidate_event, transactions: [...base.candidate_event.transactions, sameChannel] }
    serve([{ ...base, candidate_event: event }])
    renderPage()

    expect(await screen.findByText('Vitatott összekapcsolás')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ugyanaz a vásárlás' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Két külön vásárlás' })).toBeEnabled()
  })

  it('allows confirming once the conflicting record was split off', async () => {
    serve([review({ features: { a: 1, t: 0.9, m: 1, delta: '0.40h', score: 0.97, contested: true } })])
    renderPage()

    expect(await screen.findByText('1 ellenőrzésre vár')).toBeInTheDocument()
    expect(screen.queryByText('Vitatott összekapcsolás')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ugyanaz a vásárlás' })).toBeEnabled()
  })

  it('shows an identical manual entry without a score', async () => {
    serve([review({ score: null, features: { identical_row_of_id: 1 } })])
    renderPage()

    expect(await screen.findByText('Azonos kézi tétel már rögzítve')).toBeInTheDocument()
    expect(screen.queryByText('Összpontszám')).not.toBeInTheDocument()
  })

  it('says when the identical row came twice in one imported file', async () => {
    const transaction = record({ id: 2, source: 'file_import', happened_at_precision: 'day', event_id: 2 })
    serve([review({ score: null, features: { identical_row_of_id: 1 }, transaction })])
    renderPage()

    expect(await screen.findByText('Azonos sor ugyanabban a fájlban')).toBeInTheDocument()
  })
})
