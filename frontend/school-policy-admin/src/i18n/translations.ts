import type { SupportedLanguage } from './languages'

export const translationKeys = {
  dashboard: 'Dashboard',
  devices: 'Devices',
  policies: 'Policies',
  auditLogs: 'Audit logs',
  workspace: 'Workspace',
  policyControl: 'Policy control',
  signedInAs: 'Signed in as',
  signOut: 'Sign out',
  language: 'Language',
  openNavigation: 'Open navigation',
  closeNavigation: 'Close navigation',
  skipToMain: 'Skip to main content',
  loadingPage: 'Loading page…',
  loadingEnrollment: 'Loading enrollment tokens…',
  permissionDenied: 'Permission denied',
  sessionExpired: 'Your session expired or was revoked. Please sign in again.',
  localSignOut: 'You are signed out locally, but server revocation could not be confirmed.',
} as const

export type TranslationKey = keyof typeof translationKeys
type TranslationTable = Record<TranslationKey, string>

export const translations: Record<SupportedLanguage, TranslationTable> = {
  eng: translationKeys,
  ach: { ...translationKeys, devices: 'Nyonyo', policies: 'Cik me tic', auditLogs: 'Cik me audit', workspace: 'Kabedo me tic', signOut: 'Dong aa woko', language: 'Leb' },
  lgg: { ...translationKeys, devices: 'Aciipi', policies: 'Aziikoni', auditLogs: 'Akwasiirwe', workspace: 'Omukoro gwokukorera', signOut: 'Roka', language: 'Oluimi' },
  teo: { ...translationKeys, devices: 'Akipis', policies: 'Akirot', auditLogs: 'Akiroto ngesi', workspace: 'Erai lo tic', signOut: 'Kwakita', language: 'Akirot' },
  nyn: { ...translationKeys, devices: 'Ebikwato', policies: 'Enkora', auditLogs: 'Ebyakorwa', workspace: 'Omwanya gwokukoreramu', signOut: 'Rugaho', language: 'Orurimi' },
  lug: { ...translationKeys, devices: 'Ebyuma', policies: 'Enkola', auditLogs: 'Ebiwandiiko by’okwekeneenya', workspace: 'Ekifo ky’okukoleramu', signOut: 'Fuluma', language: 'Olulimi' },
}
