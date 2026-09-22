import { beforeEach, describe, expect, it, vi } from 'vitest'
import { publicHealthService } from '@/services/public-health.service'

describe('public health service', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('reports healthy and ready endpoints', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: 'ok', service: 'API' }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: 'ok', service: 'API' }), { status: 200 }))

    await expect(publicHealthService.checkHealth()).resolves.toMatchObject({
      status: 'running',
      service: 'API',
      detail: 'API process is responding',
    })
    await expect(publicHealthService.checkReadiness()).resolves.toMatchObject({
      status: 'ready',
      service: 'API',
      detail: 'Ready for authenticated administration',
    })
    expect(fetch).toHaveBeenNthCalledWith(1, expect.stringContaining('/health'), expect.anything())
    expect(fetch).toHaveBeenNthCalledWith(2, expect.stringContaining('/ready'), expect.anything())
  })

  it('reports an unhealthy response and network failure without throwing', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({}), { status: 503 }))
      .mockRejectedValueOnce(new Error('offline'))

    await expect(publicHealthService.checkReadiness()).resolves.toMatchObject({
      status: 'not_ready',
      service: 'EduGuard API',
      detail: 'API is responding but not ready',
    })
    await expect(publicHealthService.checkHealth()).resolves.toMatchObject({
      status: 'unavailable',
      service: 'EduGuard API',
      detail: 'The local or hosted API could not be reached',
    })
  })

  it('aborts an in-flight request when the caller aborts', async () => {
    let requestSignal: AbortSignal | undefined
    vi.spyOn(globalThis, 'fetch').mockImplementation((_input, init) => {
      requestSignal = init?.signal as AbortSignal
      return new Promise(() => undefined)
    })
    const controller = new AbortController()
    const request = publicHealthService.checkHealth(controller.signal)
    controller.abort()

    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(requestSignal?.aborted).toBe(true)
    expect(request).toBeInstanceOf(Promise)
  })
})