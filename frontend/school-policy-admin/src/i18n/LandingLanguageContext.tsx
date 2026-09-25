import { useEffect, useMemo, useState, type ReactNode } from 'react'
import api from '@/services/api'
import { defaultLanguage, isSupportedLanguage, publicLanguageStorageKey, type SupportedLanguage } from './languages'
import { LandingContext, type LandingKey } from './landing-language-context'

const publicKeys: LandingKey[] = [
  'header.choose_languages', 'header.open_admin',
  'hero.eyebrow', 'hero.title', 'hero.body', 'hero.capabilities', 'hero.explore', 'hero.admin',
  'capabilities.eyebrow', 'capabilities.title', 'capabilities.body', 'how.eyebrow', 'how.title', 'how.create', 'how.assign', 'how.enforce', 'how.reconcile',
  'context.eyebrow', 'context.title', 'context.body', 'status.eyebrow', 'status.title', 'status.body',
  'product.eyebrow', 'product.title', 'product.intro', 'product.administrators.title', 'product.administrators.text', 'product.devices.title', 'product.devices.text', 'product.evidence.title', 'product.evidence.text',
  'features.eyebrow', 'features.title', 'features.intro',
  'feature.offline-enforcement.title', 'feature.offline-enforcement.intro', 'feature.offline-enforcement.bullet1', 'feature.offline-enforcement.bullet2', 'feature.offline-enforcement.bullet3', 'feature.offline-enforcement.status',
  'feature.policy-management.title', 'feature.policy-management.intro', 'feature.policy-management.bullet1', 'feature.policy-management.bullet2', 'feature.policy-management.bullet3', 'feature.policy-management.status',
  'feature.device-management.title', 'feature.device-management.intro', 'feature.device-management.bullet1', 'feature.device-management.bullet2', 'feature.device-management.bullet3', 'feature.device-management.status',
  'feature.audit-and-forensics.title', 'feature.audit-and-forensics.intro', 'feature.audit-and-forensics.bullet1', 'feature.audit-and-forensics.bullet2', 'feature.audit-and-forensics.bullet3', 'feature.audit-and-forensics.status',
  'feature.security.title', 'feature.security.intro', 'feature.security.bullet1', 'feature.security.bullet2', 'feature.security.bullet3', 'feature.security.status',
  'feature.detail.eyebrow', 'feature.detail.what_this_means',
  'how-page.eyebrow', 'how-page.title', 'how-page.intro', 'how-page.card1', 'how-page.card2', 'how-page.card3', 'how-page.card4', 'how-page.card_body',
  'schools.eyebrow', 'schools.title', 'schools.intro', 'schools.ict.title', 'schools.ict.text', 'schools.leadership.title', 'schools.leadership.text', 'schools.teachers.title', 'schools.teachers.text', 'schools.reviewers.title', 'schools.reviewers.text',
  'security.eyebrow', 'security.title', 'security.intro', 'security.access.title', 'security.access.text', 'security.privacy.title', 'security.privacy.text', 'security.fail_closed.title', 'security.fail_closed.text',
  'architecture.eyebrow', 'architecture.title', 'architecture.intro', 'architecture.administrator', 'architecture.react', 'architecture.flask', 'architecture.database', 'architecture.android', 'architecture.body',
  'resources.eyebrow', 'resources.title', 'resources.intro', 'resources.how', 'resources.how.title', 'resources.architecture', 'resources.architecture.title', 'resources.security', 'resources.security.title', 'resources.about', 'resources.about.title', 'resources.schools', 'resources.schools.title', 'resources.contact', 'resources.contact.title',
  'about.eyebrow', 'about.title', 'about.intro', 'about.body1', 'about.body2',
  'contact.eyebrow', 'contact.title', 'contact.intro', 'contact.body', 'contact.link',
  'common.scope_note_title', 'common.scope_note_body', 'common.open_admin', 'common.capability', 'common.explore_capability',
]
type TranslationMap = Partial<Record<LandingKey, string>>

function storedLanguage(): SupportedLanguage {
  const value = typeof window === 'undefined' ? null : window.localStorage.getItem(publicLanguageStorageKey)
  return isSupportedLanguage(value) ? value : defaultLanguage
}

export function LandingLanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<SupportedLanguage>(storedLanguage)
  const [translatedByLanguage, setTranslatedByLanguage] = useState<Partial<Record<SupportedLanguage, TranslationMap>>>({})

  const setLanguage = (next: SupportedLanguage) => {
    setLanguageState(next)
    window.localStorage.setItem(publicLanguageStorageKey, next)
  }

  useEffect(() => {
    document.documentElement.lang = language === 'eng' ? 'en' : language
    if (language === 'eng' || translatedByLanguage[language]) return
    const controller = new AbortController()
    Promise.all(publicKeys.map(async (content_key) => {
      try {
        const response = await api.post('/public/translation/translate', { content_key, target_language: language }, { signal: controller.signal })
        return [content_key, response.data.translated_text] as const
      } catch {
        return null
      }
    })).then((entries) => {
      if (!controller.signal.aborted) {
        setTranslatedByLanguage((current) => ({ ...current, [language]: Object.fromEntries(entries.filter((entry): entry is readonly [LandingKey, string] => entry !== null)) }))
      }
    })
    return () => controller.abort()
  }, [language, translatedByLanguage])

  const value = useMemo(() => ({
    language,
    setLanguage,
    text: (key: LandingKey, english: string) => translatedByLanguage[language]?.[key] ?? english,
  }), [language, translatedByLanguage])
  return <LandingContext.Provider value={value}>{children}</LandingContext.Provider>
}
