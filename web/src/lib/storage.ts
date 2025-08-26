import { get, set, del } from 'idb-keyval'

export interface StorageKeys {
  settings: 'settings'
  conversations: 'conversations'
  theme: 'theme'
}

export const STORAGE_KEYS: StorageKeys = {
  settings: 'settings',
  conversations: 'conversations',
  theme: 'theme',
} as const

export class StorageManager {
  async get<T>(key: string): Promise<T | null> {
    try {
      return await get(key)
    } catch (error) {
      console.error(`Failed to get ${key} from storage:`, error)
      return null
    }
  }

  async set<T>(key: string, value: T): Promise<void> {
    try {
      await set(key, value)
    } catch (error) {
      console.error(`Failed to set ${key} in storage:`, error)
    }
  }

  async delete(key: string): Promise<void> {
    try {
      await del(key)
    } catch (error) {
      console.error(`Failed to delete ${key} from storage:`, error)
    }
  }

  async clear(): Promise<void> {
    try {
      // Note: idb-keyval doesn't have a clear method, so we'd need to track keys
      // For now, we'll just clear the known keys
      await Promise.all([
        this.delete(STORAGE_KEYS.settings),
        this.delete(STORAGE_KEYS.conversations),
        this.delete(STORAGE_KEYS.theme),
      ])
    } catch (error) {
      console.error('Failed to clear storage:', error)
    }
  }
}

export const storage = new StorageManager()

// Fallback to localStorage for critical settings
export class FallbackStorage {
  private useLocalStorage: boolean

  constructor(useLocalStorage = false) {
    this.useLocalStorage = useLocalStorage
  }

  async get<T>(key: string): Promise<T | null> {
    if (this.useLocalStorage) {
      try {
        const item = localStorage.getItem(key)
        return item ? JSON.parse(item) : null
      } catch (error) {
        console.error(`Failed to get ${key} from localStorage:`, error)
        return null
      }
    } else {
      return storage.get<T>(key)
    }
  }

  async set<T>(key: string, value: T): Promise<void> {
    if (this.useLocalStorage) {
      try {
        localStorage.setItem(key, JSON.stringify(value))
      } catch (error) {
        console.error(`Failed to set ${key} in localStorage:`, error)
      }
    } else {
      await storage.set(key, value)
    }
  }

  async delete(key: string): Promise<void> {
    if (this.useLocalStorage) {
      try {
        localStorage.removeItem(key)
      } catch (error) {
        console.error(`Failed to delete ${key} from localStorage:`, error)
      }
    } else {
      await storage.delete(key)
    }
  }
} 