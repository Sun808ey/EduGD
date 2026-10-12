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
        : { main: '#1D4ED8', contrastText: '#FFFFFF' },
      secondary: { main: '#0f766e' },
      background: mode === 'dark'
        ? { default: '#090D14', paper: '#111827' }
        : { default: '#f8fafc', paper: '#ffffff' },
      ...(mode === 'dark' ? {
        text: { primary: '#EAF2FF', secondary: '#B8C7DC' },
        divider: '#293241',
        action: { hover: 'rgba(59, 130, 246, 0.12)', selected: 'rgba(59, 130, 246, 0.18)' },
      } : {}),
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
