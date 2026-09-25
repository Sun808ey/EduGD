import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { newsSources } from '@/content/news'
import { NewsPage } from './NewsPage'

describe('NewsPage', () => {
  const renderPage = () => render(<MemoryRouter><NewsPage /></MemoryRouter>)

  it('renders exactly the nine source-linked headlines', () => {
    renderPage()
    expect(screen.getAllByRole('article')).toHaveLength(9)
    newsSources.forEach((source) => {
      expect(screen.getByRole('heading', { name: source.headline })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: `Open ${source.headline} from ${source.sourceName}` })).toHaveAttribute('href', source.sourceUrl)
    })
  })

  it('uses secure external links, accessible images, and the local fallback', () => {
    renderPage()
    screen.getAllByRole('link').forEach((link) => {
      expect(link).toHaveAttribute('target', '_blank')
      expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    })
    expect(screen.getAllByRole('img')).toHaveLength(9)
    expect(screen.getAllByRole('img').every((image) => image.getAttribute('alt')?.length)).toBe(true)
    const firstImage = screen.getAllByRole('img')[0]
    fireEvent.error(firstImage)
    expect(firstImage).toHaveAttribute('src', '/product-visual-placeholder.svg')
  })
})
