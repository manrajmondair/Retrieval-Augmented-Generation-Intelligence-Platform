from fastapi import APIRouter, HTTPException
from app.api.routers.ingest import get_hybrid_retriever

router = APIRouter()


@router.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def ready() -> dict[str, str]:
    """Check if the system is ready to serve requests."""
    try:
        retriever = get_hybrid_retriever()
        status = await retriever.get_retriever_status()
        
        if status["hybrid_ready"]:
            return {"status": "ready"}
        else:
            raise HTTPException(status_code=503, detail="Retriever not ready")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"System not ready: {str(e)}")


@router.get("/config")
def config() -> dict:
    """Get configuration (redacted for security)."""
    from app.core.config import settings
    
    return {
        "app_env": settings.app_env,
        "vector_store": settings.vector_store,
        "hybrid_fusion": settings.hybrid_fusion,
        "bm25_top_k": settings.bm25_top_k,
        "vector_top_k": settings.vector_top_k,
        "prometheus_enabled": settings.prometheus_enabled,
    }

