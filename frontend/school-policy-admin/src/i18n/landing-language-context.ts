import { createContext } from 'react'
import type { SupportedLanguage } from './languages'

export type LandingKey = 'hero.eyebrow' | 'hero.title' | 'hero.body' | 'hero.capabilities' | 'hero.explore' | 'hero.admin' | 'capabilities.title' | 'capabilities.body' | 'how.eyebrow' | 'how.title' | 'context.eyebrow' | 'context.title' | 'context.body' | 'status.eyebrow' | 'status.title' | 'status.body'
export type LandingContextValue = { language: SupportedLanguage; setLanguage: (language: SupportedLanguage) => void; text: (key: LandingKey, english: string) => string }
export const LandingContext = createContext<LandingContextValue | undefined>(undefined)
