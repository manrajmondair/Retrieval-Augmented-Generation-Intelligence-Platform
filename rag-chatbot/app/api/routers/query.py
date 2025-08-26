import asyncio
import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from app.api.deps import require_api_key
from app.api.routers.ingest import get_hybrid_retriever
from app.services.llm import get_llm_service
from app.services.query_processor import get_query_processor
from app.services.performance_monitor import get_performance_monitor
from app.rag.schemas import QueryRequest, QueryResponse

router = APIRouter(prefix="/query", tags=["query"])


@router.options("/")
@router.options("")
async def options_query():
    """Handle CORS preflight for query endpoint."""
    return JSONResponse(content={}, status_code=200)


@router.post("/", response_model=QueryResponse)
@router.post("", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    api_key: str = Depends(require_api_key)
) -> QueryResponse:
    """Query the RAG system for an answer with performance monitoring."""
    if not request.q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Start performance monitoring
    performance_monitor = get_performance_monitor()
    request_id = await performance_monitor.start_request()
    start_time = time.time()
    
    retriever = get_hybrid_retriever()
    llm_service = get_llm_service()
    
    # Check if retriever is ready
    if not await retriever.is_ready():
        raise HTTPException(
            status_code=503, 
            detail="Retriever not ready. Please ingest some documents first."
        )
    
    try:
        # Process and optimize query
        query_processor = get_query_processor()
        processed_query = await query_processor.process_query(request.q)
        
        # Get optimized query for better retrieval
        optimized_query = query_processor.optimize_for_retrieval(processed_query)
        
        # Retrieve relevant documents with optimized query
        retrieval_start = time.time()
        hybrid_result = await retriever.retrieve(
            query=optimized_query,
            top_k=request.top_k,
            fusion_method=request.fusion
        )
        retrieval_time = (time.time() - retrieval_start) * 1000
        
        # Record retrieval latency
        await performance_monitor.record_retrieval_latency(retrieval_time)
        
        # Use parallel execution for LLM generation
        llm_start = time.time()
        answer_task = llm_service.generate_answer(
            query=request.q,  # Use original query for answer generation
            results=hybrid_result.results
        )
        
        # Wait for answer generation
        answer = await answer_task
        llm_time = (time.time() - llm_start) * 1000
        
        # Record LLM latency
        await performance_monitor.record_llm_latency(llm_time)
        
        # Calculate total time and record success
        total_time = (time.time() - start_time) * 1000
        await performance_monitor.end_request(request_id, success=True, latency_ms=total_time)
        
        # Record cache statistics
        if hasattr(llm_service, 'get_cache_stats'):
            llm_stats = llm_service.get_cache_stats()
            await performance_monitor.record_cache_stats(
                'llm', llm_stats['hit_rate_percent'], llm_stats['memory_cache_size']
            )
        
        # Add comprehensive debug info
        enhanced_debug = {
            **hybrid_result.retrieval_debug,
            "query_processing": {
                "original_query": request.q,
                "optimized_query": optimized_query,
                "query_type": processed_query.query_type,
                "intent_score": processed_query.intent_score,
                "processing_time_ms": processed_query.processing_time_ms,
                "key_terms": processed_query.key_terms[:5]  # Top 5 key terms
            },
            "performance": {
                "total_time_ms": round(total_time, 2),
                "retrieval_time_ms": round(retrieval_time, 2),
                "llm_time_ms": round(llm_time, 2),
                "request_id": request_id
            }
        }
        
        return QueryResponse(
            answer=answer,
            citations=hybrid_result.results,
            retrieval_debug=enhanced_debug
        )
    
    except Exception as e:
        # Record failed request
        total_time = (time.time() - start_time) * 1000
        await performance_monitor.end_request(request_id, success=False, latency_ms=total_time)
        
        # Log error for monitoring
        error_msg = f"Query failed: {str(e)}"
        print(f"❌ Error in query processing: {error_msg}")
        
        raise HTTPException(status_code=500, detail=error_msg) 