import { useState, type FormEvent, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { adminService } from '@/services/admin.service'
import { ErrorState, LoadingState } from '@/components/ui/AsyncState'
import { errorMessage } from '@/services/errors'
import { useAuth } from '@/hooks/useAuth'

type FormState = {
  display_name: string
  package_name: string
  signing_certificate_sha256: string
  category: string
  education_approved: boolean
  mandatory_block: boolean
  status: 'enabled' | 'disabled'
}

const emptyForm: FormState = {
  display_name: '', package_name: '', signing_certificate_sha256: '', category: '',
  education_approved: false, mandatory_block: false, status: 'enabled',
}

export function ManagedApplicationsPage() {
  const { hasPermission } = useAuth()
  const client = useQueryClient()
  const [form, setForm] = useState<FormState>(emptyForm)
  const [error, setError] = useState('')
  const applications = useQuery({ queryKey: ['managed-applications'], queryFn: ({ signal }) => adminService.listManagedApplications(signal) })
  const create = useMutation({
    mutationFn: () => adminService.createManagedApplication({ ...form, signing_certificate_sha256: form.signing_certificate_sha256 || null }),
    onSuccess: async () => { setForm(emptyForm); setError(''); await client.invalidateQueries({ queryKey: ['managed-applications'] }) },
    onError: (caught) => setError(errorMessage(caught)),
  })
  const submit = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); setError(''); create.mutate() }

  return <section className="space-y-6">
    <header><h1 className="text-3xl font-semibold">Managed applications</h1><p className="mt-2 text-sm text-slate-600">Maintain verified application identities and category restrictions. Display names never identify an application.</p></header>
    {hasPermission('policy.manage') && <form onSubmit={submit} className="grid gap-4 rounded-2xl border bg-white p-6 shadow-sm"><h2 className="text-lg font-semibold">Add verified catalogue identity</h2><div className="grid gap-4 md:grid-cols-2"><Field label="Display name"><input required value={form.display_name} onChange={(event) => setForm({ ...form, display_name: event.target.value })} className="input" maxLength={120} /></Field><Field label="Canonical package name"><input required value={form.package_name} onChange={(event) => setForm({ ...form, package_name: event.target.value })} className="input" /></Field><Field label="Signing certificate SHA-256 (base64url)"><input required value={form.signing_certificate_sha256} onChange={(event) => setForm({ ...form, signing_certificate_sha256: event.target.value })} className="input" /></Field><Field label="Category"><input required placeholder="education, social, games" value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })} className="input" maxLength={64} /></Field></div><div className="flex flex-wrap gap-5 text-sm"><Toggle label="Education approved" checked={form.education_approved} onChange={(value) => setForm({ ...form, education_approved: value })} /><Toggle label="Mandatory block" checked={form.mandatory_block} onChange={(value) => setForm({ ...form, mandatory_block: value })} /></div>{error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}<button disabled={create.isPending} className="w-fit rounded-full bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{create.isPending ? 'Saving…' : 'Add catalogue identity'}</button></form>}
    {applications.isLoading && <LoadingState label="Loading managed applications…" />}{applications.isError && <ErrorState message="Managed applications are temporarily unavailable." retry={() => void applications.refetch()} />}
    {applications.data && <div className="overflow-hidden rounded-2xl border bg-white"><div className="overflow-x-auto"><table className="w-full min-w-220 text-left text-sm"><thead className="bg-slate-50"><tr><th className="p-4">Application</th><th className="p-4">Package</th><th className="p-4">Category</th><th className="p-4">Certificate</th><th className="p-4">Flags</th></tr></thead><tbody className="divide-y">{applications.data.map((application) => <tr key={application.application_uuid}><td className="p-4 font-medium">{application.display_name}</td><td className="p-4 font-mono text-xs">{application.package_name}</td><td className="p-4">{application.category}</td><td className="p-4">{application.signing_certificate_sha256 ? 'Verified' : 'Missing'}</td><td className="p-4">{application.education_approved ? 'Education approved' : 'Unapproved'}{application.mandatory_block ? ' · Mandatory block' : ''}</td></tr>)}</tbody></table></div></div>}
  </section>
}

function Field({ label, children }: { label: string; children: ReactNode }) { return <label className="block text-sm font-medium text-slate-700"><span>{label}</span>{children}</label> }
function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) { return <label className="flex items-center gap-2"><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />{label}</label> }
