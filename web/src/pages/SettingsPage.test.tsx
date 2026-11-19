import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ApiToken, MerchantRule } from '@/api/client'

import { SettingsPage } from './SettingsPage'

const CATEGORIES = ['groceries', 'transport', 'household', 'other']
const NEW_TOKEN = `fs_${'A'.repeat(43)}`

const token = (overrides: Partial<ApiToken>): ApiToken => ({
  id: 1,
  name: 'Anna telefonja',
  prefix: 'fs_AbCdE',
  created_at: '2026-11-12T10:00:00+00:00',
  last_used_at: null,
  revoked_at: null,
  ...overrides,
})

const rule = (overrides: Partial<MerchantRule>): MerchantRule => ({
  id: 5,
  merchant: 'SPAR',
  merchant_key: 'spar',
  category: 'groceries',
  created_by: 'anna',
  created_at: '2026-11-19T10:00:00+00:00',
  updated_at: '2026-11-19T10:00:00+00:00',
  ...overrides,
})

function serve({
  tokens = [token({})],
  rules = [rule({})],
  myRole = 'admin',
}: { tokens?: ApiToken[]; rules?: MerchantRule[]; myRole?: string } = {}) {
  const members = [
    { user_id: 'anna', email: 'anna@example.org', role: myRole, is_me: true },
    { user_id: 'balint', email: null, role: 'member', is_me: false },
  ]
  const fetchMock = vi.fn(async (request: Request) => {
    const path = new URL(request.url).pathname
    const call = `${request.method} ${path}`
    if (call === 'GET /v1/members')
      return Response.json({
        members,
      })
    if (call === 'PUT /v1/members/balint/role')
      return Response.json({ error: 'the group must keep at least one admin' }, { status: 409 })
    if (call === 'GET /v1/tokens') return Response.json({ tokens })
    if (call === 'POST /v1/tokens')
      return Response.json(
        {
          token: NEW_TOKEN,
          record: token({ id: 2, name: 'Bálint laptop', prefix: 'fs_AAAAA' }),
        },
        { status: 201 },
      )
    if (call === 'POST /v1/tokens/1/revoke') return Response.json(token({ revoked_at: '2026-11-19T12:00:00+00:00' }))
    if (call === 'GET /v1/merchant-rules') return Response.json({ rules, categories: CATEGORIES })
    if (call === 'POST /v1/merchant-rules')
      return Response.json({ error: 'The group already has a rule for this merchant (spar)' }, { status: 409 })
    if (call === 'PUT /v1/merchant-rules/5' || call === 'DELETE /v1/merchant-rules/5') return Response.json(rule({}))
    return Response.json({ error: 'unexpected' }, { status: 500 })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

const calls = (fetchMock: ReturnType<typeof serve>) =>
  fetchMock.mock.calls.map(([request]) => `${request.method} ${new URL(request.url).pathname}`)

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('SettingsPage', () => {
  it('lists the members and marks the signed-in one', async () => {
    serve()
    renderPage()
    const anna = (await screen.findByText('anna')).closest('li') as HTMLElement
    expect(anna).toHaveTextContent('Te')
    expect(anna).toHaveTextContent('anna@example.org')
    expect(screen.getByText('balint').closest('li') as HTMLElement).toHaveTextContent('nincs webes belépése')
  })

  it('creates a token and shows it once', async () => {
    const fetchMock = serve({ tokens: [] })
    renderPage()
    expect(await screen.findByText('Még nincs API-tokened.')).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText('Mire használod?'), 'Bálint laptop')
    await userEvent.click(screen.getByRole('button', { name: 'Új token' }))
    expect(await screen.findByTestId('new-token')).toHaveTextContent(NEW_TOKEN)
    expect(calls(fetchMock)).toContain('POST /v1/tokens')
    const body = await (fetchMock.mock.calls.find(([r]) => r.method === 'POST')![0] as Request).json()
    expect(body).toEqual({ name: 'Bálint laptop' })
  })

  it('asks before revoking a token', async () => {
    const fetchMock = serve()
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Visszavonás' }))
    expect(calls(fetchMock)).not.toContain('POST /v1/tokens/1/revoke')
    await userEvent.click(screen.getByRole('button', { name: 'Igen, visszavonom' }))
    expect(calls(fetchMock)).toContain('POST /v1/tokens/1/revoke')
  })

  it('shows a member the rules and roles read-only', async () => {
    serve({ myRole: 'member' })
    renderPage()
    expect(await screen.findByText('Csak a csoport adminja módosíthatja.', { exact: false })).toBeInTheDocument()
    expect(await screen.findByText('Élelmiszer')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Szabály hozzáadása' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('SPAR kategóriája')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('balint szerepköre')).not.toBeInTheDocument()
  })

  it('lets an admin change a role and explains a refusal', async () => {
    const fetchMock = serve()
    renderPage()
    await userEvent.selectOptions(await screen.findByLabelText('balint szerepköre'), 'admin')
    expect(calls(fetchMock)).toContain('PUT /v1/members/balint/role')
    expect(await screen.findByText('A csoportnak legalább egy adminja kell, hogy maradjon.')).toBeInTheDocument()
  })

  it('changes and deletes a rule, and explains a duplicate', async () => {
    const fetchMock = serve()
    renderPage()

    await userEvent.selectOptions(await screen.findByLabelText('SPAR kategóriája'), 'household')
    expect(calls(fetchMock)).toContain('PUT /v1/merchant-rules/5')
    await userEvent.click(screen.getByRole('button', { name: 'SPAR szabály törlése' }))
    expect(calls(fetchMock)).toContain('DELETE /v1/merchant-rules/5')

    const form = screen.getByRole('button', { name: 'Szabály hozzáadása' }).closest('form') as HTMLElement
    await userEvent.type(within(form).getByLabelText('Kereskedő'), 'Spar 0123')
    await userEvent.selectOptions(within(form).getByLabelText('Kategória'), 'groceries')
    await userEvent.click(within(form).getByRole('button', { name: 'Szabály hozzáadása' }))
    expect(await screen.findByText('Erre a kereskedőre már van szabály a csoportban.')).toBeInTheDocument()
  })
})
