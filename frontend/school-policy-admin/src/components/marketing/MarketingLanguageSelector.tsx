import { useEffect, useRef, useState } from 'react'
import { ChevronDown, Check } from 'lucide-react'
import { supportedLanguages } from '@/i18n/languages'
import { useLandingLanguage } from '@/i18n/useLandingLanguage'

export function MarketingLanguageSelector() {
  const { language, setLanguage, text } = useLandingLanguage()
  const [open, setOpen] = useState(false)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const current = supportedLanguages.find((item) => item.code === language) ?? supportedLanguages[0]

  useEffect(() => {
    if (!open) return
    const closeOnOutsideClick = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node) && !triggerRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false)
        triggerRef.current?.focus()
      }
    }
    document.addEventListener('mousedown', closeOnOutsideClick)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('mousedown', closeOnOutsideClick)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [open])

  return <div className="relative">
    <button
      ref={triggerRef}
      type="button"
      aria-haspopup="menu"
      aria-expanded={open}
      aria-label={text('header.choose_languages', 'Choose language')}
      onClick={() => setOpen((value) => !value)}
      className="inline-flex items-center gap-1 rounded-full px-3 py-2 text-sm font-semibold text-slate-600 transition hover:bg-white hover:text-emerald-800"
    >
      {current.label}
      <ChevronDown className={`size-4 transition-transform ${open ? 'rotate-180' : ''}`} aria-hidden="true" />
    </button>
    {open && <div ref={menuRef} role="menu" aria-label={text('header.choose_languages', 'Choose Languages')} className="absolute right-0 top-full z-50 mt-2 w-56 rounded-2xl border border-slate-200 bg-white p-3 shadow-xl">
      <p className="px-3 pb-2 text-xs font-bold uppercase tracking-[.16em] text-slate-500">{text('header.choose_languages', 'Choose Languages')}</p>
      <div className="grid gap-1">
        {supportedLanguages.map((option) => <button
          key={option.code}
          type="button"
          role="menuitemradio"
          aria-checked={language === option.code}
          onClick={() => { setLanguage(option.code); setOpen(false); triggerRef.current?.focus() }}
          className="flex items-center justify-between rounded-xl px-3 py-2 text-left text-sm font-medium text-slate-700 hover:bg-emerald-50"
        >
          {option.label}
          {language === option.code && <Check className="size-4 text-emerald-700" aria-hidden="true" />}
        </button>)}
      </div>
    </div>}
  </div>
}
