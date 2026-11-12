import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Session } from '@/api/client'
import { App } from '@/App'

import { SessionProvider } from './session'

const SESSION: Session = {
  user_id: 'anna',
  group_id: 'lakas',
  expires_at: '2026-11-12T22:00:00+00:00',
  csrf_token: 'c'.repeat(64),
}

type Handler = (request: Request) => Response | Promise<Response>

/** Answers by "METHOD /path"; anything else gets an empty list or 404. Returns the requests seen. */
function serve(routes: Record<string, Handler>) {
  const seen: Request[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (request: Request) => {
      seen.push(request.clone())
      const handler = routes[`${request.method} ${new URL(request.url).pathname}`]
      if (handler) return handler(request)
      if (request.url.endsWith('/v1/matches/review')) return Response.json({ reviews: [] })
      return Response.json({ error: 'Not Found' }, { status: 404 })
    }),
  )
  return seen
}

const signedOut = () => Response.json({ error: 'Sign in again: no valid session' }, { status: 401 })

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <SessionProvider>
        <MemoryRouter>
          <App />
        </MemoryRouter>
      </SessionProvider>
    </QueryClientProvider>,
  )
}

async function fillIn(login: string, password: string) {
  await userEvent.type(await screen.findByLabelText('E-mail-cím vagy azonosító'), login)
  await userEvent.type(screen.getByLabelText('Jelszó'), password)
  await userEvent.click(screen.getByRole('button', { name: 'Belépés' }))
}

afterEach(() => vi.unstubAllGlobals())

describe('sign-in (W1)', () => {
  it('signs in with an e-mail address and signs out with the CSRF token', async () => {
    const seen = serve({
      'GET /v1/session': signedOut,
      'POST /v1/session': () => Response.json(SESSION),
      'DELETE /v1/session': () => new Response(null, { status: 204 }),
    })
    renderApp()
    await fillIn('anna@example.com', 'anna-jelszava-1')

    expect(await screen.findByText('anna · lakas')).toBeInTheDocument()
    const signIn = seen.find((request) => request.method === 'POST')!
    expect(await signIn.json()).toEqual({ login: 'anna@example.com', password: 'anna-jelszava-1' })
    expect(signIn.headers.get('Authorization')).toBeNull()

    await userEvent.click(screen.getByRole('button', { name: 'Kijelentkezés' }))
    expect(await screen.findByRole('button', { name: 'Belépés' })).toBeInTheDocument()
    const signOut = seen.find((request) => request.method === 'DELETE')!
    expect(signOut.headers.get('X-CSRF-Token')).toBe(SESSION.csrf_token)
  })

  it('keeps the member signed in after a reload while the cookie is valid', async () => {
    const seen = serve({ 'GET /v1/session': () => Response.json(SESSION) })
    renderApp()
    expect(await screen.findByText('anna · lakas')).toBeInTheDocument()
    // Reads never carry the CSRF token; only state-changing requests need it.
    expect(seen.every((request) => request.headers.get('X-CSRF-Token') === null)).toBe(true)
  })

  it('says the same thing for every failed sign-in', async () => {
    serve({
      'GET /v1/session': signedOut,
      'POST /v1/session': () => Response.json({ error: 'Wrong e-mail address, member id or password' }, { status: 401 }),
    })
    renderApp()
    await fillIn('anna', 'rossz-jelszo')
    expect(await screen.findByRole('alert')).toHaveTextContent('Hibás e-mail-cím, azonosító vagy jelszó.')
  })

  it('asks for the group when the member belongs to several', async () => {
    const bodies: unknown[] = []
    serve({
      'GET /v1/session': signedOut,
      'POST /v1/session': async (request) => {
        const body = (await request.json()) as { group_id?: string }
        bodies.push(body)
        return body.group_id
          ? Response.json(SESSION)
          : Response.json({ error: 'group_id is required: the member belongs to several groups' }, { status: 400 })
      },
    })
    renderApp()
    await fillIn('anna', 'anna-jelszava-1')

    expect(await screen.findByRole('alert')).toHaveTextContent('Több csoport tagja vagy')
    await userEvent.type(screen.getByLabelText('Csoport'), 'lakas')
    await userEvent.click(screen.getByRole('button', { name: 'Belépés' }))
    expect(await screen.findByText('anna · lakas')).toBeInTheDocument()
    expect(bodies[1]).toEqual({ login: 'anna', password: 'anna-jelszava-1', group_id: 'lakas' })
  })

  it('checks the fields before calling the server', async () => {
    const seen = serve({ 'GET /v1/session': signedOut })
    renderApp()
    await userEvent.click(await screen.findByRole('button', { name: 'Belépés' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Add meg az e-mail-címed vagy azonosítód és a jelszavad.')
    expect(seen.filter((request) => request.method === 'POST')).toHaveLength(0)
  })

  it('returns to the sign-in page when the session ends on the server', async () => {
    serve({
      'GET /v1/session': () => Response.json(SESSION),
      'GET /v1/matches/review': signedOut,
    })
    renderApp()
    expect(await screen.findByRole('button', { name: 'Belépés' })).toBeInTheDocument()
  })
})
