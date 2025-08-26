import React, { useState, useRef } from 'react'
import { useIngest } from '@/state/useIngest'
import { useSettings } from '@/state/useSettings'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { 
  Upload, 
  FileText, 
  Link, 
  Trash2, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  ArrowLeft,
  Loader2
} from 'lucide-react'
import { Link as RouterLink } from 'react-router-dom'
import { useToast } from '@/hooks/use-toast'
import { formatFileSize, isValidUrl } from '@/lib/utils'

export function Ingest() {
  const [urlInput, setUrlInput] = useState('')
  const [urls, setUrls] = useState<string[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const { items, isUploading, addFiles, addUrls, removeItem, uploadAll, retryItem } = useIngest()
  const { toast } = useToast()
  
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || [])
    if (files.length > 0) {
      addFiles(files)
      toast({
        title: "Files added",
        description: `${files.length} file(s) added to upload queue`,
      })
    }
  }
  
  const handleAddUrl = () => {
    if (!urlInput.trim()) return
    
    if (!isValidUrl(urlInput)) {
      toast({
        title: "Invalid URL",
        description: "Please enter a valid URL",
        variant: "destructive",
      })
      return
    }
    
    addUrls([urlInput.trim()])
    setUrlInput('')
    toast({
      title: "URL added",
      description: "URL added to upload queue",
    })
  }
  
  const handleUploadAll = async () => {
    if (items.length === 0) {
      toast({
        title: "No items",
        description: "Please add files or URLs to upload",
      })
      return
    }
    
    try {
      await uploadAll()
      toast({
        title: "Upload complete",
        description: "All items have been processed",
      })
    } catch (error) {
      toast({
        title: "Upload failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      })
    }
  }
  
  const handleRetry = async (id: string) => {
    try {
      await retryItem(id)
      toast({
        title: "Retry successful",
        description: "Item has been retried",
      })
    } catch (error) {
      toast({
        title: "Retry failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      })
    }
  }
  
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'error':
        return <XCircle className="w-4 h-4 text-red-500" />
      case 'uploading':
        return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
      default:
        return <AlertCircle className="w-4 h-4 text-gray-500" />
    }
  }
  
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      case 'error':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      case 'uploading':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
    }
  }
  
  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="flex items-center gap-4 mb-6">
        <RouterLink to="/">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Chat
          </Button>
        </RouterLink>
        <h1 className="text-2xl font-bold">Document Ingestion</h1>
      </div>
      
      <div className="grid gap-6">
        {/* File Upload */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="w-5 h-5" />
              Upload Files
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                <p className="text-sm text-gray-600 mb-2">
                  Drag and drop files here, or click to select
                </p>
                <Button
                  onClick={() => fileInputRef.current?.click()}
                  variant="outline"
                >
                  Select Files
                </Button>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  onChange={handleFileSelect}
                  className="hidden"
                  accept=".pdf,.md,.txt,.doc,.docx"
                />
              </div>
            </div>
          </CardContent>
        </Card>
        
        {/* URL Input */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Link className="w-5 h-5" />
              Add URLs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Input
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="Enter URL to ingest..."
                onKeyPress={(e) => e.key === 'Enter' && handleAddUrl()}
              />
              <Button onClick={handleAddUrl} disabled={!urlInput.trim()}>
                Add
              </Button>
            </div>
          </CardContent>
        </Card>
        
        {/* Upload Queue */}
        {items.length > 0 && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Upload Queue ({items.length})</CardTitle>
                <Button 
                  onClick={handleUploadAll} 
                  disabled={isUploading || items.every(item => item.status === 'success')}
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    'Upload All'
                  )}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {items.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between p-3 border rounded-lg"
                  >
                    <div className="flex items-center gap-3 flex-1">
                      {item.type === 'file' ? (
                        <FileText className="w-4 h-4 text-blue-500" />
                      ) : (
                        <Link className="w-4 h-4 text-green-500" />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">
                          {item.name}
                        </p>
                        {item.size && (
                          <p className="text-xs text-gray-500">
                            {formatFileSize(item.size)}
                          </p>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Badge className={getStatusColor(item.status)}>
                        {item.status}
                      </Badge>
                      {getStatusIcon(item.status)}
                      
                      {item.status === 'uploading' && (
                        <Progress value={item.progress} className="w-20" />
                      )}
                      
                      {item.status === 'error' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRetry(item.id)}
                        >
                          Retry
                        </Button>
                      )}
                      
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeItem(item.id)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
} 