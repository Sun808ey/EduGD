import { createContext } from 'react'
import type { SupportedLanguage } from './languages'
import type { TranslationKey } from './translations'

export type LanguageContextValue = {
  language: SupportedLanguage
  setLanguage: (language: SupportedLanguage) => void
  translate: (key: TranslationKey) => string
}

export const LanguageContext = createContext<LanguageContextValue | undefined>(undefined)