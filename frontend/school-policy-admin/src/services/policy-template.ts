export type DeviceUseMode = 'normal_managed' | 'dedicated_learning' | 'examination'

export type ApplicationType =
  | 'learning_application'
  | 'digital_textbook'
  | 'pdf_reader'
  | 'calculator'
  | 'approved_browser'
  | 'accessibility_application'
  | 'other_approved_application'

export type ApprovedApplicationSelection = {
  application_uuid: string
  display_name: string
  package_name: string
  application_type: ApplicationType
  required: boolean
  allow_in_kiosk: boolean
}

export type ApplicationRestrictionOptions = {
  allowInstallationOfOtherApplications: boolean
  allowInstallationFromUnknownSources: boolean
  allowUninstallOfApprovedApplications: boolean
  allowDisableOfApprovedApplications: boolean
  allowGooglePlayStore: boolean
  allowFileSharingApplications: boolean
}

export type DeviceRestrictionOptions = {
  blockFactoryReset: boolean
  blockSafeMode: boolean
  blockDeveloperOptionsAndDebugging: boolean
  blockUsbFileTransfer: boolean
  blockAccountChanges: boolean
  blockUserSwitching: boolean
  blockNetworkReset: boolean
  blockWifiChanges: boolean
  disableScreenshots: boolean
  disableScreenRecording: boolean
  disableCamera: boolean
  disableMicrophone: boolean
  disableLocation: boolean
}

export type ScreenLockOptions = {
  requireScreenLock: boolean
  automaticLockAfterMinutes: number
  allowBiometricUnlock: boolean
  allowLearnerChangeLockMethod: boolean
}

export type NetworkSettings = {
  allowWifi: boolean
  allowMobileData: boolean
  allowBluetooth: boolean
  allowHotspotCreation: boolean
  allowVpnChanges: boolean
  allowNetworkReset: boolean
}

export type ComplianceSettings = {
  deviceEnrolled: boolean
  dpcActive: boolean
  policyVersionCurrent: boolean
  approvedLearningApplicationInstalled: boolean
  kioskModeActive: boolean
  unknownSourcesBlocked: boolean
  factoryResetRestrictionActive: boolean
  requiredRestrictionsApplied: boolean
  connectionReviewAfterDays: number
}

export type OfflinePolicySettings = {
  enforceLastValidPolicyOffline: true
  storeLocalPolicyCopy: true
  queueEventsWhileOffline: true
  applyPolicyChangesAfterReconnection: true
  expirePolicyWhenOffline: false
}

export type RecurringSchedule = {
  timezone?: string
  days: number[]
  startMinute: number
  endMinute: number
  modeId: string
  priority: number
}

export type DataCollectionSettings = {
  storeDeviceAssetNumber: true
  storeDevicePolicyVersion: true
  storeLastSynchronisationTime: true
  storeComplianceResult: true
  storeAdministrativeActions: true
  collectLearnerLocation: false
  readPrivateMessages: false
  readPhotographs: false
  recordMicrophone: false
  storeBrowsingHistory: false
}

export const recommendedNetworkSettings: NetworkSettings = {
  allowWifi: true,
  allowMobileData: true,
  allowBluetooth: false,
  allowHotspotCreation: false,
  allowVpnChanges: false,
  allowNetworkReset: false,
}

export const recommendedComplianceSettings: ComplianceSettings = {
  deviceEnrolled: true,
  dpcActive: true,
  policyVersionCurrent: true,
  approvedLearningApplicationInstalled: true,
  kioskModeActive: true,
  unknownSourcesBlocked: true,
  factoryResetRestrictionActive: true,
  requiredRestrictionsApplied: true,
  connectionReviewAfterDays: 3,
}

export const recommendedOfflinePolicySettings: OfflinePolicySettings = {
  enforceLastValidPolicyOffline: true,
  storeLocalPolicyCopy: true,
  queueEventsWhileOffline: true,
  applyPolicyChangesAfterReconnection: true,
  expirePolicyWhenOffline: false,
}

