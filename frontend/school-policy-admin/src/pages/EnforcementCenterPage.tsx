import { ArrowForward, Devices, Language, Policy, QueryStats, Sync } from '@mui/icons-material'
import { Box, Button, Card, CardActions, CardContent, Chip, Grid, Stack, Typography } from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'
import { useOfflineStatus } from '@/context/OfflineContext'

type Workflow = { title: string; description: string; to: string; icon: typeof Policy; action: string }

const workflows: Workflow[] = [
  { title: 'Create or schedule a policy', description: 'Set school-day rules, screen-time limits, approved applications, and browser filtering in one guided form.', to: '/policies/new', icon: Policy, action: 'Open policy builder' },
  { title: 'Manage applications and domains', description: 'Maintain verified package identities and the browser-domain catalogue used by policy forms.', to: '/policies/catalogue', icon: Language, action: 'Open catalogue' },
  { title: 'Review device enforcement', description: 'Check device status, assignments, reported evidence, and controls that need administrator attention.', to: '/devices', icon: Devices, action: 'View devices' },
  { title: 'Review usage and blocked-domain evidence', description: 'Read privacy-limited reports from enrolled devices without exposing learner content or browsing history.', to: '/reports', icon: QueryStats, action: 'Open evidence reports' },
  { title: 'Check synchronization health', description: 'See queued changes, retry state, and whether local administration actions have reached devices.', to: '/sync', icon: Sync, action: 'Open sync queue' },
]

export function EnforcementCenterPage() {
  const { isOnline, pendingCount } = useOfflineStatus()
  return <Stack spacing={3}>
    <Box component="header">
      <Typography variant="overline" color="primary.main" sx={{ fontWeight: 800, letterSpacing: '.14em' }}>Administration</Typography>
      <Typography component="h1" variant="h4" sx={{ mt: .25, fontWeight: 800 }}>Enforcement center</Typography>
      <Typography color="text.secondary" sx={{ mt: 1, maxWidth: 760 }}>Choose a guided workflow to manage school-device rules. The controls below use server validation and signed device synchronization.</Typography>
    </Box>
    <Card variant="outlined" sx={{ borderRadius: 3 }}>
      <CardContent><Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ justifyContent: 'space-between', alignItems: { sm: 'center' } }}><Box><Typography variant="h6" sx={{ fontWeight: 800 }}>Synchronization status</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: .5 }}>{pendingCount ? `${pendingCount} local change${pendingCount === 1 ? '' : 's'} waiting to synchronize.` : 'No local changes are waiting to synchronize.'}</Typography></Box><Chip color={isOnline ? 'success' : 'warning'} label={isOnline ? 'Connected' : 'Offline'} /></Stack></CardContent>
    </Card>
    <Box><Typography component="h2" variant="h6" sx={{ mb: 1.5, fontWeight: 800 }}>Choose a task</Typography><Grid container spacing={2}>{workflows.map(({ title, description, to, icon: Icon, action }) => <Grid key={to} size={{ xs: 12, sm: 6, lg: 4 }}><Card variant="outlined" sx={{ height: '100%', borderRadius: 3, display: 'flex', flexDirection: 'column' }}><CardContent sx={{ flexGrow: 1 }}><Box sx={{ display: 'grid', placeItems: 'center', width: 42, height: 42, borderRadius: 2, bgcolor: 'action.hover', color: 'primary.main', mb: 2 }}><Icon aria-hidden="true" /></Box><Typography variant="h6" sx={{ fontWeight: 800 }}>{title}</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 1, lineHeight: 1.6 }}>{description}</Typography></CardContent><CardActions sx={{ p: 2, pt: 0 }}><Button component={RouterLink} to={to} endIcon={<ArrowForward />} variant="outlined" fullWidth>{action}</Button></CardActions></Card></Grid>)}</Grid></Box>
  </Stack>
}

export default EnforcementCenterPage
