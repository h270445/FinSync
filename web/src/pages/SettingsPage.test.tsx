import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ApiToken, LlmSettings, MerchantRule } from '@/api/client'

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
  llm = {},
}: {
  tokens?: ApiToken[]
  rules?: MerchantRule[]
  myRole?: string
  llm?: Partial<LlmSettings>
} = {}) {
  const llmSettings: LlmSettings = {
    mode: 'never',
    hours_after: 24,
    run_time: '20:00',
    weekday: 6,
    monthly_budget_usd: '1.00',
    spent_this_month_usd: '0.0123',
    budget_exhausted: false,
    available: true,
    model: 'teszt-modell',
    updated_by: null,
    updated_at: null,
    ...llm,
  }
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
    if (call === 'GET /v1/own-accounts')
      return Response.json({
        own_accounts: [
          {
            id: 3,
            label: 'MINTA ANNA',
            kind: 'name',
            match_key: 'minta anna',
            created_by: 'anna',
            created_at: '2026-11-19T10:00:00+00:00',
          },
        ],
      })
    if (call === 'POST /v1/own-accounts')
      return Response.json({ error: 'The group already lists this account or name' }, { status: 409 })
    if (call === 'DELETE /v1/own-accounts/3') return Response.json({})
    if (call === 'GET /v1/llm-settings') return Response.json(llmSettings)
    if (call === 'PUT /v1/llm-settings') {
      const body = await request.clone().json()
      if (body.monthly_budget_usd === '500')
        return Response.json({ error: 'monthly_budget_usd must be from 0 to 100' }, { status: 400 })
      Object.assign(llmSettings, body, {
        updated_by: 'anna',
        updated_at: '2026-11-26T09:00:00+00:00',
      })
      return Response.json(llmSettings)
    }
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
    expect(await screen.findAllByText('Csak a csoport adminja módosíthatja.', { exact: false })).toHaveLength(3)
    expect(await screen.findByText('Élelmiszer')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Szabály hozzáadása' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('SPAR kategóriája')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('balint szerepköre')).not.toBeInTheDocument()
    expect(await screen.findByText('MINTA ANNA')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'MINTA ANNA törlése' })).not.toBeInTheDocument()
  })

  it('lets an admin change a role and explains a refusal', async () => {
    const fetchMock = serve()
    renderPage()
    await userEvent.selectOptions(await screen.findByLabelText('balint szerepköre'), 'admin')
    expect(calls(fetchMock)).toContain('PUT /v1/members/balint/role')
    expect(await screen.findByText('A csoportnak legalább egy adminja kell, hogy maradjon.')).toBeInTheDocument()
  })

  it('lists own accounts, deletes one and explains a duplicate', async () => {
    const fetchMock = serve()
    renderPage()
    expect(await screen.findByText('MINTA ANNA')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'MINTA ANNA törlése' }))
    expect(calls(fetchMock)).toContain('DELETE /v1/own-accounts/3')
    await userEvent.type(screen.getByLabelText('Számlaszám vagy név'), 'Minta Anna')
    await userEvent.click(screen.getByRole('button', { name: 'Hozzáadás' }))
    expect(await screen.findByText('Ez a számla vagy név már szerepel a listán.')).toBeInTheDocument()
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

  it('lets an admin schedule the model daily and explains a wrong value', async () => {
    const fetchMock = serve()
    renderPage()
    expect(await screen.findByText(/csak akkor kérdezzük, ha egy tag/)).toBeInTheDocument()
    expect(screen.getByText('0,0123 USD elköltve, havi keret: 1,00 USD')).toBeInTheDocument()
    expect(screen.queryByLabelText('Hánykor? (budapesti idő)')).not.toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText('Mikor kérdezzük a modellt?'), 'daily')
    const time = screen.getByLabelText('Hánykor? (budapesti idő)')
    await userEvent.clear(time)
    await userEvent.type(time, '21:30')
    await userEvent.click(screen.getByRole('button', { name: 'Mentés' }))
    expect(
      await screen.findByText('A bizonytalan tételekről naponta 21:30-kor kérdezzük a modellt.'),
    ).toBeInTheDocument()
    const put = fetchMock.mock.calls.find(([r]) => r.method === 'PUT' && r.url.endsWith('/v1/llm-settings'))!
    expect(await (put[0] as Request).json()).toEqual({
      mode: 'daily',
      hours_after: 24,
      run_time: '21:30',
      weekday: 6,
      monthly_budget_usd: '1.00',
    })

    const budget = screen.getByLabelText('Havi keret (USD)')
    await userEvent.clear(budget)
    await userEvent.type(budget, '500')
    await userEvent.click(screen.getByRole('button', { name: 'Mentés' }))
    expect(await screen.findByText(/Valamelyik érték hibás/)).toBeInTheDocument()
  })

  it('tells every member when the monthly budget is used up; a member gets no form', async () => {
    serve({
      myRole: 'member',
      llm: {
        mode: 'weekly',
        budget_exhausted: true,
        spent_this_month_usd: '1.00',
      },
    })
    renderPage()
    expect(await screen.findByTestId('budget-exhausted')).toHaveTextContent('Elfogyott a havi keret')
    expect(
      screen.getByText('A bizonytalan tételekről hetente, vasárnap 20:00-kor kérdezzük a modellt.'),
    ).toBeInTheDocument()
    expect(screen.queryByLabelText('Mikor kérdezzük a modellt?')).not.toBeInTheDocument()
  })

  it('says when the server has no model', async () => {
    serve({ llm: { available: false, model: null } })
    renderPage()
    expect(await screen.findByText('Ezen a szerveren nincs beállítva nyelvi modell')).toBeInTheDocument()
  })
})
