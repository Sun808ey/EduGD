export const supportedLanguages = [
  { code: 'eng', label: 'English' },
  { code: 'ach', label: 'Acholi' },
  { code: 'lgg', label: 'Lugbara' },
  { code: 'teo', label: 'Ateso' },
  { code: 'nyn', label: 'Runyankole' },
  { code: 'lug', label: 'Luganda' },
] as const

export type SupportedLanguage = typeof supportedLanguages[number]['code']
export const defaultLanguage: SupportedLanguage = 'eng'
export const languageStorageKey = 'edug.admin.language'
export const publicLanguageStorageKey = 'edug.public.language'
export const htmlLanguageCodes: Record<SupportedLanguage, string> = {
  eng: 'en',
  ach: 'ach',
  lgg: 'lgg',
  teo: 'teo',
  nyn: 'nyn',
  lug: 'lug',
}

export function isSupportedLanguage(value: string | null): value is SupportedLanguage {
  return supportedLanguages.some((language) => language.code === value)
}
