import { createContext } from 'react'
import type { SupportedLanguage } from './languages'

export type LandingKey = string
export type LandingContextValue = { language: SupportedLanguage; setLanguage: (language: SupportedLanguage) => void; text: (key: LandingKey, english: string) => string }
export const LandingContext = createContext<LandingContextValue | undefined>(undefined)
