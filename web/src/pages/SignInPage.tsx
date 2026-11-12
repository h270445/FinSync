import { useState } from 'react'

import { ApiError } from '@/api/client'
import { useSession } from '@/auth/session'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

/** W1: sign in with e-mail address or member id and password; the group is asked only when the member has several. */
export function SignInPage() {
  const { signIn } = useSession()
  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const [groupId, setGroupId] = useState('')
  const [askGroup, setAskGroup] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [checking, setChecking] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!login.trim() || !password) {
      setError('Add meg az e-mail-címed vagy azonosítód és a jelszavad.')
      return
    }
    if (askGroup && !groupId.trim()) {
      setError('Add meg, melyik csoportba lépsz be.')
      return
    }
    setChecking(true)
    setError(null)
    try {
      await signIn({ login: login.trim(), password, groupId: askGroup ? groupId.trim() : undefined })
    } catch (caught) {
      setError(describe(caught))
      if (caught instanceof ApiError && caught.status === 400 && caught.message.includes('group_id')) setAskGroup(true)
    } finally {
      setChecking(false)
    }
  }

  return (
    <main className="flex min-h-dvh items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-xl">Bejelentkezés</CardTitle>
          <CardDescription>A FinSync közös költségkövetőjébe e-mail-címmel vagy azonosítóval léphetsz be.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4" noValidate>
            <div className="space-y-2">
              <Label htmlFor="login">E-mail-cím vagy azonosító</Label>
              <Input
                id="login"
                name="username"
                autoComplete="username"
                autoCapitalize="none"
                spellCheck={false}
                value={login}
                onChange={(event) => setLogin(event.target.value)}
                aria-invalid={error ? true : undefined}
                aria-describedby={error ? 'sign-in-error' : undefined}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Jelszó</Label>
              <Input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                aria-invalid={error ? true : undefined}
                aria-describedby={error ? 'sign-in-error' : undefined}
              />
            </div>
            {askGroup && (
              <div className="space-y-2">
                <Label htmlFor="group">Csoport</Label>
                <Input
                  id="group"
                  autoCapitalize="none"
                  spellCheck={false}
                  value={groupId}
                  onChange={(event) => setGroupId(event.target.value)}
                />
              </div>
            )}
            {error && (
              <p id="sign-in-error" role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={checking}>
              {checking ? 'Ellenőrzés…' : 'Belépés'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  )
}

function describe(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Nem sikerült elérni a szervert. Fut az API (python -m finsync.api)?'
  if (error.status === 401) return 'Hibás e-mail-cím, azonosító vagy jelszó.'
  if (error.status === 403) return 'Nem vagy tagja ennek a csoportnak.'
  if (error.status === 400 && error.message.includes('group_id'))
    return 'Több csoport tagja vagy: add meg, melyik csoportba lépsz be.'
  return 'A bejelentkezés nem sikerült. Próbáld újra.'
}
