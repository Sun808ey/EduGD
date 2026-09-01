import { LoginForm } from '@/components/auth/LoginForm'

export function LoginPage() {
  return (
    <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-slate-100 px-4 py-10">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-6">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-sky-600">EduGD</p>
          <h1 className="mt-3 text-3xl font-semibold text-slate-900">School Policy Admin</h1>
          <p className="mt-2 text-sm text-slate-600">Administrator sign in</p>
        </div>

        <LoginForm />
      </div>
    </div>
  )
}
