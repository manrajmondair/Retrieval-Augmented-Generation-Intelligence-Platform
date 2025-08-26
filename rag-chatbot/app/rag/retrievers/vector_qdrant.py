from typing import List, Dict, Any, Optional
import asyncio
from qdrant_client import QdrantClient
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, HnswConfigDiff, OptimizersConfigDiff, SearchRequest
from app.rag.retrievers.base import BaseRetriever
from app.rag.schemas import DocumentChunk, RetrievalResult
from app.services.embeddings import get_embeddings_service


class QdrantRetriever(BaseRetriever):
    """Qdrant vector retriever for dense retrieval."""
    
    def __init__(self, url: str, collection_name: str, dimension: int = 1536):
        self.url = url
        self.collection_name = collection_name
        self.dimension = dimension
        self.embeddings_service = get_embeddings_service()
        
        # Use both sync and async clients for optimal performance
        self.client = QdrantClient(url=url, timeout=10)  # Sync for setup
        self.async_client: Optional[AsyncQdrantClient] = None
        
        # Connection pool will be initialized lazily
        self._client_pool_size = 5
        self._client_pools: List[AsyncQdrantClient] = []
        self._pool_lock = asyncio.Lock()
        
        self._ensure_collection()
    
    def _ensure_collection(self) -> None:
        """Ensure the collection exists with optimized configuration for performance."""
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.dimension,
                        distance=Distance.COSINE,
                        on_disk=False,  # Keep in memory for speed
                        hnsw_config=HnswConfigDiff(
                            m=48,  # Increase connectivity for better recall
                            ef_construct=200,  # Higher build quality
                            full_scan_threshold=1000,  # Use HNSW for small datasets
                        )
                    ),
                    optimizers_config=OptimizersConfigDiff(
                        default_segment_number=4,  # More segments for parallel processing
                        max_segment_size=500000,  # Larger segments
                        memmap_threshold=100000,  # Keep smaller segments in memory
                        indexing_threshold=50000,  # Build index sooner
                        flush_interval_sec=30,  # More frequent flushes
                        max_optimization_threads=4  # Parallel optimization
                    )
                )
        except Exception as e:
            print(f"Failed to ensure Qdrant collection: {e}")
    
    async def _get_async_client(self) -> AsyncQdrantClient:
        """Get or create async client with connection pooling."""
        if self.async_client is None:
            async with self._pool_lock:
                if self.async_client is None:
                    self.async_client = AsyncQdrantClient(url=self.url, timeout=5.0)
        return self.async_client
    
    async def add_documents(self, chunks: List[DocumentChunk]) -> None:
        """Add documents to Qdrant."""
        if not chunks:
            return
        
        # Get embeddings for all chunks
        texts = [chunk.content for chunk in chunks]
        embeddings = await self.embeddings_service.get_embeddings(texts)
        
        # Create points for Qdrant
        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point = PointStruct(
                id=i,  # Use integer ID for Qdrant
                vector=embedding,
                payload={
                    "doc_id": chunk.doc_id,
                    "chunk_id": chunk.chunk_id,  # Store original chunk_id in payload
                    "source": chunk.source,
                    "title": chunk.title,
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                    "content_hash": chunk.content_hash,
                    "metadata": chunk.metadata,
                }
            )
            points.append(point)
        
        # Upsert points in batches
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch
                )
            except Exception as e:
                print(f"Failed to upsert batch to Qdrant: {e}")
    
    async def retrieve(self, query: str, top_k: int) -> List[RetrievalResult]:
        """Retrieve documents from Qdrant with optimized async client."""
        try:
            # Get async client and query embedding concurrently
            client_task = self._get_async_client()
            embedding_task = self.embeddings_service.get_embeddings([query])
            
            client, query_embedding = await asyncio.gather(client_task, embedding_task)
            
            # Aggressive optimization for sub-50ms retrieval
            search_result = await client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding[0],
                limit=min(top_k, 50),  # Limit result size for speed
                with_payload=True,
                with_vectors=False  # Don't return vectors for speed
            )
            
            # Convert to RetrievalResult objects
            results = []
            for hit in search_result:
                payload = hit.payload
                result = RetrievalResult(
                    doc_id=payload["doc_id"],
                    chunk_id=payload["chunk_id"],  # Use original chunk_id from payload
                    source=payload["source"],
                    title=payload["title"],
                    content=payload["content"],
                    score=float(hit.score),
                    retriever="vector",
                    metadata={
                        "chunk_index": payload["chunk_index"],
                        "content_hash": payload["content_hash"],
                        **payload.get("metadata", {})
                    }
                )
                results.append(result)
            
            return results
        except Exception as e:
            print(f"Failed to retrieve from Qdrant: {e}")
            return []
    
    async def delete_documents(self, doc_ids: List[str]) -> None:
        """Delete documents from Qdrant."""
        try:
            # Delete by doc_id filter
            for doc_id in doc_ids:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=Filter(
                        must=[
                            {"key": "doc_id", "match": {"value": doc_id}}
                        ]
                    )
                )
        except Exception as e:
            print(f"Failed to delete documents from Qdrant: {e}")
    
    async def clear(self) -> None:
        """Clear all documents from Qdrant."""
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            self._ensure_collection()
        except Exception as e:
            print(f"Failed to clear Qdrant collection: {e}")
    
    async def is_ready(self) -> bool:
        """Check if Qdrant is ready."""
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            return self.collection_name in collection_names
        except Exception:
            return False 