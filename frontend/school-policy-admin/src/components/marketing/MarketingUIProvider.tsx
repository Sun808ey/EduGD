import { createTheme, ThemeProvider } from '@mui/material/styles'

const theme = createTheme({ palette: { primary: { main: '#10211d' }, secondary: { main: '#d9f99d' } }, typography: { fontFamily: '"Geist Variable", ui-sans-serif, system-ui, sans-serif' } })
export function MarketingUIProvider({ children }: { children: React.ReactNode }) { return <ThemeProvider theme={theme}>{children}</ThemeProvider> }
