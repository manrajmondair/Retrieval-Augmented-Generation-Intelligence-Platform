#!/usr/bin/env python3
"""
Comprehensive performance analysis script.
"""
import asyncio
import json
import time
from typing import Dict, List, Any
import statistics

# Test queries for analysis
TEST_QUERIES = [
    "What vector stores are supported?",
    "How do I authenticate with the API?", 
    "What security practices does the company require?",
    "What is the vacation policy?",
    "How does hybrid retrieval work?"
]

class PerformanceAnalyzer:
    """Analyzes RAG system performance bottlenecks."""
    
    def __init__(self):
        self.results = []
        
    async def run_detailed_analysis(self, num_iterations: int = 20):
        """Run comprehensive performance analysis."""
        print("🔍 Starting Detailed Performance Analysis")
        print("=" * 60)
        
        # Test individual components
        print("\n📊 Component-Level Analysis:")
        await self._analyze_embedding_service()
        await self._analyze_vector_search()
        await self._analyze_bm25_search()
        await self._analyze_fusion()
        await self._analyze_llm_generation()
        
        # Test end-to-end queries
        print("\n🎯 End-to-End Query Analysis:")
        e2e_results = await self._analyze_end_to_end_queries(num_iterations)
        
        # Analyze patterns
        print("\n📈 Performance Pattern Analysis:")
        self._analyze_patterns(e2e_results)
        
        # Generate recommendations
        print("\n💡 Optimization Recommendations:")
        self._generate_recommendations(e2e_results)
        
        return e2e_results
    
    async def _analyze_embedding_service(self):
        """Analyze embedding service performance."""
        print("  🔤 Embedding Service Analysis...")
        
        from app.services.embeddings import get_embeddings_service
        embeddings_service = get_embeddings_service()
        
        # Test single embedding
        start = time.time()
        await embeddings_service.get_embeddings(["test query"])
        single_time = (time.time() - start) * 1000
        
        # Test batch embedding
        queries = ["query " + str(i) for i in range(10)]
        start = time.time()
        await embeddings_service.get_embeddings(queries)
        batch_time = (time.time() - start) * 1000
        batch_per_query = batch_time / 10
        
        print(f"    Single embedding: {single_time:.1f}ms")
        print(f"    Batch (10): {batch_time:.1f}ms ({batch_per_query:.1f}ms/query)")
        
        if single_time > 100:
            print("    🔴 BOTTLENECK: Embedding latency >100ms")
        elif batch_per_query < single_time * 0.5:
            print("    🟢 GOOD: Batching provides efficiency gains")
        
    async def _analyze_vector_search(self):
        """Analyze vector search performance.""" 
        print("  🔍 Vector Search Analysis...")
        
        from app.rag.retrievers.vector_qdrant import QdrantRetriever
        from app.core.config import settings
        
        try:
            retriever = QdrantRetriever(
                url=settings.qdrant_url,
                collection_name=settings.qdrant_collection
            )
            
            # Test vector search
            start = time.time()
            result = await retriever.retrieve("test query", top_k=12)
            search_time = (time.time() - start) * 1000
            
            print(f"    Vector search: {search_time:.1f}ms")
            print(f"    Results returned: {len(result.documents)}")
            
            if search_time > 100:
                print("    🔴 BOTTLENECK: Vector search >100ms") 
            elif search_time < 50:
                print("    🟢 FAST: Vector search <50ms")
                
        except Exception as e:
            print(f"    ❌ Error testing vector search: {e}")
    
    async def _analyze_bm25_search(self):
        """Analyze BM25 search performance."""
        print("  📝 BM25 Search Analysis...")
        
        from app.rag.retrievers.bm25 import BM25Retriever
        
        try:
            retriever = BM25Retriever()
            
            # Test BM25 search
            start = time.time()
            result = await retriever.retrieve("test query", top_k=12)
            search_time = (time.time() - start) * 1000
            
            print(f"    BM25 search: {search_time:.1f}ms")
            print(f"    Results returned: {len(result.documents)}")
            
            if search_time > 50:
                print("    🔴 BOTTLENECK: BM25 search >50ms")
            elif search_time < 10:
                print("    🟢 FAST: BM25 search <10ms")
                
        except Exception as e:
            print(f"    ❌ Error testing BM25 search: {e}")
    
    async def _analyze_fusion(self):
        """Analyze fusion performance."""
        print("  🔗 Fusion Analysis...")
        
        from app.rag.fusion import FusionEngine
        from app.rag.schemas import RetrievalResult, DocumentChunk
        
        engine = FusionEngine()
        
        # Create mock results
        mock_docs = [
            DocumentChunk(content=f"doc {i}", doc_id=f"doc_{i}", chunk_id=f"chunk_{i}")
            for i in range(12)
        ]
        
        bm25_result = RetrievalResult(documents=mock_docs[:6])
        vector_result = RetrievalResult(documents=mock_docs[6:])
        
        # Test RRF fusion
        start = time.time()
        fused = engine.fuse_results(bm25_result, vector_result, "rrf", k=60)
        fusion_time = (time.time() - start) * 1000
        
        print(f"    RRF fusion: {fusion_time:.1f}ms")
        print(f"    Fused results: {len(fused.documents)}")
        
        if fusion_time > 10:
            print("    🔴 BOTTLENECK: Fusion >10ms")
        else:
            print("    🟢 FAST: Fusion <10ms")
    
    async def _analyze_llm_generation(self):
        """Analyze LLM generation performance."""
        print("  🤖 LLM Generation Analysis...")
        
        from app.services.llm import LLMService
        
        try:
            llm_service = LLMService()
            
            # Test LLM generation
            prompt = "Answer this question briefly: What vector stores are supported?"
            start = time.time()
            answer = await llm_service.generate(prompt, max_tokens=50)
            generation_time = (time.time() - start) * 1000
            
            print(f"    LLM generation: {generation_time:.1f}ms")
            print(f"    Answer length: {len(answer)} chars")
            
            if generation_time > 500:
                print("    🔴 BOTTLENECK: LLM generation >500ms")
            elif generation_time < 200:
                print("    🟢 FAST: LLM generation <200ms")
                
        except Exception as e:
            print(f"    ❌ Error testing LLM generation: {e}")
    
    async def _analyze_end_to_end_queries(self, num_iterations: int):
        """Analyze complete end-to-end query performance."""
        print(f"  Running {num_iterations} end-to-end queries...")
        
        results = []
        
        for i in range(num_iterations):
            query = TEST_QUERIES[i % len(TEST_QUERIES)]
            
            # Simulate the full query pipeline with timing
            start_total = time.time()
            
            try:
                # Make actual API call to measure real performance
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://localhost:8000/query",
                        headers={"x-api-key": "changeme"},
                        json={"q": query, "top_k": 12, "fusion": "rrf"},
                        timeout=30.0
                    )
                
                total_time = (time.time() - start_total) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    retrieval_time = data.get("retrieval_debug", {}).get("retrieval_time_ms", 0)
                    
                    results.append({
                        "query": query,
                        "total_time_ms": total_time,
                        "retrieval_time_ms": retrieval_time,
                        "llm_time_ms": total_time - retrieval_time,
                        "success": True,
                        "answer_length": len(data.get("answer", "")),
                        "citations_count": len(data.get("citations", []))
                    })
                    
                    if i < 5:  # Show first few for debugging
                        print(f"    Query {i+1}: {total_time:.1f}ms (retrieval: {retrieval_time:.1f}ms)")
                
                else:
                    results.append({
                        "query": query,
                        "total_time_ms": total_time,
                        "success": False,
                        "error": f"HTTP {response.status_code}"
                    })
                    
            except Exception as e:
                results.append({
                    "query": query,
                    "success": False,
                    "error": str(e)
                })
                
            # Small delay to avoid overwhelming the system
            await asyncio.sleep(0.1)
        
        return results
    
    def _analyze_patterns(self, results: List[Dict]):
        """Analyze performance patterns."""
        successful_results = [r for r in results if r.get("success")]
        
        if not successful_results:
            print("    ❌ No successful queries to analyze")
            return
        
        # Calculate statistics
        total_times = [r["total_time_ms"] for r in successful_results]
        retrieval_times = [r["retrieval_time_ms"] for r in successful_results]
        llm_times = [r.get("llm_time_ms", 0) for r in successful_results]
        
        print(f"    Success Rate: {len(successful_results)}/{len(results)} ({len(successful_results)/len(results)*100:.1f}%)")
        print(f"    Total Time - Avg: {statistics.mean(total_times):.1f}ms, P95: {self._percentile(total_times, 95):.1f}ms")
        print(f"    Retrieval Time - Avg: {statistics.mean(retrieval_times):.1f}ms, P95: {self._percentile(retrieval_times, 95):.1f}ms")
        
        if llm_times and max(llm_times) > 0:
            print(f"    LLM Time - Avg: {statistics.mean(llm_times):.1f}ms, P95: {self._percentile(llm_times, 95):.1f}ms")
        
        # Identify bottleneck breakdown
        avg_total = statistics.mean(total_times)
        avg_retrieval = statistics.mean(retrieval_times)
        avg_llm = statistics.mean(llm_times) if llm_times else 0
        
        print(f"\n    📊 Time Breakdown:")
        print(f"      Retrieval: {avg_retrieval:.1f}ms ({avg_retrieval/avg_total*100:.1f}%)")
        print(f"      LLM: {avg_llm:.1f}ms ({avg_llm/avg_total*100:.1f}%)")
        print(f"      Other: {avg_total - avg_retrieval - avg_llm:.1f}ms ({(avg_total - avg_retrieval - avg_llm)/avg_total*100:.1f}%)")
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int((percentile / 100.0) * len(sorted_data))
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        return sorted_data[index]
    
    def _generate_recommendations(self, results: List[Dict]):
        """Generate optimization recommendations."""
        successful_results = [r for r in results if r.get("success")]
        
        if not successful_results:
            return
            
        total_times = [r["total_time_ms"] for r in successful_results]
        retrieval_times = [r["retrieval_time_ms"] for r in successful_results]
        
        avg_total = statistics.mean(total_times)
        avg_retrieval = statistics.mean(retrieval_times)
        
        recommendations = []
        
        # Priority recommendations based on analysis
        if avg_retrieval > 200:
            recommendations.append("🔥 HIGH PRIORITY: Optimize retrieval pipeline (>200ms)")
            recommendations.append("  • Implement aggressive caching")
            recommendations.append("  • Optimize vector search parameters")
            recommendations.append("  • Consider faster embedding models")
        elif avg_retrieval > 100:
            recommendations.append("🟡 MEDIUM PRIORITY: Improve retrieval speed (>100ms)")
            recommendations.append("  • Add query result caching")
            recommendations.append("  • Optimize Qdrant configuration")
        
        if avg_total > 500:
            recommendations.append("🔥 HIGH PRIORITY: Overall latency too high (>500ms)")
            recommendations.append("  • Implement connection pooling")
            recommendations.append("  • Add request batching")
            recommendations.append("  • Consider hardware upgrades")
        
        # Success rate recommendations
        success_rate = len(successful_results) / len(results)
        if success_rate < 0.95:
            recommendations.append(f"⚠️ RELIABILITY: Success rate {success_rate*100:.1f}% < 95%")
            recommendations.append("  • Add retry logic")
            recommendations.append("  • Improve error handling")
        
        # Specific optimization targets
        if avg_total > 50:  # Target: <50ms
            recommendations.append("🎯 TARGET OPTIMIZATIONS for <50ms:")
            
            if avg_retrieval > 30:
                recommendations.append("  • Retrieval needs <30ms (currently {:.1f}ms)".format(avg_retrieval))
            
            recommendations.append("  • Consider precomputed embeddings")
            recommendations.append("  • Implement memory-based caching")
            recommendations.append("  • Optimize database queries")
        
        if recommendations:
            for rec in recommendations:
                print(f"    {rec}")
        else:
            print("    ✅ Performance looks good! Consider fine-tuning for edge cases.")


async def main():
    """Run comprehensive performance analysis."""
    analyzer = PerformanceAnalyzer()
    
    # Check if system is ready
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8000/readyz",
                headers={"x-api-key": "changeme"},
                timeout=10.0
            )
            
            if response.status_code != 200:
                print("❌ System not ready. Please ensure:")
                print("  1. Backend is running: docker-compose up -d")
                print("  2. Documents are seeded: make seed")
                return
                
    except Exception as e:
        print(f"❌ Cannot connect to system: {e}")
        return
    
    print("✅ System is ready, starting analysis...\n")
    
    # Run analysis
    results = await analyzer.run_detailed_analysis(num_iterations=20)
    
    # Save detailed results
    import json
    import datetime
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"performance_analysis_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")
    print("\n🎯 Next Steps:")
    print("  1. Review recommendations above")
    print("  2. Implement high-priority optimizations")  
    print("  3. Re-run analysis to measure improvements")
    print("  4. Continue iterating until <50ms target is achieved")


if __name__ == "__main__":
    asyncio.run(main())