export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{message}{retry && <button type="button" onClick={retry} className="ml-2 font-semibold underline">Try again</button>}</div>
}

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return <div className="grid min-h-40 place-items-center text-sm text-slate-500" aria-busy="true">{label}</div>
}
