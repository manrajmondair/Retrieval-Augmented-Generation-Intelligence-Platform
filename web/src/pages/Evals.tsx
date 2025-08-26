import React from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ArrowLeft, BarChart3 } from 'lucide-react'
import { Link } from 'react-router-dom'

export function Evals() {
  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="flex items-center gap-4 mb-6">
        <Link to="/">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Chat
          </Button>
        </Link>
        <h1 className="text-2xl font-bold">RAG Evaluations</h1>
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            Evaluation Dashboard
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            RAGAS evaluation functionality coming soon. This will include:
          </p>
          <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
            <li>• Answer Relevance scoring</li>
            <li>• Context Precision and Recall</li>
            <li>• Faithfulness metrics</li>
            <li>• Answer Correctness evaluation</li>
            <li>• Comparative analysis between different retrieval methods</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  )
} 