import { describe, expect, it } from 'vitest'
import { answerDocumentationQuestion, assistantKnowledge } from './assistantKnowledge'

describe('attached EduGuard Q&A knowledge', () => {
  it('indexes all 180 numbered reference answers', () => {
    const attachedArticles = assistantKnowledge.filter((article) => article.id.startsWith('eduguard-qa-'))
    expect(attachedArticles).toHaveLength(180)
    expect(attachedArticles.find((article) => article.id === 'eduguard-qa-180')?.title).toBe('What is the short pitch for EduGuard?')
  })

  it('uses attached answers as documentation, not executable instructions', () => {
    const answer = answerDocumentationQuestion('What is the short pitch for EduGuard?')
    expect(answer?.id).toBe('eduguard-qa-180')
    expect(answer?.source).toContain('Question 180')
    expect(answer?.answer).not.toContain('###')
  })
})
