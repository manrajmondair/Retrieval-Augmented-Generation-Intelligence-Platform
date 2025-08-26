import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { storage, STORAGE_KEYS } from '@/lib/storage'

export interface Settings {
  apiBaseUrl: string
  apiKey: string
  useLocalStorage: boolean
  theme: 'light' | 'dark' | 'system'
  topK: number
  fusionMode: 'rrf' | 'weighted'
  vectorStore: 'qdrant' | 'chroma' | 'pinecone'
  temperature: number
  showDebugPanel: boolean
  showMetricsBar: boolean
  autoScroll: boolean
  enableStreaming: boolean
}

interface SettingsState extends Settings {
  setApiBaseUrl: (url: string) => void
  setApiKey: (key: string) => void
  setUseLocalStorage: (use: boolean) => void
  setTheme: (theme: 'light' | 'dark' | 'system') => void
  setTopK: (topK: number) => void
  setFusionMode: (mode: 'rrf' | 'weighted') => void
  setVectorStore: (store: 'qdrant' | 'chroma' | 'pinecone') => void
  setTemperature: (temp: number) => void
  setShowDebugPanel: (show: boolean) => void
  setShowMetricsBar: (show: boolean) => void
  setAutoScroll: (auto: boolean) => void
  setEnableStreaming: (enable: boolean) => void
  reset: () => void
}

const defaultSettings: Settings = {
  apiBaseUrl: '', // Empty string for relative URLs - Vite proxy handles routing
  apiKey: 'changeme',
  useLocalStorage: false,
  theme: 'dark',
  topK: 12,
  fusionMode: 'rrf',
  vectorStore: 'qdrant',
  temperature: 0.7,
  showDebugPanel: true,
  showMetricsBar: true,
  autoScroll: true,
  enableStreaming: true,
}

export const useSettings = create<SettingsState>()(
  persist(
    (set, get) => ({
      ...defaultSettings,
      
      setApiBaseUrl: (apiBaseUrl: string) => set({ apiBaseUrl }),
      setApiKey: (apiKey: string) => set({ apiKey }),
      setUseLocalStorage: (useLocalStorage: boolean) => set({ useLocalStorage }),
      setTheme: (theme: 'light' | 'dark' | 'system') => set({ theme }),
      setTopK: (topK: number) => set({ topK }),
      setFusionMode: (fusionMode: 'rrf' | 'weighted') => set({ fusionMode }),
      setVectorStore: (vectorStore: 'qdrant' | 'chroma' | 'pinecone') => set({ vectorStore }),
      setTemperature: (temperature: number) => set({ temperature }),
      setShowDebugPanel: (showDebugPanel: boolean) => set({ showDebugPanel }),
      setShowMetricsBar: (showMetricsBar: boolean) => set({ showMetricsBar }),
      setAutoScroll: (autoScroll: boolean) => set({ autoScroll }),
      setEnableStreaming: (enableStreaming: boolean) => set({ enableStreaming }),
      
      reset: () => set(defaultSettings),
    }),
    {
      name: STORAGE_KEYS.settings,
      storage: {
        getItem: async (name) => {
          const value = await storage.get(name)
          return value ? JSON.stringify(value) : null
        },
        setItem: async (name, value) => {
          await storage.set(name, JSON.parse(value))
        },
        removeItem: async (name) => {
          await storage.delete(name)
        },
      },
    }
  )
) 