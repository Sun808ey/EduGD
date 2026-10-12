export const OFFLINE_SYNC_STATES = ['LOCAL_ONLY', 'PENDING_SYNC', 'SENT_TO_DEVICE', 'APPLIED', 'FAILED'] as const
export type OfflineSyncState = typeof OFFLINE_SYNC_STATES[number]

export type OfflineMutationKind =
  | 'policy_create'
  | 'policy_revision'
  | 'policy_lifecycle'
  | 'policy_assign'
  | 'policy_clear'
  | 'location_assignment'

export interface OfflineQueueItem {
  id: string
  kind: OfflineMutationKind
  method: 'POST' | 'PATCH'
  url: string
  payload: Record<string, unknown>
  state: OfflineSyncState
  createdAt: string
  updatedAt: string
  attempts: number
  lastError?: string
  response?: unknown
}

const DB_NAME = 'edugd-offline-v1'
const DB_VERSION = 1
const CACHE_STORE = 'cache'
const QUEUE_STORE = 'queue'
const STORAGE_PREFIX = 'edugd.offline.v1.'

const newUuid = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (character) => {
    const random = Math.floor(Math.random() * 16)
    const value = character === 'x' ? random : (random & 3) | 8
    return value.toString(16)
  })
}

export function createOfflineUuid() {
  return newUuid()
}

function canUseIndexedDb() {
  return typeof indexedDB !== 'undefined'
}

function openDatabase(): Promise<IDBDatabase | null> {
  if (!canUseIndexedDb()) return Promise.resolve(null)
  return new Promise((resolve) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)
    request.onupgradeneeded = () => {
      const database = request.result
      if (!database.objectStoreNames.contains(CACHE_STORE)) database.createObjectStore(CACHE_STORE)
      if (!database.objectStoreNames.contains(QUEUE_STORE)) database.createObjectStore(QUEUE_STORE, { keyPath: 'id' })
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => resolve(null)
    request.onblocked = () => resolve(null)
  })
}

function localStorageRead<T>(key: string): T | null {
  try {
    const value = globalThis.localStorage?.getItem(STORAGE_PREFIX + key)
    return value ? JSON.parse(value) as T : null
  } catch {
    return null
  }
}

function localStorageWrite(key: string, value: unknown) {
  try { globalThis.localStorage?.setItem(STORAGE_PREFIX + key, JSON.stringify(value)) } catch { /* best effort cache */ }
}

export async function readOfflineCache<T>(key: string): Promise<T | null> {
  const database = await openDatabase()
  if (!database) return localStorageRead<T>(`cache.${key}`)
  return new Promise((resolve) => {
    const request = database.transaction(CACHE_STORE, 'readonly').objectStore(CACHE_STORE).get(key)
    request.onsuccess = () => resolve((request.result as T | undefined) ?? null)
    request.onerror = () => resolve(localStorageRead<T>(`cache.${key}`))
  })
}

export async function writeOfflineCache<T>(key: string, value: T): Promise<void> {
  const database = await openDatabase()
  if (!database) { localStorageWrite(`cache.${key}`, value); return }
  await new Promise<void>((resolve) => {
    const request = database.transaction(CACHE_STORE, 'readwrite').objectStore(CACHE_STORE).put(value, key)
    request.onsuccess = () => resolve()
    request.onerror = () => { localStorageWrite(`cache.${key}`, value); resolve() }
  })
}

async function readQueueFromIndexedDb(): Promise<OfflineQueueItem[] | null> {
  const database = await openDatabase()
  if (!database) return null
  return new Promise((resolve) => {
    const request = database.transaction(QUEUE_STORE, 'readonly').objectStore(QUEUE_STORE).getAll()
    request.onsuccess = () => resolve(request.result as OfflineQueueItem[])
    request.onerror = () => resolve(null)
  })
}

export async function listOfflineQueue(): Promise<OfflineQueueItem[]> {
  const indexed = await readQueueFromIndexedDb()
  if (indexed) return indexed.sort((a, b) => a.createdAt.localeCompare(b.createdAt))
  return (localStorageRead<OfflineQueueItem[]>('queue') ?? []).sort((a, b) => a.createdAt.localeCompare(b.createdAt))
}

async function persistQueue(queue: OfflineQueueItem[]) {
  const database = await openDatabase()
  if (!database) { localStorageWrite('queue', queue); return }
  await new Promise<void>((resolve) => {
    const transaction = database.transaction(QUEUE_STORE, 'readwrite')
    const store = transaction.objectStore(QUEUE_STORE)
    store.clear()
    queue.forEach((item) => store.put(item))
    transaction.oncomplete = () => resolve()
    transaction.onerror = () => { localStorageWrite('queue', queue); resolve() }
  })
}

export async function enqueueOfflineMutation(input: Omit<OfflineQueueItem, 'id' | 'createdAt' | 'updatedAt' | 'attempts'> & Partial<Pick<OfflineQueueItem, 'id' | 'createdAt' | 'updatedAt' | 'attempts'>>): Promise<OfflineQueueItem> {
  const now = new Date().toISOString()
  const item: OfflineQueueItem = {
    ...input,
    id: input.id ?? newUuid(),
    createdAt: input.createdAt ?? now,
    updatedAt: input.updatedAt ?? now,
    attempts: input.attempts ?? 0,
  }
  const queue = await listOfflineQueue()
  queue.push(item)
  await persistQueue(queue)
  return item
}

export async function updateOfflineQueueItem(id: string, patch: Partial<OfflineQueueItem>): Promise<OfflineQueueItem | null> {
  const queue = await listOfflineQueue()
  const index = queue.findIndex((item) => item.id === id)
  if (index < 0) return null
  queue[index] = { ...queue[index], ...patch, updatedAt: new Date().toISOString() }
  await persistQueue(queue)
  return queue[index]
}

export async function countPendingOfflineQueue() {
  const queue = await listOfflineQueue()
  return queue.filter((item) => item.state === 'LOCAL_ONLY' || item.state === 'PENDING_SYNC').length
}

export async function flushOfflineQueue(sender: (item: OfflineQueueItem) => Promise<unknown>) {
  const queue = await listOfflineQueue()
  const results: OfflineQueueItem[] = []
  for (const item of queue) {
    if (item.state !== 'LOCAL_ONLY' && item.state !== 'PENDING_SYNC' && item.state !== 'FAILED') continue
    await updateOfflineQueueItem(item.id, { state: 'PENDING_SYNC', attempts: item.attempts + 1, lastError: undefined })
    try {
      const response = await sender(item)
      const updated = await updateOfflineQueueItem(item.id, { state: 'SENT_TO_DEVICE', response })
      if (updated) results.push(updated)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Synchronization failed'
      const offline = typeof navigator !== 'undefined' && navigator.onLine === false
      const updated = await updateOfflineQueueItem(item.id, offline ? { state: 'PENDING_SYNC', lastError: message } : { state: 'FAILED', lastError: message })
      if (updated) results.push(updated)
    }
  }
  return results
}
