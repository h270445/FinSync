import { AlertCircle } from 'lucide-react'

import { ApiError } from '@/api/client'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'

export function LoadingRows({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2" aria-busy="true" aria-label="Betöltés">
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className="h-10 w-full" />
      ))}
    </div>
  )
}

function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return 'A token hiányzik, érvénytelen vagy visszavonták. Jelentkezz be újra.'
    if (error.status === 403) return 'Ez a tag már nem tagja a csoportnak.'
    return error.message
  }
  return 'Nem sikerült elérni a szervert. Fut az API (python -m finsync.api)?'
}

export function ErrorState({ error }: { error: unknown }) {
  return (
    <Alert variant="destructive">
      <AlertCircle />
      <AlertTitle>Hiba történt</AlertTitle>
      <AlertDescription>{errorText(error)}</AlertDescription>
    </Alert>
  )
}

export function EmptyState({ children }: { children: React.ReactNode }) {
  return <p className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">{children}</p>
}
