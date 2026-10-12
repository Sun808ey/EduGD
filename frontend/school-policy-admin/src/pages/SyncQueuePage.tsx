import { Button, Chip, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from '@mui/material'
import { RefreshCw } from 'lucide-react'
import { useOfflineStatus } from '@/context/OfflineContext'

const stateColor = (state: string) => state === 'FAILED' ? 'error' : state === 'APPLIED' ? 'success' : state === 'SENT_TO_DEVICE' ? 'info' : 'warning'

export default function SyncQueuePage() {
  const { queue, pendingCount, isOnline, refresh, syncNow } = useOfflineStatus()
  return <Stack spacing={3}>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ justifyContent: 'space-between' }}>
      <BoxTitle pendingCount={pendingCount} />
      <Stack direction="row" spacing={1}><Button variant="outlined" startIcon={<RefreshCw size={16} />} onClick={() => void refresh()}>Refresh</Button><Button variant="contained" disabled={!isOnline || pendingCount === 0} onClick={() => void syncNow()}>Sync now</Button></Stack>
    </Stack>
    <Paper variant="outlined" sx={{ p: 2 }}><Typography variant="body2" color="text.secondary">A command is only marked <strong>APPLIED</strong> after the enrolled device confirms it. Sent commands remain visible for audit and retry failures.</Typography></Paper>
    <Paper variant="outlined" sx={{ overflow: 'auto' }}>
      {queue.length === 0 ? <Typography sx={{ p: 3 }} color="text.secondary">No local changes are waiting for synchronisation.</Typography> : <Table size="small"><TableHead><TableRow><TableCell>Change</TableCell><TableCell>State</TableCell><TableCell>Attempts</TableCell><TableCell>Updated</TableCell><TableCell>Error</TableCell></TableRow></TableHead><TableBody>{queue.map((item) => <TableRow key={item.id}><TableCell><Typography variant="body2" sx={{ fontWeight: 700 }}>{item.kind.replaceAll('_', ' ')}</Typography><Typography variant="caption" color="text.secondary">{item.url}</Typography></TableCell><TableCell><Chip size="small" color={stateColor(item.state) as 'error' | 'success' | 'info' | 'warning'} label={item.state.replaceAll('_', ' ')} /></TableCell><TableCell>{item.attempts}</TableCell><TableCell>{new Date(item.updatedAt).toLocaleString()}</TableCell><TableCell>{item.lastError ?? '—'}</TableCell></TableRow>)}</TableBody></Table>}
    </Paper>
  </Stack>
}

function BoxTitle({ pendingCount }: { pendingCount: number }) {
  return <Stack spacing={0.5}><Typography variant="overline" color="text.secondary">Connectivity</Typography><Typography variant="h4" sx={{ fontWeight: 800 }}>Synchronisation queue</Typography><Typography color="text.secondary">{pendingCount ? `${pendingCount} change${pendingCount === 1 ? '' : 's'} pending synchronisation.` : 'All local changes have been sent.'}</Typography></Stack>
}
