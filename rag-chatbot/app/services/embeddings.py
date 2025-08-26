from typing import List, Dict, Optional
import hashlib
import asyncio
import time
from functools import lru_cache
import openai
import redis.asyncio as redis
from app.core.config import settings

_embeddings_service = None


class EmbeddingsService:
    """Service for generating embeddings."""
    
    def __init__(self):
        if settings.embeddings_provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key required for embeddings")
            openai.api_key = settings.openai_api_key
            self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)  # Use async client
            self.model = settings.embeddings_model
        else:
            raise NotImplementedError(f"Embeddings provider {settings.embeddings_provider} not implemented")
        
        # Initialize caching
        self.memory_cache: Dict[str, List[float]] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.redis_client: Optional[redis.Redis] = None
        
        # Batch optimization
        self.batch_requests: Dict[str, asyncio.Event] = {}
        self.batch_results: Dict[str, List[List[float]]] = {}
        
        # Initialize Redis connection
        asyncio.create_task(self._init_redis())
    
    async def _init_redis(self):
        """Initialize Redis connection for persistent caching."""
        try:
            self.redis_client = redis.from_url(settings.redis_url)
            await self.redis_client.ping()
        except Exception:
            self.redis_client = None
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return f"emb:{hashlib.md5(text.encode()).hexdigest()}"
    
    async def _get_from_cache(self, text: str) -> Optional[List[float]]:
        """Get embedding from cache (memory first, then Redis)."""
        cache_key = self._get_cache_key(text)
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            self.cache_hits += 1
            return self.memory_cache[cache_key]
        
        # Check Redis cache
        if self.redis_client:
            try:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    import json
                    embedding = json.loads(cached)
                    # Store in memory cache for faster access
                    self.memory_cache[cache_key] = embedding
                    self.cache_hits += 1
                    return embedding
            except Exception:
                pass
        
        return None
    
    async def _store_in_cache(self, text: str, embedding: List[float]):
        """Store embedding in cache."""
        cache_key = self._get_cache_key(text)
        
        # Store in memory cache (with size limit)
        if len(self.memory_cache) < 1000:  # Limit memory cache size
            self.memory_cache[cache_key] = embedding
        
        # Store in Redis cache
        if self.redis_client:
            try:
                import json
                await self.redis_client.setex(
                    cache_key, 
                    3600,  # 1 hour TTL
                    json.dumps(embedding)
                )
            except Exception:
                pass

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a list of texts with aggressive caching."""
        if not texts:
            return []
        
        # Check cache for all texts first
        cached_results = {}
        uncached_texts = []
        
        for i, text in enumerate(texts):
            cached = await self._get_from_cache(text)
            if cached is not None:
                cached_results[i] = cached
            else:
                uncached_texts.append((i, text))
        
        # If all texts are cached, return immediately
        if not uncached_texts:
            return [cached_results[i] for i in range(len(texts))]
        
        # Get embeddings for uncached texts
        try:
            uncached_text_list = [text for _, text in uncached_texts]
            
            response = await self.client.embeddings.create(
                model=self.model,
                input=uncached_text_list
            )
            
            new_embeddings = [embedding.embedding for embedding in response.data]
            
            # Store new embeddings in cache and results
            for (original_idx, text), embedding in zip(uncached_texts, new_embeddings):
                cached_results[original_idx] = embedding
                await self._store_in_cache(text, embedding)
                self.cache_misses += 1
            
            # Return embeddings in original order
            return [cached_results[i] for i in range(len(texts))]
            
        except Exception as e:
            print(f"Failed to get embeddings: {e}")
            # Return zero vectors as fallback for uncached texts
            for original_idx, _ in uncached_texts:
                cached_results[original_idx] = [0.0] * 1536
                self.cache_misses += 1
            
            return [cached_results[i] for i in range(len(texts))]
    
    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text with caching."""
        # Check cache first
        cached = await self._get_from_cache(text)
        if cached is not None:
            return cached
        
        # Get from API
        embeddings = await self.get_embeddings([text])
        return embeddings[0] if embeddings else [0.0] * 1536
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get caching statistics."""
        total = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total * 100) if total > 0 else 0
        
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate_percent": round(hit_rate, 1),
            "memory_cache_size": len(self.memory_cache)
        }


def get_embeddings_service() -> EmbeddingsService:
    """Get or create the embeddings service singleton."""
    global _embeddings_service
    if _embeddings_service is None:
        _embeddings_service = EmbeddingsService()
    return _embeddings_service 