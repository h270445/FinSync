import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SessionProvider } from '@/auth/session'

import { NewTransactionPage } from './NewTransactionPage'

const SESSION = { user_id: 'balint', group_id: 'lakas', expires_at: '2026-12-01T00:00:00+00:00', csrf_token: 'csrf' }

function serve(answer: () => Response) {
  const fetchMock = vi.fn(async (request: Request) => {
    if (new URL(request.url).pathname === '/v1/session') return Response.json(SESSION)
    return answer()
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

const posted = (fetchMock: ReturnType<typeof serve>) =>
  fetchMock.mock.calls.map(([request]) => request).filter((request) => request.method === 'POST')

async function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <SessionProvider>
        <MemoryRouter>
          <NewTransactionPage />
        </MemoryRouter>
      </SessionProvider>
    </QueryClientProvider>,
  )
  expect(await screen.findByText('balint')).toBeInTheDocument()
}

afterEach(() => vi.unstubAllGlobals())

describe('NewTransactionPage', () => {
  it('sends a Budapest wall-clock time as typed and shows that a review is needed', async () => {
    const fetchMock = serve(() => Response.json({ transaction_id: 5, event_id: 3, match_outcome: 'needs_review' }, { status: 201 }))
    await renderPage()

    await userEvent.type(screen.getByLabelText('Összeg'), '4 990')
    await userEvent.clear(screen.getByLabelText('Dátum'))
    await userEvent.type(screen.getByLabelText('Dátum'), '2026-11-14')
    await userEvent.type(screen.getByLabelText('Időpont (nem kötelező)'), '23:30')
    await userEvent.type(screen.getByLabelText('Kereskedő (nem kötelező)'), 'Peldabolt')
    await userEvent.type(screen.getByLabelText('Leírás'), 'Bevásárlás')
    await userEvent.click(screen.getByRole('button', { name: 'Mentés' }))

    expect(await screen.findByText('Mentve, de hasonlít egy meglévő eseményre.')).toBeInTheDocument()
    const [request] = posted(fetchMock)
    expect(new URL(request.url).pathname).toBe('/v1/transactions')
    expect(await request.json()).toEqual({
      amount: '4990',
      currency: 'HUF',
      direction: 'expense',
      happened_at: '2026-11-14T23:30',
      description: 'Bevásárlás',
      merchant: 'Peldabolt',
    })
    expect(screen.getByLabelText('Összeg')).toHaveValue('')
  })

  it('sends a date without a time as a calendar day', async () => {
    const fetchMock = serve(() => Response.json({ transaction_id: 6, event_id: 4, match_outcome: 'separate' }, { status: 201 }))
    await renderPage()

    await userEvent.type(screen.getByLabelText('Összeg'), '1500')
    await userEvent.selectOptions(screen.getByLabelText('Irány'), 'income')
    await userEvent.type(screen.getByLabelText('Leírás'), 'Visszafizetés')
    await userEvent.click(screen.getByRole('button', { name: 'Mentés' }))

    expect(await screen.findByText('Mentve új eseményként.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Esemény megnyitása' })).toHaveAttribute('href', '/esemenyek/4')
    const body = await posted(fetchMock)[0].json()
    expect(body.happened_at).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(body).toMatchObject({ direction: 'income', amount: '1500', merchant: null })
  })

  it('checks the form before sending', async () => {
    const fetchMock = serve(() => Response.json({}))
    await renderPage()

    await userEvent.type(screen.getByLabelText('Összeg'), '-20')
    await userEvent.click(screen.getByRole('button', { name: 'Mentés' }))

    expect(screen.getByText('Az összegnek pozitív számnak kell lennie, legfeljebb két tizedesjeggyel.')).toBeInTheDocument()
    expect(screen.getByText('Add meg a leírást.')).toBeInTheDocument()
    expect(posted(fetchMock)).toEqual([])
  })

  it("shows the server's refusal", async () => {
    serve(() => Response.json({ error: 'Currency must be a 3-letter code' }, { status: 400 }))
    await renderPage()

    await userEvent.type(screen.getByLabelText('Összeg'), '100')
    await userEvent.type(screen.getByLabelText('Leírás'), 'Kávé')
    await userEvent.click(screen.getByRole('button', { name: 'Mentés' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Currency must be a 3-letter code')
  })
})
