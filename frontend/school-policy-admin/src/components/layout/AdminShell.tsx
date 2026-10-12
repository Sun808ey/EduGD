import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { BarChart3, Building2, ClipboardList, FileText, KeyRound, Languages, LayoutDashboard, LogOut, Menu, PackageCheck, RefreshCw, Settings2, ShieldCheck, SunMoon, UsersRound, X } from 'lucide-react'
import { lazy, Suspense, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AppBar, Box, Button, Divider, Drawer, IconButton, List, ListItem, ListItemButton, ListItemIcon, ListItemText, Paper, Stack, Toolbar, Typography } from '@mui/material'
import { useAuth } from '@/hooks/useAuth'
import { LoadingState } from '@/components/ui/AsyncState'
import { useLanguage } from '@/i18n/useLanguage'
import { AdminLanguageSelector } from './AdminLanguageSelector'
import { adminService } from '@/services/admin.service'
import { OfflineStatusBanner } from './OfflineStatusBanner'
import { useThemeMode } from '@/hooks/useThemeMode'

const drawerWidth = 272
const EnrollmentTokensPanel = lazy(() => import('@/components/devices/EnrollmentTokensPanel').then((module) => ({ default: module.EnrollmentTokensPanel })))
type NavigationItem = {
  to: string
  key?: 'dashboard' | 'devices' | 'policies' | 'auditLogs'
  label?: string
  icon: typeof LayoutDashboard
}

type NavigationSection = {
  label: string
  items: NavigationItem[]
}

function buildNavSections(hasSchool: boolean, canManageAdministrators: boolean): NavigationSection[] {
  return [
  {
    label: 'Overview',
    items: [{ to: '/dashboard', key: 'dashboard' as const, icon: LayoutDashboard }, { to: '/sync', label: 'Sync queue', icon: RefreshCw }],
  },
  {
    label: 'Asset management',
    items: [
      { to: '/devices', key: 'devices' as const, icon: ShieldCheck },
      { to: '/assignments', label: 'Assignments', icon: UsersRound },
    ],
  },
  {
    label: 'Policy management',
    items: [
      { to: '/policies', key: 'policies' as const, icon: FileText },
      { to: '/policy-changes', label: 'Policy changes', icon: ClipboardList },
      { to: '/policies/catalogue', label: 'Applications & domains', icon: PackageCheck },
    ],
  },
  {
    label: 'Compliance and governance',
    items: [
      { to: '/logs', key: 'auditLogs' as const, icon: ClipboardList },
      { to: '/reports', label: 'Violations', icon: BarChart3 },
      { to: '/translations', label: 'Translations', icon: Languages },
    ],
  },
  {
    label: 'Administration',
    items: [
      { to: hasSchool ? '/settings' : '/school', label: hasSchool ? 'Settings' : 'Schools', icon: hasSchool ? Settings2 : Building2 },
      ...(canManageAdministrators ? [{ to: '/administrators', label: 'Administrators', icon: ShieldCheck }] : []),
      { to: '/data-protection', label: 'Data protection', icon: ShieldCheck },
    ],
  },
  {
    label: 'Provisioning',
    items: [{ to: '/provisioning', label: 'Provisioning', icon: KeyRound }],
  },
  ]
}

