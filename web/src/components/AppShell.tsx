import { ClipboardCheck, FileUp, LayoutDashboard, List, LogOut, Plus, Settings } from 'lucide-react'
import { NavLink, Outlet } from 'react-router'

import { useReviews } from '@/api/queries'
import { useToken } from '@/auth/token'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const NAV = [
  { to: '/', label: 'Áttekintés', icon: LayoutDashboard, end: true },
  { to: '/esemenyek', label: 'Események', icon: List },
  { to: '/ellenorzes', label: 'Ellenőrzés', icon: ClipboardCheck, counter: true },
  { to: '/uj-tetel', label: 'Új tétel', icon: Plus },
  { to: '/importalas', label: 'Importálás', icon: FileUp },
  { to: '/beallitasok', label: 'Beállítások', icon: Settings },
]

export function AppShell() {
  const { signOut } = useToken()
  const reviews = useReviews()
  const waiting = reviews.data?.length ?? 0

  return (
    <div className="min-h-dvh">
      <header className="flex h-14 items-center justify-between border-b bg-card px-4">
        <span className="text-lg font-semibold">FinSync</span>
        <Button variant="ghost" size="sm" onClick={signOut}>
          <LogOut />
          Kijelentkezés
        </Button>
      </header>
      <div className="md:flex">
        <nav aria-label="Fő navigáció" className="border-b bg-card md:min-h-[calc(100dvh-3.5rem)] md:w-56 md:border-r md:border-b-0">
          <ul className="flex gap-1 overflow-x-auto p-2 md:flex-col">
            {NAV.map(({ to, label, icon: Icon, end, counter }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    cn(
                      'flex h-10 items-center gap-2 rounded-md px-3 text-sm whitespace-nowrap hover:bg-muted',
                      'focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none',
                      isActive && 'bg-accent font-medium text-accent-foreground',
                    )
                  }
                >
                  <Icon className="size-4" aria-hidden />
                  {label}
                  {counter && waiting > 0 && (
                    <span className="ml-auto rounded-full bg-warning px-2 text-xs font-medium text-warning-foreground">
                      <span className="sr-only">várakozó tétel: </span>
                      {waiting}
                    </span>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <main className="min-w-0 flex-1 p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
