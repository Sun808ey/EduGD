import { describe, expect, it, vi } from 'vitest'
import { announceLiveAction, subscribeToLiveActions } from './liveActionEvents'

describe('live action events', () => {
  it('does nothing when no browser window is available', () => {
    vi.stubGlobal('window', undefined)
    expect(() => announceLiveAction({ state: 'pending', label: 'Sync' })).not.toThrow()
    vi.unstubAllGlobals()
  })

  it('publishes events and stops publishing after unsubscribe', () => {
    const listener = vi.fn()
    const unsubscribe = subscribeToLiveActions(listener)
    const event = { state: 'success' as const, label: 'Saved' }

    announceLiveAction(event)
    expect(listener).toHaveBeenCalledWith(event)

    unsubscribe()
    announceLiveAction({ state: 'error', label: 'Failed' })
    expect(listener).toHaveBeenCalledOnce()
  })
})
