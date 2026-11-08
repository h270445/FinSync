import { createContext, useContext, useState, type ReactNode } from 'react'

import { setApiToken } from '@/api/client'

// Development stopgap until password login with an HttpOnly session cookie (W1, M2): the member
// pastes an API token, kept in sessionStorage so it is gone when the tab closes. A real browser
// sign-in must not keep long-lived secrets in JavaScript-readable storage (technology-stack.md).
const STORAGE_KEY = 'finsync.devToken'

interface TokenState {
  token: string | null
  signIn: (token: string) => void
  signOut: () => void
}

const TokenContext = createContext<TokenState | null>(null)

function readStored(): string | null {
  try {
    return sessionStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

export function TokenProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState(() => {
    const stored = readStored()
    setApiToken(stored)
    return stored
  })

  function update(value: string | null) {
    setApiToken(value)
    setToken(value)
    try {
      if (value) sessionStorage.setItem(STORAGE_KEY, value)
      else sessionStorage.removeItem(STORAGE_KEY)
    } catch {
      // Storage blocked: the token lives only in memory for this page load.
    }
  }

  return (
    <TokenContext.Provider value={{ token, signIn: update, signOut: () => update(null) }}>
      {children}
    </TokenContext.Provider>
  )
}

export function useToken(): TokenState {
  const state = useContext(TokenContext)
  if (!state) throw new Error('useToken outside TokenProvider')
  return state
}
