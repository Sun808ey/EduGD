import { useMemo } from 'react'
import { Dialog } from '@base-ui/react/dialog'
import { QRCodeSVG } from 'qrcode.react'
import { buildAndroidProvisioningPayload, resolveAndroidProvisioningConfig } from '@/lib/android-provisioning'
import { resolveApiBaseUrl } from '@/lib/environment'
import type { IssuedEnrollmentToken } from '@/types/api.types'

export function AndroidProvisioningQrDialog({ issued, open, onOpenChange }: { issued: IssuedEnrollmentToken; open: boolean; onOpenChange: (open: boolean) => void }) {
  const result = useMemo(() => {
    try {
      const config = resolveAndroidProvisioningConfig()
      if (!config) return { error: 'QR provisioning is not configured for this deployment.' }
      const apiBaseUrl = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL, import.meta.env.PROD)
      const apiOrigin = new URL(apiBaseUrl).origin
      const payload = buildAndroidProvisioningPayload({ ...config, apiOrigin, pairingToken: issued.pairing_token })
      return { payload, encoded: JSON.stringify(payload) }
    } catch (error) {
      return { error: error instanceof Error ? error.message : 'QR provisioning configuration is invalid.' }
    }
  }, [issued])

  const bundle = result.payload?.['android.app.extra.PROVISIONING_ADMIN_EXTRAS_BUNDLE']
  const redactedSummary = result.payload ? `API origin: ${typeof bundle === 'object' && bundle ? bundle.api_origin : 'unavailable'}\nDPC component: ${result.payload['android.app.extra.PROVISIONING_DEVICE_ADMIN_COMPONENT_NAME']}\nAPK: ${result.payload['android.app.extra.PROVISIONING_DEVICE_ADMIN_PACKAGE_DOWNLOAD_LOCATION']}\nMinimum version: ${result.payload['android.app.extra.PROVISIONING_DEVICE_ADMIN_MINIMUM_VERSION_CODE']}` : ''

  return <Dialog.Root open={open} onOpenChange={onOpenChange}>
    <Dialog.Portal>
      <Dialog.Backdrop className="fixed inset-0 z-40 bg-slate-950/50" />
      <Dialog.Viewport className="fixed inset-0 z-50 grid place-items-center overflow-y-auto p-4">
        <Dialog.Popup className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
          <Dialog.Title className="text-xl font-semibold">Android enrollment QR</Dialog.Title>
          <Dialog.Description className="mt-2 text-sm text-slate-600">Scan this once from the factory-reset device setup wizard. The QR is generated in memory and is never stored by EduGD.</Dialog.Description>
          {result.error ? <div role="alert" className="mt-6 rounded-lg bg-amber-50 p-4 text-sm text-amber-900">{result.error}</div> : <>
            <div className="mt-6 flex justify-center rounded-xl border bg-white p-4"><QRCodeSVG value={result.encoded!} size={300} level="M" includeMargin aria-label="Android device enrollment QR code" /></div>
            <p className="mt-4 whitespace-pre-wrap rounded-lg bg-slate-50 p-3 font-mono text-xs text-slate-700">{redactedSummary}</p>
            <p className="mt-3 text-xs text-slate-600">The pairing token is embedded only in the QR value. Do not screenshot, export, or reuse this code after the token expires.</p>
          </>}
          <div className="mt-6 flex justify-end"><Dialog.Close className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white">Close</Dialog.Close></div>
        </Dialog.Popup>
      </Dialog.Viewport>
    </Dialog.Portal>
  </Dialog.Root>
}
