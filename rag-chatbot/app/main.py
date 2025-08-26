import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
import httpx

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.security import api_key_auth_middleware
from app.api.routers.health import router as health_router
from app.api.routers.ingest import router as ingest_router
from app.api.routers.query import router as query_router
from app.api.routers.chat import router as chat_router
from app.api.routers.ultra_fast_chat import router as ultra_chat_router
from app.api.routers.intelligence import router as intelligence_router
from app.api.routers.knowledge_graph import router as knowledge_router
from app.api.routers.multimodal import router as multimodal_router
from app.api.routers.summaries import router as summaries_router
from app.api.routers.collaboration import router as collaboration_router
from app.api.routers.analytics import router as analytics_router
from app.services.cache_prewarmer import get_cache_prewarmer
from app.rag.retrievers.hybrid import HybridRetriever


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting RAG Chatbot with performance optimizations...")
    
    # Initialize HTTP client with connection pooling
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
    app.state.http_client = httpx.AsyncClient(
        limits=limits,
        timeout=httpx.Timeout(10.0),
        http2=True  # Enable HTTP/2 support
    )
    
    # Start cache prewarming in background
    cache_prewarmer = get_cache_prewarmer()
    hybrid_retriever = HybridRetriever()
    
    # Wait a bit for services to initialize
    await asyncio.sleep(2)
    
    # Prewarm caches in background task
    asyncio.create_task(_prewarm_caches(cache_prewarmer, hybrid_retriever))
    
    yield
    
    # Shutdown
    print("🛑 Shutting down RAG Chatbot...")
    await app.state.http_client.aclose()

async def _prewarm_caches(cache_prewarmer, hybrid_retriever):
    """Background task to prewarm caches."""
    try:
        # Wait for retrievers to be ready
        for _ in range(30):  # Wait up to 30 seconds
            if await hybrid_retriever.is_ready():
                break
            await asyncio.sleep(1)
        
        if await hybrid_retriever.is_ready():
            await cache_prewarmer.prewarm_all(hybrid_retriever)
        else:
            print("⚠️ Retriever not ready, skipping cache prewarming")
    except Exception as e:
        print(f"Error during cache prewarming: {e}")

def create_app() -> FastAPI:
    # Setup logging
    setup_logging()
    
    app = FastAPI(
        title="RAG Chatbot", 
        version="0.1.0",
        lifespan=lifespan,  # Add lifespan context manager
        # Add upload limits to prevent network issues
        docs_url="/docs" if settings.app_env == "dev" else None,
        redoc_url="/redoc" if settings.app_env == "dev" else None
    )

    # Add API key auth middleware first (this runs last in the chain)
    app.middleware("http")(api_key_auth_middleware)

    # Add request size limiting middleware
    @app.middleware("http")
    async def limit_upload_size(request, call_next):
        if request.method == "POST" and any(path in str(request.url) for path in ["/ingest", "/multimodal/upload"]):
            content_length = request.headers.get("content-length")
            if content_length:
                content_length = int(content_length)
                max_size = 50 * 1024 * 1024  # 50MB total request limit
                if content_length > max_size:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request too large. Maximum 50MB total."}
                    )
        return await call_next(request)

    # Optimized CORS middleware for performance (this runs first in the chain)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_env == "dev" else ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["GET", "POST"] if settings.app_env != "dev" else ["*"],
        allow_headers=["x-api-key", "content-type", "accept"] if settings.app_env != "dev" else ["*"],
        max_age=3600  # Cache preflight requests for 1 hour
    )

    # Include routers
    app.include_router(health_router)
    app.include_router(ingest_router)
    app.include_router(query_router)
    app.include_router(chat_router)
    app.include_router(ultra_chat_router)  # Ultra-fast optimized endpoints
    app.include_router(intelligence_router)  # Document intelligence features
    app.include_router(knowledge_router)  # Knowledge graph visualization
    app.include_router(multimodal_router)  # Multi-modal document processing
    app.include_router(summaries_router)  # One-click smart summaries
    app.include_router(collaboration_router)  # Real-time collaboration & sharing
    app.include_router(analytics_router)  # Advanced usage analytics

    # Mount static files under /static only
    app.mount("/static", StaticFiles(directory="web"), name="static")

    # Serve index at root
    @app.get("/")
    def index() -> FileResponse:
        return FileResponse("web/index.html")
    
    # Serve premium UI at /premium
    @app.get("/premium")
    def premium() -> FileResponse:
        return FileResponse("web/premium.html")
    
    # Serve multimodal UI at /multimodal
    @app.get("/multimodal")
    def multimodal() -> FileResponse:
        return FileResponse("web/multimodal.html")
    
    # Serve test upload page at /test-upload
    @app.get("/test-upload")
    def test_upload() -> FileResponse:
        return FileResponse("web/test_upload.html")

    # Performance monitoring
    if settings.prometheus_enabled:
        instrumentator = Instrumentator(
            should_group_status_codes=False,
            should_ignore_untemplated=True,
            should_respect_env_var=True,
            should_instrument_requests_inprogress=True,
            excluded_handlers=["/health", "/metrics", "/static/*"],
            env_var_name="ENABLE_METRICS",
            inprogress_name="fastapi_inprogress",
            inprogress_labels=True,
        )
        instrumentator.instrument(app).expose(app)
    
    # Add performance optimization endpoints
    @app.get("/performance/cache-stats")
    async def get_cache_stats():
        """Get cache performance statistics."""
        cache_prewarmer = get_cache_prewarmer()
        return cache_prewarmer.get_stats()
    
    @app.get("/performance/metrics")
    async def get_performance_metrics():
        """Get real-time performance metrics."""
        from app.services.performance_monitor import get_performance_monitor
        monitor = get_performance_monitor()
        return monitor.get_current_stats()
    
    @app.get("/performance/health")
    async def get_system_health():
        """Get overall system health score."""
        from app.services.performance_monitor import get_performance_monitor
        monitor = get_performance_monitor()
        return monitor.get_health_score()
    
    @app.post("/performance/prewarm")
    async def trigger_prewarm():
        """Manually trigger cache prewarming."""
        cache_prewarmer = get_cache_prewarmer()
        hybrid_retriever = HybridRetriever()
        
        if not await hybrid_retriever.is_ready():
            return {"error": "Retriever not ready"}
        
        stats = await cache_prewarmer.prewarm_all(hybrid_retriever)
        return {"message": "Cache prewarming triggered", "stats": stats}

    return app


app = create_app()

