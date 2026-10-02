import { useState, type FormEvent, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ActionDialog } from '@/components/ui/ActionDialog'
import { adminService } from '@/services/admin.service'
import { errorMessage } from '@/services/errors'
import { useAuth } from '@/hooks/useAuth'
import type { AdministratorInventoryItem, AdministratorPermission } from '@/types/api.types'

type CreateForm = { username: string; displayName: string; password: string; operatorPassword: string; reason: string }
type SensitiveAction = 'permissions' | 'sessions' | 'disable' | 'password' | null
type SensitiveForm = { operatorPassword: string; reason: string; password: string; permissions: AdministratorPermission[] }

const permissions: AdministratorPermission[] = ['administrator.manage', 'enrollment_token.issue', 'enrollment_token.revoke', 'device_credential.revoke', 'policy.assign', 'device.control', 'policy.manage']
const emptyCreate: CreateForm = { username: '', displayName: '', password: '', operatorPassword: '', reason: '' }
const emptySensitive = (): SensitiveForm => ({ operatorPassword: '', reason: '', password: '', permissions: [] })

export function AdministratorsPage() {
  const { hasPermission } = useAuth()
  const queryClient = useQueryClient()
  const [createForm, setCreateForm] = useState<CreateForm>(emptyCreate)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [target, setTarget] = useState<AdministratorInventoryItem | null>(null)
  const [action, setAction] = useState<SensitiveAction>(null)
  const [sensitive, setSensitive] = useState<SensitiveForm>(emptySensitive)
  const canManage = hasPermission('administrator.manage')
  const administrators = useQuery({
    queryKey: ['administrators', 1],
    queryFn: ({ signal }) => adminService.listAdministrators({ page: 1, perPage: 100 }, signal),
    enabled: canManage,
  })
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['administrators'] })
  const closeDialog = () => { if (!mutate.isPending) { setAction(null); setTarget(null); setSensitive(emptySensitive) } }
  const create = useMutation({
    mutationFn: () => adminService.createAdministrator(createForm.username.trim(), createForm.displayName.trim(), createForm.password, createForm.operatorPassword, createForm.reason.trim()),
    onSuccess: (result) => { setCreateForm(emptyCreate); setError(''); setNotice(`Administrator ${result.username} was created.`); refresh() },
    onError: (caught) => setError(errorMessage(caught)),
  })
  const mutate = useMutation({
    mutationFn: async () => {
      if (!target || !action) throw new Error('Select an administrator action.')
      if (action === 'permissions') return adminService.replaceAdministratorPermissions(target.administrator_uuid, sensitive.permissions, sensitive.operatorPassword, sensitive.reason.trim())
      if (action === 'sessions') return adminService.revokeAdministratorSessions(target.administrator_uuid, sensitive.operatorPassword, sensitive.reason.trim())
      if (action === 'disable') return adminService.disableAdministrator(target.administrator_uuid, sensitive.operatorPassword, sensitive.reason.trim())
      return adminService.resetAdministratorPassword(target.administrator_uuid, sensitive.password, sensitive.operatorPassword, sensitive.reason.trim())
    },
    onSuccess: (result) => { setNotice(result.revoked_sessions === undefined ? 'Administrator permissions were updated.' : `Administrator action completed; revoked sessions: ${result.revoked_sessions}.`); setError(''); setAction(null); setTarget(null); setSensitive(emptySensitive); refresh() },
    onError: (caught) => setError(errorMessage(caught)),
  })
  const openAction = (next: Exclude<SensitiveAction, null>, administrator: AdministratorInventoryItem) => { setError(''); setNotice(''); setTarget(administrator); setAction(next); setSensitive({ ...emptySensitive(), permissions: administrator.permissions }) }
  const submitCreate = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); setError(''); setNotice(''); create.mutate() }
  const submitSensitive = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); setError(''); setNotice(''); mutate.mutate() }

  if (!canManage) return <section className="space-y-4"><header><h1 className="text-3xl font-semibold">Administrators</h1><p className="mt-2 text-sm text-slate-600">Manage administrator access.</p></header><p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">Your account does not have permission to manage administrators.</p></section>

  return <section className="space-y-6">
    <header><h1 className="text-3xl font-semibold">Administrators</h1><p className="mt-2 max-w-3xl text-sm text-slate-600">Manage authorised school administrators through Flask. Sensitive actions require your current operator password and a recorded reason. Passwords remain only in this form while the request is in progress.</p></header>
    {notice && <p role="status" className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p>}
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    <section className="rounded-2xl border bg-white p-6 shadow-sm"><div className="mb-4 flex items-center justify-between gap-4"><div><h2 className="text-lg font-semibold">Administrator inventory</h2><p className="text-sm text-slate-600">Sanitized account status and permission state.</p></div><button type="button" onClick={() => administrators.refetch()} disabled={administrators.isFetching} className="rounded-lg border px-3 py-2 text-sm font-medium disabled:opacity-60">{administrators.isFetching ? 'Refreshing…' : 'Refresh'}</button></div>
      {administrators.isLoading && <p className="text-sm text-slate-600">Loading administrators…</p>}
      {administrators.isError && <p role="alert" className="text-sm text-red-700">{errorMessage(administrators.error)}</p>}
      {administrators.data?.administrators.length === 0 && <p className="text-sm text-slate-600">No administrators were returned by the backend.</p>}
      <div className="grid gap-4">{administrators.data?.administrators.map((administrator) => <article key={administrator.administrator_uuid} className="rounded-xl border p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="font-semibold">{administrator.display_name}</h3><p className="font-mono text-xs text-slate-600">{administrator.username}</p><p className="mt-1 text-sm text-slate-600">Status: <strong>{administrator.status}</strong></p></div><div className="flex flex-wrap gap-2"><button type="button" onClick={() => openAction('permissions', administrator)} className="rounded-lg border px-3 py-2 text-sm">Permissions</button><button type="button" onClick={() => openAction('sessions', administrator)} className="rounded-lg border px-3 py-2 text-sm">Revoke sessions</button><button type="button" onClick={() => openAction('password', administrator)} className="rounded-lg border px-3 py-2 text-sm">Reset password</button>{administrator.status !== 'disabled' && <button type="button" onClick={() => openAction('disable', administrator)} className="rounded-lg border border-red-300 px-3 py-2 text-sm text-red-700">Disable</button>}</div></div><p className="mt-3 text-xs text-slate-600">Permissions: {administrator.permissions.join(', ') || 'none'}</p></article>)}</div>
    </section>
    <form onSubmit={submitCreate} className="grid gap-5 rounded-2xl border bg-white p-6 shadow-sm"><h2 className="text-lg font-semibold">Create administrator</h2><div className="grid gap-4 md:grid-cols-2"><Field label="Username"><input required minLength={3} maxLength={64} value={createForm.username} onChange={(event) => setCreateForm({ ...createForm, username: event.target.value })} className="input" autoComplete="off" /></Field><Field label="Display name"><input required maxLength={120} value={createForm.displayName} onChange={(event) => setCreateForm({ ...createForm, displayName: event.target.value })} className="input" /></Field><Field label="New administrator password"><input required minLength={12} maxLength={128} type="password" value={createForm.password} onChange={(event) => setCreateForm({ ...createForm, password: event.target.value })} className="input" autoComplete="new-password" /></Field><Field label="Your operator password"><input required type="password" value={createForm.operatorPassword} onChange={(event) => setCreateForm({ ...createForm, operatorPassword: event.target.value })} className="input" autoComplete="current-password" /></Field></div><Field label="Reason for granting administrator access"><textarea required maxLength={512} value={createForm.reason} onChange={(event) => setCreateForm({ ...createForm, reason: event.target.value })} className="input min-h-24" /></Field><div><button type="submit" disabled={create.isPending} className="rounded-full bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{create.isPending ? 'Creating…' : 'Create administrator'}</button></div></form>
    <ActionDialog open={action !== null} onOpenChange={(open) => { if (!open) closeDialog() }} title={dialogTitle(action)} description={dialogDescription(action, target)} submitLabel={dialogSubmit(action)} busy={mutate.isPending} destructive={action === 'disable' || action === 'sessions' || action === 'password'} onSubmit={submitSensitive}>{action === 'permissions' && <PermissionSelector selected={sensitive.permissions} onChange={(next) => setSensitive({ ...sensitive, permissions: next })} />}{action === 'password' && <Field label="New password"><input required minLength={12} maxLength={128} type="password" value={sensitive.password} onChange={(event) => setSensitive({ ...sensitive, password: event.target.value })} className="input" autoComplete="new-password" /></Field>}<Field label="Your operator password"><input required type="password" value={sensitive.operatorPassword} onChange={(event) => setSensitive({ ...sensitive, operatorPassword: event.target.value })} className="input" autoComplete="current-password" /></Field><Field label="Reason"><textarea required maxLength={512} value={sensitive.reason} onChange={(event) => setSensitive({ ...sensitive, reason: event.target.value })} className="input min-h-24" /></Field></ActionDialog>
  </section>
}

function PermissionSelector({ selected, onChange }: { selected: AdministratorPermission[]; onChange: (permissions: AdministratorPermission[]) => void }) { return <fieldset><legend className="text-sm font-medium text-slate-700">Permissions</legend><div className="mt-2 grid gap-2">{permissions.map((permission) => <label key={permission} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={selected.includes(permission)} onChange={(event) => onChange(event.target.checked ? [...selected, permission] : selected.filter((item) => item !== permission))} />{permission}</label>)}</div></fieldset> }
function dialogTitle(action: SensitiveAction) { return action === 'permissions' ? 'Replace administrator permissions' : action === 'sessions' ? 'Revoke administrator sessions' : action === 'password' ? 'Reset administrator password' : 'Disable administrator' }
function dialogSubmit(action: SensitiveAction) { return action === 'permissions' ? 'Update permissions' : action === 'sessions' ? 'Revoke sessions' : action === 'password' ? 'Reset password' : 'Disable account' }
function dialogDescription(action: SensitiveAction, target: AdministratorInventoryItem | null) { const name = target?.username ?? 'the selected administrator'; return action === 'permissions' ? `Replace the complete permission set for ${name}. The backend prevents removal of the final active management capability.` : action === 'sessions' ? `Revoke every active session for ${name}.` : action === 'password' ? `Set a new password and revoke active sessions for ${name}.` : `Disable ${name} and revoke active sessions. The backend prevents disabling the final active administrator account.` }
function Field({ label, children }: { label: string; children: ReactNode }) { return <label className="block text-sm font-medium text-slate-700"><span>{label}</span>{children}</label> }
