import { useContext } from 'react'
import { ThemeModeContext } from '@/context/ThemeModeContext'

export function useThemeMode() {
  const value = useContext(ThemeModeContext)
  if (!value) throw new Error('useThemeMode must be used inside ThemeModeProvider')
  return value
}
