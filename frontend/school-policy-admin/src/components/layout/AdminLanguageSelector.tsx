import { ChevronDown, Check } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { supportedLanguages } from '@/i18n/languages'
import { useLanguage } from '@/i18n/useLanguage'

export function AdminLanguageSelector() {
  const { language, setLanguage, translate } = useLanguage()
  const [open, setOpen] = useState(false)
  const trigger = useRef<HTMLButtonElement>(null)
  const menu = useRef<HTMLDivElement>(null)
  const current = supportedLanguages.find((item) => item.code === language) ?? supportedLanguages[0]

  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: PointerEvent) => { if (!menu.current?.contains(event.target as Node) && !trigger.current?.contains(event.target as Node)) setOpen(false) }
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === 'Escape') { setOpen(false); trigger.current?.focus() } }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => { document.removeEventListener('pointerdown', onPointerDown); document.removeEventListener('keydown', onKeyDown) }
  }, [open])

  return <div className="relative">
    <button ref={trigger} type="button" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((value) => !value)} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50">
      <span>{translate('language')}: {current.label}</span><ChevronDown className="size-4" aria-hidden="true" />
    </button>
    {open && <div ref={menu} role="menu" aria-label={translate('chooseLanguage')} className="absolute right-0 top-full z-50 mt-2 w-56 rounded-xl border border-slate-200 bg-white p-2 shadow-xl">
      <p className="px-3 pb-2 pt-1 text-xs font-bold uppercase tracking-[.14em] text-slate-500">{translate('chooseLanguage')}</p>
      {supportedLanguages.map((item) => <button key={item.code} type="button" role="menuitemradio" aria-checked={item.code === language} onClick={() => { setLanguage(item.code); setOpen(false); trigger.current?.focus() }} className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-100" >{item.label}{item.code === language && <Check className="size-4 text-emerald-700" aria-hidden="true" />}</button>)}
    </div>}
  </div>
}