export function AdminShell() {
  const { user, logout, hasPermission } = useAuth()
  const { mode, toggle } = useThemeMode()
  const { translate } = useLanguage()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const school = useQuery({ queryKey: ['school'], queryFn: ({ signal }) => adminService.getSchool(signal) })
  const navSections = buildNavSections(Boolean(school.data), hasPermission('administrator.manage'))
  const navigation = (
    <Stack component="aside" aria-label="Administration sidebar" sx={{ height: '100%', p: 2, gap: 2 }}>
      <Stack direction="row" spacing={1.25} sx={{ px: 1, py: 1, alignItems: 'center' }}>
        <Box sx={{ display: 'grid', placeItems: 'center', width: 36, height: 36, borderRadius: 2, bgcolor: 'primary.main', color: 'primary.contrastText' }}><ShieldCheck size={20} aria-hidden="true" /></Box>
        <Box><Typography variant="subtitle2" sx={{ fontWeight: 800 }}>EduGD</Typography><Typography variant="caption" color="text.secondary">{translate('policyControl')}</Typography></Box>
      </Stack>
      <Divider />
      <Box component="nav" aria-label="Primary navigation">
        <Typography variant="overline" color="text.secondary" sx={{ display: 'block', px: 1.5, mb: 1, letterSpacing: '.12em' }}>{translate('workspace')}</Typography>
        <List disablePadding sx={{ display: 'grid', gap: 1.5 }}>
          {navSections.map(({ label: sectionLabel, items }) => <Box key={sectionLabel} component="li" sx={{ listStyle: 'none' }}>
            <Typography variant="overline" color="text.secondary" sx={{ display: 'block', px: 1.5, mb: .5, fontSize: 10, fontWeight: 800, letterSpacing: '.1em' }}>{sectionLabel}</Typography>
            <List disablePadding sx={{ display: 'grid', gap: .5 }}>
              {items.map(({ to, key, label, icon: Icon }) => <ListItem key={to} disablePadding><ListItemButton component={NavLink} to={to} onClick={() => setMobileOpen(false)} sx={{ borderRadius: 2, '&.active': { bgcolor: 'primary.main', color: 'primary.contrastText', '& .MuiListItemIcon-root': { color: 'inherit' } } }}><ListItemIcon sx={{ minWidth: 38 }}><Icon size={18} aria-hidden="true" /></ListItemIcon><ListItemText primary={<Typography sx={{ fontSize: 14, fontWeight: 650 }}>{label ?? (key ? translate(key) : 'Applications')}</Typography>} /></ListItemButton></ListItem>)}
            </List>
          </Box>)}
        </List>
      </Box>
      <Box sx={{ mt: 'auto' }}>
        <Paper variant="outlined" sx={{ p: 1.5, bgcolor: 'action.hover', borderRadius: 2 }}><Typography variant="caption" color="text.secondary">{translate('signedInAs')}</Typography><Typography noWrap variant="body2" sx={{ mt: .25, fontWeight: 700 }}>{user?.display_name ?? user?.username ?? 'Administrator'}</Typography></Paper>
        <Button fullWidth startIcon={<SunMoon size={17} />} onClick={toggle} color="inherit" sx={{ mt: 1.25, justifyContent: 'flex-start', px: 1.5, textTransform: 'none' }}>Use {mode === 'dark' ? 'light' : 'dark'} mode</Button>
        <Button fullWidth startIcon={<LogOut size={17} />} onClick={() => void logout()} color="inherit" sx={{ mt: .5, justifyContent: 'flex-start', px: 1.5, textTransform: 'none' }}>{translate('signOut')}</Button>
      </Box>
    </Stack>
  )
  return <Box sx={{ minHeight: '100vh', display: 'flex', bgcolor: 'background.default', color: 'text.primary' }}>
    <a href="#main-content" className="sr-only z-50 bg-white p-3 focus:not-sr-only focus:fixed focus:left-3 focus:top-3">Skip to main content</a>
    <AppBar position="fixed" color="inherit" elevation={0} sx={{ display: { md: 'none' }, borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper' }}><Toolbar sx={{ minHeight: '64px !important', justifyContent: 'space-between' }}><Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}><ShieldCheck size={21} aria-hidden="true" /><Typography variant="subtitle2" sx={{ fontWeight: 800 }}>EduGD Admin</Typography></Stack><Stack direction="row" spacing={.5} sx={{ alignItems: 'center' }}><IconButton aria-label={`Use ${mode === 'dark' ? 'light' : 'dark'} mode`} onClick={toggle}><SunMoon size={19} /></IconButton><AdminLanguageSelector /><IconButton aria-label={mobileOpen ? translate('closeNavigation') : translate('openNavigation')} aria-expanded={mobileOpen} onClick={() => setMobileOpen((open) => !open)}>{mobileOpen ? <X size={21} /> : <Menu size={21} />}</IconButton></Stack></Toolbar></AppBar>
    <Drawer variant="permanent" sx={{ display: { xs: 'none', md: 'block' }, width: drawerWidth, flexShrink: 0, '& .MuiDrawer-paper': { width: drawerWidth, boxSizing: 'border-box', borderRightColor: 'divider' } }}><Box sx={{ position: 'absolute', top: 16, right: 16 }}><Stack direction="row" spacing={.5}><IconButton aria-label={`Use ${mode === 'dark' ? 'light' : 'dark'} mode`} size="small" onClick={toggle}><SunMoon size={17} /></IconButton><AdminLanguageSelector /></Stack></Box>{navigation}</Drawer>
    <Drawer open={mobileOpen} onClose={() => setMobileOpen(false)} variant="temporary" ModalProps={{ keepMounted: true }} sx={{ display: { xs: 'block', md: 'none' }, '& .MuiDrawer-paper': { width: drawerWidth, maxWidth: '85vw' } }}>{navigation}</Drawer>
    <Box component="main" id="main-content" sx={{ flexGrow: 1, minWidth: 0, pt: { xs: 10, md: 0 }, p: { xs: 2, sm: 3, lg: 4 } }}><Box sx={{ maxWidth: 1440, mx: 'auto' }}><OfflineStatusBanner /><Outlet />{location.pathname === '/devices' && <Box sx={{ mt: 4 }}><Suspense fallback={<LoadingState label="Loading enrollment tokensâ€¦" />}><EnrollmentTokensPanel /></Suspense></Box>}</Box></Box>
  </Box>
}
