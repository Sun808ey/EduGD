import { EnrollmentTokensPanel } from '@/components/devices/EnrollmentTokensPanel'

export function ProvisioningPage() {
  return <section className="space-y-6"><header><h1 className="text-3xl font-semibold">Provisioning</h1><p className="mt-2 text-sm text-slate-600">Create short-lived enrollment tokens for approved school-owned devices, then review token status and revoke unused credentials.</p></header><EnrollmentTokensPanel /></section>
}
