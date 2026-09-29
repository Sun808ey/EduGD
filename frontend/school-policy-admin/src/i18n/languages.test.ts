import { describe, expect, it } from 'vitest'
import { defaultLanguage, isSupportedLanguage, supportedLanguages } from './languages'
import { translations } from './translations'

describe('administrator languages', () => {
  it('keeps English as the default and exposes the approved language set', () => {
    expect(defaultLanguage).toBe('eng')
    expect(supportedLanguages.map((language) => language.code)).toEqual(['eng', 'ach', 'lgg', 'teo', 'nyn', 'lug'])
  })

  it('rejects invalid persisted language values', () => {
    expect(isSupportedLanguage('lug')).toBe(true)
    expect(isSupportedLanguage('fra')).toBe(false)
    expect(isSupportedLanguage(null)).toBe(false)
  })

  it('keeps every translated key available with English fallback values', () => {
    const keys = Object.keys(translations.eng)
    for (const language of supportedLanguages) {
      expect(Object.keys(translations[language.code])).toEqual(keys)
    }
  })
})
