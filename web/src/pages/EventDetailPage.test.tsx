import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { FinSyncEvent } from '@/api/client'
import { Toaster } from '@/components/ui/sonner'
import { event } from '@/test/fixtures'

import { EventDetailPage } from './EventDetailPage'

function serve(shown: FinSyncEvent) {
  const fetchMock = vi.fn(async (request: Request) => {
    const path = new URL(request.url).pathname
    if (request.method === 'GET' && path === '/v1/events') return Response.json({ events: [shown] })
    if (path.endsWith('/decisions')) return Response.json({ decisions: [] })
    if (path.endsWith('/category-changes')) {
      return Response.json({
        changes: [
          { id: 1, kind: 'mixed', old_value: false, new_value: true, changed_by: 'balint', created_at: '2026-11-10T10:00:00+00:00' },
        ],
      })
    }
    if (path.endsWith('/category')) {
      return Response.json({
        event: shown,
        merchant_rule_outcome: 'created',
        merchant_rule: {
          id: 1, merchant: 'Minta Kozert', merchant_key: 'minta kozert', category: 'household', created_by: 'anna',
          created_at: '2026-11-10T10:00:00+00:00', updated_at: '2026-11-10T10:00:00+00:00',
        },
      })
    }
    return Response.json(shown)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/esemenyek/1']}>
        <Routes>
          <Route path="/esemenyek/:eventId" element={<EventDetailPage />} />
        </Routes>
        <Toaster />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const sentBody = async (fetchMock: ReturnType<typeof serve>, path: string) => {
  const request = fetchMock.mock.calls.map(([call]) => call).find((call) => call.method === 'PUT' && call.url.endsWith(path))
  return request ? await request.json() : undefined
}

afterEach(() => vi.unstubAllGlobals())

describe('EventDetailPage category card', () => {
  it('shows where the suggestion came from and the change log', async () => {
    serve(event())
    renderPage()

    expect(await screen.findByText('Forrás: beépített szótár · bizonytalan, csak javaslat')).toBeInTheDocument()
    expect(await screen.findByText('Kategória-előzmények')).toBeInTheDocument()
    expect(screen.getByText('bekapcsolva')).toBeInTheDocument()
    // Tesco-like merchants (no remember_merchant): no "always use this".
    expect(screen.queryByText(/Mindig ezt használd/)).not.toBeInTheDocument()
  })

  it('remembers the category for a clear merchant', async () => {
    const fetchMock = serve(event({ merchant: 'Minta Kozert', category: 'other', category_source: 'none', remember_merchant: 'Minta Kozert' }))
    renderPage()

    await userEvent.selectOptions(await screen.findByLabelText('Kategória'), 'household')
    await userEvent.click(screen.getByRole('checkbox', { name: 'Mindig ezt használd: Minta Kozert' }))
    await userEvent.click(screen.getByRole('button', { name: 'Mentés' }))
    expect(await sentBody(fetchMock, '/category')).toEqual({ category: 'household', remember: true })
    expect(await screen.findByText(/Új szabály: Minta Kozert → Háztartás/)).toBeInTheDocument()
  })

  it('splits the amount into lines, the last taking the remainder', async () => {
    const fetchMock = serve(event())
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: 'Felosztás kategóriákra' }))
    const first = screen.getByLabelText('1. sor összege')
    await userEvent.clear(first)
    await userEvent.type(first, '9000')
    await userEvent.selectOptions(screen.getByLabelText('2. sor kategóriája'), 'clothing')
    expect(screen.getByLabelText('2. sor összege (maradék)')).toHaveTextContent('3 000 Ft')
    await userEvent.click(screen.getByRole('button', { name: 'Felosztás mentése' }))
    expect(await sentBody(fetchMock, '/category-lines')).toEqual({
      lines: [
        { category: 'groceries', amount: '-9000' },
        { category: 'clothing', amount: '-3000' },
      ],
    })
  })

  it('marks the purchase as mixed', async () => {
    const fetchMock = serve(event())
    renderPage()

    await userEvent.click(await screen.findByRole('checkbox', { name: 'Vegyes vásárlás (több kategória, összeg nélkül)' }))
    expect(await sentBody(fetchMock, '/mixed')).toEqual({ mixed: true })
  })
})
