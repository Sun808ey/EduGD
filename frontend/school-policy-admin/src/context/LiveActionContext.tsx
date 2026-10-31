import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { Box, CircularProgress, Paper, Typography } from '@mui/material'
import { subscribeToLiveActions, type LiveActionEvent } from '@/context/liveActionEvents'
const LiveActionContext = createContext<LiveActionEvent | null>(null)

export function LiveActionProvider({ children }: { children: React.ReactNode }) {
  const [event, setEvent] = useState<LiveActionEvent | null>(null)
  useEffect(() => {
    const handleEvent = (next: LiveActionEvent) => { if (next) setEvent(next) }
    if (typeof window === 'undefined') return
    return subscribeToLiveActions(handleEvent)
  }, [])
  useEffect(() => {
    if (!event || event.state === 'pending') return
    const timer = window.setTimeout(() => setEvent((current) => current === event ? null : current), 4500)
    return () => window.clearTimeout(timer)
  }, [event])
  return <LiveActionContext.Provider value={event}>{children}</LiveActionContext.Provider>
}
export function LiveActionStatus() {
  const event = useContext(LiveActionContext)
  const content = useMemo(() => {
    if (!event) return null
    if (event.state === 'pending') return { title: `${event.label} in progress`, color: 'info.main', detail: 'Waiting for the service response.' }
    if (event.state === 'success') return { title: `${event.label} completed`, color: 'success.main', detail: event.detail ?? 'The latest records are being refreshed.' }
    return { title: `${event.label} needs attention`, color: 'error.main', detail: event.detail ?? 'Review the action message and try again if needed.' }
  }, [event])
  if (!content) return null
  return <Paper aria-live="polite" variant="outlined" sx={{ position: 'fixed', right: { xs: 16, sm: 24 }, bottom: { xs: 16, sm: 24 }, zIndex: 1300, display: 'flex', alignItems: 'center', gap: 1.25, maxWidth: { xs: 'calc(100vw - 32px)', sm: 420 }, p: 1.5, borderColor: content.color, boxShadow: 4 }}>
    {event?.state === 'pending' && <CircularProgress size={18} aria-label="Action in progress" />}
    <Box><Typography variant="body2" sx={{ fontWeight: 800 }}>{content.title}</Typography><Typography variant="caption" color="text.secondary">{content.detail}</Typography></Box>
  </Paper>
}
