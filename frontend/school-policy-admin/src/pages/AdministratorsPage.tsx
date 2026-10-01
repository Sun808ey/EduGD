import { useState, type FormEvent, type ReactNode } from 'react'
import { useMutation } from '@tanstack/react-query'
import { adminService } from '@/services/admin.service'
import { errorMessage } from '@/services/errors'
import { useAuth } from '@/hooks/useAuth'

type FormState = {
  username: string
  displayName: string
  password: string
  operatorPassword: string
  reason: string
}

const emptyForm: FormState = {
  username: '',
  displayName: '',
  password: '',
  operatorPassword: '',
  reason: '',
}

export function AdministratorsPage() {
  const { hasPermission } = useAuth()
  const [form, setForm] = useState<FormState>(emptyForm)
  const [error, setError] = useState('')
  const [createdUsername, setCreatedUsername] = useState<string | null>(null)
  const canManage = hasPermission('administrator.manage')
  const create = useMutation({
    mutationFn: () => adminService.createAdministrator(
      form.username.trim(),
      form.displayName.trim(),
      form.password,
      form.operatorPassword,
      form.reason.trim(),
    ),
    onSuccess: (result) => {
      setForm(emptyForm)
      setError('')
      setCreatedUsername(result.username)
    },
    onError: (caught) => {
      setCreatedUsername(null)
      setError(errorMessage(caught))
    },
  })

  if (!canManage) {
    return <section className="space-y-4"><header><h1 className="text-3xl font-semibold">Administrators</h1><p className="mt-2 text-sm text-slate-600">Manage administrator access.</p></header><p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">Your account does not have permission to manage administrators.</p></section>
  }

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError('')
    setCreatedUsername(null)
    create.mutate()
  }

  return <section className="space-y-6">
    <header><h1 className="text-3xl font-semibold">Administrators</h1><p className="mt-2 max-w-3xl text-sm text-slate-600">Create a fully privileged administrator through the protected backend contract. The operator password re-authenticates this sensitive action; it is never displayed or persisted by the dashboard.</p></header>
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900" role="note">This screen currently supports administrator creation only. Permission editing, account disabling, and session revocation require browser API contracts that are not available.</div>
    <form onSubmit={submit} className="grid gap-5 rounded-2xl border bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold">Create administrator</h2>
      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Username"><input required minLength={1} maxLength={64} value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} className="input" autoComplete="off" /></Field>
        <Field label="Display name"><input required maxLength={120} value={form.displayName} onChange={(event) => setForm({ ...form, displayName: event.target.value })} className="input" /></Field>
        <Field label="New administrator password"><input required minLength={1} maxLength={128} type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} className="input" autoComplete="new-password" /></Field>
        <Field label="Your operator password"><input required type="password" value={form.operatorPassword} onChange={(event) => setForm({ ...form, operatorPassword: event.target.value })} className="input" autoComplete="current-password" /></Field>
      </div>
      <Field label="Reason for granting administrator access"><textarea required maxLength={512} value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} className="input min-h-24" /></Field>
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {createdUsername && <p role="status" className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">Administrator <strong>{createdUsername}</strong> was created. All permissions were assigned by the server contract.</p>}
      <div><button type="submit" disabled={create.isPending} className="rounded-full bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{create.isPending ? 'Creating…' : 'Create administrator'}</button></div>
    </form>
  </section>
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="block text-sm font-medium text-slate-700"><span>{label}</span>{children}</label>
}
