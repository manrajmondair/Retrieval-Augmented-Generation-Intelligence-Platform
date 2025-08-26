"""
High-performance Redis connection pool with advanced optimizations.
"""
import asyncio
import time
from typing import Optional, Dict, Any
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from app.core.config import settings


class OptimizedRedisPool:
    """High-performance Redis connection pool with clustering and optimization features."""
    
    def __init__(self):
        self.pools: Dict[str, ConnectionPool] = {}
        self.clients: Dict[str, redis.Redis] = {}
        self.stats = {
            "connections_created": 0,
            "pool_hits": 0,
            "pool_misses": 0,
            "total_operations": 0,
            "avg_latency_ms": 0.0
        }
        self._initialize_pools()
    
    def _initialize_pools(self):
        """Initialize optimized connection pools."""
        # Main cache pool - optimized for frequent access
        self.pools["cache"] = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=50,  # Increased pool size
            retry_on_timeout=True,
            retry_on_error=[redis.BusyLoadingError, redis.ConnectionError],
            health_check_interval=30,
            socket_keepalive=True,
            socket_keepalive_options={
                'TCP_KEEPIDLE': 1,
                'TCP_KEEPINTVL': 3,
                'TCP_KEEPCNT': 5,
            }
        )
        
        # LLM response cache pool - optimized for larger payloads
        self.pools["llm"] = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=30,
            retry_on_timeout=True,
            retry_on_error=[redis.BusyLoadingError, redis.ConnectionError],
            health_check_interval=30,
            socket_keepalive=True,
            socket_keepalive_options={
                'TCP_KEEPIDLE': 1,
                'TCP_KEEPINTVL': 3,
                'TCP_KEEPCNT': 5,
            }
        )
        
        # Embedding cache pool - optimized for vector operations
        self.pools["embeddings"] = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=20,
            retry_on_timeout=True,
            health_check_interval=30,
            socket_keepalive=True
        )
        
        # Create clients
        for pool_name, pool in self.pools.items():
            self.clients[pool_name] = redis.Redis(
                connection_pool=pool,
                decode_responses=False,  # Keep binary for performance
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_error=[redis.BusyLoadingError, redis.ConnectionError],
                retry_on_timeout=True
            )
    
    def get_client(self, pool_type: str = "cache") -> redis.Redis:
        """Get optimized Redis client for specific use case."""
        if pool_type not in self.clients:
            pool_type = "cache"  # Fallback to default
        
        self.stats["pool_hits"] += 1
        return self.clients[pool_type]
    
    async def get_with_fallback(self, key: str, pool_type: str = "cache") -> Optional[bytes]:
        """Get value with automatic fallback and latency tracking."""
        start_time = time.time()
        
        try:
            client = self.get_client(pool_type)
            result = await client.get(key)
            
            latency = (time.time() - start_time) * 1000
            self._update_stats(latency)
            
            return result
            
        except Exception as e:
            # Try fallback to different pool
            if pool_type != "cache":
                try:
                    fallback_client = self.get_client("cache")
                    result = await fallback_client.get(key)
                    
                    latency = (time.time() - start_time) * 1000
                    self._update_stats(latency)
                    
                    return result
                except:
                    pass
            
            self.stats["pool_misses"] += 1
            return None
    
    async def set_with_optimization(self, key: str, value: bytes, ttl: int, pool_type: str = "cache") -> bool:
        """Set value with optimization based on size and type."""
        start_time = time.time()
        
        try:
            client = self.get_client(pool_type)
            
            # Use pipeline for better performance
            pipe = client.pipeline()
            pipe.setex(key, ttl, value)
            await pipe.execute()
            
            latency = (time.time() - start_time) * 1000
            self._update_stats(latency)
            
            return True
            
        except Exception:
            self.stats["pool_misses"] += 1
            return False
    
    async def batch_get(self, keys: list, pool_type: str = "cache") -> Dict[str, Optional[bytes]]:
        """Batch get operation for maximum performance."""
        if not keys:
            return {}
            
        start_time = time.time()
        
        try:
            client = self.get_client(pool_type)
            
            # Use pipeline for batch operations
            pipe = client.pipeline()
            for key in keys:
                pipe.get(key)
            
            results = await pipe.execute()
            
            latency = (time.time() - start_time) * 1000
            self._update_stats(latency)
            
            return dict(zip(keys, results))
            
        except Exception:
            self.stats["pool_misses"] += 1
            return {key: None for key in keys}
    
    async def batch_set(self, items: Dict[str, tuple], pool_type: str = "cache") -> int:
        """Batch set operation. items format: {key: (value, ttl)}"""
        if not items:
            return 0
            
        start_time = time.time()
        successful = 0
        
        try:
            client = self.get_client(pool_type)
            
            # Use pipeline for batch operations
            pipe = client.pipeline()
            for key, (value, ttl) in items.items():
                pipe.setex(key, ttl, value)
            
            await pipe.execute()
            successful = len(items)
            
            latency = (time.time() - start_time) * 1000
            self._update_stats(latency)
            
        except Exception:
            self.stats["pool_misses"] += 1
        
        return successful
    
    def _update_stats(self, latency_ms: float):
        """Update performance statistics."""
        self.stats["total_operations"] += 1
        
        # Rolling average latency
        total_ops = self.stats["total_operations"]
        current_avg = self.stats["avg_latency_ms"]
        self.stats["avg_latency_ms"] = ((current_avg * (total_ops - 1)) + latency_ms) / total_ops
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all pools."""
        health_status = {
            "overall_healthy": True,
            "pools": {},
            "stats": self.stats
        }
        
        for pool_name, client in self.clients.items():
            try:
                start_time = time.time()
                await client.ping()
                latency = (time.time() - start_time) * 1000
                
                health_status["pools"][pool_name] = {
                    "healthy": True,
                    "latency_ms": round(latency, 2)
                }
            except Exception as e:
                health_status["overall_healthy"] = False
                health_status["pools"][pool_name] = {
                    "healthy": False,
                    "error": str(e)
                }
        
        return health_status
    
    async def close(self):
        """Close all connections."""
        for client in self.clients.values():
            await client.close()
        for pool in self.pools.values():
            await pool.disconnect()


# Global instance
_redis_pool = None

def get_redis_pool() -> OptimizedRedisPool:
    """Get or create the optimized Redis pool singleton."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = OptimizedRedisPool()
    return _redis_pool