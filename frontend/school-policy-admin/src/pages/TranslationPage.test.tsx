import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TranslationPage } from './TranslationPage'
import { adminService } from '@/services/admin.service'

vi.mock('@/services/admin.service', () => ({ adminService: { translateApprovedDynamicContent: vi.fn() } }))

function renderPage() {
  return render(<QueryClientProvider client={new QueryClient()}><TranslationPage /></QueryClientProvider>)
}

describe('approved-content translation', () => {
  beforeEach(() => vi.clearAllMocks())

  it('submits only approved dynamic content through the Flask service', async () => {
    vi.mocked(adminService.translateApprovedDynamicContent).mockResolvedValue({
      translated_text: 'Oli otya?', source_language: 'eng', target_language: 'lug', cached: false, content_class: 'approved_dynamic', quality_status: 'machine',
    })
    renderPage()
    fireEvent.change(screen.getByLabelText('Approved text'), { target: { value: 'How are you?' } })
    fireEvent.change(screen.getByLabelText('Target language'), { target: { value: 'lug' } })
    fireEvent.click(screen.getByRole('button', { name: /translate approved text/i }))
    await waitFor(() => expect(adminService.translateApprovedDynamicContent).toHaveBeenCalledWith('How are you?', 'lug'))
    expect(await screen.findByRole('heading', { name: 'Translation result' })).toBeInTheDocument()
    expect(screen.getByText('Oli otya?')).toBeInTheDocument()
  })
})
