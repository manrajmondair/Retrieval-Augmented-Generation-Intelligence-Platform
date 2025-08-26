import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { storage, STORAGE_KEYS } from '@/lib/storage'
import { Citation, RetrievalDebug } from '@/lib/api'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  citations?: Citation[]
  retrievalDebug?: RetrievalDebug
  isStreaming?: boolean
  error?: string
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  createdAt: number
  updatedAt: number
}

interface ChatState {
  conversations: Conversation[]
  currentConversationId: string | null
  isLoading: boolean
  error: string | null
  
  // Actions
  createConversation: (title?: string) => string
  deleteConversation: (id: string) => void
  clearConversations: () => void
  setCurrentConversation: (id: string | null) => void
  addMessage: (conversationId: string, message: Omit<Message, 'id' | 'timestamp'>) => void
  updateMessage: (conversationId: string, messageId: string, updates: Partial<Message>) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  
  // Getters
  getCurrentConversation: () => Conversation | null
  getConversation: (id: string) => Conversation | null
}

export const useChat = create<ChatState>()(
  persist(
    (set, get) => ({
      conversations: [],
      currentConversationId: null,
      isLoading: false,
      error: null,
      
      createConversation: (title = 'New Conversation') => {
        const id = `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
        const conversation: Conversation = {
          id,
          title,
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        }
        
        set((state) => ({
          conversations: [conversation, ...state.conversations],
          currentConversationId: id,
        }))
        
        return id
      },
      
      deleteConversation: (id: string) => {
        set((state) => {
          const newConversations = state.conversations.filter(conv => conv.id !== id)
          const newCurrentId = state.currentConversationId === id 
            ? (newConversations[0]?.id || null)
            : state.currentConversationId
            
          return {
            conversations: newConversations,
            currentConversationId: newCurrentId,
          }
        })
      },
      
      clearConversations: () => {
        set({
          conversations: [],
          currentConversationId: null,
        })
      },
      
      setCurrentConversation: (id: string | null) => {
        set({ currentConversationId: id })
      },
      
      addMessage: (conversationId: string, message: Omit<Message, 'id' | 'timestamp'>) => {
        const newMessage: Message = {
          ...message,
          id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          timestamp: Date.now(),
        }
        
        set((state) => ({
          conversations: state.conversations.map(conv =>
            conv.id === conversationId
              ? {
                  ...conv,
                  messages: [...conv.messages, newMessage],
                  updatedAt: Date.now(),
                  title: conv.title === 'New Conversation' && message.role === 'user'
                    ? message.content.slice(0, 50) + (message.content.length > 50 ? '...' : '')
                    : conv.title,
                }
              : conv
          ),
        }))
      },
      
      updateMessage: (conversationId: string, messageId: string, updates: Partial<Message>) => {
        set((state) => ({
          conversations: state.conversations.map(conv =>
            conv.id === conversationId
              ? {
                  ...conv,
                  messages: conv.messages.map(msg =>
                    msg.id === messageId
                      ? { ...msg, ...updates }
                      : msg
                  ),
                  updatedAt: Date.now(),
                }
              : conv
          ),
        }))
      },
      
      setLoading: (isLoading: boolean) => set({ isLoading }),
      setError: (error: string | null) => set({ error }),
      
      getCurrentConversation: () => {
        const { conversations, currentConversationId } = get()
        return conversations.find(conv => conv.id === currentConversationId) || null
      },
      
      getConversation: (id: string) => {
        const { conversations } = get()
        return conversations.find(conv => conv.id === id) || null
      },
    }),
    {
      name: STORAGE_KEYS.conversations,
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