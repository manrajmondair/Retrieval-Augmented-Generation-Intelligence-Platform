"""
Performance profiler for RAG system bottleneck identification.
"""
import time
import asyncio
import functools
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
import statistics


@dataclass
class ProfileResult:
    """Result of a performance measurement."""
    operation: str
    duration_ms: float
    start_time: float
    end_time: float
    metadata: Dict[str, Any] = None
    

class PerformanceProfiler:
    """Comprehensive performance profiler."""
    
    def __init__(self):
        self.results: List[ProfileResult] = []
        self.enabled = True
    
    def enable(self):
        """Enable profiling."""
        self.enabled = True
    
    def disable(self):
        """Disable profiling."""
        self.enabled = False
    
    def clear(self):
        """Clear all results."""
        self.results.clear()
    
    @asynccontextmanager
    async def profile(self, operation: str, **metadata):
        """Context manager for profiling async operations."""
        if not self.enabled:
            yield
            return
            
        start_time = time.time()
        try:
            yield
        finally:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            result = ProfileResult(
                operation=operation,
                duration_ms=duration_ms,
                start_time=start_time,
                end_time=end_time,
                metadata=metadata
            )
            self.results.append(result)
    
    def profile_sync(self, operation: str, **metadata):
        """Decorator for profiling sync functions."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                start_time = time.time()
                try:
                    return func(*args, **kwargs)
                finally:
                    end_time = time.time()
                    duration_ms = (end_time - start_time) * 1000
                    
                    result = ProfileResult(
                        operation=operation,
                        duration_ms=duration_ms,
                        start_time=start_time,
                        end_time=end_time,
                        metadata=metadata
                    )
                    self.results.append(result)
            return wrapper
        return decorator
    
    def profile_async(self, operation: str, **metadata):
        """Decorator for profiling async functions."""
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                if not self.enabled:
                    return await func(*args, **kwargs)
                
                async with self.profile(operation, **metadata):
                    return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def get_stats(self, operation_filter: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.results:
            return {}
        
        # Filter results if specified
        results = self.results
        if operation_filter:
            results = [r for r in results if operation_filter in r.operation]
        
        if not results:
            return {}
        
        # Calculate statistics
        durations = [r.duration_ms for r in results]
        operations = {}
        
        # Group by operation
        for result in results:
            if result.operation not in operations:
                operations[result.operation] = []
            operations[result.operation].append(result.duration_ms)
        
        # Overall stats
        stats = {
            "total_operations": len(results),
            "total_time_ms": sum(durations),
            "avg_duration_ms": statistics.mean(durations),
            "median_duration_ms": statistics.median(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "p95_duration_ms": self._percentile(durations, 95),
            "p99_duration_ms": self._percentile(durations, 99),
        }
        
        # Per-operation breakdown
        operation_stats = {}
        for op, op_durations in operations.items():
            operation_stats[op] = {
                "count": len(op_durations),
                "total_ms": sum(op_durations),
                "avg_ms": statistics.mean(op_durations),
                "median_ms": statistics.median(op_durations),
                "min_ms": min(op_durations),
                "max_ms": max(op_durations),
                "p95_ms": self._percentile(op_durations, 95),
                "std_dev": statistics.stdev(op_durations) if len(op_durations) > 1 else 0,
            }
        
        stats["operations"] = operation_stats
        return stats
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        sorted_data = sorted(data)
        index = int((percentile / 100.0) * len(sorted_data))
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        return sorted_data[index]
    
    def print_report(self, operation_filter: Optional[str] = None, top_n: int = 10):
        """Print performance report."""
        stats = self.get_stats(operation_filter)
        if not stats:
            print("No profiling data available")
            return
        
        print("🔍 PERFORMANCE PROFILING REPORT")
        print("=" * 50)
        print(f"Total Operations: {stats['total_operations']}")
        print(f"Total Time: {stats['total_time_ms']:.2f}ms")
        print(f"Average Duration: {stats['avg_duration_ms']:.2f}ms")
        print(f"Median Duration: {stats['median_duration_ms']:.2f}ms")
        print(f"P95 Duration: {stats['p95_duration_ms']:.2f}ms")
        print(f"P99 Duration: {stats['p99_duration_ms']:.2f}ms")
        
        print(f"\n📊 TOP {top_n} SLOWEST OPERATIONS")
        print("-" * 50)
        
        # Sort operations by average duration
        sorted_ops = sorted(
            stats["operations"].items(),
            key=lambda x: x[1]["avg_ms"],
            reverse=True
        )
        
        for i, (operation, op_stats) in enumerate(sorted_ops[:top_n]):
            print(f"{i+1:2d}. {operation}")
            print(f"    Count: {op_stats['count']}")
            print(f"    Avg: {op_stats['avg_ms']:.2f}ms")
            print(f"    P95: {op_stats['p95_ms']:.2f}ms")
            print(f"    Total: {op_stats['total_ms']:.2f}ms")
            
            if op_stats['avg_ms'] > 50:
                print("    🔴 BOTTLENECK: >50ms average")
            elif op_stats['avg_ms'] > 20:
                print("    🟡 SLOW: >20ms average")
            else:
                print("    🟢 FAST: <20ms average")
            print()
        
        # Identify bottlenecks
        print("🎯 OPTIMIZATION RECOMMENDATIONS")
        print("-" * 50)
        
        bottlenecks = [(op, stats) for op, stats in sorted_ops if stats["avg_ms"] > 50]
        slow_ops = [(op, stats) for op, stats in sorted_ops if 20 < stats["avg_ms"] <= 50]
        
        if bottlenecks:
            print("❌ Critical Bottlenecks (>50ms):")
            for op, stats in bottlenecks:
                print(f"  • {op}: {stats['avg_ms']:.1f}ms avg")
        
        if slow_ops:
            print("⚠️ Slow Operations (20-50ms):")
            for op, stats in slow_ops:
                print(f"  • {op}: {stats['avg_ms']:.1f}ms avg")
        
        if not bottlenecks and not slow_ops:
            print("✅ No significant bottlenecks detected")
    
    def export_results(self, filepath: str):
        """Export results to JSON file."""
        import json
        data = {
            "stats": self.get_stats(),
            "raw_results": [asdict(r) for r in self.results]
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Results exported to {filepath}")


# Global profiler instance
profiler = PerformanceProfiler()


# Convenience functions
async def profile_query_pipeline(query: str):
    """Profile a complete query pipeline."""
    from app.rag.retrievers.hybrid import HybridRetriever
    from app.services.llm import LLMService
    
    retriever = HybridRetriever()
    llm_service = LLMService()
    
    print(f"🔍 Profiling query: '{query}'")
    profiler.clear()
    profiler.enable()
    
    # Profile retrieval
    async with profiler.profile("total_retrieval"):
        retrieval_result = await retriever.retrieve(query, top_k=12, fusion_method="rrf")
    
    # Profile LLM generation
    context = "\n".join([doc.content for doc in retrieval_result.documents])
    prompt = f"Based on the context, answer: {query}\n\nContext: {context}"
    
    async with profiler.profile("llm_generation"):
        answer = await llm_service.generate(prompt, max_tokens=200)
    
    profiler.print_report()
    return {
        "answer": answer,
        "retrieval_debug": retrieval_result.retrieval_debug,
        "profile_stats": profiler.get_stats()
    }


if __name__ == "__main__":
    # Test the profiler
    import asyncio
    
    async def test_profiler():
        result = await profile_query_pipeline("What vector stores are supported?")
        print("\n" + "="*50)
        print("PROFILING COMPLETE")
        print(f"Answer: {result['answer'][:100]}...")
    
    asyncio.run(test_profiler())