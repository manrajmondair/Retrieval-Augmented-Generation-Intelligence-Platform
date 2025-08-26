import React, { useState, useRef, useEffect } from 'react'
import { useChat } from '@/state/useChat'
import { useSettings } from '@/state/useSettings'
import { sseClient } from '@/lib/sse'
import { apiClient } from '@/lib/api'
import { formatTime } from '@/lib/time'
import { renderMarkdown, renderInlineMarkdown, sanitizeHtml } from '@/lib/markdown'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { 
  Send, 
  Plus, 
  Trash2, 
  Settings, 
  FileText, 
  ExternalLink,
  Loader2,
  AlertCircle,
  CheckCircle,
  XCircle
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useToast } from '@/hooks/use-toast'

export function Home() {
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentStreamingMessage, setCurrentStreamingMessage] = useState<string>('')
  const [currentCitations, setCurrentCitations] = useState<any[]>([])
  const [currentMetadata, setCurrentMetadata] = useState<any>(null)
  const [selectedCitation, setSelectedCitation] = useState<any>(null)
  
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  
  const {
    conversations,
    currentConversationId,
    isLoading,
    error,
    createConversation,
    setCurrentConversation,
    addMessage,
    updateMessage,
    setLoading,
    setError,
    getCurrentConversation,
  } = useChat()
  
  const { enableStreaming, showDebugPanel, autoScroll } = useSettings()
  const { toast } = useToast()
  
  const currentConversation = getCurrentConversation()
  
  // Auto-scroll to bottom when new messages are added
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [currentConversation?.messages, autoScroll])
  
  // Focus input when conversation changes
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus()
    }
  }, [currentConversationId])
  
  const handleSendMessage = async () => {
    if (!input.trim() || isLoading || isStreaming) return
    
    const message = input.trim()
    setInput('')
    
    // Create conversation if none exists
    let conversationId = currentConversationId
    if (!conversationId) {
      conversationId = createConversation()
    }
    
    // Add user message
    addMessage(conversationId, {
      role: 'user',
      content: message,
    })
    
    // Add assistant message placeholder
    const assistantMessageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    addMessage(conversationId, {
      role: 'assistant',
      content: '',
      isStreaming: true,
    })
    
    setLoading(true)
    setError(null)
    setIsStreaming(true)
    setCurrentStreamingMessage('')
    setCurrentCitations([])
    setCurrentMetadata(null)
    
    try {
      if (enableStreaming) {
        // Use streaming
        await sseClient.connect(message, {
          onMessage: (data) => {
            setCurrentStreamingMessage(prev => prev + data)
          },
          onCitations: (citations) => {
            setCurrentCitations(citations)
          },
          onMetadata: (metadata) => {
            setCurrentMetadata(metadata)
          },
          onError: (error) => {
            setError(error)
            toast({
              title: "Error",
              description: error,
              variant: "destructive",
            })
          },
          onDone: (metadata) => {
            setCurrentMetadata(metadata)
            setIsStreaming(false)
            setLoading(false)
            
            // Update the assistant message with final content
            updateMessage(conversationId, assistantMessageId, {
              content: currentStreamingMessage,
              citations: currentCitations,
              retrievalDebug: metadata?.retrieval_debug,
              isStreaming: false,
            })
          },
        })
      } else {
        // Use regular query
        const response = await apiClient.query({ q: message })
        
        updateMessage(conversationId, assistantMessageId, {
          content: response.answer,
          citations: response.citations,
          retrievalDebug: response.retrieval_debug,
          isStreaming: false,
        })
        
        setLoading(false)
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Unknown error')
      updateMessage(conversationId, assistantMessageId, {
        content: 'Sorry, I encountered an error while processing your request.',
        error: error instanceof Error ? error.message : 'Unknown error',
        isStreaming: false,
      })
      setLoading(false)
      setIsStreaming(false)
      
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: "destructive",
      })
    }
  }
  
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      handleSendMessage()
    }
  }
  
  const handleNewConversation = () => {
    createConversation()
  }
  
  const handleCitationClick = (citation: any) => {
    setSelectedCitation(citation)
  }
  
  const renderMessage = (message: any) => {
    const isUser = message.role === 'user'
    const isStreaming = message.isStreaming
    
    return (
      <div
        key={message.id}
        className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}
      >
        <div
          className={`max-w-[80%] rounded-lg px-4 py-2 ${
            isUser
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-foreground'
          }`}
        >
          {isUser ? (
            <div className="whitespace-pre-wrap">{message.content}</div>
          ) : (
            <div className="space-y-2">
              <div 
                className="prose prose-sm max-w-none"
                dangerouslySetInnerHTML={{
                  __html: sanitizeHtml(
                    isStreaming 
                      ? renderInlineMarkdown(currentStreamingMessage || message.content)
                      : renderInlineMarkdown(message.content)
                  )
                }}
              />
              
              {message.citations && message.citations.length > 0 && (
                <div className="mt-3 space-y-2">
                  <div className="text-xs text-muted-foreground">Sources:</div>
                  <div className="flex flex-wrap gap-1">
                    {message.citations.map((citation: any, index: number) => (
                      <Button
                        key={index}
                        variant="outline"
                        size="sm"
                        className="text-xs"
                        onClick={() => handleCitationClick(citation)}
                      >
                        <FileText className="w-3 h-3 mr-1" />
                        {citation.title || citation.source}
                        <Badge variant="secondary" className="ml-1">
                          {citation.score.toFixed(3)}
                        </Badge>
                      </Button>
                    ))}
                  </div>
                </div>
              )}
              
              {message.error && (
                <div className="flex items-center gap-2 text-destructive text-sm">
                  <AlertCircle className="w-4 h-4" />
                  {message.error}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    )
  }
  
  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <div className="w-64 border-r bg-muted/50 flex flex-col">
        <div className="p-4 border-b">
          <Button onClick={handleNewConversation} className="w-full">
            <Plus className="w-4 h-4 mr-2" />
            New Chat
          </Button>
        </div>
        
        <ScrollArea className="flex-1">
          <div className="p-2 space-y-1">
            {conversations.map((conversation) => (
              <div
                key={conversation.id}
                className={`p-2 rounded cursor-pointer hover:bg-accent ${
                  conversation.id === currentConversationId ? 'bg-accent' : ''
                }`}
                onClick={() => setCurrentConversation(conversation.id)}
              >
                <div className="text-sm font-medium truncate">
                  {conversation.title}
                </div>
                <div className="text-xs text-muted-foreground">
                  {formatTime(conversation.updatedAt)}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
        
        <div className="p-4 border-t">
          <Link to="/ingest">
            <Button variant="outline" className="w-full mb-2">
              <FileText className="w-4 h-4 mr-2" />
              Ingest Documents
            </Button>
          </Link>
          <Link to="/evals">
            <Button variant="ghost" className="w-full">
              <Settings className="w-4 h-4 mr-2" />
              Settings
            </Button>
          </Link>
        </div>
      </div>
      
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b">
          <div className="flex items-center justify-between">
            <h1 className="text-lg font-semibold">
              {currentConversation?.title || 'New Conversation'}
            </h1>
            <div className="flex items-center gap-2">
              {isLoading && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Processing...
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* Messages */}
        <ScrollArea ref={scrollRef} className="flex-1 p-4">
          <div className="space-y-4">
            {currentConversation?.messages.map(renderMessage)}
            {isStreaming && (
              <div className="flex justify-start mb-4">
                <div className="bg-muted rounded-lg px-4 py-2">
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-sm text-muted-foreground">
                      Generating response...
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>
        
        {/* Input */}
        <div className="p-4 border-t">
          <div className="flex gap-2">
            <Input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask a question... (⌘+Enter to send)"
              disabled={isLoading || isStreaming}
              className="flex-1"
            />
            <Button
              onClick={handleSendMessage}
              disabled={!input.trim() || isLoading || isStreaming}
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
      
      {/* Citation Preview Drawer */}
      {selectedCitation && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background rounded-lg p-6 max-w-2xl max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Source: {selectedCitation.title}</h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedCitation(null)}
              >
                <XCircle className="w-4 h-4" />
              </Button>
            </div>
            
            <div className="space-y-4">
              <div>
                <div className="text-sm text-muted-foreground mb-1">Source:</div>
                <div className="text-sm">{selectedCitation.source}</div>
              </div>
              
              <div>
                <div className="text-sm text-muted-foreground mb-1">Score:</div>
                <div className="text-sm">{selectedCitation.score.toFixed(4)}</div>
              </div>
              
              <div>
                <div className="text-sm text-muted-foreground mb-1">Content:</div>
                <div className="text-sm bg-muted p-3 rounded whitespace-pre-wrap">
                  {selectedCitation.content}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Debug Panel */}
      {showDebugPanel && currentMetadata && (
        <div className="fixed bottom-4 right-4 w-80 bg-background border rounded-lg p-4 shadow-lg">
          <h4 className="font-semibold mb-2">Retrieval Debug</h4>
          <div className="space-y-2 text-sm">
            <div>BM25 Count: {currentMetadata.retrieval_debug?.bm25_count || 0}</div>
            <div>Vector Count: {currentMetadata.retrieval_debug?.vector_count || 0}</div>
            <div>Fused Count: {currentMetadata.retrieval_debug?.fused_count || 0}</div>
            <div>Retrieval Time: {currentMetadata.retrieval_debug?.retrieval_time_ms?.toFixed(1)}ms</div>
            <div>Fusion Method: {currentMetadata.retrieval_debug?.fusion_method}</div>
          </div>
        </div>
      )}
    </div>
  )
} 