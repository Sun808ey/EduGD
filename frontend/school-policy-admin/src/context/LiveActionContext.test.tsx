import { act, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { announceLiveAction } from './liveActionEvents'
import { LiveActionProvider, LiveActionStatus } from './LiveActionContext'

function renderStatus() {
  return render(<LiveActionProvider><LiveActionStatus /></LiveActionProvider>)
}

describe('live action status', () => {
  afterEach(() => { vi.useRealTimers() })

  it('shows pending work with a progress indicator', () => {
    renderStatus()
    act(() => announceLiveAction({ state: 'pending', label: 'Synchronisation' }))
    expect(screen.getByText('Synchronisation in progress')).toBeInTheDocument()
    expect(screen.getByLabelText('Action in progress')).toBeInTheDocument()
  })

  it('shows success and error details, then clears completed work', () => {
    vi.useFakeTimers()
    renderStatus()
    act(() => announceLiveAction({ state: 'success', label: 'Save', detail: 'Saved locally.' }))
    expect(screen.getByText('Save completed')).toBeInTheDocument()
    expect(screen.getByText('Saved locally.')).toBeInTheDocument()

    act(() => announceLiveAction({ state: 'error', label: 'Sync' }))
    expect(screen.getByText('Sync needs attention')).toBeInTheDocument()
    expect(screen.getByText('Review the action message and try again if needed.')).toBeInTheDocument()

    act(() => vi.advanceTimersByTime(4500))
    expect(screen.queryByText('Sync needs attention')).not.toBeInTheDocument()
  })
})
