import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { expect, test } from 'vitest'
import { LandingPage } from '@/pages/LandingPage'
import { AboutPage, ArchitecturePage, ContactPage, FeatureDetailPage, FeaturesPage, HowItWorksPage, ProductPage, ResourcesPage, SchoolsPage, SecurityPage } from '@/pages/MarketingPages'
import { MarketingShell } from './MarketingShell'
import { LandingLanguageProvider } from '@/i18n/LandingLanguageContext'

function renderPage(page: React.ReactNode) { return render(<MemoryRouter><LandingLanguageProvider><MarketingShell>{page}</MarketingShell></LandingLanguageProvider></MemoryRouter>) }

test('renders the public homepage and shared marketing shell', () => {
  renderPage(<LandingPage />)
  expect(screen.getByRole('heading', { name: /keep the school day/i })).toBeInTheDocument()
  expect(screen.getAllByText(/academic proof-of-concept/i).length).toBeGreaterThan(0)
  expect(screen.getAllByRole('link', { name: /open admin console/i }).length).toBeGreaterThan(0)
})

test('renders every public page family with its primary content', () => {
  for (const page of [<ProductPage />, <FeaturesPage />, <FeatureDetailPage />, <HowItWorksPage />, <SchoolsPage />, <SecurityPage />, <ArchitecturePage />, <ResourcesPage />, <AboutPage />, <ContactPage />]) {
    const view = renderPage(page)
    expect(view.container.querySelector('h1')).toBeTruthy()
    view.unmount()
  }
})
