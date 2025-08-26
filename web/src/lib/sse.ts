import { useSettings } from '@/state/useSettings'

export interface SSEMessage {
  type: 'message' | 'citations' | 'metadata' | 'error' | 'done'
  data: any
}

export interface SSECallbacks {
  onMessage?: (data: string) => void
  onCitations?: (citations: any[]) => void
  onMetadata?: (metadata: any) => void
  onError?: (error: string) => void
  onDone?: (metadata: any) => void
  onOpen?: () => void
  onClose?: () => void
}

export class SSEClient {
  private eventSource: EventSource | null = null
  private retryCount = 0
  private maxRetries = 3
  private retryDelay = 1000
  private abortController: AbortController | null = null

  async connect(query: string, callbacks: SSECallbacks): Promise<void> {
    this.disconnect()

    const settings = useSettings.getState()
    const baseUrl = settings.apiBaseUrl
    const apiKey = settings.apiKey

    const url = new URL(`${baseUrl}/chat/stream`)
    url.searchParams.set('q', query)

    const headers: Record<string, string> = {
      'Accept': 'text/event-stream',
      'Cache-Control': 'no-cache',
    }

    if (apiKey) {
      headers['x-api-key'] = apiKey
    }

    try {
      this.abortController = new AbortController()
      
      const response = await fetch(url.toString(), {
        method: 'GET',
        headers,
        signal: this.abortController.signal,
      })

      if (!response.ok) {
        throw new Error(`SSE connection failed: ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response body')
      }

      const decoder = new TextDecoder()
      let buffer = ''

      callbacks.onOpen?.()

      while (true) {
        const { done, value } = await reader.read()
        
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            const eventType = line.slice(7)
            const dataLine = lines[lines.indexOf(line) + 1]
            
            if (dataLine?.startsWith('data: ')) {
              const data = dataLine.slice(6)
              
              try {
                const parsedData = JSON.parse(data)
                this.handleEvent(eventType, parsedData, callbacks)
              } catch (e) {
                // Handle non-JSON data (like streaming text)
                if (eventType === 'message') {
                  callbacks.onMessage?.(data)
                }
              }
            }
          }
        }
      }

      callbacks.onClose?.()
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        callbacks.onClose?.()
        return
      }

      console.error('SSE error:', error)
      
      if (this.retryCount < this.maxRetries) {
        this.retryCount++
        setTimeout(() => {
          this.connect(query, callbacks)
        }, this.retryDelay * this.retryCount)
      } else {
        callbacks.onError?.(error instanceof Error ? error.message : 'Unknown error')
        callbacks.onClose?.()
      }
    }
  }

  private handleEvent(eventType: string, data: any, callbacks: SSECallbacks) {
    switch (eventType) {
      case 'message':
        callbacks.onMessage?.(data)
        break
      case 'citations':
        callbacks.onCitations?.(data)
        break
      case 'metadata':
        callbacks.onMetadata?.(data)
        break
      case 'error':
        callbacks.onError?.(data)
        break
      case 'done':
        callbacks.onDone?.(data)
        break
    }
  }

  disconnect(): void {
    if (this.abortController) {
      this.abortController.abort()
      this.abortController = null
    }
    
    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
    }
    
    this.retryCount = 0
  }
}

export const sseClient = new SSEClient() 