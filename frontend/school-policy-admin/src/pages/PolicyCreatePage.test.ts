import { describe, expect, it } from 'vitest'
import { buildPolicyPayload, recommendedComplianceSettings, recommendedDataCollectionSettings, recommendedNetworkSettings, recommendedOfflinePolicySettings } from '@/services/policy-template'

const options = {
  policyCode: 'LEARNING_DEVICE',
  description: 'Controls tablets used for classroom learning activities.',
  emergency: 'io.github.sun808ey.edugd.dpc',
  allowed: 'org.edugd.learning\ncom.google.android.apps.pdfviewer',
  blocked: '',
  limit: '480',
  reset: '0',
  domains: '',
  webDefaultAction: 'allow' as const,
  includeSubdomains: true,
  wifiOnly: true,
  disallowMobileNetworkConfiguration: true,
  disallowTethering: true,
  disallowUserVpn: true,
  alwaysOnFilteringVpn: true,
  vpnLockdownRequired: true,
  disallowOutgoingCalls: true,
  disallowSms: true,
  deviceUseMode: 'dedicated_learning' as const,
  kioskModeEnabled: true,
  displaySchoolName: true,
  supportMessage: 'Contact the ICT office',
  administratorNotes: 'This policy is for normal classroom learning.',
}

describe('policy template device-use mode', () => {
  it('keeps new network permissions and legacy controls consistent', () => {
    const payload = buildPolicyPayload({ ...options, networkSettings: recommendedNetworkSettings })
    expect(payload.network_settings).toEqual({
      allow_wifi: true, allow_mobile_data: true, allow_bluetooth: false,
      allow_hotspot_creation: false, allow_vpn_changes: false, allow_network_reset: false,
    })
    expect(payload.network_controls).toMatchObject({ wifi_only: false, disallow_tethering: true, disallow_user_vpn: true })
    expect(payload.required_capabilities).toContain('network_settings')
    const relaxed = buildPolicyPayload({ ...options, networkSettings: { ...recommendedNetworkSettings, allowWifi: false, allowHotspotCreation: true, allowVpnChanges: true } })
    expect(relaxed.network_controls).toMatchObject({ wifi_only: false, disallow_tethering: false, disallow_user_vpn: false })
    expect(relaxed.required_capabilities).toContain('wifi_state_control')
  })

  it('serializes the selected compliance checks and connection-review threshold', () => {
    const payload = buildPolicyPayload({ ...options, complianceSettings: recommendedComplianceSettings })

    expect(payload.compliance_settings).toEqual({
      device_enrolled: true,
      dpc_active: true,
      policy_version_current: true,
      approved_learning_application_installed: true,
      kiosk_mode_active: true,
      unknown_sources_blocked: true,
      factory_reset_restriction_active: true,
      required_restrictions_applied: true,
      connection_review_after_days: 3,
    })
    expect(buildPolicyPayload({ ...options, offlineSettings: recommendedOfflinePolicySettings }).offline_settings).toEqual({
      enforce_last_valid_policy_offline: true,
      store_local_policy_copy: true,
      queue_events_while_offline: true,
      apply_policy_changes_after_reconnection: true,
      expire_policy_when_offline: false,
    })
    expect(buildPolicyPayload(options).administrator_notes).toBe('This policy is for normal classroom learning.')
    expect(buildPolicyPayload({ ...options, dataCollectionSettings: recommendedDataCollectionSettings }).data_collection_settings).toEqual({
      store_device_asset_number: true,
      store_device_policy_version: true,
      store_last_synchronisation_time: true,
      store_compliance_result: true,
      store_administrative_actions: true,
      collect_learner_location: false,
      read_private_messages: false,
      read_photographs: false,
      record_microphone: false,
      store_browsing_history: false,
    })
  })

  it('serializes the dedicated learning defaults for backend validation', () => {
    const payload = buildPolicyPayload(options)
    expect(payload.policy_code).toBe('LEARNING_DEVICE')
    expect(payload.description).toBe('Controls tablets used for classroom learning activities.')
    const deviceUse = payload.device_use as Record<string, unknown>
    const modes = payload.modes as Array<Record<string, unknown>>

    expect(payload.schedules).toEqual([{ schedule_id: 'school_timetable', days: [1, 2, 3, 4, 5], start_minute: 480, end_minute: 960, mode_id: 'learning', priority: 1 }])
    expect(payload).not.toHaveProperty('allowed_start_time')
    expect(payload).not.toHaveProperty('allowed_end_time')
    expect(payload).not.toHaveProperty('allowed_days')
    expect(payload).not.toHaveProperty('lock_outside_hours')
    expect(deviceUse).toEqual({
      mode: 'dedicated_learning',
      kiosk_mode_enabled: true,
      display_school_name: true,
      school_name: null,
      support_message: 'Contact the ICT office',
    })
    expect(payload.default_mode).toBe('learning')
    expect(modes[0].lock_task_packages).toEqual(modes[0].allowed_packages)
    expect(modes[1].lock_task_packages).toEqual(modes[1].allowed_packages)
  })

  it('removes lock-task packages when kiosk mode is disabled', () => {
    const payload = buildPolicyPayload({ ...options, kioskModeEnabled: false })
    const modes = payload.modes as Array<Record<string, unknown>>

    expect(modes.every((mode) => (mode.lock_task_packages as unknown[]).length === 0)).toBe(true)
  })

  it('serializes approved applications into the allowlist and kiosk packages', () => {
    const payload = buildPolicyPayload({
      ...options,
      approvedApplications: [
        {
          application_uuid: '11111111-1111-4111-8111-111111111111',
          display_name: 'Learning app',
          package_name: 'org.example.learning',
          application_type: 'learning_application',
          required: true,
          allow_in_kiosk: true,
        },
        {
          application_uuid: '22222222-2222-4222-8222-222222222222',
          display_name: 'Teacher browser',
          package_name: 'org.example.browser',
          application_type: 'approved_browser',
          required: false,
          allow_in_kiosk: false,
        },
      ],
    })
    const modes = payload.modes as Array<Record<string, unknown>>

    expect(payload.approved_applications).toHaveLength(2)
    expect(modes[0].allowed_packages).toEqual([
      'io.github.sun808ey.edugd.dpc',
      'org.example.learning',
      'org.example.browser',
    ])
    expect(modes[0].lock_task_packages).toEqual([
      'io.github.sun808ey.edugd.dpc',
      'org.example.learning',
    ])
  })

  it('serializes the locked-down application restriction defaults', () => {
    const payload = buildPolicyPayload({
      ...options,
      applicationControls: {
        allowInstallationOfOtherApplications: false,
        allowInstallationFromUnknownSources: false,
        allowUninstallOfApprovedApplications: false,
        allowDisableOfApprovedApplications: false,
        allowGooglePlayStore: false,
        allowFileSharingApplications: false,
      },
    })

    expect(payload.application_controls).toEqual({
      allow_installation_of_other_applications: false,
      allow_installation_from_unknown_sources: false,
      allow_uninstall_of_approved_applications: false,
      allow_disable_of_approved_applications: false,
      allow_google_play_store: false,
      allow_file_sharing_applications: false,
    })
    expect(payload.required_capabilities).toContain('application_restrictions')
  })

  it('serializes the Iteration 4 device restriction defaults', () => {
    const payload = buildPolicyPayload({
      ...options,
      deviceRestrictions: {
        blockFactoryReset: true,
        blockSafeMode: true,
        blockDeveloperOptionsAndDebugging: true,
        blockUsbFileTransfer: true,
        blockAccountChanges: true,
        blockUserSwitching: true,
        blockNetworkReset: false,
        blockWifiChanges: false,
        disableScreenshots: false,
        disableScreenRecording: false,
        disableCamera: false,
        disableMicrophone: false,
        disableLocation: false,
      },
    })

    expect(payload.device_restrictions).toEqual({
      block_factory_reset: true,
      block_safe_mode: true,
      block_developer_options_and_debugging: true,
      block_usb_file_transfer: true,
      block_account_changes: true,
      block_user_switching: true,
      block_network_reset: false,
      block_wifi_changes: false,
      disable_screenshots: false,
      disable_screen_recording: false,
      disable_camera: false,
      disable_microphone: false,
      disable_location: false,
    })
    expect(payload.required_capabilities).toContain('device_restrictions')
  })

  it('serializes the recommended screen-lock policy', () => {
    const payload = buildPolicyPayload({
      ...options,
      screenLock: {
        requireScreenLock: true,
        automaticLockAfterMinutes: 5,
        allowBiometricUnlock: false,
        allowLearnerChangeLockMethod: false,
      },
    })

    expect(payload.screen_lock).toEqual({
      require_screen_lock: true,
      automatic_lock_after_minutes: 5,
      allow_biometric_unlock: false,
      allow_learner_change_lock_method: false,
    })
    expect(payload.required_capabilities).toContain('screen_lock')
  })
})
