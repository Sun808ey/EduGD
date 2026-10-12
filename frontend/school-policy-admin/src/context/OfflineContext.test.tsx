import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from '@/services/api'
import { flushOfflineQueue, listOfflineQueue, type OfflineQueueItem } from '@/services/offlineStore'
import { OfflineProvider, useOfflineStatus } from './OfflineContext'

vi.mock('@/services/api', () => ({ default: { request: vi.fn() } }))
vi.mock('@/services/offlineStore', () => ({ flushOfflineQueue: vi.fn(), listOfflineQueue: vi.fn() }))

const queueItem: OfflineQueueItem = {
  id: 'offline-queue-item',
  kind: 'policy_lifecycle',
  method: 'POST',
  url: '/admin/policies/policy/lifecycle',
  payload: { policy_uuid: 'policy' },
  state: 'LOCAL_ONLY',
  createdAt: '2026-09-11T10:00:00.000Z',
  updatedAt: '2026-09-11T10:00:00.000Z',
  attempts: 0,
}

function Probe() {
  const offline = useOfflineStatus()
  return <div>
    <output>{offline.isOnline ? 'online' : 'offline'}:{offline.pendingCount}:{offline.queue.length}</output>
    <button onClick={() => void offline.syncNow()}>sync</button>
    <button onClick={() => void offline.refresh()}>refresh</button>
  </div>
}

function renderProvider() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}><OfflineProvider><Probe /></OfflineProvider></QueryClientProvider>)
}

describe('offline provider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Object.defineProperty(navigator, 'onLine', { configurable: true, value: true })
    vi.mocked(listOfflineQueue).mockResolvedValue([queueItem])
    vi.mocked(api.request).mockResolvedValue({ data: { accepted: true } })
    vi.mocked(flushOfflineQueue).mockImplementation(async (sender) => {
      await sender(queueItem)
      return [queueItem]
    })
  })

  it('loads pending work, sends it, and exposes the current queue state', async () => {
    renderProvider()
    await screen.findByText('online:1:1')
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'sync' })); await Promise.resolve() })
    expect(api.request).toHaveBeenCalledWith({ method: 'POST', url: queueItem.url, data: queueItem.payload })
    expect(flushOfflineQueue).toHaveBeenCalledOnce()
  })

  it('refreshes without sending while offline and reacts to connectivity events', async () => {
    Object.defineProperty(navigator, 'onLine', { configurable: true, value: false })
    renderProvider()
    await screen.findByText('offline:1:1')
    fireEvent.click(screen.getByRole('button', { name: 'sync' }))
    await waitFor(() => expect(listOfflineQueue).toHaveBeenCalledTimes(2))
    expect(flushOfflineQueue).not.toHaveBeenCalled()

    Object.defineProperty(navigator, 'onLine', { configurable: true, value: true })
    await act(async () => { window.dispatchEvent(new Event('online')); await Promise.resolve() })
    expect(screen.getByText('online:1:1')).toBeInTheDocument()
    act(() => window.dispatchEvent(new Event('offline')))
    expect(screen.getByText('offline:1:1')).toBeInTheDocument()
  })

  it('requires the provider when using the hook', () => {
    expect(() => render(<Probe />)).toThrow('useOfflineStatus must be used within OfflineProvider')
  })
})