export const recommendedDataCollectionSettings: DataCollectionSettings = {
  storeDeviceAssetNumber: true,
  storeDevicePolicyVersion: true,
  storeLastSynchronisationTime: true,
  storeComplianceResult: true,
  storeAdministrativeActions: true,
  collectLearnerLocation: false,
  readPrivateMessages: false,
  readPhotographs: false,
  recordMicrophone: false,
  storeBrowsingHistory: false,
}

const split = (value: string) => value.split('\n').map((item) => item.trim()).filter(Boolean)

export type PolicyPayloadOptions = {
  policyCode?: string
  description?: string
  emergency: string
  allowed: string
  blocked: string
  blockedPackages?: string[]
  limit: string
  reset: string
  domains: string
  webDefaultAction: 'allow' | 'block'
  includeSubdomains: boolean
  wifiOnly: boolean
  disallowMobileNetworkConfiguration: boolean
  disallowTethering: boolean
  disallowUserVpn: boolean
  alwaysOnFilteringVpn: boolean
  vpnLockdownRequired: boolean
  disallowOutgoingCalls: boolean
  disallowSms: boolean
  deviceUseMode: DeviceUseMode
  kioskModeEnabled: boolean
  displaySchoolName: boolean
  supportMessage: string
  approvedApplications?: ApprovedApplicationSelection[]
  applicationControls?: ApplicationRestrictionOptions
  deviceRestrictions?: DeviceRestrictionOptions
  screenLock?: ScreenLockOptions
  networkSettings?: NetworkSettings
  complianceSettings?: ComplianceSettings
  offlineSettings?: OfflinePolicySettings
  administratorNotes?: string
  dataCollectionSettings?: DataCollectionSettings
  schedule?: RecurringSchedule
}

const modeIds: Record<DeviceUseMode, string> = {
  normal_managed: 'normal',
  dedicated_learning: 'learning',
  examination: 'examination',
}

