#!/usr/bin/env python3
"""
Simple performance analysis using direct API calls.
"""
import asyncio
import json
import time
import statistics
import httpx


async def analyze_performance():
    """Analyze RAG system performance bottlenecks."""
    print("🔍 RAG PERFORMANCE ANALYSIS")
    print("=" * 50)
    
    queries = [
        "What vector stores are supported?",
        "How do I authenticate with the API?",
        "What security practices does the company require?",
        "What is the vacation policy?",
        "How does hybrid retrieval work?"
    ] * 4  # 20 total queries
    
    results = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"📊 Testing {len(queries)} queries...")
        
        for i, query in enumerate(queries):
            start_time = time.time()
            
            try:
                response = await client.post(
                    "http://localhost:8000/query",
                    headers={"x-api-key": "changeme"},
                    json={"q": query, "top_k": 12, "fusion": "rrf"}
                )
                
                total_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    retrieval_time = data.get("retrieval_debug", {}).get("retrieval_time_ms", 0)
                    
                    result = {
                        "query_num": i + 1,
                        "query": query,
                        "total_time_ms": total_time,
                        "retrieval_time_ms": retrieval_time,
                        "llm_time_ms": total_time - retrieval_time,
                        "success": True,
                        "answer_length": len(data.get("answer", "")),
                        "citations_count": len(data.get("citations", []))
                    }
                    results.append(result)
                    
                    if i < 5:
                        print(f"  Query {i+1}: {total_time:.1f}ms (retrieval: {retrieval_time:.1f}ms)")
                else:
                    print(f"  Query {i+1}: FAILED (HTTP {response.status_code})")
                    
            except Exception as e:
                print(f"  Query {i+1}: ERROR - {e}")
            
            # Small delay between queries
            await asyncio.sleep(0.1)
    
    if not results:
        print("❌ No successful queries to analyze")
        return
    
    # Calculate statistics
    total_times = [r["total_time_ms"] for r in results]
    retrieval_times = [r["retrieval_time_ms"] for r in results]
    llm_times = [r["llm_time_ms"] for r in results if r["llm_time_ms"] > 0]
    
    print(f"\n📈 PERFORMANCE STATISTICS")
    print("-" * 50)
    print(f"Successful queries: {len(results)}")
    print(f"Total time - Avg: {statistics.mean(total_times):.1f}ms, Min: {min(total_times):.1f}ms, Max: {max(total_times):.1f}ms")
    print(f"Retrieval time - Avg: {statistics.mean(retrieval_times):.1f}ms, Min: {min(retrieval_times):.1f}ms, Max: {max(retrieval_times):.1f}ms")
    
    if llm_times:
        print(f"LLM time - Avg: {statistics.mean(llm_times):.1f}ms, Min: {min(llm_times):.1f}ms, Max: {max(llm_times):.1f}ms")
    
    # Calculate percentiles
    def percentile(data, p):
        return sorted(data)[int(len(data) * p / 100)]
    
    print(f"\n📊 PERCENTILES")
    print("-" * 50)
    print(f"Total time P95: {percentile(total_times, 95):.1f}ms")
    print(f"Total time P99: {percentile(total_times, 99):.1f}ms")
    print(f"Retrieval P95: {percentile(retrieval_times, 95):.1f}ms")
    print(f"Retrieval P99: {percentile(retrieval_times, 99):.1f}ms")
    
    # Time breakdown analysis
    avg_total = statistics.mean(total_times)
    avg_retrieval = statistics.mean(retrieval_times)
    avg_llm = statistics.mean(llm_times) if llm_times else 0
    avg_other = avg_total - avg_retrieval - avg_llm
    
    print(f"\n⚡ TIME BREAKDOWN")
    print("-" * 50)
    print(f"Retrieval: {avg_retrieval:.1f}ms ({avg_retrieval/avg_total*100:.1f}%)")
    print(f"LLM: {avg_llm:.1f}ms ({avg_llm/avg_total*100:.1f}%)")
    print(f"Network/Other: {avg_other:.1f}ms ({avg_other/avg_total*100:.1f}%)")
    
    # Bottleneck identification
    print(f"\n🔍 BOTTLENECK ANALYSIS")
    print("-" * 50)
    
    if avg_retrieval > 200:
        print("🔥 CRITICAL: Retrieval is major bottleneck (>200ms)")
    elif avg_retrieval > 100:
        print("🟡 WARNING: Retrieval needs optimization (>100ms)")
    elif avg_retrieval > 50:
        print("⚠️ MODERATE: Retrieval could be faster (>50ms)")
    else:
        print("✅ GOOD: Retrieval performance acceptable (<50ms)")
    
    if avg_total > 500:
        print("🔥 CRITICAL: Overall latency too high (>500ms)")
    elif avg_total > 200:
        print("🟡 WARNING: Overall latency needs work (>200ms)")
    elif avg_total > 50:
        print("⚠️ MODERATE: Close to target but needs optimization (>50ms)")
    else:
        print("✅ EXCELLENT: Meeting <50ms target!")
    
    # Optimization recommendations
    print(f"\n💡 OPTIMIZATION RECOMMENDATIONS")
    print("-" * 50)
    
    if avg_retrieval > 150:
        print("🎯 HIGH PRIORITY - Retrieval Optimizations:")
        print("  • Implement aggressive result caching")
        print("  • Optimize Qdrant HNSW parameters (ef, M)")
        print("  • Use faster embedding models or cache embeddings")
        print("  • Consider approximate search techniques")
        
    if avg_total > 300:
        print("🎯 HIGH PRIORITY - System Optimizations:")
        print("  • Add connection pooling for all services")
        print("  • Implement request batching")
        print("  • Optimize serialization/deserialization")
        print("  • Consider async improvements")
    
    if avg_retrieval > 50:
        print("🎯 TARGET OPTIMIZATION for <50ms:")
        print("  • Need retrieval <30ms (currently {:.1f}ms)".format(avg_retrieval))
        print("  • Implement memory-based indexes")
        print("  • Precompute popular query results")
        print("  • Use semantic caching with similarity matching")
    
    # Performance grade
    print(f"\n🏆 PERFORMANCE GRADE")
    print("-" * 50)
    
    if avg_total < 50:
        grade = "A+"
        message = "EXCELLENT - Meets all targets!"
    elif avg_total < 100:
        grade = "B+"
        message = "GOOD - Close to targets"
    elif avg_total < 200:
        grade = "C+"
        message = "ACCEPTABLE - Needs optimization"
    else:
        grade = "D"
        message = "POOR - Major optimizations needed"
    
    print(f"Grade: {grade} - {message}")
    print(f"Current: {avg_total:.1f}ms | Target: <50ms | Gap: {max(0, avg_total - 50):.1f}ms")
    
    # Save results
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"performance_analysis_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "summary": {
                "avg_total_ms": avg_total,
                "avg_retrieval_ms": avg_retrieval,
                "avg_llm_ms": avg_llm,
                "p95_total_ms": percentile(total_times, 95),
                "p95_retrieval_ms": percentile(retrieval_times, 95),
                "grade": grade,
                "meets_target": avg_total < 50
            },
            "results": results
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {filename}")


if __name__ == "__main__":
    asyncio.run(analyze_performance())