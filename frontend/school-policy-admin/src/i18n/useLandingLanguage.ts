import { useContext } from 'react'
import { LandingContext } from './landing-language-context'

export function useLandingLanguage() {
  const value = useContext(LandingContext)
  if (!value) throw new Error('useLandingLanguage must be used inside LandingLanguageProvider')
  return value
}
