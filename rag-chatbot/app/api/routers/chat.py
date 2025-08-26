import time
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from app.api.deps import require_api_key
from app.api.routers.ingest import get_hybrid_retriever
from app.services.llm import get_llm_service
from app.services.performance_monitor import get_performance_monitor
from app.rag.schemas import ChatStreamRequest

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/stream")
async def chat_stream(
    q: str,
    top_k: int = 12,
    store: str = "qdrant",
    fusion: str = "rrf",
    api_key: str = Depends(require_api_key)
):
    """High-performance stream chat response with Server-Sent Events."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Performance monitoring
    monitor = get_performance_monitor()
    request_id = await monitor.start_request()
    start_time = time.time()
    
    retriever = get_hybrid_retriever()
    llm_service = get_llm_service()
    
    # Check if retriever is ready with fast path
    if not await retriever.is_ready():
        await monitor.end_request(request_id, False, (time.time() - start_time) * 1000)
        raise HTTPException(
            status_code=503, 
            detail="Retriever not ready. Please ingest some documents first."
        )
    
    async def event_generator():
        retrieval_start = time.time()
        try:
            # Parallel execution for better performance
            retrieval_task = asyncio.create_task(
                retriever.retrieve(
                    query=q,
                    top_k=top_k,
                    fusion_method=fusion
                )
            )
            
            # Start citation processing while retrieval completes
            hybrid_result = await retrieval_task
            retrieval_time = (time.time() - retrieval_start) * 1000
            await monitor.record_retrieval_latency(retrieval_time)
            
            # Fast citation formatting (minimal processing)
            citations_data = []
            for i, result in enumerate(hybrid_result.results[:min(top_k, 8)], 1):  # Limit citations for speed
                source_name = result.source.split('/')[-1] if '/' in result.source else result.source
                content_preview = result.content[:150] + "..." if len(result.content) > 150 else result.content
                
                citations_data.append({
                    "id": i,
                    "source": source_name,
                    "title": result.title or source_name,
                    "content": content_preview,
                    "score": round(result.score, 4),
                    "relevance": "High" if result.score > 0.5 else "Medium" if result.score > 0.2 else "Low"
                })
            
            # Send citations immediately
            yield {
                "event": "citations",
                "data": citations_data
            }
            
            # Stream LLM response with latency tracking
            llm_start = time.time()
            token_count = 0
            
            async for token in llm_service.generate_answer_stream(q, hybrid_result.results):
                yield {
                    "event": "message",
                    "data": token
                }
                token_count += 1
            
            llm_time = (time.time() - llm_start) * 1000
            await monitor.record_llm_latency(llm_time)
            
            # Send completion event with minimal debug info
            total_time = (time.time() - start_time) * 1000
            yield {
                "event": "done",
                "data": {
                    "performance": {
                        "total_ms": round(total_time, 1),
                        "retrieval_ms": round(retrieval_time, 1), 
                        "llm_ms": round(llm_time, 1),
                        "tokens": token_count
                    }
                }
            }
            
            # Record successful request
            await monitor.end_request(request_id, True, total_time)
            
        except Exception as e:
            error_time = (time.time() - start_time) * 1000
            await monitor.end_request(request_id, False, error_time)
            yield {
                "event": "error",
                "data": {"error": str(e)}
            }
    
    return EventSourceResponse(event_generator()) 