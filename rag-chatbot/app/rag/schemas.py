from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """A chunk of a document with metadata."""
    doc_id: str
    source: str
    title: str
    chunk_id: str
    chunk_index: int
    content: str
    content_hash: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RetrievalResult(BaseModel):
    """A single retrieval result with score and metadata."""
    doc_id: str
    chunk_id: str
    source: str
    title: str
    content: str
    score: float
    retriever: str  # "bm25" or "vector"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HybridRetrievalResult(BaseModel):
    """Fused retrieval results from multiple retrievers."""
    results: List[RetrievalResult]
    fusion_method: str
    fusion_params: Dict[str, Any] = Field(default_factory=dict)
    retrieval_debug: Dict[str, Any] = Field(default_factory=dict)


class QueryRequest(BaseModel):
    """Request for a query."""
    q: str
    top_k: int = 12
    store: str = "qdrant"  # qdrant|chroma|pinecone
    fusion: str = "rrf"  # rrf|weighted


class QueryResponse(BaseModel):
    """Response from a query."""
    answer: str
    citations: List[RetrievalResult]
    retrieval_debug: Dict[str, Any] = Field(default_factory=dict)


class ChatStreamRequest(BaseModel):
    """Request for streaming chat."""
    q: str
    top_k: int = 12
    store: str = "qdrant"
    fusion: str = "rrf"


class IngestRequest(BaseModel):
    """Request for document ingestion."""
    files: List[str] = Field(default_factory=list)
    urls: List[str] = Field(default_factory=list)


class IngestResponse(BaseModel):
    """Response from document ingestion."""
    ingested: List[Dict[str, Any]] = Field(default_factory=list)
    skipped: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list) 