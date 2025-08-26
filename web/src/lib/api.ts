import { useSettings } from '@/state/useSettings'

export interface HealthResponse {
  status: string
}

export interface ConfigResponse {
  app_env: string
  vector_store: string
  hybrid_fusion: string
  bm25_top_k: number
  vector_top_k: number
  prometheus_enabled: boolean
}

export interface IngestResponse {
  ingested: Array<{
    filename: string
    doc_id: string
    chunks: number
    source: string
  }>
  skipped: string[]
  errors: string[]
}

export interface Citation {
  doc_id: string
  chunk_id: string
  source: string
  title: string
  content: string
  score: number
  retriever: string
  metadata: Record<string, any>
}

export interface RetrievalDebug {
  bm25_count: number
  vector_count: number
  fused_count: number
  fusion_method: string
  fusion_params: Record<string, any>
  retrieval_time_ms: number
  bm25_time_ms: number
  vector_time_ms: number
}

export interface QueryResponse {
  answer: string
  citations: Citation[]
  retrieval_debug: RetrievalDebug
}

export interface QueryRequest {
  q: string
}

export interface IngestRequest {
  files?: File[]
  urls?: string[]
}

class ApiClient {
  private getBaseUrl(): string {
    // Use empty string for relative URLs - Vite proxy will handle routing to backend
    return ''
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    
    const settings = useSettings.getState()
    const apiKey = settings.apiKey || 'changeme'
    headers['x-api-key'] = apiKey
    
    return headers
  }

  async health(): Promise<HealthResponse> {
    const response = await fetch(`${this.getBaseUrl()}/healthz`)
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`)
    }
    return response.json()
  }

  async config(): Promise<ConfigResponse> {
    const response = await fetch(`${this.getBaseUrl()}/readyz`, {
      headers: this.getHeaders(),
    })
    if (!response.ok) {
      throw new Error(`Config check failed: ${response.status}`)
    }
    return response.json()
  }

  async query(request: QueryRequest): Promise<QueryResponse> {
    const response = await fetch(`${this.getBaseUrl()}/query/`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(request),
    })
    if (!response.ok) {
      throw new Error(`Query failed: ${response.status}`)
    }
    return response.json()
  }

  async ingest(request: IngestRequest): Promise<IngestResponse> {
    const formData = new FormData()
    
    if (request.files) {
      request.files.forEach((file) => {
        formData.append('files', file)
      })
    }
    
    if (request.urls) {
      formData.append('urls', JSON.stringify(request.urls))
    }

    const headers: Record<string, string> = {}
    const apiKey = useSettings.getState().apiKey
    if (apiKey) {
      headers['x-api-key'] = apiKey
    }

    const response = await fetch(`${this.getBaseUrl()}/ingest/`, {
      method: 'POST',
      headers,
      body: formData,
    })
    
    if (!response.ok) {
      throw new Error(`Ingest failed: ${response.status}`)
    }
    
    return response.json()
  }

  async ingestUrl(url: string): Promise<IngestResponse> {
    return this.ingest({ urls: [url] })
  }

  async ingestFiles(files: File[]): Promise<IngestResponse> {
    return this.ingest({ files })
  }

  // Multimodal Analysis
  async analyzeImage(imageData: string, mediaType: string, docId?: string): Promise<any> {
    const response = await fetch(`${this.getBaseUrl()}/multimodal/analyze`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        image_data: imageData,
        media_type: mediaType,
        doc_id: docId || `analysis_${Date.now()}`
      }),
    })
    if (!response.ok) {
      throw new Error(`Multimodal analysis failed: ${response.status}`)
    }
    return response.json()
  }

  async getMultimodalTypes(): Promise<any> {
    const response = await fetch(`${this.getBaseUrl()}/multimodal/types`, {
      headers: this.getHeaders(),
    })
    if (!response.ok) {
      throw new Error(`Failed to get multimodal types: ${response.status}`)
    }
    return response.json()
  }

  // Intelligence Features
  async generateIntelligence(docId: string): Promise<any> {
    const response = await fetch(`${this.getBaseUrl()}/intelligence/generate/${docId}`, {
      method: 'POST',
      headers: this.getHeaders(),
    })
    if (!response.ok) {
      throw new Error(`Intelligence generation failed: ${response.status}`)
    }
    return response.json()
  }

  async getIntelligence(docId: string): Promise<any> {
    const response = await fetch(`${this.getBaseUrl()}/intelligence/analyze/${docId}`, {
      headers: this.getHeaders(),
    })
    if (!response.ok) {
      throw new Error(`Failed to get intelligence: ${response.status}`)
    }
    return response.json()
  }

  // Summaries
  async generateSummary(docId: string, summaryType?: string): Promise<any> {
    const url = summaryType 
      ? `${this.getBaseUrl()}/summaries/generate/${docId}?summary_type=${summaryType}`
      : `${this.getBaseUrl()}/summaries/suite/${docId}`
    
    const response = await fetch(url, {
      method: 'POST',
      headers: this.getHeaders(),
    })
    if (!response.ok) {
      throw new Error(`Summary generation failed: ${response.status}`)
    }
    return response.json()
  }

  // Knowledge Graph
  async generateKnowledgeGraph(): Promise<any> {
    const response = await fetch(`${this.getBaseUrl()}/knowledge/generate`, {
      method: 'POST',
      headers: this.getHeaders(),
    })
    if (!response.ok) {
      throw new Error(`Knowledge graph generation failed: ${response.status}`)
    }
    return response.json()
  }

  async getKnowledgeGraph(): Promise<any> {
    const response = await fetch(`${this.getBaseUrl()}/knowledge/graph`, {
      headers: this.getHeaders(),
    })
    if (!response.ok) {
      throw new Error(`Failed to get knowledge graph: ${response.status}`)
    }
    return response.json()
  }

  // Analytics
  async getAnalytics(): Promise<any> {
    const response = await fetch(`${this.getBaseUrl()}/analytics/dashboard`, {
      headers: this.getHeaders(),
    })
    if (!response.ok) {
      throw new Error(`Failed to get analytics: ${response.status}`)
    }
    return response.json()
  }

  // Performance
  async getCacheStats(): Promise<any> {
    const response = await fetch(`${this.getBaseUrl()}/performance/cache-stats`, {
      headers: this.getHeaders(),
    })
    if (!response.ok) {
      throw new Error(`Failed to get cache stats: ${response.status}`)
    }
    return response.json()
  }

  // Ultra Fast Chat
  async ultraQuickAnswer(query: string): Promise<any> {
    const response = await fetch(`${this.getBaseUrl()}/ultra/quick?q=${encodeURIComponent(query)}`, {
      headers: this.getHeaders(),
    })
    if (!response.ok) {
      throw new Error(`Ultra quick answer failed: ${response.status}`)
    }
    return response.json()
  }
}

export const apiClient = new ApiClient() 