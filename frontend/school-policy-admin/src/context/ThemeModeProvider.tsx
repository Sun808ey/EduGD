import { useEffect, useMemo, useState } from 'react'
import { createTheme, CssBaseline, ThemeProvider } from '@mui/material'
import { ThemeModeContext, type ThemeMode } from './ThemeModeContext'

function initialMode(): ThemeMode {
  const stored = window.localStorage.getItem('edugd-theme')
  if (stored === 'light' || stored === 'dark') {
    return stored
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function ThemeModeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>(initialMode)

  useEffect(() => {
    document.documentElement.dataset.theme = mode
    document.documentElement.style.colorScheme = mode
  }, [mode])

  const value = useMemo(() => ({
    mode,
    toggle: () => setMode((current) => {
      const next = current === 'light' ? 'dark' : 'light'
      window.localStorage.setItem('edugd-theme', next)
      return next
    }),
  }), [mode])

  const theme = useMemo(() => createTheme({
    palette: {
      mode,
      primary: mode === 'dark'
        ? { main: '#3B82F6', contrastText: '#090D14' }
        : { main: '#0F766E', contrastText: '#FFFFFF' },
      secondary: mode === 'dark'
        ? { main: '#A78BFA', contrastText: '#171225' }
        : { main: '#7C3AED', contrastText: '#FFFFFF' },
      info: { main: mode === 'dark' ? '#60A5FA' : '#2563EB' },
      success: { main: mode === 'dark' ? '#4ADE80' : '#15803D' },
      warning: { main: mode === 'dark' ? '#FBBF24' : '#B45309' },
      error: { main: mode === 'dark' ? '#FB7185' : '#BE123C' },
      background: mode === 'dark'
        ? { default: '#090D14', paper: '#111827' }
        : { default: '#f8fafc', paper: '#ffffff' },
      ...(mode === 'dark' ? {
        text: { primary: '#EAF2FF', secondary: '#B8C7DC' },
        divider: '#293241',
        action: { hover: 'rgba(59, 130, 246, 0.12)', selected: 'rgba(59, 130, 246, 0.18)' },
      } : {
        divider: '#DDE7EF',
        action: { hover: 'rgba(15, 118, 110, 0.07)', selected: 'rgba(124, 58, 237, 0.10)' },
      }),
    },
    shape: { borderRadius: 12 },
  }), [mode])

  return (
    <ThemeModeContext.Provider value={value}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ThemeModeContext.Provider>
  )
}
