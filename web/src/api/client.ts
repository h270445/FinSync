import createClient, { type Middleware } from 'openapi-fetch'

import type { components, paths } from './schema'

export type Transaction = components['schemas']['TransactionOut']
export type FinSyncEvent = components['schemas']['EventOut']
export type Review = components['schemas']['ReviewOut']
export type StoreResult = components['schemas']['StoreResultOut']
export type Decision = components['schemas']['DecisionOut']

/** A refused request, with the backend's `{"error": "..."}` message. */
export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

let token: string | null = null

/** The bearer token sent with every request (see auth/token.tsx). */
export function setApiToken(value: string | null) {
  token = value
}

const auth: Middleware = {
  onRequest({ request }) {
    if (token) request.headers.set('Authorization', `Bearer ${token}`)
    return request
  },
}

// Same origin: the Vite dev server proxies /v1 to the API (vite.config.ts).
// fetch is looked up per request, so tests can stub the global.
export const api = createClient<paths>({ baseUrl: window.location.origin, fetch: (request) => globalThis.fetch(request) })
api.use(auth)

/** The response data, or an ApiError for any non-2xx answer. */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.data !== undefined) return result.data
  const body = result.error as { error?: string } | undefined
  throw new ApiError(result.response.status, body?.error ?? result.response.statusText)
}
