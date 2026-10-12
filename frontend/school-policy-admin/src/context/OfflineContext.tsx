/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import api from '@/services/api'
import { flushOfflineQueue, listOfflineQueue, type OfflineQueueItem } from '@/services/offlineStore'

interface OfflineContextValue {
  isOnline: boolean
  queue: OfflineQueueItem[]
  pendingCount: number
  refresh: () => Promise<void>
  syncNow: () => Promise<void>
}

const OfflineContext = createContext<OfflineContextValue | null>(null)

export function OfflineProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient()
  const [isOnline, setIsOnline] = useState(() => typeof navigator === 'undefined' || navigator.onLine !== false)
  const [queue, setQueue] = useState<OfflineQueueItem[]>([])

  const refresh = useCallback(async () => { setQueue(await listOfflineQueue()) }, [])
  const syncNow = useCallback(async () => {
    if (!isOnline) { await refresh(); return }
    await flushOfflineQueue(async (item) => {
      const response = await api.request({ method: item.method, url: item.url, data: item.payload })
      return response.data
    })
    await refresh()
    await queryClient.invalidateQueries({ queryKey: ['devices'] })
    await queryClient.invalidateQueries({ queryKey: ['policies'] })
    await queryClient.invalidateQueries({ queryKey: ['policy'] })
    await queryClient.invalidateQueries({ queryKey: ['assignments'] })
  }, [isOnline, queryClient, refresh])

  useEffect(() => {
    void Promise.resolve().then(() => refresh())
    const handleOnline = () => { setIsOnline(true); void Promise.resolve().then(() => refresh()) }
    const handleOffline = () => setIsOnline(false)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    const timer = window.setInterval(() => { if (navigator.onLine !== false) void syncNow() }, 30_000)
    return () => { window.removeEventListener('online', handleOnline); window.removeEventListener('offline', handleOffline); window.clearInterval(timer) }
  }, [refresh, syncNow])

  const pendingCount = useMemo(() => queue.filter((item) => item.state === 'LOCAL_ONLY' || item.state === 'PENDING_SYNC' || item.state === 'FAILED').length, [queue])
  return <OfflineContext.Provider value={{ isOnline, queue, pendingCount, refresh, syncNow }}>{children}</OfflineContext.Provider>
}

export function useOfflineStatus() {
  const value = useContext(OfflineContext)
  if (!value) throw new Error('useOfflineStatus must be used within OfflineProvider')
  return value
}
