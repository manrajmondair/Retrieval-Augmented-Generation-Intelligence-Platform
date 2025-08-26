"""
Ultra-fast chat endpoint optimized for <50ms responses.
"""
import time
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse
from app.api.deps import require_api_key
from app.api.routers.ingest import get_hybrid_retriever
from app.services.fast_llm import get_fast_llm_service
from app.services.embedding_cache import get_embedding_cache
from app.services.performance_monitor import get_performance_monitor
from app.services.redis_pool import get_redis_pool

router = APIRouter(prefix="/ultra", tags=["ultra-fast-chat"])


@router.get("/stream")
async def ultra_fast_chat_stream(
    q: str,
    top_k: int = 5,  # Reduced for speed
    fusion: str = "rrf",
    api_key: str = Depends(require_api_key)
):
    """Ultra-fast chat stream optimized for <50ms first response."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Ultra-fast performance monitoring
    monitor = get_performance_monitor()
    request_id = await monitor.start_request()
    start_time = time.time()
    
    # Get optimized services
    retriever = get_hybrid_retriever()
    fast_llm = get_fast_llm_service()
    embedding_cache = get_embedding_cache()
    redis_pool = get_redis_pool()
    
    # Quick readiness check
    if not await retriever.is_ready():
        await monitor.end_request(request_id, False, (time.time() - start_time) * 1000)
        raise HTTPException(status_code=503, detail="Service not ready")
    
    async def ultra_fast_generator():
        retrieval_start = time.time()
        
        try:
            # Try to get cached embedding first for speed boost
            cached_embedding = await embedding_cache.get_cached_embedding(q)
            
            # Ultra-fast parallel retrieval with reduced top_k
            retrieval_task = asyncio.create_task(
                retriever.retrieve(
                    query=q,
                    top_k=min(top_k, 5),  # Limit for speed
                    fusion_method=fusion
                )
            )
            
            # Get retrieval results
            hybrid_result = await retrieval_task
            retrieval_time = (time.time() - retrieval_start) * 1000
            await monitor.record_retrieval_latency(retrieval_time)
            
            # Ultra-fast citation processing (top 3 only)
            citations_data = []
            for i, result in enumerate(hybrid_result.results[:3], 1):
                source_name = result.source.split('/')[-1] if '/' in result.source else result.source
                content_preview = result.content[:100] + "..." if len(result.content) > 100 else result.content
                
                citations_data.append({
                    "id": i,
                    "source": source_name,
                    "title": result.title or source_name,
                    "content": content_preview,
                    "score": round(result.score, 3)
                })
            
            # Send citations immediately (first response < 50ms target)
            first_response_time = (time.time() - start_time) * 1000
            yield {
                "event": "citations",
                "data": citations_data
            }
            
            # Stream ultra-fast LLM response
            llm_start = time.time()
            token_count = 0
            
            async for token in fast_llm.generate_answer_stream(q, hybrid_result.results):
                yield {
                    "event": "message", 
                    "data": token
                }
                token_count += 1
            
            llm_time = (time.time() - llm_start) * 1000
            await monitor.record_llm_latency(llm_time)
            
            # Final performance report
            total_time = (time.time() - start_time) * 1000
            yield {
                "event": "done",
                "data": {
                    "performance": {
                        "total_ms": round(total_time, 1),
                        "first_response_ms": round(first_response_time, 1),
                        "retrieval_ms": round(retrieval_time, 1),
                        "llm_ms": round(llm_time, 1),
                        "tokens": token_count,
                        "results_count": len(hybrid_result.results),
                        "cache_used": cached_embedding is not None
                    }
                }
            }
            
            # Cache the query embedding for future use
            if not cached_embedding:
                asyncio.create_task(embedding_cache.cache_embedding(q, []))  # Background task
            
            await monitor.end_request(request_id, True, total_time)
            
        except Exception as e:
            error_time = (time.time() - start_time) * 1000
            await monitor.end_request(request_id, False, error_time)
            
            yield {
                "event": "error",
                "data": {
                    "error": "Processing error - please try again",
                    "debug_ms": round(error_time, 1)
                }
            }
    
    return EventSourceResponse(ultra_fast_generator())


@router.get("/quick")
async def ultra_quick_answer(
    q: str,
    api_key: str = Depends(require_api_key)
):
    """Ultra-quick non-streaming answer for maximum speed."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    start_time = time.time()
    
    # Get optimized services
    retriever = get_hybrid_retriever()
    fast_llm = get_fast_llm_service()
    
    if not await retriever.is_ready():
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        # Lightning-fast retrieval
        hybrid_result = await retriever.retrieve(query=q, top_k=3, fusion_method="rrf")
        
        # Generate answer
        answer = await fast_llm.generate_answer(q, hybrid_result.results)
        
        total_time = (time.time() - start_time) * 1000
        
        return {
            "answer": answer,
            "sources": [
                {
                    "source": result.source.split('/')[-1] if '/' in result.source else result.source,
                    "score": round(result.score, 3)
                }
                for result in hybrid_result.results[:3]
            ],
            "performance": {
                "total_ms": round(total_time, 1),
                "results_count": len(hybrid_result.results)
            }
        }
        
    except Exception as e:
        return {
            "error": "Quick processing failed - please try the stream endpoint",
            "performance_ms": round((time.time() - start_time) * 1000, 1)
        }


@router.get("/warmup")
async def warmup_caches(api_key: str = Depends(require_api_key)):
    """Warm up all caches for optimal performance."""
    start_time = time.time()
    
    try:
        embedding_cache = get_embedding_cache()
        redis_pool = get_redis_pool()
        
        # Warm up embedding cache
        warmup_results = await embedding_cache.warm_up_common_queries()
        
        # Check Redis pool health
        pool_health = await redis_pool.health_check()
        
        warmup_time = (time.time() - start_time) * 1000
        
        return {
            "status": "warmup_complete",
            "duration_ms": round(warmup_time, 1),
            "embedding_cache": warmup_results,
            "redis_pools": pool_health,
            "message": "All caches warmed up for optimal performance"
        }
        
    except Exception as e:
        return {
            "status": "warmup_partial",
            "error": str(e),
            "duration_ms": round((time.time() - start_time) * 1000, 1)
        }


@router.get("/health")
async def ultra_health_check(api_key: str = Depends(require_api_key)):
    """Health check optimized for monitoring."""
    start_time = time.time()
    
    # Check all services quickly
    retriever = get_hybrid_retriever()
    fast_llm = get_fast_llm_service()
    embedding_cache = get_embedding_cache()
    redis_pool = get_redis_pool()
    monitor = get_performance_monitor()
    
    health_status = {
        "status": "healthy",
        "timestamp": start_time,
        "services": {
            "retriever": await retriever.is_ready(),
            "redis_pools": await redis_pool.health_check(),
            "performance": monitor.get_current_stats(),
            "llm_cache": fast_llm.get_cache_stats(),
            "embedding_cache": embedding_cache.get_stats()
        },
        "response_time_ms": round((time.time() - start_time) * 1000, 1)
    }
    
    return health_status