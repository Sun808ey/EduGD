import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { defaultLanguage, htmlLanguageCodes, isSupportedLanguage, languageStorageKey, type SupportedLanguage } from './languages'
import { translations, type TranslationKey } from './translations'
import { LanguageContext } from './language-context'

function initialLanguage(): SupportedLanguage {
  if (typeof window === 'undefined') return defaultLanguage
  const stored = window.localStorage.getItem(languageStorageKey)
  return isSupportedLanguage(stored) ? stored : defaultLanguage
}
export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<SupportedLanguage>(initialLanguage)

  const setLanguage = (next: SupportedLanguage) => {
    setLanguageState(next)
    window.localStorage.setItem(languageStorageKey, next)
  }

  useEffect(() => {
    document.documentElement.lang = htmlLanguageCodes[language]
  }, [language])

  const value = useMemo(() => ({
    language,
    setLanguage,
    translate: (key: TranslationKey) => translations[language][key] ?? translations.eng[key],
  }), [language])

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}
