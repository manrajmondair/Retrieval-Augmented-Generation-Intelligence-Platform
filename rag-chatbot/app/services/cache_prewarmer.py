from typing import List, Dict, Optional
import asyncio
import json
import time
import hashlib
from collections import defaultdict
import redis.asyncio as redis
from app.core.config import settings
from app.services.embeddings import get_embeddings_service
from app.services.llm import get_llm_service


class CachePrewarmer:
    """Smart cache prewarming service for popular queries and patterns."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.embeddings_service = get_embeddings_service()
        self.llm_service = get_llm_service()
        
        # Popular query patterns and variations
        self.common_queries = [
            "What vector stores are supported?",
            "How do I authenticate with the API?",
            "What security practices does the company require?",
            "What is the vacation policy?",
            "How does hybrid retrieval work?",
            "How to setup authentication?",
            "What are the security requirements?",
            "Vacation and time off policy",
            "Hybrid search implementation",
            "Vector database options",
        ]
        
        # Query categories for semantic prewarming
        self.query_categories = {
            "authentication": ["auth", "login", "api key", "authenticate", "security"],
            "vector_stores": ["vector", "database", "qdrant", "chroma", "embedding"],
            "retrieval": ["search", "retrieve", "hybrid", "bm25", "semantic"],
            "policies": ["policy", "vacation", "time off", "benefits", "hr"],
            "technical": ["implementation", "setup", "configure", "install"]
        }
        
        # Statistics tracking
        self.prewarming_stats = {
            "queries_prewarmed": 0,
            "embeddings_cached": 0,
            "responses_cached": 0,
            "last_prewarm_time": None
        }
        
        # Initialize Redis connection
        asyncio.create_task(self._init_redis())
    
    async def _init_redis(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(settings.redis_url)
            await self.redis_client.ping()
        except Exception as e:
            print(f"Failed to initialize Redis for cache prewarmer: {e}")
            self.redis_client = None
    
    def _generate_query_variations(self, base_query: str) -> List[str]:
        """Generate variations of a query for better cache coverage."""
        variations = [base_query]
        
        # Add common question formats
        if not base_query.endswith("?"):
            variations.append(f"{base_query}?")
        
        # Add "How to" variations
        if "how" not in base_query.lower():
            variations.append(f"How to {base_query.lower()}")
        
        # Add "What is" variations
        if "what" not in base_query.lower() and "how" not in base_query.lower():
            variations.append(f"What is {base_query.lower()}?")
        
        # Add shortened versions
        words = base_query.split()
        if len(words) > 3:
            variations.append(" ".join(words[:3]))
        
        return variations
    
    async def prewarm_embeddings(self, queries: List[str]) -> int:
        """Prewarm embedding cache with common queries."""
        if not self.redis_client:
            return 0
        
        cached_count = 0
        
        # Generate all query variations
        all_queries = []
        for query in queries:
            all_queries.extend(self._generate_query_variations(query))
        
        # Remove duplicates
        unique_queries = list(set(all_queries))
        
        try:
            # Get embeddings in batches for efficiency
            batch_size = 20
            for i in range(0, len(unique_queries), batch_size):
                batch = unique_queries[i:i + batch_size]
                
                # Check which queries already have cached embeddings
                uncached_queries = []
                for query in batch:
                    cache_key = f"emb:{hashlib.md5(query.encode()).hexdigest()}"
                    if not await self.redis_client.exists(cache_key):
                        uncached_queries.append(query)
                
                # Get embeddings for uncached queries
                if uncached_queries:
                    await self.embeddings_service.get_embeddings(uncached_queries)
                    cached_count += len(uncached_queries)
                    
                # Small delay to avoid overwhelming the API
                await asyncio.sleep(0.1)
            
            self.prewarming_stats["embeddings_cached"] += cached_count
            return cached_count
            
        except Exception as e:
            print(f"Error prewarming embeddings: {e}")
            return cached_count
    
    async def prewarm_responses(self, retriever, queries: List[str]) -> int:
        """Prewarm LLM response cache with common queries."""
        if not self.redis_client:
            return 0
        
        cached_count = 0
        
        try:
            for query in queries:
                # Generate variations for better coverage
                query_variations = self._generate_query_variations(query)
                
                for variant in query_variations:
                    try:
                        # Perform retrieval to get context
                        hybrid_result = await retriever.retrieve(variant, top_k=5)
                        
                        if hybrid_result.results:
                            # Generate and cache response
                            await self.llm_service.generate_answer(variant, hybrid_result.results)
                            cached_count += 1
                        
                        # Small delay to avoid overwhelming services
                        await asyncio.sleep(0.2)
                        
                    except Exception as e:
                        print(f"Error prewarming response for '{variant}': {e}")
                        continue
            
            self.prewarming_stats["responses_cached"] += cached_count
            return cached_count
            
        except Exception as e:
            print(f"Error prewarming responses: {e}")
            return cached_count
    
    async def prewarm_semantic_cache(self, retriever) -> Dict[str, int]:
        """Prewarm cache with semantically similar queries."""
        stats = {"embeddings": 0, "responses": 0}
        
        try:
            # Generate semantic variations based on categories
            semantic_queries = []
            
            for category, keywords in self.query_categories.items():
                base_templates = [
                    f"Tell me about {keyword}",
                    f"How does {keyword} work?",
                    f"What is {keyword}?",
                    f"Explain {keyword}",
                    f"I need help with {keyword}"
                ]
                
                for keyword in keywords:
                    for template in base_templates:
                        semantic_queries.append(template.format(keyword=keyword))
            
            # Prewarm embeddings for semantic queries
            stats["embeddings"] = await self.prewarm_embeddings(semantic_queries[:50])  # Limit to prevent overload
            
            # Prewarm responses for top semantic queries  
            stats["responses"] = await self.prewarm_responses(retriever, semantic_queries[:20])
            
            return stats
            
        except Exception as e:
            print(f"Error in semantic cache prewarming: {e}")
            return stats
    
    async def prewarm_all(self, retriever) -> Dict[str, int]:
        """Comprehensive cache prewarming strategy."""
        start_time = time.time()
        total_stats = {"embeddings": 0, "responses": 0, "semantic_embeddings": 0, "semantic_responses": 0}
        
        try:
            print("🔥 Starting smart cache prewarming...")
            
            # 1. Prewarm common query embeddings
            print("📊 Prewarming embedding cache...")
            total_stats["embeddings"] = await self.prewarm_embeddings(self.common_queries)
            
            # 2. Prewarm common query responses
            print("🤖 Prewarming LLM response cache...")
            total_stats["responses"] = await self.prewarm_responses(retriever, self.common_queries[:10])
            
            # 3. Prewarm semantic cache
            print("🧠 Prewarming semantic cache...")
            semantic_stats = await self.prewarm_semantic_cache(retriever)
            total_stats["semantic_embeddings"] = semantic_stats["embeddings"]
            total_stats["semantic_responses"] = semantic_stats["responses"]
            
            # Update statistics
            self.prewarming_stats.update({
                "queries_prewarmed": len(self.common_queries),
                "embeddings_cached": total_stats["embeddings"] + total_stats["semantic_embeddings"],
                "responses_cached": total_stats["responses"] + total_stats["semantic_responses"],
                "last_prewarm_time": time.time()
            })
            
            total_time = time.time() - start_time
            
            print(f"✅ Cache prewarming completed in {total_time:.1f}s:")
            print(f"   - Embeddings cached: {total_stats['embeddings'] + total_stats['semantic_embeddings']}")
            print(f"   - Responses cached: {total_stats['responses'] + total_stats['semantic_responses']}")
            
            return total_stats
            
        except Exception as e:
            print(f"Error in comprehensive prewarming: {e}")
            return total_stats
    
    async def analyze_query_patterns(self) -> Dict[str, any]:
        """Analyze query patterns from Redis logs for intelligent prewarming."""
        if not self.redis_client:
            return {}
        
        try:
            # Get all cache keys to analyze patterns
            pattern_stats = defaultdict(int)
            cache_keys = []
            
            # Scan for LLM cache keys
            async for key in self.redis_client.scan_iter(match="llm:*"):
                cache_keys.append(key.decode())
            
            # Scan for embedding cache keys  
            async for key in self.redis_client.scan_iter(match="emb:*"):
                cache_keys.append(key.decode())
            
            return {
                "total_cached_items": len(cache_keys),
                "llm_cache_items": len([k for k in cache_keys if k.startswith("llm:")]),
                "embedding_cache_items": len([k for k in cache_keys if k.startswith("emb:")]),
                "analysis_timestamp": time.time()
            }
            
        except Exception as e:
            print(f"Error analyzing query patterns: {e}")
            return {}
    
    def get_stats(self) -> Dict[str, any]:
        """Get prewarming statistics."""
        return {
            **self.prewarming_stats,
            "cache_hit_rates": {
                "embeddings": self.embeddings_service.get_cache_stats(),
                "llm": self.llm_service.get_cache_stats()
            }
        }


# Global instance
_cache_prewarmer = None

def get_cache_prewarmer() -> CachePrewarmer:
    """Get or create the cache prewarmer singleton."""
    global _cache_prewarmer
    if _cache_prewarmer is None:
        _cache_prewarmer = CachePrewarmer()
    return _cache_prewarmer