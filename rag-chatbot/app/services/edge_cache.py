"""
Edge caching strategy for ultra-fast local responses.
"""
import time
import asyncio
import hashlib
import json
import sqlite3
import aiosqlite
from typing import Dict, Optional, List, Tuple, Any
from pathlib import Path
from app.services.redis_pool import get_redis_pool


class EdgeCacheManager:
    """Ultra-fast edge caching with local SQLite and Redis tiers."""
    
    def __init__(self):
        self.db_path = Path("/tmp/rag_edge_cache.db")
        self.redis_pool = get_redis_pool()
        
        # Multi-tier cache statistics
        self.stats = {
            "l1_hits": 0,      # Local SQLite cache
            "l2_hits": 0,      # Redis cache  
            "cache_misses": 0,
            "l1_avg_ms": 0.0,
            "l2_avg_ms": 0.0,
            "total_requests": 0
        }
        
        # Initialize local cache
        asyncio.create_task(self._init_local_cache())
    
    async def _init_local_cache(self):
        """Initialize ultra-fast local SQLite cache."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Create optimized tables
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS query_cache (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        ttl REAL NOT NULL,
                        access_count INTEGER DEFAULT 1,
                        last_accessed REAL NOT NULL
                    )
                """)
                
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS retrieval_cache (
                        query_hash TEXT PRIMARY KEY,
                        results TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        ttl REAL NOT NULL
                    )
                """)
                
                # Create indexes for performance
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_query_ttl 
                    ON query_cache(created_at, ttl)
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_access_count 
                    ON query_cache(access_count DESC)
                """)
                
                await db.commit()
                
                # Set SQLite optimizations
                await db.execute("PRAGMA journal_mode=WAL")
                await db.execute("PRAGMA synchronous=NORMAL") 
                await db.execute("PRAGMA cache_size=10000")
                await db.execute("PRAGMA temp_store=memory")
                
        except Exception as e:
            print(f"Error initializing edge cache: {e}")
    
    def _get_cache_key(self, query: str, context_type: str = "query") -> str:
        """Generate optimized cache key."""
        key_data = f"{context_type}:{query.lower()[:200]}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get_cached_response(self, query: str, context_type: str = "query") -> Optional[str]:
        """Get cached response with multi-tier lookup."""
        cache_key = self._get_cache_key(query, context_type)
        current_time = time.time()
        
        # L1 Cache: Ultra-fast local SQLite lookup
        l1_start = time.time()
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT value, created_at, ttl, access_count 
                    FROM query_cache 
                    WHERE key = ? AND created_at + ttl > ?
                """, (cache_key, current_time)) as cursor:
                    row = await cursor.fetchone()
                    
                    if row:
                        value, created_at, ttl, access_count = row
                        
                        # Update access statistics (background)
                        asyncio.create_task(self._update_access_stats(cache_key, access_count))
                        
                        l1_time = (time.time() - l1_start) * 1000
                        self._update_l1_stats(l1_time)
                        self.stats["l1_hits"] += 1
                        
                        return value
                        
        except Exception:
            pass  # Fall through to L2 cache
        
        # L2 Cache: Redis lookup
        l2_start = time.time()
        try:
            redis_key = f"edge:{cache_key}"
            cached_data = await self.redis_pool.get_with_fallback(redis_key, "cache")
            
            if cached_data:
                value = cached_data.decode('utf-8')
                
                # Store in L1 cache for future ultra-fast access
                asyncio.create_task(self._store_l1_cache(cache_key, value, 300))  # 5 min TTL
                
                l2_time = (time.time() - l2_start) * 1000
                self._update_l2_stats(l2_time)
                self.stats["l2_hits"] += 1
                
                return value
                
        except Exception:
            pass
        
        # Cache miss
        self.stats["cache_misses"] += 1
        return None
    
    async def store_cached_response(self, query: str, response: str, ttl: int = 600, context_type: str = "query") -> bool:
        """Store response in multi-tier cache."""
        cache_key = self._get_cache_key(query, context_type)
        current_time = time.time()
        
        try:
            # Store in both L1 and L2 caches simultaneously
            l1_task = asyncio.create_task(self._store_l1_cache(cache_key, response, ttl))
            l2_task = asyncio.create_task(self._store_l2_cache(cache_key, response, ttl))
            
            # Wait for both to complete
            l1_result, l2_result = await asyncio.gather(l1_task, l2_task, return_exceptions=True)
            
            # Return True if at least one succeeded
            return not isinstance(l1_result, Exception) or not isinstance(l2_result, Exception)
            
        except Exception:
            return False
    
    async def _store_l1_cache(self, cache_key: str, value: str, ttl: int) -> bool:
        """Store in ultra-fast local cache."""
        try:
            current_time = time.time()
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO query_cache 
                    (key, value, created_at, ttl, access_count, last_accessed)
                    VALUES (?, ?, ?, ?, 1, ?)
                """, (cache_key, value, current_time, ttl, current_time))
                
                await db.commit()
                return True
                
        except Exception:
            return False
    
    async def _store_l2_cache(self, cache_key: str, value: str, ttl: int) -> bool:
        """Store in Redis cache."""
        try:
            redis_key = f"edge:{cache_key}"
            return await self.redis_pool.set_with_optimization(
                redis_key,
                value.encode('utf-8'),
                ttl,
                "cache"
            )
        except Exception:
            return False
    
    async def _update_access_stats(self, cache_key: str, current_count: int):
        """Update access statistics in background."""
        try:
            current_time = time.time()
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE query_cache 
                    SET access_count = ?, last_accessed = ?
                    WHERE key = ?
                """, (current_count + 1, current_time, cache_key))
                await db.commit()
        except Exception:
            pass
    
    async def cache_popular_queries(self, queries_responses: Dict[str, str]) -> int:
        """Pre-cache popular queries for ultra-fast access."""
        cached_count = 0
        
        for query, response in queries_responses.items():
            try:
                success = await self.store_cached_response(query, response, 1800)  # 30 min TTL
                if success:
                    cached_count += 1
            except Exception:
                continue
        
        return cached_count
    
    async def get_hot_queries(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most frequently accessed queries."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT key, access_count 
                    FROM query_cache 
                    ORDER BY access_count DESC, last_accessed DESC 
                    LIMIT ?
                """, (limit,)) as cursor:
                    return await cursor.fetchall()
        except Exception:
            return []
    
    async def cleanup_expired(self) -> int:
        """Clean up expired cache entries."""
        try:
            current_time = time.time()
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    DELETE FROM query_cache 
                    WHERE created_at + ttl < ?
                """, (current_time,))
                
                deleted_count = cursor.rowcount
                
                await db.execute("""
                    DELETE FROM retrieval_cache 
                    WHERE created_at + ttl < ?
                """, (current_time,))
                
                await db.commit()
                return deleted_count
                
        except Exception:
            return 0
    
    def _update_l1_stats(self, latency_ms: float):
        """Update L1 cache statistics."""
        self.stats["total_requests"] += 1
        
        if self.stats["l1_hits"] > 0:
            current_avg = self.stats["l1_avg_ms"]
            self.stats["l1_avg_ms"] = ((current_avg * (self.stats["l1_hits"] - 1)) + latency_ms) / self.stats["l1_hits"]
    
    def _update_l2_stats(self, latency_ms: float):
        """Update L2 cache statistics."""
        if self.stats["l2_hits"] > 0:
            current_avg = self.stats["l2_avg_ms"]
            self.stats["l2_avg_ms"] = ((current_avg * (self.stats["l2_hits"] - 1)) + latency_ms) / self.stats["l2_hits"]
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache performance statistics."""
        total_requests = self.stats["l1_hits"] + self.stats["l2_hits"] + self.stats["cache_misses"]
        
        l1_hit_rate = (self.stats["l1_hits"] / total_requests * 100) if total_requests > 0 else 0
        l2_hit_rate = (self.stats["l2_hits"] / total_requests * 100) if total_requests > 0 else 0
        overall_hit_rate = ((self.stats["l1_hits"] + self.stats["l2_hits"]) / total_requests * 100) if total_requests > 0 else 0
        
        # Get cache sizes
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT COUNT(*) FROM query_cache") as cursor:
                    l1_size = (await cursor.fetchone())[0]
        except Exception:
            l1_size = 0
        
        return {
            "cache_performance": {
                "l1_hit_rate": round(l1_hit_rate, 1),
                "l2_hit_rate": round(l2_hit_rate, 1), 
                "overall_hit_rate": round(overall_hit_rate, 1),
                "l1_avg_latency_ms": round(self.stats["l1_avg_ms"], 2),
                "l2_avg_latency_ms": round(self.stats["l2_avg_ms"], 2)
            },
            "cache_stats": {
                "total_requests": total_requests,
                "l1_hits": self.stats["l1_hits"],
                "l2_hits": self.stats["l2_hits"],
                "cache_misses": self.stats["cache_misses"],
                "l1_cache_size": l1_size
            }
        }


# Global instance
_edge_cache = None

def get_edge_cache() -> EdgeCacheManager:
    """Get or create the edge cache manager singleton."""
    global _edge_cache
    if _edge_cache is None:
        _edge_cache = EdgeCacheManager()
    return _edge_cache