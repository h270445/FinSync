import { useQueryClient } from '@tanstack/react-query'
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

import { ApiError, api, setCsrfToken, unwrap, type Session } from '@/api/client'

// W1 sign-in (ADR 0010): e-mail address or member id and password. The server keeps the session in
// an HttpOnly cookie; this context only knows who is signed in and the CSRF token, both in memory.
// After a page reload GET /v1/session tells whether the cookie is still valid.

export interface SignInInput {
  login: string
  password: string
  groupId?: string
}

interface SessionState {
  /** undefined while the first check runs, null when nobody is signed in. */
  session: Session | null | undefined
  signIn: (input: SignInInput) => Promise<void>
  signOut: () => Promise<void>
}

const SessionContext = createContext<SessionState | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [session, setSession] = useState<Session | null | undefined>(undefined)

  function update(value: Session | null) {
    // Another session may be another member or group: drop every cached answer and in-flight request.
    void queryClient.cancelQueries()
    queryClient.clear()
    setCsrfToken(value?.csrf_token ?? null)
    setSession(value)
  }

  useEffect(() => {
    let cancelled = false
    api
      .GET('/v1/session')
      .then((result) => {
        if (cancelled) return
        const value = result.data ?? null
        setCsrfToken(value?.csrf_token ?? null)
        setSession(value)
      })
      .catch(() => {
        if (!cancelled) setSession(null)
      })
    return () => {
      cancelled = true
    }
  }, [])

  // A 401 on any request means the session ended on the server (expired, new password, signed out
  // in another tab): show the sign-in page instead of an error.
  useEffect(() => {
    function onError(error: unknown) {
      if (!isSignedOut(error)) return
      setCsrfToken(null)
      setSession(null)
    }
    const queries = queryClient.getQueryCache().subscribe((event) => {
      if (event.type === 'updated' && event.action.type === 'error') onError(event.action.error)
    })
    const mutations = queryClient.getMutationCache().subscribe((event) => {
      if (event.type === 'updated' && event.action.type === 'error') onError(event.action.error)
    })
    return () => {
      queries()
      mutations()
    }
  }, [queryClient])

  async function signIn({ login, password, groupId }: SignInInput) {
    const body = { login, password, ...(groupId ? { group_id: groupId } : {}) }
    update(unwrap(await api.POST('/v1/session', { body })))
  }

  async function signOut() {
    try {
      const result = await api.DELETE('/v1/session')
      // 401: the session had already ended on the server; the member is signed out either way.
      if (result.error !== undefined && result.response.status !== 401) unwrap(result)
    } finally {
      update(null)
    }
  }

  return <SessionContext.Provider value={{ session, signIn, signOut }}>{children}</SessionContext.Provider>
}

export function useSession(): SessionState {
  const state = useContext(SessionContext)
  if (!state) throw new Error('useSession outside SessionProvider')
  return state
}

/** True for the API's answer to a request whose session has ended (expired, signed out elsewhere). */
export function isSignedOut(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}
