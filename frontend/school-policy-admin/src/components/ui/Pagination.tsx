import type { Pagination as PaginationData } from '@/types/api.types'

export function Pagination({ value, onPage }: { value: PaginationData; onPage: (page: number) => void }) {
  const start = value.total === 0 ? 0 : (value.page - 1) * value.per_page + 1
  const end = Math.min(value.total, value.page * value.per_page)
  return <nav aria-label="Pagination" className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-5 py-4 text-sm">
    <span>{start}–{end} of {value.total}</span>
    <div className="flex gap-2">
      <button type="button" disabled={value.page <= 1} onClick={() => onPage(value.page - 1)} className="rounded-lg border px-3 py-2 disabled:opacity-40">Previous</button>
      <button type="button" disabled={!value.has_next} onClick={() => onPage(value.page + 1)} className="rounded-lg border px-3 py-2 disabled:opacity-40">Next</button>
    </div>
  </nav>
}
