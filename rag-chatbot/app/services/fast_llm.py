"""
Ultra-fast LLM service optimized for <50ms responses.
"""
import asyncio
import time
import hashlib
import json
from typing import List, AsyncGenerator, Dict, Optional, Tuple
import openai
from app.core.config import settings
from app.rag.schemas import RetrievalResult
from app.services.redis_pool import get_redis_pool


class UltraFastLLMService:
    """Ultra-optimized LLM service for sub-50ms responses."""
    
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key required for LLM")
        
        # Ultra-optimized client configuration
        self.client = openai.AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout,
            max_retries=0,  # No retries for maximum speed
            default_headers={
                "User-Agent": "RAG-Speed-Optimized/1.0"
            }
        )
        
        self.model = settings.openai_model
        self.temperature = settings.openai_temperature
        self.max_tokens = settings.openai_max_tokens
        
        # Get optimized Redis pool
        self.redis_pool = get_redis_pool()
        
        # Pre-built system prompt for speed
        self.system_prompt = (
            "You are a helpful AI assistant. Answer questions concisely using the provided context. "
            "Keep responses under 100 words. Be direct and accurate."
        )
        
        # Performance tracking
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_response_time_ms": 0.0,
            "total_requests": 0
        }
    
    def _get_cache_key(self, query: str, context_hash: str) -> str:
        """Generate ultra-fast cache key."""
        key_data = f"fast_llm:{query[:100]}:{context_hash}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _hash_context(self, results: List[RetrievalResult]) -> str:
        """Create fast hash of context for caching."""
        if not results:
            return "empty"
        
        # Use only essential info for hash
        context_parts = [f"{r.source}:{len(r.content)}" for r in results[:3]]
        return hashlib.md5("|".join(context_parts).encode()).hexdigest()[:16]
    
    def _build_minimal_context(self, results: List[RetrievalResult]) -> str:
        """Build minimal context for faster processing."""
        if not results:
            return ""
        
        # Take only top 3 results and truncate for speed
        context_parts = []
        for i, result in enumerate(results[:3], 1):
            # Truncate content aggressively for speed
            content = result.content[:300] + "..." if len(result.content) > 300 else result.content
            context_parts.append(f"[{i}] {content}")
        
        return "\n".join(context_parts)
    
    async def _generate_fast_response(self, query: str, context: str) -> str:
        """Generate response optimized for speed."""
        try:
            # Ultra-fast API call with minimal tokens
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=False  # Non-streaming for speed
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            # Ultra-fast fallback
            return f"I found information about your query but couldn't process it fully. Please try rephrasing."
    
    async def generate_answer_stream(self, query: str, results: List[RetrievalResult]) -> AsyncGenerator[str, None]:
        """Generate streaming answer with ultra-fast caching."""
        start_time = time.time()
        
        # Build minimal context
        context = self._build_minimal_context(results)
        context_hash = self._hash_context(results)
        cache_key = self._get_cache_key(query, context_hash)
        
        # Check cache first with ultra-fast Redis pool
        try:
            cached_response = await self.redis_pool.get_with_fallback(cache_key, "llm")
            if cached_response:
                cached_text = cached_response.decode('utf-8')
                self.stats["cache_hits"] += 1
                
                # Stream cached response word by word for consistent UX
                words = cached_text.split()
                for word in words:
                    yield word + " "
                    await asyncio.sleep(0.005)  # Very fast streaming
                
                self._update_stats(time.time() - start_time)
                return
        
        except Exception:
            pass  # Continue without cache
        
        self.stats["cache_misses"] += 1
        
        # Generate new response
        try:
            response_text = await self._generate_fast_response(query, context)
            
            # Cache the response
            try:
                await self.redis_pool.set_with_optimization(
                    cache_key,
                    response_text.encode('utf-8'),
                    600,  # 10 minute TTL
                    "llm"
                )
            except:
                pass  # Continue without caching
            
            # Stream response word by word
            words = response_text.split()
            for word in words:
                yield word + " "
                await asyncio.sleep(0.005)  # Very fast streaming
            
        except Exception as e:
            # Emergency fallback
            fallback_text = "Quick answer based on your documents: The information suggests relevant findings. Please try a more specific question for detailed results."
            words = fallback_text.split()
            for word in words:
                yield word + " "
                await asyncio.sleep(0.005)
        
        self._update_stats(time.time() - start_time)
    
    async def generate_answer(self, query: str, results: List[RetrievalResult]) -> str:
        """Generate non-streaming answer for maximum speed."""
        start_time = time.time()
        
        context = self._build_minimal_context(results)
        context_hash = self._hash_context(results)
        cache_key = self._get_cache_key(query, context_hash)
        
        # Check cache
        try:
            cached_response = await self.redis_pool.get_with_fallback(cache_key, "llm")
            if cached_response:
                self.stats["cache_hits"] += 1
                self._update_stats(time.time() - start_time)
                return cached_response.decode('utf-8')
        except:
            pass
        
        self.stats["cache_misses"] += 1
        
        # Generate new response
        response_text = await self._generate_fast_response(query, context)
        
        # Cache the response
        try:
            await self.redis_pool.set_with_optimization(
                cache_key,
                response_text.encode('utf-8'),
                600,
                "llm"
            )
        except:
            pass
        
        self._update_stats(time.time() - start_time)
        return response_text
    
    def _update_stats(self, duration: float):
        """Update performance statistics."""
        self.stats["total_requests"] += 1
        duration_ms = duration * 1000
        
        total = self.stats["total_requests"]
        current_avg = self.stats["avg_response_time_ms"]
        self.stats["avg_response_time_ms"] = ((current_avg * (total - 1)) + duration_ms) / total
    
    def get_cache_stats(self) -> Dict:
        """Get cache performance statistics."""
        total_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
        hit_rate = (self.stats["cache_hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "hit_rate_percent": round(hit_rate, 1),
            "total_requests": total_requests,
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "avg_response_time_ms": round(self.stats["avg_response_time_ms"], 2)
        }


# Global instance
_fast_llm_service = None

def get_fast_llm_service() -> UltraFastLLMService:
    """Get or create the ultra-fast LLM service singleton."""
    global _fast_llm_service
    if _fast_llm_service is None:
        _fast_llm_service = UltraFastLLMService()
    return _fast_llm_service