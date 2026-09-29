import { LoginForm } from '@/components/auth/LoginForm'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'

export function LoginPage() {
  const { isAuthenticated, notice, clearNotice } = useAuth()
  if (isAuthenticated) return <Navigate to="/dashboard" replace />
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 px-4 py-10">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-6">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-sky-700">EduGD</p>
          <h1 className="mt-3 text-3xl font-semibold text-slate-900">School Policy Admin</h1>
          <p className="mt-2 text-sm text-slate-600">Administrator sign in</p>
        </div>
        {notice && <div role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{notice}<button type="button" onClick={clearNotice} className="ml-2 underline">Dismiss</button></div>}
        <LoginForm />
      </div>
    </main>
  )
}
