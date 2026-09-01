import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { ClipboardList, FileText, LayoutDashboard, LogOut, Menu, ShieldCheck, X } from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { EnrollmentTokensPanel } from '@/components/devices/EnrollmentTokensPanel'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/devices', label: 'Devices', icon: ShieldCheck },
  { to: '/policies', label: 'Policies', icon: FileText },
  { to: '/logs', label: 'Audit logs', icon: ClipboardList },
]

export function AdminShell() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <div className="min-h-screen bg-slate-100 text-slate-950">
      <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur md:hidden">
        <div className="flex items-center gap-3">
          <div className="grid size-9 place-items-center rounded-xl bg-slate-950 text-white">
            <ShieldCheck className="size-5" aria-hidden="true" />
          </div>
          <span className="text-sm font-semibold">EduGD Admin</span>
        </div>
        <button
          type="button"
          aria-label={mobileOpen ? 'Close navigation' : 'Open navigation'}
          onClick={() => setMobileOpen((open) => !open)}
          className="grid size-9 place-items-center rounded-lg text-slate-600 hover:bg-slate-100"
        >
          {mobileOpen ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </header>

      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-[1600px]">
        <aside className={`${mobileOpen ? 'fixed inset-x-0 top-16 z-10 block' : 'hidden'} w-full border-b border-slate-800 bg-slate-950 p-5 text-slate-100 md:relative md:top-0 md:block md:min-h-screen md:w-64 md:shrink-0 md:border-b-0 md:border-r md:p-6`}>
          <div className="mb-10 hidden items-center gap-3 md:flex">
            <div className="grid size-10 place-items-center rounded-xl bg-emerald-400 text-slate-950">
              <ShieldCheck className="size-5" aria-hidden="true" />
            </div>
            <div>
              <div className="text-sm font-bold">EduGD</div>
              <div className="text-xs text-slate-400">Policy control</div>
            </div>
          </div>

          <nav aria-label="Primary navigation" className="space-y-1">
            <p className="mb-3 px-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Workspace</p>
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${isActive ? 'bg-white text-slate-950' : 'text-slate-300 hover:bg-slate-800 hover:text-white'}`}
              >
                <Icon className="size-4" aria-hidden="true" />
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="mt-12 border-t border-slate-800 pt-5">
            <div className="mb-4 px-3">
              <p className="text-xs text-slate-500">Signed in as</p>
              <p className="mt-1 truncate text-sm font-medium text-slate-200">{user?.display_name ?? user?.username ?? 'Administrator'}</p>
            </div>
            <button type="button" onClick={logout} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-white">
              <LogOut className="size-4" aria-hidden="true" />
              Sign out
            </button>
          </div>
        </aside>

        <main className="min-w-0 flex-1 p-4 sm:p-6 lg:p-10">
          <Outlet />
          {location.pathname === '/devices' && <div className="mt-8"><EnrollmentTokensPanel /></div>}
        </main>
      </div>
    </div>
  )
}
