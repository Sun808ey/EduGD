import { Alert, Button, Stack, Typography } from '@mui/material'
import { Link } from 'react-router-dom'
import { useOfflineStatus } from '@/context/OfflineContext'

export function OfflineStatusBanner() {
  const { isOnline, pendingCount, syncNow } = useOfflineStatus()
  if (isOnline && pendingCount === 0) return null
  return <Alert severity={isOnline ? 'info' : 'warning'} sx={{ mb: 3 }} action={<Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}><Button component={Link} to="/sync" color="inherit" size="small">View queue</Button>{isOnline && pendingCount > 0 && <Button color="inherit" size="small" onClick={() => void syncNow()}>Sync now</Button>}</Stack>}>
    <Typography variant="body2" sx={{ fontWeight: 700 }}>{isOnline ? `Pending synchronisation: ${pendingCount} change${pendingCount === 1 ? '' : 's'}` : 'Offline mode — showing locally cached school data.'}</Typography>
    <Typography variant="caption">{isOnline ? 'Changes are sent to the school server and device confirmation is required before they are marked applied.' : 'Local changes will remain pending synchronisation until connectivity returns.'}</Typography>
  </Alert>
}
