import { Dialog } from '@base-ui/react/dialog'
import type { FormEvent, ReactNode } from 'react'

export function ActionDialog({ open, onOpenChange, title, description, children, submitLabel, busy, destructive = false, closeLabel, onSubmit }: {
  open: boolean; onOpenChange: (open: boolean) => void; title: string; description: string; children: ReactNode
  submitLabel?: string; busy: boolean; destructive?: boolean; closeLabel?: string; onSubmit: (event: FormEvent<HTMLFormElement>) => void
}) {
  return <Dialog.Root open={open} onOpenChange={(nextOpen) => { if (!busy || nextOpen) onOpenChange(nextOpen) }}>
    <Dialog.Portal>
      <Dialog.Backdrop className="fixed inset-0 z-40 bg-slate-950/50" />
      <Dialog.Viewport className="fixed inset-0 z-50 grid place-items-center overflow-y-auto p-4">
        <Dialog.Popup className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
          <Dialog.Title className="text-xl font-semibold">{title}</Dialog.Title>
          <Dialog.Description className="mt-2 text-sm text-slate-600">{description}</Dialog.Description>
          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            {children}
            <div className="flex justify-end gap-3">
              <Dialog.Close disabled={busy} className="rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50">{closeLabel ?? 'Cancel'}</Dialog.Close>
              {submitLabel && <button type="submit" disabled={busy} className={`rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 ${destructive ? 'bg-red-700' : 'bg-slate-950'}`}>{busy ? 'Working…' : submitLabel}</button>}
            </div>
          </form>
        </Dialog.Popup>
      </Dialog.Viewport>
    </Dialog.Portal>
  </Dialog.Root>
}
