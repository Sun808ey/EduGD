import { useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { adminService } from '@/services/admin.service'
import { errorMessage } from '@/services/errors'
import {
  buildPolicyPayload,
  recommendedComplianceSettings,
  recommendedDataCollectionSettings,
  recommendedOfflinePolicySettings,
  recommendedNetworkSettings,
  type NetworkSettings,
  type ApplicationType,
  type ApplicationRestrictionOptions,
  type ApprovedApplicationSelection,
  type ComplianceSettings,
  type DataCollectionSettings,
  type DeviceRestrictionOptions,
  type DeviceUseMode,
  type ScreenLockOptions,
} from '@/services/policy-template'
import type { ManagedApplication } from '@/types/api.types'

const DPC_PACKAGE = 'io.github.sun808ey.edugd.dpc'

const recommendedDeviceRestrictions: DeviceRestrictionOptions = {
  blockFactoryReset: true,
  blockSafeMode: true,
  blockDeveloperOptionsAndDebugging: true,
  blockUsbFileTransfer: true,
  blockAccountChanges: true,
  blockUserSwitching: true,
  blockNetworkReset: true,
  blockWifiChanges: false,
  disableScreenshots: false,
  disableScreenRecording: false,
  disableCamera: false,
  disableMicrophone: false,
  disableLocation: false,
}

const recommendedScreenLock: ScreenLockOptions = {
  requireScreenLock: true,
  automaticLockAfterMinutes: 5,
  allowBiometricUnlock: false,
  allowLearnerChangeLockMethod: false,
}

const modeOptions: Array<{ value: DeviceUseMode; label: string; description: string }> = [
  { value: 'normal_managed', label: 'Normal managed device', description: 'The device remains managed while learners can use its normal managed-device experience.' },
  { value: 'dedicated_learning', label: 'Dedicated learning device', description: 'Restricted to approved school applications; it is not normally used as a personal phone.' },
  { value: 'examination', label: 'Examination device', description: 'Use the managed device for controlled examination activities.' },
]

const applicationTypeOptions: Array<{ value: ApplicationType; label: string }> = [
  { value: 'learning_application', label: 'Learning application' },
  { value: 'digital_textbook', label: 'Digital textbook' },
  { value: 'pdf_reader', label: 'PDF reader' },
  { value: 'calculator', label: 'Calculator' },
  { value: 'approved_browser', label: 'Approved browser' },
  { value: 'accessibility_application', label: 'Accessibility application' },
  { value: 'other_approved_application', label: 'Other approved application' },
]
function inferApplicationType(application: ManagedApplication): ApplicationType {
  const category = application.category.toLowerCase()
  if (category.includes('textbook')) return 'digital_textbook'
  if (category.includes('pdf')) return 'pdf_reader'
  if (category.includes('calculator')) return 'calculator'
  if (category.includes('browser')) return 'approved_browser'
  if (category.includes('accessibility')) return 'accessibility_application'
  if (category.includes('education') || category.includes('learning')) return 'learning_application'
  return 'other_approved_application'
}

function selectionFromApplication(application: ManagedApplication): ApprovedApplicationSelection {
  return {
    application_uuid: application.application_uuid,
    display_name: application.display_name,
    package_name: application.package_name,
    application_type: inferApplicationType(application),
    required: false,
    allow_in_kiosk: true,
  }
}

export function PolicyCreatePage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const applications = useQuery({
    queryKey: ['managed-applications'],
    queryFn: ({ signal }) => adminService.listManagedApplications(signal),
  })
  const school = useQuery({ queryKey: ['school'], queryFn: ({ signal }) => adminService.getSchool(signal) })
  const domainCatalogueQuery = useQuery({ queryKey: ['managed-domains'], queryFn: ({ signal }) => adminService.listManagedDomains(signal) })
  const [name, setName] = useState('')
  const [policyCode, setPolicyCode] = useState('LEARNING_DEVICE')
  const [description, setDescription] = useState('Controls tablets used for classroom learning activities.')
  const [policyType, setPolicyType] = useState<'learning' | 'examination'>('learning')
  const [appliesTo, setAppliesTo] = useState<'selected_classes' | 'department' | 'selected_devices'>('selected_classes')
  const [effectiveDate, setEffectiveDate] = useState('2026-10-05')
  const [expiryDate, setExpiryDate] = useState('')
  const [applicationSearch, setApplicationSearch] = useState('')
  const [catalogueSelectionUuid, setCatalogueSelectionUuid] = useState('')
  const [selectedApplications, setSelectedApplications] = useState<ApprovedApplicationSelection[]>([])
  const [blockedApplicationUuids, setBlockedApplicationUuids] = useState<string[]>([])
  const [scheduleDays, setScheduleDays] = useState<number[]>([1, 2, 3, 4, 5])
  const [scheduleStart, setScheduleStart] = useState('08:00')
  const [scheduleEnd, setScheduleEnd] = useState('16:00')
  const [blockedSelection, setBlockedSelection] = useState('')
  const [newDomain, setNewDomain] = useState('')
  const [limit] = useState('480')
  const [reset] = useState('0')
  const [domains, setDomains] = useState('')
  const [webDefaultAction, setWebDefaultAction] = useState<'allow' | 'block'>('allow')
  const [includeSubdomains, setIncludeSubdomains] = useState(true)
  const [networkSettings, setNetworkSettings] = useState<NetworkSettings>(recommendedNetworkSettings)
  const [complianceSettings, setComplianceSettings] = useState<ComplianceSettings>(recommendedComplianceSettings)
  const [disallowOutgoingCalls] = useState(true)
  const [disallowSms] = useState(true)
  const [deviceUseMode, setDeviceUseMode] = useState<DeviceUseMode>('dedicated_learning')
  const [kioskModeEnabled, setKioskModeEnabled] = useState(true)
  const [displaySchoolName, setDisplaySchoolName] = useState(true)
  const [supportMessage, setSupportMessage] = useState('Contact the ICT office')
  const [administratorNotes, setAdministratorNotes] = useState('This policy is for tablets used during normal classroom lessons.\nScreenshots are allowed for learning activities.\nCamera use is allowed only when required by the teacher.\nThe device must be returned to the ICT office after the lesson.')
  const dataCollectionSettings: DataCollectionSettings = recommendedDataCollectionSettings
  const [applicationControls, setApplicationControls] = useState<ApplicationRestrictionOptions>({
    allowInstallationOfOtherApplications: false,
    allowInstallationFromUnknownSources: false,
    allowUninstallOfApprovedApplications: false,
    allowDisableOfApprovedApplications: false,
    allowGooglePlayStore: false,
    allowFileSharingApplications: false,
  })
  const [deviceRestrictions, setDeviceRestrictions] = useState<DeviceRestrictionOptions>(recommendedDeviceRestrictions)
  const [screenLock, setScreenLock] = useState<ScreenLockOptions>(recommendedScreenLock)
  const [error, setError] = useState('')
  const [previewOpen, setPreviewOpen] = useState(false)
  const [publishConfirmOpen, setPublishConfirmOpen] = useState(false)
  const addDomainMutation = useMutation({
    mutationFn: () => adminService.createManagedDomain({ domain: newDomain.trim().toLowerCase(), category: 'custom', status: 'enabled' }),
    onSuccess: (domain) => {
      setDomains((current) => current ? `${current}\n${domain.domain}` : domain.domain)
      setNewDomain('')
      void queryClient.invalidateQueries({ queryKey: ['managed-domains'] })
    },
    onError: (caught) => setError(errorMessage(caught)),
  })

  const eligibleApplications = (applications.data ?? [])
    .filter((application) => application.status === 'enabled' && application.education_approved && !application.mandatory_block)
  const filteredApplications = eligibleApplications.filter((application) => {
    const query = applicationSearch.trim().toLowerCase()
    return !query || `${application.display_name} ${application.package_name} ${application.category}`.toLowerCase().includes(query)
  })
  const selectedUuids = new Set(selectedApplications.map((application) => application.application_uuid))
  const availableApplications = filteredApplications.filter((application) => !selectedUuids.has(application.application_uuid))
  const blockedApplications = (applications.data ?? []).filter((application) => application.status === 'enabled' && !selectedUuids.has(application.application_uuid) && !blockedApplicationUuids.includes(application.application_uuid))

  function addApplication() {
    const application = eligibleApplications.find((candidate) => candidate.application_uuid === catalogueSelectionUuid)
    if (!application || selectedUuids.has(application.application_uuid)) return
    setSelectedApplications((current) => [...current, selectionFromApplication(application)])
    setCatalogueSelectionUuid('')
  }

  function removeApplication(applicationUuid: string) {
    setSelectedApplications((current) => current.filter((application) => application.application_uuid !== applicationUuid))
  }

  function updateApplication(applicationUuid: string, update: Partial<ApprovedApplicationSelection>) {
    setSelectedApplications((current) => current.map((application) => application.application_uuid === applicationUuid ? { ...application, ...update } : application))
  }

  function applyLearningTemplate() {
    setName('Learning Device')
    setPolicyType('learning')
    setAppliesTo('selected_classes')
    setEffectiveDate('2026-10-05')
    setExpiryDate('')
    setSelectedApplications(eligibleApplications.slice(0, 3).map(selectionFromApplication))
    setWebDefaultAction('allow')
    setNetworkSettings(recommendedNetworkSettings)
    setComplianceSettings(recommendedComplianceSettings)
    setDeviceUseMode('dedicated_learning')
    setKioskModeEnabled(true)
    setDisplaySchoolName(true)
    setSupportMessage('Contact the ICT office')
    setApplicationControls({
      allowInstallationOfOtherApplications: false,
      allowInstallationFromUnknownSources: false,
      allowUninstallOfApprovedApplications: false,
      allowDisableOfApprovedApplications: false,
      allowGooglePlayStore: false,
      allowFileSharingApplications: false,
    })
    setDeviceRestrictions(recommendedDeviceRestrictions)
    setScreenLock(recommendedScreenLock)
  }

  const selectedMode = modeOptions.find((option) => option.value === deviceUseMode) ?? modeOptions[1]
  const affectedDeviceCount = 0
  function validateBeforePreview(): boolean {
    setError('')
    if (!name.trim()) { setError('Policy name is required.'); return false }
    if (!/^[A-Z][A-Z0-9_]{2,63}$/.test(policyCode.trim())) { setError('Policy code must use 3–64 uppercase letters, numbers, or underscores and start with a letter.'); return false }
    if (!description.trim()) { setError('Policy description is required.'); return false }
    if (!effectiveDate) { setError('An effective date is required.'); return false }
    if (!school.data?.timezone) { setError('Set the school timetable timezone in Settings before creating a policy.'); return false }
    if (!scheduleDays.length || scheduleStart >= scheduleEnd) { setError('Choose at least one weekday and a valid timetable window.'); return false }
    if (expiryDate && expiryDate < effectiveDate) { setError('Expiry date cannot be before the effective date.'); return false }
    if (!networkSettings.allowMobileData) { setError('Mobile-data blocking is unavailable on standard managed Android devices.'); return false }
    if (!selectedApplications.length) { setError('Select at least one approved application before saving this policy.'); return false }
    if (kioskModeEnabled && !selectedApplications.some((application) => application.allow_in_kiosk)) { setError('Kiosk mode requires at least one approved kiosk application.'); return false }
    if (deviceUseMode === 'examination' && (!deviceRestrictions.disableCamera || !deviceRestrictions.disableScreenshots || !deviceRestrictions.disableMicrophone)) { setError('Examination mode requires camera, screenshots, and microphone to be disabled.'); return false }
    if (deviceRestrictions.blockWifiChanges && !networkSettings.allowWifi) { setError('Allow Wi-Fi before blocking Wi-Fi changes so the device can reconnect.'); return false }
    return true
  }
  const mutation = useMutation({
    mutationFn: async (publish: boolean) => {
      const result = await adminService.createPolicy(name.trim(), buildPolicyPayload({
      policyCode,
      description,
      emergency: DPC_PACKAGE,
      allowed: '',
      blocked: '',
      limit,
      reset,
      domains,
      webDefaultAction,
      includeSubdomains,
      wifiOnly: false,
      disallowMobileNetworkConfiguration: false,
      disallowTethering: !networkSettings.allowHotspotCreation,
      disallowUserVpn: !networkSettings.allowVpnChanges,
      alwaysOnFilteringVpn: false,
      vpnLockdownRequired: false,
      networkSettings,
      disallowOutgoingCalls,
      disallowSms,
      deviceUseMode,
      kioskModeEnabled,
      displaySchoolName,
      supportMessage,
      approvedApplications: selectedApplications,
      blockedPackages: (applications.data ?? []).filter((application) => blockedApplicationUuids.includes(application.application_uuid)).map((application) => application.package_name),
      applicationControls,
      deviceRestrictions,
      screenLock,
      complianceSettings,
      offlineSettings: recommendedOfflinePolicySettings,
      administratorNotes,
      dataCollectionSettings,
      schedule: { timezone: school.data?.timezone, days: scheduleDays, startMinute: Number(scheduleStart.slice(0, 2)) * 60 + Number(scheduleStart.slice(3)), endMinute: Number(scheduleEnd.slice(0, 2)) * 60 + Number(scheduleEnd.slice(3)), modeId: deviceUseMode === 'examination' ? 'examination' : 'learning', priority: 1 },
      }))
      if (publish) await adminService.setPolicyLifecycle(result.policy_uuid, 'active', 'Published from policy template confirmation.')
      return { result, publish }
    },
    onSuccess: ({ result, publish }) => navigate(result.sync_state ? '/policies' : `/policies/${result.policy_uuid}`, { state: result.sync_state ? { notice: publish ? 'Policy published locally and queued for synchronisation.' : 'Policy saved locally and queued for synchronisation.' } : undefined }),
    onError: (caught) => setError(errorMessage(caught)),
  })

  return <section className="mx-auto max-w-4xl space-y-8"><header><Link to="/policies" className="text-sm font-semibold text-emerald-700">← Policies</Link><p className="mt-5 text-xs font-bold uppercase tracking-[.16em] text-emerald-700">EDUGD policy template</p><h1 className="mt-2 text-3xl font-semibold">Create policy template</h1><p className="mt-2 text-sm text-slate-600">Choose school-facing controls. Saving creates revision 1 and the server validates the canonical DPC v3 contract.</p></header>
    <form className="grid gap-6" onSubmit={(event) => { event.preventDefault(); if (validateBeforePreview()) setPreviewOpen(true) }}>
      <Panel title="School timetable"><p className="text-sm text-slate-600">This policy is active during the selected recurring school-day window. The DPC uses the school timezone configured in Settings and rejects ambiguous overlaps.</p><div className="mt-4 grid gap-4 sm:grid-cols-3"><Field label="Start time"><input required type="time" value={scheduleStart} onChange={(event) => setScheduleStart(event.target.value)} className="input mt-2" /></Field><Field label="End time"><input required type="time" value={scheduleEnd} onChange={(event) => setScheduleEnd(event.target.value)} className="input mt-2" /></Field><Field label="Timezone"><input readOnly value={school.data?.timezone || 'Set in Settings'} className="input mt-2 bg-slate-50" /></Field></div><fieldset className="mt-4"><legend className="text-sm font-medium text-slate-700">Days of the week</legend><div className="mt-2 flex flex-wrap gap-2">{[['Mon', 1], ['Tue', 2], ['Wed', 3], ['Thu', 4], ['Fri', 5], ['Sat', 6], ['Sun', 7]].map(([label, day]) => <label key={day} className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm"><input type="checkbox" checked={scheduleDays.includes(day as number)} onChange={(event) => setScheduleDays((current) => event.target.checked ? [...current, day as number].sort() : current.filter((item) => item !== day))} />{label}</label>)}</div></fieldset></Panel>
      <Panel title="Blocked applications"><p className="text-sm text-slate-600">Choose apps from the school catalogue. Social media, games, and other restricted apps are blocked by package identity supplied by the catalogue.</p><Field label="Application blocklist"><select value={blockedSelection} onChange={(event) => { const next = event.target.value; if (next) { setBlockedApplicationUuids((current) => [...current, next]); setBlockedSelection('') } }} className="input mt-2"><option value="">Choose an application to block</option>{blockedApplications.map((application) => <option key={application.application_uuid} value={application.application_uuid}>{application.display_name} · {application.category}</option>)}</select></Field><div className="mt-3 flex flex-wrap gap-2">{blockedApplicationUuids.map((uuid) => { const application = applications.data?.find((item) => item.application_uuid === uuid); return application ? <button type="button" key={uuid} onClick={() => setBlockedApplicationUuids((current) => current.filter((item) => item !== uuid))} className="rounded-full bg-rose-100 px-3 py-1 text-sm text-rose-900">{application.display_name} ×</button> : null })}</div></Panel>
      <Panel title="Start with a template"><p className="text-sm text-slate-600">Templates use plain school-facing rules. You can review the detailed settings below before saving version 1.</p><button type="button" onClick={applyLearningTemplate} className="mt-3 rounded-full border border-emerald-700 px-4 py-2 text-sm font-semibold text-emerald-800">Use Learning Device template</button><ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600"><li>Approved learning apps and PDF reader</li><li>Dedicated learning mode with kiosk mode enabled</li><li>Factory reset, Safe Mode, debugging, USB transfer, account changes, and user switching restricted</li></ul></Panel>
      <Panel title="Policy details"><div className="grid gap-4 sm:grid-cols-2"><Field label="Policy type"><select required value={policyType} onChange={(event) => { const next = event.target.value as 'learning' | 'examination'; setPolicyType(next); setDeviceUseMode(next === 'examination' ? 'examination' : 'dedicated_learning') }} className="input"><option value="learning">Learning device</option><option value="examination">Examination device</option></select></Field><Field label="Status"><select required value="draft" disabled className="input"><option value="draft">Draft</option></select></Field><Field label="Applies to"><select required value={appliesTo} onChange={(event) => setAppliesTo(event.target.value as typeof appliesTo)} className="input"><option value="selected_classes">Selected classes</option><option value="department">Department</option><option value="selected_devices">Selected devices</option></select></Field><Field label="Version"><input value="1 (generated on save)" readOnly className="input bg-slate-50" /></Field><Field label="Effective date"><input required type="date" value={effectiveDate} onChange={(event) => setEffectiveDate(event.target.value)} className="input" /></Field><Field label="Expiry date (optional)"><input type="date" value={expiryDate} min={effectiveDate} onChange={(event) => setExpiryDate(event.target.value)} className="input" /></Field></div><div className="mt-4 grid gap-4 sm:grid-cols-2"><Field label="Policy name"><input required value={name} onChange={(event) => setName(event.target.value)} className="input input-comfortable" maxLength={255} /></Field><Field label="Policy code"><input required value={policyCode} onChange={(event) => setPolicyCode(event.target.value.toUpperCase())} className="input input-comfortable font-mono" maxLength={64} pattern="[A-Z][A-Z0-9_]{2,63}" /></Field></div><Field label="Description"><textarea required value={description} onChange={(event) => setDescription(event.target.value)} className="input input-comfortable mt-2" maxLength={2048} /></Field><p className="mt-2 text-xs text-slate-500">Policy versions are generated automatically by the server. Draft is the only authoring status; publishing is confirmed after preview.</p></Panel>
      <Panel title="Device-use mode"><fieldset><legend className="text-sm font-medium text-slate-700">Select how the device will operate</legend><div className="mt-3 grid gap-3">{modeOptions.map((option) => <label key={option.value} className="flex items-start gap-3 rounded-xl border border-slate-200 p-4 text-sm text-slate-700"><input type="radio" name="device-use-mode" value={option.value} checked={deviceUseMode === option.value} onChange={() => setDeviceUseMode(option.value)} className="mt-1" /> <span><span className="font-semibold text-slate-950">{option.label}</span><span className="mt-1 block text-slate-600">{option.description}</span></span></label>)}</div></fieldset><p className="mt-4 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-950">{selectedMode.value === 'dedicated_learning' ? 'A dedicated learning device is restricted to approved school applications. Learners cannot normally use it as a personal phone.' : selectedMode.description}</p><div className="mt-4 grid gap-3 sm:grid-cols-2"><Toggle label="Enable kiosk mode" checked={kioskModeEnabled} onChange={setKioskModeEnabled} /><Toggle label="Display school name on device" checked={displaySchoolName} onChange={setDisplaySchoolName} /></div><Field label="School support message"><input required value={supportMessage} onChange={(event) => setSupportMessage(event.target.value)} className="input mt-2" maxLength={256} /></Field><p className="mt-2 text-xs text-slate-500">Only these kiosk settings are configurable in the first EDUGD version. The registered school name is supplied by the server when the policy is saved.</p></Panel>
      <Panel title="Approved applications"><p className="text-sm text-slate-600">Select applications already approved and tested by the school. The catalogue is the source of truth; this form does not install apps or provide an app store.</p>{applications.isLoading && <p className="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">Loading the approved application catalogue…</p>}{applications.isError && <p role="alert" className="mt-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">The approved application catalogue is temporarily unavailable. Try again before saving.</p>}<div className="mt-4 grid gap-4 md:grid-cols-3 md:items-end"><Field label="Search application"><input value={applicationSearch} onChange={(event) => setApplicationSearch(event.target.value)} className="input mt-2" placeholder="Name, package, or category" /></Field><Field label="Application name"><select value={catalogueSelectionUuid} onChange={(event) => setCatalogueSelectionUuid(event.target.value)} className="input mt-2"><option value="">Choose an approved application</option>{availableApplications.map((application) => <option key={application.application_uuid} value={application.application_uuid}>{application.display_name}</option>)}</select></Field><Field label="Package name"><select aria-label="Package name" value={catalogueSelectionUuid} onChange={(event) => setCatalogueSelectionUuid(event.target.value)} className="input mt-2"><option value="">Choose package</option>{availableApplications.map((application) => <option key={application.application_uuid} value={application.application_uuid}>{application.package_name}</option>)}</select></Field></div><button type="button" onClick={addApplication} disabled={!catalogueSelectionUuid} className="mt-3 rounded-full border border-emerald-700 px-4 py-2 text-sm font-semibold text-emerald-800 disabled:opacity-50">Add application</button><div className="mt-6 space-y-3"><h3 className="text-sm font-semibold text-slate-900">Selected apps ({selectedApplications.length})</h3>{selectedApplications.length === 0 && <p className="rounded-xl border border-dashed border-slate-300 p-4 text-sm text-slate-600">No approved applications selected yet.</p>}{selectedApplications.map((application) => <article key={application.application_uuid} className="rounded-xl border border-slate-200 p-4"><div className="flex flex-wrap items-start justify-between gap-3"><label className="flex items-start gap-3"><input type="checkbox" checked onChange={() => removeApplication(application.application_uuid)} className="mt-1" /><span><span className="font-semibold text-slate-950">{application.display_name}</span><span className="mt-1 block font-mono text-xs text-slate-600">{application.package_name}</span></span></label><span className="text-xs text-slate-500">Uncheck to remove</span></div><div className="mt-4 grid gap-3 sm:grid-cols-3"><Field label="Application type"><select value={application.application_type} onChange={(event) => updateApplication(application.application_uuid, { application_type: event.target.value as ApplicationType })} className="input mt-2">{applicationTypeOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></Field><Toggle label="Required" checked={application.required} onChange={(value) => updateApplication(application.application_uuid, { required: value })} /><Toggle label="Allow in kiosk mode" checked={application.allow_in_kiosk} onChange={(value) => updateApplication(application.application_uuid, { allow_in_kiosk: value })} /></div></article>)}</div></Panel>
      <Panel title="Application restrictions"><p className="text-sm text-slate-600">These controls prevent unmanaged app installation and changes on school-owned devices. They default to the recommended locked-down values.</p><div className="grid gap-3 sm:grid-cols-2"><div><Toggle label="Allow installation of other applications" checked={applicationControls.allowInstallationOfOtherApplications} onChange={(value) => setApplicationControls((current) => ({ ...current, allowInstallationOfOtherApplications: value }))} />{applicationControls.allowInstallationOfOtherApplications && <p role="note" className="mt-2 rounded-lg bg-amber-50 p-3 text-xs leading-5 text-amber-950">Allowing other applications may reduce the school’s control over the device.</p>}</div><Toggle label="Allow installation from unknown sources" checked={applicationControls.allowInstallationFromUnknownSources} onChange={(value) => setApplicationControls((current) => ({ ...current, allowInstallationFromUnknownSources: value }))} /><Toggle label="Allow learners to uninstall approved applications" checked={applicationControls.allowUninstallOfApprovedApplications} onChange={(value) => setApplicationControls((current) => ({ ...current, allowUninstallOfApprovedApplications: value }))} /><Toggle label="Allow learners to disable approved applications" checked={applicationControls.allowDisableOfApprovedApplications} onChange={(value) => setApplicationControls((current) => ({ ...current, allowDisableOfApprovedApplications: value }))} /><Toggle label="Allow Google Play Store" checked={applicationControls.allowGooglePlayStore} onChange={(value) => setApplicationControls((current) => ({ ...current, allowGooglePlayStore: value }))} /><Toggle label="Allow file-sharing applications" checked={applicationControls.allowFileSharingApplications} onChange={(value) => setApplicationControls((current) => ({ ...current, allowFileSharingApplications: value }))} /></div></Panel>
      <Panel title="Device restrictions"><p className="text-sm text-slate-600">These controls map to Android device-owner restrictions. Recommended security restrictions are enabled while network recovery remains available.</p><h3 className="mt-5 text-sm font-semibold text-slate-900">Security restrictions</h3><div className="mt-3 grid gap-3 sm:grid-cols-2"><Toggle label="Block factory reset from device settings" checked={deviceRestrictions.blockFactoryReset} onChange={(value) => setDeviceRestrictions((current) => ({ ...current, blockFactoryReset: value }))} /><Toggle label="Block Safe Mode" checked={deviceRestrictions.blockSafeMode} onChange={(value) => setDeviceRestrictions((current) => ({ ...current, blockSafeMode: value }))} /><Toggle label="Block developer options and debugging" checked={deviceRestrictions.blockDeveloperOptionsAndDebugging} onChange={(value) => setDeviceRestrictions((current) => ({ ...current, blockDeveloperOptionsAndDebugging: value }))} /><Toggle label="Block USB file transfer" checked={deviceRestrictions.blockUsbFileTransfer} onChange={(value) => setDeviceRestrictions((current) => ({ ...current, blockUsbFileTransfer: value }))} /><Toggle label="Block account changes" checked={deviceRestrictions.blockAccountChanges} onChange={(value) => setDeviceRestrictions((current) => ({ ...current, blockAccountChanges: value }))} /><Toggle label="Block user switching" checked={deviceRestrictions.blockUserSwitching} onChange={(value) => setDeviceRestrictions((current) => ({ ...current, blockUserSwitching: value }))} /><Toggle label="Block network reset" checked={!networkSettings.allowNetworkReset} onChange={(value) => setNetworkSettings((current) => ({ ...current, allowNetworkReset: !value }))} /><Toggle label="Block Wi-Fi changes" checked={deviceRestrictions.blockWifiChanges} onChange={(value) => setDeviceRestrictions((current) => ({ ...current, blockWifiChanges: value }))} /></div><p role="note" className="mt-4 rounded-xl bg-amber-50 p-4 text-sm leading-6 text-amber-950">Do not block Wi-Fi changes by default. If the device moves between school networks, blocking Wi-Fi changes may prevent it from reconnecting and synchronising.</p><h3 className="mt-6 text-sm font-semibold text-slate-900">Privacy and capture restrictions</h3><div className="mt-3 grid gap-3 sm:grid-cols-2"><Toggle label="Disable screenshots" checked={deviceRestrictions.disableScreenshots} onChange={(value) => setDeviceRestrictions((current) => ({ ...current, disableScreenshots: value }))} /><Toggle label="Disable screen recording" checked={deviceRestrictions.disableScreenRecording} onChange={(value) => setDeviceRestrictions((current) => ({ ...current, disableScreenRecording: value }))} /><Toggle label="Disable camera" checked={deviceRestrictions.disableCamera} onChange={(value) => setDeviceRestrictions((current) => ({ ...current, disableCamera: value }))} /><Toggle label="Disable microphone" checked={deviceRestrictions.disableMicrophone} onChange={(value) => setDeviceRestrictions((current) => ({ ...current, disableMicrophone: value }))} /></div><p className="mt-4 rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-700">EDUGD does not read private photographs, messages, recordings, contacts, location, or browsing history. These controls change device availability only; they do not collect learner content.</p></Panel>
      <Panel title="Screen-lock policy"><p className="text-sm text-slate-600">For shared school tablets, this protects the device after inactivity without requiring each learner to use a personal password.</p><div className="mt-4 grid gap-3 sm:grid-cols-2"><Toggle label="Require a device screen lock" checked={screenLock.requireScreenLock} onChange={(value) => setScreenLock((current) => ({ ...current, requireScreenLock: value }))} /><Toggle label="Allow biometric unlock" checked={screenLock.allowBiometricUnlock} onChange={(value) => setScreenLock((current) => ({ ...current, allowBiometricUnlock: value }))} /><Toggle label="Allow learner to change the lock method" checked={screenLock.allowLearnerChangeLockMethod} onChange={(value) => setScreenLock((current) => ({ ...current, allowLearnerChangeLockMethod: value }))} /></div><Field label="Automatic lock after inactivity"><select value={screenLock.automaticLockAfterMinutes} onChange={(event) => setScreenLock((current) => ({ ...current, automaticLockAfterMinutes: Number(event.target.value) }))} className="input mt-2"><option value="1">1 minute</option><option value="5">5 minutes</option><option value="10">10 minutes</option><option value="15">15 minutes</option><option value="30">30 minutes</option><option value="60">60 minutes</option></select></Field><p className="mt-4 rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-700">The recommended minimum complexity is basic. EDUGD does not choose or collect a learner’s credential.</p></Panel>
      <Panel title="Compliance rules"><p className="text-sm text-slate-600">Choose the device checks EDUGD should report. These checks are evidence about device state; a missed synchronisation creates a connection review, not an automatic policy failure.</p><div className="mt-4 grid gap-3 sm:grid-cols-2"><Toggle label="Device is enrolled" checked={complianceSettings.deviceEnrolled} onChange={(value) => setComplianceSettings((current) => ({ ...current, deviceEnrolled: value }))} /><Toggle label="EDUGD DPC is active" checked={complianceSettings.dpcActive} onChange={(value) => setComplianceSettings((current) => ({ ...current, dpcActive: value }))} /><Toggle label="Correct policy version is installed" checked={complianceSettings.policyVersionCurrent} onChange={(value) => setComplianceSettings((current) => ({ ...current, policyVersionCurrent: value }))} /><Toggle label="Approved learning application is installed" checked={complianceSettings.approvedLearningApplicationInstalled} onChange={(value) => setComplianceSettings((current) => ({ ...current, approvedLearningApplicationInstalled: value }))} /><Toggle label="Kiosk mode is active" checked={complianceSettings.kioskModeActive} onChange={(value) => setComplianceSettings((current) => ({ ...current, kioskModeActive: value }))} /><Toggle label="Unknown-source installation is blocked" checked={complianceSettings.unknownSourcesBlocked} onChange={(value) => setComplianceSettings((current) => ({ ...current, unknownSourcesBlocked: value }))} /><Toggle label="Factory-reset restriction is active" checked={complianceSettings.factoryResetRestrictionActive} onChange={(value) => setComplianceSettings((current) => ({ ...current, factoryResetRestrictionActive: value }))} /><Toggle label="Required restrictions are applied" checked={complianceSettings.requiredRestrictionsApplied} onChange={(value) => setComplianceSettings((current) => ({ ...current, requiredRestrictionsApplied: value }))} /></div><div className="mt-5 max-w-xs"><Field label="Mark device for connection review after (days)"><input required type="number" min="1" max="30" value={complianceSettings.connectionReviewAfterDays} onChange={(event) => setComplianceSettings((current) => ({ ...current, connectionReviewAfterDays: Number(event.target.value) }))} className="input mt-2" /></Field></div></Panel>
      <Panel title="Offline policy behaviour"><p className="text-sm text-slate-600">These fail-safe behaviours are fixed for EDUGD devices. A lost connection never removes the last valid controls.</p><div className="mt-4 grid gap-3 sm:grid-cols-2"><label className="flex items-center gap-3 text-sm font-medium text-slate-700"><input type="checkbox" checked disabled />Enforce last valid policy offline</label><label className="flex items-center gap-3 text-sm font-medium text-slate-700"><input type="checkbox" checked disabled />Store local policy copy</label><label className="flex items-center gap-3 text-sm font-medium text-slate-700"><input type="checkbox" checked disabled />Queue events while offline</label><label className="flex items-center gap-3 text-sm font-medium text-slate-700"><input type="checkbox" checked disabled />Apply policy changes after reconnection</label><label className="flex items-center gap-3 text-sm font-medium text-slate-700"><input type="checkbox" checked={false} disabled />Expire policy when offline</label></div><p className="mt-4 rounded-xl bg-emerald-50 p-4 text-sm leading-6 text-emerald-950">Connection review uses the {complianceSettings.connectionReviewAfterDays}-day threshold above. It is an operational follow-up, not policy expiry or automatic failure.</p></Panel>
      <Panel title="Administrator notes"><p className="text-sm text-slate-600">These notes are staff-only policy context. They are retained in the signed policy record and are not displayed to learners or interpreted as device controls.</p><Field label="Policy notes"><textarea value={administratorNotes} onChange={(event) => setAdministratorNotes(event.target.value)} className="input input-comfortable mt-2" maxLength={2000} /></Field><p className="mt-2 text-xs text-slate-500">Maximum 2,000 characters. Use a short acceptable-use notice separately if the school wants to show guidance to learners.</p></Panel>
      <Panel title="Data and privacy settings"><p className="text-sm text-slate-600">EDUGD collects device-management information only. These controls are fixed in the MVP so the policy form cannot configure learner surveillance.</p><div className="mt-4 grid gap-3 sm:grid-cols-2"><label className="flex items-center gap-3 text-sm font-medium text-slate-700"><input type="checkbox" checked disabled />Store device asset number</label><label className="flex items-center gap-3 text-sm font-medium text-slate-700"><input type="checkbox" checked disabled />Store device policy version</label><label className="flex items-center gap-3 text-sm font-medium text-slate-700"><input type="checkbox" checked disabled />Store last synchronisation time</label><label className="flex items-center gap-3 text-sm font-medium text-slate-700"><input type="checkbox" checked disabled />Store compliance result</label><label className="flex items-center gap-3 text-sm font-medium text-slate-700"><input type="checkbox" checked disabled />Store administrative actions</label></div><p className="mt-4 rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-700">EDUGD does not read private learner messages, photographs, contacts or personal files. Learner location, microphone recording, and browsing-history collection are permanently unavailable.</p></Panel>
      <Panel title="URL filtering"><p className="text-sm text-slate-600">Choose validated domains from the persistent Policy management catalogue. New domains are saved to that catalogue for later policies.</p><div className="grid gap-4 sm:grid-cols-2"><Field label="Default action"><select value={webDefaultAction} onChange={(event) => setWebDefaultAction(event.target.value as 'allow' | 'block')} className="input mt-2"><option value="allow">Allow by default</option><option value="block">Block by default</option></select></Field><label className="flex items-center gap-3 pt-7 text-sm font-medium text-slate-700"><input type="checkbox" checked={includeSubdomains} onChange={(event) => setIncludeSubdomains(event.target.checked)} /> Include subdomains in every rule</label></div><Field label={webDefaultAction === 'allow' ? 'Blocked domains' : 'Allowed domains'}><select multiple value={domains.split('\n').filter(Boolean)} onChange={(event) => setDomains(Array.from(event.target.selectedOptions, (option) => option.value).join('\n'))} className="input input-comfortable mt-3 min-h-48">{domainCatalogueQuery.data?.map((domain) => <option key={domain.domain_uuid} value={domain.domain}>{domain.domain} · {domain.category}</option>)}</select></Field><div className="mt-3 flex w-full flex-col gap-3 sm:flex-row"><input value={newDomain} onChange={(event) => setNewDomain(event.target.value)} placeholder="Add a new domain to the catalogue" className="input input-comfortable min-w-0 flex-1" /><button type="button" disabled={!newDomain.trim() || addDomainMutation.isPending} className="min-h-12 shrink-0 rounded-lg border border-slate-300 px-4 text-sm font-semibold disabled:opacity-50" onClick={() => addDomainMutation.mutate()}>Add domain</button></div>{domainCatalogueQuery.isLoading && <p className="mt-2 text-xs text-slate-500">Loading domain catalogue…</p>}{domainCatalogueQuery.isError && <p role="alert" className="mt-2 text-xs text-red-700">The domain catalogue is unavailable; try again before saving.</p>}</Panel>
      <Panel title="Network controls">
        <div className="grid gap-3 sm:grid-cols-2">
          <Toggle label="Allow Wi-Fi" checked={networkSettings.allowWifi} onChange={(value) => setNetworkSettings((current) => ({ ...current, allowWifi: value }))} />
          <label className="flex items-center gap-3 text-sm font-medium text-slate-700"><input type="checkbox" checked={networkSettings.allowMobileData} disabled />Allow mobile data</label>
          <Toggle label="Allow Bluetooth" checked={networkSettings.allowBluetooth} onChange={(value) => setNetworkSettings((current) => ({ ...current, allowBluetooth: value }))} />
          <Toggle label="Allow hotspot creation" checked={networkSettings.allowHotspotCreation} onChange={(value) => setNetworkSettings((current) => ({ ...current, allowHotspotCreation: value }))} />
          <Toggle label="Allow network reset" checked={networkSettings.allowNetworkReset} onChange={(value) => setNetworkSettings((current) => ({ ...current, allowNetworkReset: value }))} />
        </div>
        {!networkSettings.allowWifi && <p role="note" className="mt-4 rounded-xl bg-amber-50 p-4 text-sm">Disabling Wi-Fi requires Android 13 or newer. Devices without another connection will receive updates only after connectivity is restored.</p>}
        <p role="note" className="mt-4 rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-700">Mobile data remains allowed in this MVP because standard Android device-owner APIs cannot switch it off. A carrier or OEM integration is required for that control.</p>
        <p className="mt-4 rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-700">The device will continue enforcing the last valid policy when it cannot connect to the EDUGD server. Policy changes and device reports will be synchronised when connectivity returns.</p>
      </Panel>
      <p className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-700">MVP scope: learner location controls, browsing-history collection, parent accounts, learner-specific policies, disciplinary automation, and advanced application distribution are not available. Emergency calling remains preserved.</p>
      {error && <p role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}
      <button type="submit" disabled={mutation.isPending} className="w-fit rounded-full bg-emerald-700 px-6 py-3 font-semibold text-white disabled:opacity-60">Preview policy</button>
    </form><aside className="rounded-2xl border border-emerald-200 bg-[#eaf4e3] p-5 shadow-sm"><p className="text-xs font-bold uppercase tracking-[.16em] text-emerald-800">Policy preview</p><h2 className="mt-2 text-xl font-semibold">{name || 'Untitled policy'}</h2><dl className="mt-5 space-y-3 text-sm"><Summary label="Policy code" value={policyCode || 'Not set'} /><Summary label="Policy type" value={policyType === 'examination' ? 'Examination device' : 'Learning device'} /><Summary label="Status" value="Draft" /><Summary label="Version" value="1 (generated on save)" /><Summary label="Applies to" value={appliesTo === 'selected_classes' ? 'Selected classes' : appliesTo === 'department' ? 'Department' : 'Selected devices'} /><Summary label="Effective date" value={effectiveDate || 'Not set'} /><Summary label="Device-use mode" value={selectedMode.label} /><Summary label="Kiosk mode" value={kioskModeEnabled ? 'Enabled' : 'Disabled'} /><Summary label="Approved applications" value={String(selectedApplications.length)} /><Summary label="Required applications" value={String(selectedApplications.filter((application) => application.required).length)} /><Summary label="Other app installation" value={applicationControls.allowInstallationOfOtherApplications ? 'Allowed' : 'Blocked'} /><Summary label="Google Play Store" value={applicationControls.allowGooglePlayStore ? 'Allowed' : 'Blocked'} /><Summary label="Factory reset" value={deviceRestrictions.blockFactoryReset ? 'Blocked' : 'Allowed'} /><Summary label="Wi-Fi changes" value={deviceRestrictions.blockWifiChanges ? 'Blocked' : 'Allowed'} /><Summary label="Screen lock" value={screenLock.requireScreenLock ? `${screenLock.automaticLockAfterMinutes} minutes` : 'Not required'} /><Summary label="Biometric unlock" value={screenLock.allowBiometricUnlock ? 'Allowed' : 'Blocked'} /><Summary label="Camera" value={deviceRestrictions.disableCamera ? 'Disabled' : 'Allowed'} /><Summary label="Emergency calls" value="Preserved" /></dl><p className="mt-5 border-t border-emerald-200 pt-4 text-xs leading-5 text-slate-600">No DPC connection is required to author or save this policy. Device evidence appears after enrollment and check-in.</p></aside>
    {previewOpen && <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-slate-950/50 p-4" role="dialog" aria-modal="true" aria-labelledby="policy-preview-title"><section className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl"><div className="flex items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[.16em] text-emerald-700">Before saving</p><h2 id="policy-preview-title" className="mt-2 text-2xl font-semibold">{name || 'Untitled policy'}</h2><p className="mt-2 text-sm text-slate-600">Review the canonical policy summary before creating revision 1.</p></div><button type="button" onClick={() => setPreviewOpen(false)} className="rounded-full px-3 py-1 text-sm font-semibold text-slate-600">Cancel</button></div><div className="mt-6 grid gap-6 md:grid-cols-2"><div><h3 className="font-semibold">Policy</h3><dl className="mt-3 space-y-2 text-sm"><Summary label="Code" value={policyCode} /><Summary label="Version" value="1" /><Summary label="Type" value={selectedMode.label} /><Summary label="Approved applications" value={String(selectedApplications.length)} /></dl><h3 className="mt-6 font-semibold">Approved applications</h3><ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-700">{selectedApplications.map((application) => <li key={application.application_uuid}>{application.display_name} <span className="font-mono text-xs">({application.package_name})</span></li>)}</ul></div><div><h3 className="font-semibold">Enabled controls</h3><ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-700">{kioskModeEnabled && <li>Kiosk mode</li>}{!applicationControls.allowInstallationFromUnknownSources && <li>Block unknown application installation</li>}{deviceRestrictions.blockFactoryReset && <li>Block factory reset</li>}{deviceRestrictions.blockSafeMode && <li>Block Safe Mode</li>}{deviceRestrictions.blockAccountChanges && <li>Block account changes</li>}{deviceRestrictions.blockUsbFileTransfer && <li>Block USB file transfer</li>}</ul><h3 className="mt-6 font-semibold">Allowed</h3><ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-700"><li>{deviceRestrictions.disableScreenshots ? 'Screenshots disabled' : 'Screenshots allowed'}</li><li>{deviceRestrictions.disableCamera ? 'Camera disabled' : 'Camera allowed'}</li><li>{networkSettings.allowWifi ? 'Wi-Fi' : 'Wi-Fi disabled'}</li><li>Mobile data</li></ul></div></div><div className="mt-6 rounded-xl bg-emerald-50 p-4"><h3 className="font-semibold text-emerald-950">Offline behaviour</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-emerald-950"><li>Last valid policy remains active</li><li>Events are queued locally</li><li>Updates synchronise after reconnection</li></ul></div><div className="mt-6 rounded-xl border border-slate-200 p-4"><h3 className="font-semibold">Administrator notes</h3><p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{administratorNotes || 'No notes entered.'}</p></div><div className="mt-6 flex flex-wrap justify-end gap-3"><button type="button" onClick={() => setPreviewOpen(false)} className="rounded-full border border-slate-300 px-5 py-2 text-sm font-semibold text-slate-700">Cancel</button><button type="button" disabled={mutation.isPending} onClick={() => { setPreviewOpen(false); mutation.mutate(false) }} className="rounded-full border border-emerald-700 px-5 py-2 text-sm font-semibold text-emerald-800 disabled:opacity-60">{mutation.isPending ? 'Saving…' : 'Save as draft'}</button><button type="button" disabled={mutation.isPending} onClick={() => { setPreviewOpen(false); setPublishConfirmOpen(true) }} className="rounded-full bg-emerald-700 px-5 py-2 text-sm font-semibold text-white disabled:opacity-60">Save and publish</button></div></section></div>}
    {publishConfirmOpen && <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/50 p-4" role="dialog" aria-modal="true" aria-labelledby="publish-confirm-title"><section className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl"><p className="text-xs font-bold uppercase tracking-[.16em] text-amber-700">Publish confirmation</p><h2 id="publish-confirm-title" className="mt-2 text-2xl font-semibold">Publish {name || 'this policy'}?</h2><p className="mt-4 text-sm leading-6 text-slate-700">This policy will be applied to devices assigned to it. Existing devices may change their restrictions after synchronisation. Devices that are offline will receive the policy when they reconnect.</p><dl className="mt-5 space-y-3 rounded-xl bg-amber-50 p-4 text-sm"><Summary label="Policy" value={name || 'Untitled policy'} /><Summary label="Version" value="1" /><Summary label="Devices affected" value={String(affectedDeviceCount)} /></dl><p className="mt-4 text-xs leading-5 text-slate-500">Publishing records the administrator’s confirmation and activates the policy. New or reassigned devices receive it through the normal signed-policy synchronisation path.</p><div className="mt-6 flex justify-end gap-3"><button type="button" onClick={() => setPublishConfirmOpen(false)} className="rounded-full border border-slate-300 px-5 py-2 text-sm font-semibold text-slate-700">Cancel</button><button type="button" disabled={mutation.isPending} onClick={() => { setPublishConfirmOpen(false); mutation.mutate(true) }} className="rounded-full bg-emerald-700 px-5 py-2 text-sm font-semibold text-white disabled:opacity-60">{mutation.isPending ? 'Publishing…' : 'Publish policy'}</button></div></section></div>}
  </section>
}

function Panel({ title, children }: { title: string; children: ReactNode }) { return <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="text-lg font-semibold">{title}</h2><div className="mt-4">{children}</div></section> }
function Field({ label, children }: { label: string; children: ReactNode }) { return <label className="block text-sm font-medium text-slate-700"><span>{label}</span>{children}</label> }
function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) { return <label className="flex items-center gap-3 text-sm font-medium text-slate-700"><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />{label}</label> }
function Summary({ label, value }: { label: string; value: string }) { return <div className="flex items-center justify-between gap-3"><dt className="text-slate-600">{label}</dt><dd className="font-semibold text-slate-950">{value}</dd></div> }
