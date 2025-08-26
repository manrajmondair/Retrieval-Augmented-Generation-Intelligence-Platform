from typing import List, AsyncGenerator, Dict, Optional
import hashlib
import asyncio
import json
import openai
import redis.asyncio as redis
from app.core.config import settings
from app.rag.schemas import RetrievalResult

_llm_service = None


class LLMService:
    """Service for LLM interactions."""
    
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key required for LLM")
        openai.api_key = settings.openai_api_key
        
        # Optimized async client with connection pooling
        self.client = openai.AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=10.0,  # Faster timeout
            max_retries=1   # Reduce retries for speed
        )
        self.model = settings.openai_model
        self.temperature = settings.openai_temperature
        
        # Aggressive caching for responses
        self.response_cache: Dict[str, str] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.redis_client: Optional[redis.Redis] = None
        
        # Initialize Redis connection
        asyncio.create_task(self._init_redis())
    
    def _build_context(self, results: List[RetrievalResult]) -> str:
        """Build well-formatted context string from retrieval results."""
        if not results:
            return ""
        
        context_parts = []
        for i, result in enumerate(results, 1):
            # Clean up source path to show just filename
            source_name = result.source.split('/')[-1] if '/' in result.source else result.source
            
            context_parts.append(f"[{i}] Source: {source_name}")
            if result.title and result.title != source_name:
                context_parts.append(f"Title: {result.title}")
            context_parts.append(f"Content: {result.content.strip()}")
            context_parts.append("")  # Empty line between sources
        
        return "\n".join(context_parts)
    
    async def _init_redis(self):
        """Initialize Redis connection for response caching."""
        try:
            self.redis_client = redis.from_url(settings.redis_url)
            await self.redis_client.ping()
        except Exception:
            self.redis_client = None
    
    def _get_cache_key(self, query: str, context: str) -> str:
        """Generate cache key for query and context."""
        combined = f"{query}|{context}"
        return f"llm:{hashlib.md5(combined.encode()).hexdigest()}"
    
    async def _get_cached_response(self, query: str, context: str) -> Optional[str]:
        """Get cached response if available."""
        cache_key = self._get_cache_key(query, context)
        
        # Check memory cache first
        if cache_key in self.response_cache:
            self.cache_hits += 1
            return self.response_cache[cache_key]
        
        # Check Redis cache
        if self.redis_client:
            try:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    response = cached.decode()
                    # Store in memory cache for faster access
                    self.response_cache[cache_key] = response
                    self.cache_hits += 1
                    return response
            except Exception:
                pass
        
        return None
    
    async def _cache_response(self, query: str, context: str, response: str):
        """Cache the response."""
        cache_key = self._get_cache_key(query, context)
        
        # Store in memory cache (with size limit)
        if len(self.response_cache) < 500:  # Limit memory cache size
            self.response_cache[cache_key] = response
        
        # Store in Redis cache
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    cache_key,
                    1800,  # 30 minutes TTL
                    response
                )
            except Exception:
                pass

    def _build_system_prompt(self) -> str:
        """Build system prompt optimized for user experience."""
        return """You are a helpful AI assistant that answers questions using provided context. 

RULES:
1. Use ONLY the provided context to answer
2. Provide comprehensive, well-structured answers
3. Include citations as [1], [2], etc. referring to source numbers
4. If context is insufficient, say "I don't have enough information to fully answer this question"
5. For research papers, summarize key findings, methodology, and conclusions
6. Format your response clearly with bullet points or paragraphs as appropriate
7. Be accurate and cite specific information from the sources"""
    
    async def generate_answer(self, query: str, results: List[RetrievalResult]) -> str:
        """Generate an answer from retrieved context with aggressive caching."""
        if not results:
            return "I don't have enough information to answer this question."
        
        context = self._build_context(results)
        
        # Check cache first
        cached_response = await self._get_cached_response(query, context)
        if cached_response:
            return cached_response
        
        system_prompt = self._build_system_prompt()
        
        try:
            # Dynamic token allocation based on query complexity
            max_tokens = 150  # Default for simple queries
            if len(results) > 5:  # More comprehensive answer for multiple sources
                max_tokens = 400
            if any(word in query.lower() for word in ['research', 'paper', 'study', 'analysis', 'methodology']):
                max_tokens = 500  # Research papers need detailed summaries
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
                ],
                temperature=0.1,  # Lower temperature for consistency
                max_tokens=max_tokens,   # Dynamic token allocation
                top_p=0.9,       # More focused responses
                frequency_penalty=0.1  # Reduce repetition
            )
            
            answer = response.choices[0].message.content
            self.cache_misses += 1
            
            # Cache the response for future use
            await self._cache_response(query, context, answer)
            
            return answer
            
        except Exception as e:
            print(f"Failed to generate answer: {e}")
            return "I encountered an error while generating an answer."
    
    async def generate_answer_stream(
        self, query: str, results: List[RetrievalResult]
    ) -> AsyncGenerator[str, None]:
        """Generate an answer stream from retrieved context."""
        if not results:
            yield "I don't have enough information to answer this question."
            return
        
        # Fallback: Use non-streaming and simulate streaming by yielding in chunks
        try:
            print("FALLBACK: Using non-streaming approach with word-by-word yielding")
            # Use the working non-streaming method and yield word by word
            context = self._build_context(results)
            system_prompt = self._build_system_prompt()
            
            # Dynamic token allocation  
            max_tokens = 500
            if len(results) > 5:
                max_tokens = 800
            if any(word in query.lower() for word in ['research', 'paper', 'study', 'analysis', 'methodology']):
                max_tokens = 1000
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
                ],
                temperature=0.1,
                max_tokens=max_tokens,
                top_p=0.9,
                frequency_penalty=0.1
            )
            
            answer = response.choices[0].message.content
            
            # Cache the response
            await self._cache_response(query, context, answer)
            
            # Simulate streaming by yielding words with small delays
            words = answer.split()
            for word in words:
                yield word + " "
                await asyncio.sleep(0.01)  # Small delay to simulate streaming
                
        except Exception as e:
            print(f"Failed to generate answer stream: {e}")
            yield "I encountered an error while generating an answer."
    
    async def generate(self, prompt: str, max_tokens: int = 150) -> str:
        """Fast generate method for direct prompts with caching."""
        # Check cache first
        cache_key = f"direct:{hashlib.md5(prompt.encode()).hexdigest()}"
        
        if cache_key in self.response_cache:
            self.cache_hits += 1
            return self.response_cache[cache_key]
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=max_tokens,
                top_p=0.9
            )
            
            answer = response.choices[0].message.content
            self.cache_misses += 1
            
            # Cache for future use
            if len(self.response_cache) < 500:
                self.response_cache[cache_key] = answer
            
            return answer
            
        except Exception as e:
            print(f"Failed to generate: {e}")
            return "Error generating response."
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get LLM caching statistics."""
        total = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total * 100) if total > 0 else 0
        
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate_percent": round(hit_rate, 1),
            "memory_cache_size": len(self.response_cache)
        }


def get_llm_service() -> LLMService:
    """Get or create the LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service 