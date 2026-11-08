import { useState } from 'react'

import { ApiError, api, setApiToken, unwrap } from '@/api/client'
import { useToken } from '@/auth/token'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

/** W1 stand-in: signs in with an API token until password login exists (see auth/token.tsx). */
export function SignInPage() {
  const { signIn } = useToken()
  const [value, setValue] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [checking, setChecking] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    const token = value.trim()
    if (!token) {
      setError('Add meg a tokent.')
      return
    }
    setChecking(true)
    setError(null)
    setApiToken(token)
    try {
      unwrap(await api.GET('/v1/matches/review'))
      signIn(token)
    } catch (caught) {
      setApiToken(null)
      setError(
        caught instanceof ApiError && caught.status === 401
          ? 'Ismeretlen vagy visszavont token.'
          : 'Nem sikerült elérni a szervert. Fut az API (python -m finsync.api)?',
      )
    } finally {
      setChecking(false)
    }
  }

  return (
    <main className="flex min-h-dvh items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-xl">Bejelentkezés</CardTitle>
          <CardDescription>
            Fejlesztői mód: a jelszavas bejelentkezés még nem készült el, addig egy API tokennel lépsz be. Tokent így
            hozhatsz létre:
            <code className="mt-2 block rounded bg-muted p-2 font-mono text-xs break-all text-foreground">
              python -m finsync.api.tokens create --user anna --group lakas --name "Webes fejlesztés"
            </code>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4" noValidate>
            <div className="space-y-2">
              <Label htmlFor="token">API token</Label>
              <Input
                id="token"
                type="password"
                autoComplete="off"
                placeholder="fs_…"
                value={value}
                onChange={(event) => setValue(event.target.value)}
                aria-invalid={error ? true : undefined}
                aria-describedby={error ? 'token-error' : undefined}
              />
              {error && (
                <p id="token-error" role="alert" className="text-sm text-destructive">
                  {error}
                </p>
              )}
            </div>
            <Button type="submit" className="w-full" disabled={checking}>
              {checking ? 'Ellenőrzés…' : 'Belépés'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  )
}
