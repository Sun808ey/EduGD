import { useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { adminService } from '@/services/admin.service'
import { ErrorState } from '@/components/ui/AsyncState'
import { errorMessage } from '@/services/errors'
import type { SupportedLanguage } from '@/types/api.types'

const languages: Array<{ value: SupportedLanguage; label: string }> = [
  { value: 'ach', label: 'Acholi' },
  { value: 'lgg', label: 'Lugbara' },
  { value: 'teo', label: 'Ateso' },
  { value: 'nyn', label: 'Runyankole' },
  { value: 'lug', label: 'Luganda' },
]

export function TranslationPage() {
  const [text, setText] = useState('')
  const [targetLanguage, setTargetLanguage] = useState<SupportedLanguage>('lug')
  const [error, setError] = useState('')
  const translation = useMutation({
    mutationFn: () => adminService.translateApprovedDynamicContent(text.trim(), targetLanguage),
    onSuccess: () => setError(''),
    onError: (caught) => setError(errorMessage(caught)),
  })

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    translation.mutate()
  }

  return <section className="space-y-6">
    <header>
      <h1 className="text-3xl font-semibold">Approved-content translation</h1>
      <p className="mt-2 max-w-3xl text-sm text-slate-600">Translate approved dynamic school content through the protected Flask contract. Text is not stored by the browser or sent directly to a translation provider.</p>
    </header>
    <div role="note" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">Only approved dynamic content is accepted. Do not enter learner names, credentials, device identifiers, or other personal data.</div>
    <form onSubmit={submit} className="grid gap-4 rounded-2xl border bg-white p-6 shadow-sm">
      <label className="block text-sm font-medium">Source language<input value="English (eng)" readOnly className="input mt-2 bg-slate-50" /></label>
      <label className="block text-sm font-medium">Target language<select value={targetLanguage} onChange={(event) => setTargetLanguage(event.target.value as SupportedLanguage)} className="input mt-2">{languages.map((language) => <option key={language.value} value={language.value}>{language.label}</option>)}</select></label>
      <label className="block text-sm font-medium">Approved text<textarea required minLength={1} maxLength={4000} value={text} onChange={(event) => setText(event.target.value)} className="input mt-2 min-h-32" /></label>
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      <button type="submit" disabled={translation.isPending || !text.trim()} className="w-fit rounded-full bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{translation.isPending ? 'Translating…' : 'Translate approved text'}</button>
    </form>
    {translation.isError && <ErrorState message="Translation is temporarily unavailable." retry={() => translation.mutate()} />}
    {translation.data && <section aria-live="polite" className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6">
      <h2 className="text-lg font-semibold">Translation result</h2>
      <p className="mt-3 whitespace-pre-wrap text-slate-800">{translation.data.translated_text}</p>
      <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-3"><div><dt className="text-slate-500">Target</dt><dd className="font-semibold">{translation.data.target_language}</dd></div><div><dt className="text-slate-500">Quality</dt><dd className="font-semibold">{translation.data.quality_status}</dd></div><div><dt className="text-slate-500">Cache</dt><dd className="font-semibold">{translation.data.cached ? 'Cached' : 'New result'}</dd></div></dl>
    </section>}
  </section>
}