export function buildPolicyPayload(options: PolicyPayloadOptions): Record<string, unknown> {
  const schedule = options.schedule ?? { timezone: 'Africa/Kampala', days: [1, 2, 3, 4, 5], startMinute: 480, endMinute: 960, modeId: modeIds[options.deviceUseMode], priority: 1 }
  const emergencyPackages = split(options.emergency)
  const selectedPackages = options.approvedApplications?.map((application) => application.package_name) ?? split(options.allowed)
  const primaryPackages = [...new Set([...emergencyPackages, ...selectedPackages])]
  const primaryModeId = modeIds[options.deviceUseMode]
  const controls = {
    camera_disabled: options.deviceRestrictions?.disableCamera ?? false,
    screen_capture_disabled: (options.deviceRestrictions?.disableScreenshots ?? false) || (options.deviceRestrictions?.disableScreenRecording ?? false),
    unknown_sources_disabled: true,
    factory_reset_disabled: options.deviceRestrictions?.blockFactoryReset ?? true,
    safe_boot_disabled: options.deviceRestrictions?.blockSafeMode ?? true,
    add_users_disabled: false,
    account_changes_disabled: options.deviceRestrictions?.blockAccountChanges ?? false,
    usb_file_transfer_disabled: options.deviceRestrictions?.blockUsbFileTransfer ?? false,
  }
  const mode = (modeId: string, allowedPackages: string[]) => ({
    mode_id: modeId,
    application_mode: 'allowlist',
    allowed_packages: allowedPackages,
    blocked_packages: options.blockedPackages ?? split(options.blocked),
    lock_task_packages: options.kioskModeEnabled
      ? options.approvedApplications
        ? [...new Set([...emergencyPackages, ...options.approvedApplications.filter((application) => application.allow_in_kiosk).map((application) => application.package_name)])]
        : allowedPackages
      : [],
    user_restrictions: [],
    device_controls: controls,
  })

  return {
    ...(options.policyCode?.trim() ? { policy_code: options.policyCode.trim() } : {}),
    ...(options.description?.trim() ? { description: options.description.trim() } : {}),
    schema_version: 3,
    timezone: schedule.timezone ?? 'Africa/Kampala',
    refresh_after_seconds: 3600,
    default_mode: primaryModeId,
    emergency_packages: emergencyPackages,
    required_capabilities: ['screen_time', 'web_filter', 'app_visibility', ...(options.applicationControls ? ['application_restrictions'] : []), ...(options.deviceRestrictions ? ['device_restrictions'] : []), ...(options.networkSettings ? ['network_settings', ...(!options.networkSettings.allowWifi ? ['wifi_state_control'] : [])] : []), ...(options.screenLock ? ['screen_lock'] : []), ...(options.kioskModeEnabled ? ['lock_task'] : [])],
    minimum_dpc_version: 1,
    modes: [mode(primaryModeId, primaryPackages), mode('restricted', emergencyPackages)],
    schedules: [{ schedule_id: 'school_timetable', days: schedule.days, start_minute: schedule.startMinute, end_minute: schedule.endMinute, mode_id: schedule.modeId, priority: schedule.priority }],
    screen_time: { daily_limit_minutes: Number(options.limit), reset_minute: Number(options.reset), exhausted_mode_id: 'restricted' },
    web_filter: {
      default_action: options.webDefaultAction,
      rules: split(options.domains).map((domain, index) => ({
        rule_id: `rule_${index + 1}`,
        domain,
        include_subdomains: options.includeSubdomains,
        action: options.webDefaultAction === 'block' ? 'allow' : 'block',
        reason: 'School policy',
      })),
    },
    network_controls: {
      wifi_only: options.networkSettings ? false : options.wifiOnly,
      disallow_mobile_network_configuration: options.disallowMobileNetworkConfiguration,
      disallow_tethering: options.networkSettings ? !options.networkSettings.allowHotspotCreation : options.disallowTethering,
      disallow_user_vpn: options.networkSettings ? !options.networkSettings.allowVpnChanges : options.disallowUserVpn,
      always_on_filtering_vpn: options.alwaysOnFilteringVpn,
      vpn_lockdown_required: options.vpnLockdownRequired,
    },
    telephony_controls: {
      disallow_outgoing_calls: options.disallowOutgoingCalls,
      disallow_sms: options.disallowSms,
      preserve_emergency_calls: true,
    },
    ...(options.approvedApplications ? { approved_applications: options.approvedApplications } : {}),
    ...(options.applicationControls ? {
      application_controls: {
        allow_installation_of_other_applications: options.applicationControls.allowInstallationOfOtherApplications,
        allow_installation_from_unknown_sources: options.applicationControls.allowInstallationFromUnknownSources,
        allow_uninstall_of_approved_applications: options.applicationControls.allowUninstallOfApprovedApplications,
        allow_disable_of_approved_applications: options.applicationControls.allowDisableOfApprovedApplications,
        allow_google_play_store: options.applicationControls.allowGooglePlayStore,
        allow_file_sharing_applications: options.applicationControls.allowFileSharingApplications,
      },
    } : {}),
    ...(options.deviceRestrictions ? {
      device_restrictions: {
        block_factory_reset: options.deviceRestrictions.blockFactoryReset,
        block_safe_mode: options.deviceRestrictions.blockSafeMode,
        block_developer_options_and_debugging: options.deviceRestrictions.blockDeveloperOptionsAndDebugging,
        block_usb_file_transfer: options.deviceRestrictions.blockUsbFileTransfer,
        block_account_changes: options.deviceRestrictions.blockAccountChanges,
        block_user_switching: options.deviceRestrictions.blockUserSwitching,
        block_network_reset: options.networkSettings ? !options.networkSettings.allowNetworkReset : options.deviceRestrictions.blockNetworkReset,
        block_wifi_changes: options.deviceRestrictions.blockWifiChanges,
        disable_screenshots: options.deviceRestrictions.disableScreenshots,
        disable_screen_recording: options.deviceRestrictions.disableScreenRecording,
        disable_camera: options.deviceRestrictions.disableCamera,
        disable_microphone: options.deviceRestrictions.disableMicrophone,
        disable_location: options.deviceRestrictions.disableLocation,
      },
    } : {}),
    ...(options.screenLock ? {
      screen_lock: {
        require_screen_lock: options.screenLock.requireScreenLock,
        automatic_lock_after_minutes: options.screenLock.automaticLockAfterMinutes,
        allow_biometric_unlock: options.screenLock.allowBiometricUnlock,
        allow_learner_change_lock_method: options.screenLock.allowLearnerChangeLockMethod,
      },
    } : {}),
    ...(options.networkSettings ? {
      network_settings: {
        allow_wifi: options.networkSettings.allowWifi,
        allow_mobile_data: options.networkSettings.allowMobileData,
        allow_bluetooth: options.networkSettings.allowBluetooth,
        allow_hotspot_creation: options.networkSettings.allowHotspotCreation,
        allow_vpn_changes: options.networkSettings.allowVpnChanges,
        allow_network_reset: options.networkSettings.allowNetworkReset,
      },
    } : {}),
    ...(options.complianceSettings ? {
      compliance_settings: {
        device_enrolled: options.complianceSettings.deviceEnrolled,
        dpc_active: options.complianceSettings.dpcActive,
        policy_version_current: options.complianceSettings.policyVersionCurrent,
        approved_learning_application_installed: options.complianceSettings.approvedLearningApplicationInstalled,
        kiosk_mode_active: options.complianceSettings.kioskModeActive,
        unknown_sources_blocked: options.complianceSettings.unknownSourcesBlocked,
        factory_reset_restriction_active: options.complianceSettings.factoryResetRestrictionActive,
        required_restrictions_applied: options.complianceSettings.requiredRestrictionsApplied,
        connection_review_after_days: options.complianceSettings.connectionReviewAfterDays,
      },
    } : {}),
    ...(options.offlineSettings ? {
      offline_settings: {
        enforce_last_valid_policy_offline: options.offlineSettings.enforceLastValidPolicyOffline,
        store_local_policy_copy: options.offlineSettings.storeLocalPolicyCopy,
        queue_events_while_offline: options.offlineSettings.queueEventsWhileOffline,
        apply_policy_changes_after_reconnection: options.offlineSettings.applyPolicyChangesAfterReconnection,
        expire_policy_when_offline: options.offlineSettings.expirePolicyWhenOffline,
      },
    } : {}),
    ...(options.administratorNotes?.trim() ? { administrator_notes: options.administratorNotes.trim() } : {}),
    ...(options.dataCollectionSettings ? {
      data_collection_settings: {
        store_device_asset_number: options.dataCollectionSettings.storeDeviceAssetNumber,
        store_device_policy_version: options.dataCollectionSettings.storeDevicePolicyVersion,
        store_last_synchronisation_time: options.dataCollectionSettings.storeLastSynchronisationTime,
        store_compliance_result: options.dataCollectionSettings.storeComplianceResult,
        store_administrative_actions: options.dataCollectionSettings.storeAdministrativeActions,
        collect_learner_location: options.dataCollectionSettings.collectLearnerLocation,
        read_private_messages: options.dataCollectionSettings.readPrivateMessages,
        read_photographs: options.dataCollectionSettings.readPhotographs,
        record_microphone: options.dataCollectionSettings.recordMicrophone,
        store_browsing_history: options.dataCollectionSettings.storeBrowsingHistory,
      },
    } : {}),
    device_use: {
      mode: options.deviceUseMode,
      kiosk_mode_enabled: options.kioskModeEnabled,
      display_school_name: options.displaySchoolName,
      school_name: null,
      support_message: options.supportMessage.trim(),
    },
  }
}
