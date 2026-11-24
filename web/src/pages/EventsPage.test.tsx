import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { FinSyncEvent } from '@/api/client'
import { Toaster } from '@/components/ui/sonner'
import { event, record } from '@/test/fixtures'

import { EventsPage } from './EventsPage'

const settled = event({
  id: 2,
  merchant: 'MINTA KAVEZO',
  category: 'eating_out',
  category_source: 'user',
  category_confidence: 'high',
  uncertain: false,
  transactions: [record({ id: 2, event_id: 2, merchant: 'MINTA KAVEZO' })],
})

function serve(events: FinSyncEvent[], answer: (request: Request) => Response | undefined = () => undefined) {
  const fetchMock = vi.fn(async (request: Request) => {
    if (request.method === 'GET' && request.url.endsWith('/v1/events')) return Response.json({ events })
    return answer(request) ?? Response.json({ event: events[0], merchant_rule_outcome: null, merchant_rule: null })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <EventsPage />
        <Toaster />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('EventsPage category correction', () => {
  it('marks a suggestion and confirms it with one tap', async () => {
    const fetchMock = serve([event(), settled])
    renderPage()

    const table = await screen.findByRole('table')
    expect(within(table).getAllByText('MINTA HIPERMARKET')).not.toHaveLength(0)
    await userEvent.click(within(table).getByRole('button', { name: 'Javaslat elfogadása: Élelmiszer (MINTA HIPERMARKET)' }))

    const put = fetchMock.mock.calls.map(([request]) => request).find((request) => request.method === 'PUT')
    expect(new URL(put!.url).pathname).toBe('/v1/events/1/category')
    expect(await put!.json()).toEqual({ category: 'groceries', remember: false })
    // A settled category has no confirm button.
    expect(within(table).queryByRole('button', { name: /MINTA KAVEZO/ })).not.toBeInTheDocument()
  })

  it('changes the category from the list', async () => {
    const fetchMock = serve([event(), settled])
    renderPage()

    const table = await screen.findByRole('table')
    await userEvent.selectOptions(within(table).getByRole('combobox', { name: 'Kategória: MINTA HIPERMARKET' }), 'clothing')
    const put = fetchMock.mock.calls.map(([request]) => request).find((request) => request.method === 'PUT')
    expect(await put!.json()).toEqual({ category: 'clothing', remember: false })
  })

  it('filters to uncertain categories', async () => {
    serve([event(), settled])
    renderPage()

    expect(await screen.findByText('2 esemény')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('checkbox', { name: 'Csak bizonytalan kategóriák (1)' }))
    expect(screen.getByText('1 esemény')).toBeInTheDocument()
  })

  it('shows income as income, without a category to confirm', async () => {
    const salary = event({
      id: 3,
      amount: '450000',
      direction: 'income',
      merchant: 'MINTA MUNKAADO',
      category: 'other',
      category_source: 'none',
      uncertain: false,
      transactions: [record({ id: 3, event_id: 3, amount: '450000', merchant: 'MINTA MUNKAADO' })],
    })
    serve([salary])
    renderPage()

    const table = await screen.findByRole('table')
    expect(within(table).getAllByText('Bevétel')).not.toHaveLength(0)
    expect(within(table).queryByRole('combobox', { name: /MINTA MUNKAADO/ })).not.toBeInTheDocument()
    expect(within(table).queryByText('javaslat')).not.toBeInTheDocument()
  })

  it('shows the refusal of the server', async () => {
    serve([event()], () => Response.json({ error: 'The event is a transfer; unmark it as a transfer first' }, { status: 409 }))
    renderPage()

    const table = await screen.findByRole('table')
    await userEvent.click(within(table).getByRole('button', { name: /Javaslat elfogadása/ }))
    expect(await screen.findByText('The event is a transfer; unmark it as a transfer first')).toBeInTheDocument()
  })
})
