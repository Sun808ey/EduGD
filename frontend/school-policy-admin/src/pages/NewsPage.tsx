import { ExternalLink, Newspaper } from 'lucide-react'
import { newsSources } from '@/content/news'

const fallbackImage = '/product-visual-placeholder.svg'

export function NewsPage() {
  return <section className="mx-auto max-w-7xl px-5 py-16 sm:px-8 sm:py-24">
    <header className="mb-12 max-w-3xl"><p className="text-xs font-bold uppercase tracking-[.18em] text-emerald-700">News and sources</p><h1 className="mt-4 text-4xl font-bold tracking-tight sm:text-6xl">Education technology in Uganda</h1><p className="mt-5 text-lg leading-8 text-slate-600">Headlines and source previews from the public references informing this project. Open each card to read the original source.</p></header>
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">{newsSources.map((source) => <article key={source.id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"><a href={source.sourceUrl} target="_blank" rel="noopener noreferrer" aria-label={`Open ${source.headline} from ${source.sourceName}`} className="block focus:outline-none focus:ring-2 focus:ring-emerald-700 focus:ring-inset"><div className="aspect-[16/9] overflow-hidden bg-slate-100"><img src={source.imageUrl ?? fallbackImage} alt={source.imageAlt} loading="lazy" width="640" height="360" className="size-full object-cover" onError={(event) => { event.currentTarget.src = fallbackImage }} /></div><div className="p-6"><p className="text-xs font-bold uppercase tracking-[.14em] text-emerald-700">{source.sourceName}</p><h2 className="mt-3 text-xl font-bold leading-7 text-slate-950">{source.headline}</h2><span className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-emerald-800">Read original source <ExternalLink className="size-4" aria-hidden="true" /></span></div></a></article>)}</div>
    <p className="mt-10 flex items-center gap-2 text-xs leading-5 text-slate-500"><Newspaper className="size-4" aria-hidden="true" />Source images are shown only when individually verified and approved for external use; otherwise a neutral fallback is used.</p>
  </section>
}
