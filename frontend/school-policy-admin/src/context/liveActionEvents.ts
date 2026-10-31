export type LiveActionState = 'pending' | 'success' | 'error'
export type LiveActionEvent = { state: LiveActionState; label: string; detail?: string }

const eventName = 'edugd:admin-action'

export function announceLiveAction(event: LiveActionEvent) {
  if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent<LiveActionEvent>(eventName, { detail: event }))
}

export function subscribeToLiveActions(listener: (event: LiveActionEvent) => void) {
  const handleEvent = (incoming: Event) => listener((incoming as CustomEvent<LiveActionEvent>).detail)
  window.addEventListener(eventName, handleEvent)
  return () => window.removeEventListener(eventName, handleEvent)
}
