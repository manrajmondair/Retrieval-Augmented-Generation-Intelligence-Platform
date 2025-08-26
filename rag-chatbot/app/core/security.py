from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from app.core.config import settings


async def api_key_auth_middleware(request: Request, call_next: Callable):
    # Exclude UI routes and static files from API key auth
    if request.url.path in {"/healthz", "/metrics", "/", "/premium", "/multimodal", "/test-upload"} or request.url.path.startswith("/static"):
        return await call_next(request)
    
    # Allow CORS preflight requests (OPTIONS) to pass through without authentication
    if request.method == "OPTIONS":
        return await call_next(request)

    api_key = request.headers.get("x-api-key")
    if not api_key or api_key != settings.api_key:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    response: Response = await call_next(request)
    return response

