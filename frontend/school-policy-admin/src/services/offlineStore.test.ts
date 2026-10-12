import { beforeEach, describe, expect, it } from 'vitest'
import { countPendingOfflineQueue, createOfflineUuid, enqueueOfflineMutation, flushOfflineQueue, listOfflineQueue, readOfflineCache, updateOfflineQueueItem, writeOfflineCache } from './offlineStore'

describe('offline synchronization store', () => {
  beforeEach(() => {
    window.localStorage.clear()
    Object.defineProperty(navigator, 'onLine', { configurable: true, value: true })
  })

  it('persists local changes and transitions them after a successful send', async () => {
    const marker = `offline-test-${Date.now()}-${Math.random()}`
    const item = await enqueueOfflineMutation({ kind: 'policy_lifecycle', method: 'POST', url: '/admin/policies/test/lifecycle', payload: { marker }, state: 'LOCAL_ONLY' })
    expect(item.state).toBe('LOCAL_ONLY')
    expect((await listOfflineQueue()).some((entry) => entry.id === item.id && entry.payload.marker === marker)).toBe(true)

    await flushOfflineQueue(async () => ({ accepted: true }))
    const updated = (await listOfflineQueue()).find((entry) => entry.id === item.id)
    expect(updated?.state).toBe('SENT_TO_DEVICE')
  })

  it('uses local storage fallback for cache and queue updates', async () => {
    await writeOfflineCache('school', { name: 'Demo school' })
    await expect(readOfflineCache<{ name: string }>('school')).resolves.toEqual({ name: 'Demo school' })
    await expect(updateOfflineQueueItem('missing', { state: 'FAILED' })).resolves.toBeNull()
    const item = await enqueueOfflineMutation({ kind: 'policy_create', method: 'POST', url: '/policies', payload: {}, state: 'PENDING_SYNC' })
    await expect(updateOfflineQueueItem(item.id, { lastError: 'retry later' })).resolves.toMatchObject({ lastError: 'retry later', attempts: 0 })
    expect(await countPendingOfflineQueue()).toBe(1)
    expect(createOfflineUuid()).toMatch(/^[0-9a-f-]{36}$/)
  })

  it('uses indexed db when the browser provides it', async () => {
    type FakeRequest = { result: unknown; onsuccess?: () => void; onerror?: () => void }
    type FakeStore = { get: (key: string) => FakeRequest; getAll: () => FakeRequest; put: (value: unknown, key?: string) => FakeRequest; clear: () => FakeRequest }
    type FakeTransaction = { objectStore: () => FakeStore; oncomplete?: () => void; onerror?: () => void }
    const stores = new Map<string, Map<string, unknown>>()
    const createStore = (name: string): FakeStore => {
      const values = stores.get(name) ?? new Map<string, unknown>()
      stores.set(name, values)
      return {
        get: (key) => {
          const request: FakeRequest = { result: values.get(key) }
          queueMicrotask(() => request.onsuccess?.())
          return request
        },
        getAll: () => {
          const request: FakeRequest = { result: [...values.values()] }
          queueMicrotask(() => request.onsuccess?.())
          return request
        },
        put: (value, key) => {
          values.set(key ?? String((value as { id: string }).id), value)
          const request: FakeRequest = { result: undefined }
          queueMicrotask(() => request.onsuccess?.())
          return request
        },
        clear: () => {
          values.clear()
          const request: FakeRequest = { result: undefined }
          queueMicrotask(() => request.onsuccess?.())
          return request
        },
      }
    }
    const database = {
      objectStoreNames: { contains: (name: string) => stores.has(name) },
      createObjectStore: (name: string) => { stores.set(name, new Map()); return createStore(name) },
      transaction: (name: string) => {
        const transaction: FakeTransaction = { objectStore: () => createStore(name) }
        setTimeout(() => transaction.oncomplete?.(), 0)
        return transaction
      },
    }
    const open = () => {
      const request: FakeRequest & { onupgradeneeded?: () => void; onblocked?: () => void } = { result: database }
      queueMicrotask(() => { request.onupgradeneeded?.(); request.onsuccess?.() })
      return request
    }
    const originalIndexedDb = (globalThis as unknown as { indexedDB?: IDBFactory }).indexedDB
    Object.defineProperty(globalThis, 'indexedDB', { configurable: true, value: { open } as unknown as IDBFactory })
    try {
      await writeOfflineCache('indexed', { enabled: true })
      await expect(readOfflineCache<{ enabled: boolean }>('indexed')).resolves.toEqual({ enabled: true })
      const item = await enqueueOfflineMutation({ kind: 'policy_create', method: 'POST', url: '/indexed', payload: {}, state: 'LOCAL_ONLY' })
      await expect(listOfflineQueue()).resolves.toEqual([item])
    } finally {
      if (originalIndexedDb) Object.defineProperty(globalThis, 'indexedDB', { configurable: true, value: originalIndexedDb })
      else Reflect.deleteProperty(globalThis, 'indexedDB')
    }
  })

  it('records online failures as failed and offline failures as pending', async () => {
    const online = await enqueueOfflineMutation({ kind: 'policy_clear', method: 'POST', url: '/clear', payload: {}, state: 'LOCAL_ONLY' })
    await flushOfflineQueue(async () => { throw new Error('server rejected') })
    expect((await listOfflineQueue()).find((item) => item.id === online.id)).toMatchObject({ state: 'FAILED', attempts: 1, lastError: 'server rejected' })

    Object.defineProperty(navigator, 'onLine', { configurable: true, value: false })
    const offline = await enqueueOfflineMutation({ kind: 'policy_assign', method: 'POST', url: '/assign', payload: {}, state: 'LOCAL_ONLY' })
    await flushOfflineQueue(async () => { throw new Error('connection lost') })
    expect((await listOfflineQueue()).find((item) => item.id === offline.id)).toMatchObject({ state: 'PENDING_SYNC', lastError: 'connection lost' })
  })
})
