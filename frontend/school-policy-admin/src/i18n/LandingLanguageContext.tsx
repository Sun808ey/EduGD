import { useEffect, useMemo, useState, type ReactNode } from 'react'
import api from '@/services/api'
import { defaultLanguage, isSupportedLanguage, languageStorageKey, type SupportedLanguage } from './languages'
import { LandingContext, type LandingKey } from './landing-language-context'


function storedLanguage(): SupportedLanguage {
  const value = typeof window === 'undefined' ? null : window.localStorage.getItem(languageStorageKey)
  return isSupportedLanguage(value) ? value : defaultLanguage
}

export function LandingLanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<SupportedLanguage>(storedLanguage)
  const [translated, setTranslated] = useState<Partial<Record<LandingKey, string>>>({})
  const setLanguage = (next: SupportedLanguage) => { setLanguageState(next); if (next === 'eng') setTranslated({}); window.localStorage.setItem(languageStorageKey, next) }

  useEffect(() => {
    document.documentElement.lang = language === 'eng' ? 'en' : language
    if (language === 'eng') return
    let cancelled = false
    const keys: LandingKey[] = ['hero.eyebrow', 'hero.title', 'hero.body', 'hero.capabilities', 'hero.explore', 'hero.admin', 'capabilities.title', 'capabilities.body', 'how.eyebrow', 'how.title', 'context.eyebrow', 'context.title', 'context.body', 'status.eyebrow', 'status.title', 'status.body']
    void Promise.all(keys.map(async (content_key) => {
      try { const response = await api.post('/public/translation/translate', { content_key, target_language: language }); return [content_key, response.data.translated_text] as const } catch { return null }
    })).then((entries) => { if (!cancelled) setTranslated(Object.fromEntries(entries.filter((entry): entry is readonly [LandingKey, string] => entry !== null))) })
    return () => { cancelled = true }
  }, [language])

  const value = useMemo(() => ({ language, setLanguage, text: (key: LandingKey, english: string) => translated[key] ?? english }), [language, translated])
  return <LandingContext.Provider value={value}>{children}</LandingContext.Provider>
}
