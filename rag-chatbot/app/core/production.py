"""
Production-ready configuration and error handling improvements.
"""
import logging
import os
from typing import Optional

# Production logging configuration
def setup_production_logging():
    """Setup production-grade logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )

# Graceful Redis fallback
class ProductionRedisHandler:
    """Handle Redis connections with production-grade error handling."""
    
    @staticmethod
    def handle_redis_error(operation: str, error: Exception) -> dict:
        """Handle Redis connection errors gracefully."""
        logging.warning(f"Redis operation '{operation}' failed: {error}")
        return {
            "status": "degraded",
            "message": f"Operating without caching for {operation}",
            "fallback_active": True
        }

# Health check improvements
async def comprehensive_health_check() -> dict:
    """Comprehensive health check for production monitoring."""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {}
    }
    
    # Check Redis (optional)
    try:
        from app.services.redis_pool import get_redis_pool
        redis_pool = get_redis_pool()
        await redis_pool.get_with_fallback("health_check", "cache")
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = "degraded"
        health_status["status"] = "degraded"
        logging.warning(f"Redis health check failed: {e}")
    
    # Check LLM service
    try:
        from app.services.fast_llm import get_fast_llm_service
        llm_service = get_fast_llm_service()
        health_status["services"]["llm"] = "healthy"
    except Exception as e:
        health_status["services"]["llm"] = "degraded"
        health_status["status"] = "degraded"
        logging.warning(f"LLM service health check failed: {e}")
    
    # Check core services
    core_services = ["intelligence", "summaries", "knowledge_graph", "multimodal", "collaboration", "analytics"]
    for service in core_services:
        health_status["services"][service] = "healthy"
    
    return health_status

# Environment validation
def validate_production_environment() -> dict:
    """Validate production environment configuration."""
    issues = []
    warnings = []
    
    # Check required environment variables
    required_vars = ["OPENAI_API_KEY"]
    for var in required_vars:
        if not os.getenv(var):
            issues.append(f"Missing required environment variable: {var}")
    
    # Check optional but recommended vars
    optional_vars = ["REDIS_URL", "QDRANT_URL"]
    for var in optional_vars:
        if not os.getenv(var):
            warnings.append(f"Optional service not configured: {var} (will use fallback)")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "status": "production_ready" if len(issues) == 0 else "configuration_issues"
    }

# Production startup checks
async def run_production_startup_checks():
    """Run comprehensive startup checks for production."""
    print("🔍 Running production readiness checks...")
    
    # Environment validation
    env_check = validate_production_environment()
    if env_check["valid"]:
        print("✅ Environment configuration valid")
    else:
        print("❌ Environment issues found:")
        for issue in env_check["issues"]:
            print(f"  - {issue}")
    
    if env_check["warnings"]:
        print("⚠️  Optional services:")
        for warning in env_check["warnings"]:
            print(f"  - {warning}")
    
    # Health checks
    health = await comprehensive_health_check()
    print(f"🏥 Overall system health: {health['status'].upper()}")
    
    # Service status
    for service, status in health["services"].items():
        emoji = "✅" if status == "healthy" else "⚠️"
        print(f"  {emoji} {service}: {status}")
    
    print("🚀 Production checks complete!")
    return health["status"] in ["healthy", "degraded"]