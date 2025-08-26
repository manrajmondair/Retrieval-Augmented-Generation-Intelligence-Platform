import time
import asyncio
import hashlib
from typing import List, Optional
from app.rag.retrievers.base import BaseRetriever
from app.rag.retrievers.bm25 import BM25Retriever
from app.rag.retrievers.vector_qdrant import QdrantRetriever
from app.rag.fusion import FusionEngine
from app.rag.schemas import DocumentChunk, RetrievalResult, HybridRetrievalResult
from app.core.config import settings
import redis.asyncio as redis


class HybridRetriever(BaseRetriever):
    """Hybrid retriever combining BM25 and vector search."""
    
    def __init__(self):
        self.bm25_retriever = BM25Retriever(
            k1=settings.bm25_k1,
            b=settings.bm25_b
        )
        
        # Initialize vector retriever based on config
        if settings.vector_store == "qdrant":
            self.vector_retriever = QdrantRetriever(
                url=settings.qdrant_url,
                collection_name=settings.qdrant_collection
            )
        else:
            # TODO: Add Chroma and Pinecone support
            raise NotImplementedError(f"Vector store {settings.vector_store} not implemented")
        
        self.fusion_engine = FusionEngine()
        
        # Initialize Redis cache for performance
        self.redis_client = None
        self.cache_ttl = settings.cache_ttl_sec
    
    async def add_documents(self, chunks: List[DocumentChunk]) -> None:
        """Add documents to both BM25 and vector retrievers concurrently."""
        # Add to both retrievers in parallel for speed
        await asyncio.gather(
            self.bm25_retriever.add_documents(chunks),
            self.vector_retriever.add_documents(chunks)
        )
    
    async def _get_cache_key(self, query: str, top_k: int, fusion_method: str) -> str:
        """Generate cache key for query."""
        key_data = f"{query}:{top_k}:{fusion_method}:{settings.vector_store}"
        return f"rag_cache:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    async def _get_redis_client(self):
        """Get Redis client, initializing if needed."""
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(settings.redis_url)
            except Exception:
                self.redis_client = None
        return self.redis_client

    async def retrieve(self, query: str, top_k: int, fusion_method: str = "rrf") -> HybridRetrievalResult:
        """Retrieve documents using hybrid approach with caching and parallel execution."""
        start_time = time.time()
        
        # Check cache first
        cache_key = await self._get_cache_key(query, top_k, fusion_method)
        redis_client = await self._get_redis_client()
        
        if redis_client:
            try:
                cached_result = await redis_client.get(cache_key)
                if cached_result:
                    import json
                    cached_data = json.loads(cached_result)
                    cached_data["retrieval_debug"]["cache_hit"] = True
                    cached_data["retrieval_debug"]["retrieval_time_ms"] = (time.time() - start_time) * 1000
                    return HybridRetrievalResult(**cached_data)
            except Exception:
                pass  # Continue without cache on error
        
        # Run both retrievers in parallel for maximum speed
        retrieval_start = time.time()
        
        # Use asyncio.gather for true parallel execution
        bm25_results, vector_results = await asyncio.gather(
            self.bm25_retriever.retrieve(query, top_k),
            self.vector_retriever.retrieve(query, top_k),
            return_exceptions=True  # Continue even if one fails
        )
        
        # Handle exceptions from retrievers
        if isinstance(bm25_results, Exception):
            print(f"BM25 retriever error: {bm25_results}")
            bm25_results = []
        if isinstance(vector_results, Exception):
            print(f"Vector retriever error: {vector_results}")
            vector_results = []
        
        parallel_time = (time.time() - retrieval_start) * 1000
        
        # Fuse results
        if fusion_method == "rrf":
            fused_result = self.fusion_engine.fuse_results(
                bm25_results, vector_results, "rrf", k=settings.hybrid_rrf_k
            )
        elif fusion_method == "weighted":
            fused_result = self.fusion_engine.fuse_results(
                bm25_results, vector_results, "weighted",
                bm25_weight=settings.hybrid_weight_bm25,
                vector_weight=settings.hybrid_weight_vector
            )
        else:
            raise ValueError(f"Unknown fusion method: {fusion_method}")
        
        retrieval_time = (time.time() - start_time) * 1000
        
        # Add detailed timing info to debug
        fused_result.retrieval_debug.update({
            "retrieval_time_ms": retrieval_time,
            "parallel_retrieval_ms": parallel_time,
            "bm25_count": len(bm25_results) if bm25_results else 0,
            "vector_count": len(vector_results) if vector_results else 0,
            "fused_count": len(fused_result.results),
            "cache_hit": False,
            "parallel_execution": True
        })
        
        # Cache the result for future queries
        if redis_client:
            try:
                import json
                cache_data = fused_result.dict()
                await redis_client.setex(cache_key, self.cache_ttl, json.dumps(cache_data))
            except Exception:
                pass  # Continue without caching on error
        
        return fused_result
    
    async def delete_documents(self, doc_ids: List[str]) -> None:
        """Delete documents from both retrievers concurrently."""
        await asyncio.gather(
            self.bm25_retriever.delete_documents(doc_ids),
            self.vector_retriever.delete_documents(doc_ids)
        )
    
    async def clear(self) -> None:
        """Clear all documents from both retrievers concurrently."""
        await asyncio.gather(
            self.bm25_retriever.clear(),
            self.vector_retriever.clear()
        )
    
    async def is_ready(self) -> bool:
        """Check if both retrievers are ready concurrently."""
        bm25_ready, vector_ready = await asyncio.gather(
            self.bm25_retriever.is_ready(),
            self.vector_retriever.is_ready()
        )
        return bm25_ready and vector_ready
    
    async def get_retriever_status(self) -> dict:
        """Get status of individual retrievers concurrently."""
        bm25_ready, vector_ready = await asyncio.gather(
            self.bm25_retriever.is_ready(),
            self.vector_retriever.is_ready()
        )
        
        status = {
            "bm25_ready": bm25_ready,
            "vector_ready": vector_ready,
            "hybrid_ready": bm25_ready and vector_ready,
            "vector_store": settings.vector_store,
            "fusion_method": settings.hybrid_fusion,
        }
        
        # Add cache statistics if available
        if hasattr(self.bm25_retriever, 'get_cache_stats'):
            status['bm25_cache_stats'] = self.bm25_retriever.get_cache_stats()
        
        return status 