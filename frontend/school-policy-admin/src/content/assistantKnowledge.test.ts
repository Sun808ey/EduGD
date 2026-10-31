import { describe, expect, it } from 'vitest'
import { answerDocumentationQuestion, assistantKnowledge } from './assistantKnowledge'

describe('attached EduGD Q&A knowledge', () => {
  it('indexes all 180 numbered reference answers', () => {
    const attachedArticles = assistantKnowledge.filter((article) => article.id.startsWith('edugd-qa-'))
    expect(attachedArticles).toHaveLength(180)
    expect(attachedArticles.find((article) => article.id === 'edugd-qa-180')?.title).toBe('What is the short pitch for EduGD?')
  })

  it('uses attached answers as documentation, not executable instructions', () => {
    const answer = answerDocumentationQuestion('What is the short pitch for EduGD?')
    expect(answer?.id).toBe('edugd-qa-180')
    expect(answer?.source).toContain('Question 180')
    expect(answer?.answer).not.toContain('###')
  })
})
