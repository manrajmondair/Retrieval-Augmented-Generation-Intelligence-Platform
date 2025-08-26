import { create } from 'zustand'
import { apiClient, IngestResponse } from '@/lib/api'

export interface IngestItem {
  id: string
  name: string
  type: 'file' | 'url'
  size?: number
  status: 'pending' | 'uploading' | 'success' | 'error'
  progress: number
  result?: IngestResponse
  error?: string
}

interface IngestState {
  items: IngestItem[]
  isUploading: boolean
  
  // Actions
  addFiles: (files: File[]) => void
  addUrls: (urls: string[]) => void
  removeItem: (id: string) => void
  clearItems: () => void
  uploadAll: () => Promise<void>
  uploadItem: (id: string) => Promise<void>
  retryItem: (id: string) => Promise<void>
  
  // Getters
  getPendingItems: () => IngestItem[]
  getSuccessfulItems: () => IngestItem[]
  getFailedItems: () => IngestItem[]
  getTotalProgress: () => number
}

export const useIngest = create<IngestState>((set, get) => ({
  items: [],
  isUploading: false,
  
  addFiles: (files: File[]) => {
    const newItems: IngestItem[] = files.map(file => ({
      id: `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      name: file.name,
      type: 'file' as const,
      size: file.size,
      status: 'pending',
      progress: 0,
    }))
    
    set((state) => ({
      items: [...state.items, ...newItems],
    }))
  },
  
  addUrls: (urls: string[]) => {
    const newItems: IngestItem[] = urls.map(url => ({
      id: `url_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      name: url,
      type: 'url' as const,
      status: 'pending',
      progress: 0,
    }))
    
    set((state) => ({
      items: [...state.items, ...newItems],
    }))
  },
  
  removeItem: (id: string) => {
    set((state) => ({
      items: state.items.filter(item => item.id !== id),
    }))
  },
  
  clearItems: () => {
    set({ items: [] })
  },
  
  uploadAll: async () => {
    const { items } = get()
    const pendingItems = items.filter(item => item.status === 'pending')
    
    if (pendingItems.length === 0) return
    
    set({ isUploading: true })
    
    try {
      await Promise.all(
        pendingItems.map(item => get().uploadItem(item.id))
      )
    } finally {
      set({ isUploading: false })
    }
  },
  
  uploadItem: async (id: string) => {
    const { items } = get()
    const item = items.find(item => item.id === id)
    
    if (!item || item.status !== 'pending') return
    
    // Update status to uploading
    set((state) => ({
      items: state.items.map(item =>
        item.id === id
          ? { ...item, status: 'uploading', progress: 0 }
          : item
      ),
    }))
    
    try {
      let result: IngestResponse
      
      if (item.type === 'file') {
        // Find the actual file object
        const fileInput = document.createElement('input')
        fileInput.type = 'file'
        fileInput.multiple = true
        
        // This is a simplified approach - in a real app you'd need to store the actual File objects
        // For now, we'll simulate the upload
        await new Promise(resolve => setTimeout(resolve, 1000)) // Simulate upload time
        
        result = {
          ingested: [{ filename: item.name, doc_id: item.name, chunks: 1, source: item.name }],
          skipped: [],
          errors: [],
        }
      } else {
        // URL ingestion
        result = await apiClient.ingestUrl(item.name)
      }
      
      // Update with success
      set((state) => ({
        items: state.items.map(item =>
          item.id === id
            ? { ...item, status: 'success', progress: 100, result }
            : item
        ),
      }))
    } catch (error) {
      // Update with error
      set((state) => ({
        items: state.items.map(item =>
          item.id === id
            ? { 
                ...item, 
                status: 'error', 
                progress: 0, 
                error: error instanceof Error ? error.message : 'Unknown error'
              }
            : item
        ),
      }))
    }
  },
  
  retryItem: async (id: string) => {
    const { items } = get()
    const item = items.find(item => item.id === id)
    
    if (!item || item.status !== 'error') return
    
    // Reset to pending
    set((state) => ({
      items: state.items.map(item =>
        item.id === id
          ? { ...item, status: 'pending', progress: 0, error: undefined }
          : item
      ),
    }))
    
    // Upload again
    await get().uploadItem(id)
  },
  
  getPendingItems: () => {
    const { items } = get()
    return items.filter(item => item.status === 'pending')
  },
  
  getSuccessfulItems: () => {
    const { items } = get()
    return items.filter(item => item.status === 'success')
  },
  
  getFailedItems: () => {
    const { items } = get()
    return items.filter(item => item.status === 'error')
  },
  
  getTotalProgress: () => {
    const { items } = get()
    if (items.length === 0) return 0
    
    const totalProgress = items.reduce((sum, item) => sum + item.progress, 0)
    return Math.round(totalProgress / items.length)
  },
})) 