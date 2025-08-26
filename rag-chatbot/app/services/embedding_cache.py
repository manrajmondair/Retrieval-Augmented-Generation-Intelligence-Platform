"""
Pre-computed embeddings cache for ultra-fast retrieval.
"""
import asyncio
import time
import hashlib
import json
import numpy as np
from typing import List, Dict, Optional, Tuple
from app.services.redis_pool import get_redis_pool
from app.services.embeddings import get_embeddings_service


class PreComputedEmbeddingCache:
    """Ultra-fast pre-computed embeddings cache for common queries."""
    
    def __init__(self):
        self.redis_pool = get_redis_pool()
        self.embeddings_service = get_embeddings_service()
        
        # Common query patterns for pre-computation
        self.common_patterns = [
            "what", "how", "why", "when", "where", "who", 
            "explain", "describe", "tell me about", "what is",
            "how does", "what are", "can you", "show me",
            "findings", "results", "conclusion", "summary",
            "key", "main", "important", "significant",
            "data", "analysis", "research", "study",
            "method", "approach", "technique", "process"
        ]
        
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "precomputed_queries": 0,
            "avg_lookup_time_ms": 0.0
        }
    
    def _get_embedding_cache_key(self, query: str) -> str:
        """Generate cache key for embeddings."""
        return f"emb_fast:{hashlib.md5(query.lower().encode()).hexdigest()}"
    
    def _get_query_variations(self, base_query: str) -> List[str]:
        """Generate query variations for pre-computation."""
        variations = [base_query.lower()]
        
        # Add variations with different patterns
        for pattern in self.common_patterns[:10]:  # Limit for speed
            if pattern not in base_query.lower():
                variations.extend([
                    f"{pattern} {base_query}",
                    f"{base_query} {pattern}",
                    f"{pattern} about {base_query}"
                ])
        
        return list(set(variations))[:20]  # Limit to 20 variations
    
    async def precompute_embeddings(self, queries: List[str]) -> int:
        """Pre-compute embeddings for common queries."""
        if not queries:
            return 0
        
        start_time = time.time()
        cached_count = 0
        
        try:
            # Generate all variations
            all_queries = []
            for query in queries:
                all_queries.extend(self._get_query_variations(query))
            
            # Remove duplicates and limit for performance
            unique_queries = list(set(all_queries))[:100]  # Limit to 100 for speed
            
            # Check which are already cached
            cache_keys = [self._get_embedding_cache_key(q) for q in unique_queries]
            existing_cache = await self.redis_pool.batch_get(cache_keys, "embeddings")
            
            # Get embeddings for uncached queries
            uncached_queries = []
            for i, query in enumerate(unique_queries):
                if existing_cache.get(cache_keys[i]) is None:
                    uncached_queries.append(query)
            
            if uncached_queries:
                # Batch compute embeddings
                batch_size = 25  # Optimal batch size for speed
                for i in range(0, len(uncached_queries), batch_size):
                    batch = uncached_queries[i:i + batch_size]
                    
                    try:
                        # Get embeddings from service
                        embeddings = await self.embeddings_service.get_embeddings(batch)
                        
                        # Prepare for batch caching
                        cache_items = {}
                        for j, embedding in enumerate(embeddings):
                            if embedding is not None:
                                query = batch[j]
                                cache_key = self._get_embedding_cache_key(query)
                                # Serialize embedding efficiently
                                embedding_data = json.dumps(embedding).encode('utf-8')
                                cache_items[cache_key] = (embedding_data, 3600)  # 1 hour TTL
                        
                        # Batch cache the embeddings
                        cached_count += await self.redis_pool.batch_set(cache_items, "embeddings")
                        
                        # Small delay to avoid overwhelming the service
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        print(f"Error in batch embedding: {e}")
                        continue
            
            duration = time.time() - start_time
            print(f"Pre-computed {cached_count} embeddings in {duration:.2f}s")
            
            self.stats["precomputed_queries"] += cached_count
            return cached_count
            
        except Exception as e:
            print(f"Error pre-computing embeddings: {e}")
            return cached_count
    
    async def get_cached_embedding(self, query: str) -> Optional[List[float]]:
        """Get cached embedding with ultra-fast lookup."""
        start_time = time.time()
        
        cache_key = self._get_embedding_cache_key(query)
        
        try:
            cached_data = await self.redis_pool.get_with_fallback(cache_key, "embeddings")
            
            if cached_data:
                embedding = json.loads(cached_data.decode('utf-8'))
                self.stats["cache_hits"] += 1
                
                duration_ms = (time.time() - start_time) * 1000
                self._update_lookup_stats(duration_ms)
                
                return embedding
            
        except Exception:
            pass
        
        self.stats["cache_misses"] += 1
        self._update_lookup_stats((time.time() - start_time) * 1000)
        return None
    
    async def cache_embedding(self, query: str, embedding: List[float]) -> bool:
        """Cache a single embedding."""
        try:
            cache_key = self._get_embedding_cache_key(query)
            embedding_data = json.dumps(embedding).encode('utf-8')
            
            return await self.redis_pool.set_with_optimization(
                cache_key, 
                embedding_data, 
                3600,  # 1 hour TTL
                "embeddings"
            )
            
        except Exception:
            return False
    
    async def warm_up_common_queries(self) -> Dict[str, int]:
        """Warm up cache with most common query patterns."""
        common_queries = [
            "what are the key findings",
            "what are the main results",
            "what does this research show",
            "what are the conclusions",
            "what is the methodology",
            "what are the recommendations",
            "what data was collected",
            "what analysis was performed",
            "how does this work",
            "how was this implemented",
            "why is this important",
            "why does this matter",
            "when was this conducted",
            "where was this research done",
            "who conducted this study",
            "explain the approach",
            "describe the method",
            "summarize the findings",
            "tell me about the results",
            "show me the data"
        ]
        
        cached_count = await self.precompute_embeddings(common_queries)
        
        return {
            "queries_processed": len(common_queries),
            "embeddings_cached": cached_count,
            "cache_performance": self.get_stats()
        }
    
    def _update_lookup_stats(self, duration_ms: float):
        """Update lookup performance statistics."""
        total_lookups = self.stats["cache_hits"] + self.stats["cache_misses"]
        if total_lookups > 0:
            current_avg = self.stats["avg_lookup_time_ms"]
            self.stats["avg_lookup_time_ms"] = ((current_avg * (total_lookups - 1)) + duration_ms) / total_lookups
    
    def get_stats(self) -> Dict:
        """Get cache performance statistics."""
        total_lookups = self.stats["cache_hits"] + self.stats["cache_misses"]
        hit_rate = (self.stats["cache_hits"] / total_lookups * 100) if total_lookups > 0 else 0
        
        return {
            "embedding_cache_hit_rate": round(hit_rate, 1),
            "total_lookups": total_lookups,
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "precomputed_queries": self.stats["precomputed_queries"],
            "avg_lookup_time_ms": round(self.stats["avg_lookup_time_ms"], 2)
        }


# Global instance
_embedding_cache = None

def get_embedding_cache() -> PreComputedEmbeddingCache:
    """Get or create the pre-computed embedding cache singleton."""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = PreComputedEmbeddingCache()
    return _embedding_cache