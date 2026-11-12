import { Route, Routes } from 'react-router'

import { useSession } from '@/auth/session'
import { AppShell } from '@/components/AppShell'
import { LoadingRows } from '@/components/states'
import { EventDetailPage } from '@/pages/EventDetailPage'
import { EventsPage } from '@/pages/EventsPage'
import { PlaceholderPage } from '@/pages/PlaceholderPage'
import { ReviewPage } from '@/pages/ReviewPage'
import { SignInPage } from '@/pages/SignInPage'

// Screen ids (W1–W8) follow docs/design/user-interface.md#web-app.
export function App() {
  const { session } = useSession()
  if (session === undefined)
    return (
      <main className="mx-auto max-w-md p-4" aria-busy="true">
        <LoadingRows rows={3} />
      </main>
    )
  if (session === null) return <SignInPage />

  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<PlaceholderPage title="Áttekintés" screen="W2" />} />
        <Route path="esemenyek" element={<EventsPage />} />
        <Route path="esemenyek/:eventId" element={<EventDetailPage />} />
        <Route path="ellenorzes" element={<ReviewPage />} />
        <Route path="uj-tetel" element={<PlaceholderPage title="Új tétel" screen="W6" />} />
        <Route path="importalas" element={<PlaceholderPage title="Importálás" screen="W7" />} />
        <Route path="beallitasok" element={<PlaceholderPage title="Beállítások" screen="W8" />} />
        <Route path="*" element={<PlaceholderPage title="Nincs ilyen oldal" screen="404" />} />
      </Route>
    </Routes>
  )
}
