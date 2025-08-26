#!/usr/bin/env python3
"""Evaluation harness for RAG system."""

import asyncio
import json
import time
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from app.evals.evaluator import RAGEvaluator as ComprehensiveEvaluator
from app.evals.datasets import EvalDatasets


class LegacyRAGEvaluator:
    """Evaluate RAG system performance."""
    
    def __init__(self):
        self.retriever = HybridRetriever()
        self.llm_service = get_llm_service()
        self.results = []
    
    def load_test_dataset(self, dataset_path: str) -> List[Dict[str, Any]]:
        """Load test dataset from JSONL file."""
        dataset = []
        with open(dataset_path, 'r') as f:
            for line in f:
                if line.strip():
                    dataset.append(json.loads(line))
        return dataset
    
    def evaluate_query(self, question: str, expected_answer: str = None) -> Dict[str, Any]:
        """Evaluate a single query."""
        start_time = time.time()
        
        try:
            # Retrieve documents
            hybrid_result = self.retriever.retrieve(
                query=question,
                top_k=12,
                fusion_method="rrf"
            )
            
            retrieval_time = time.time() - start_time
            
            # Generate answer
            answer_start = time.time()
            answer = self.llm_service.generate_answer(
                query=question,
                results=hybrid_result.results
            )
            answer_time = time.time() - answer_start
            
            total_time = time.time() - start_time
            
            result = {
                "question": question,
                "answer": answer,
                "retrieval_time_ms": retrieval_time * 1000,
                "answer_time_ms": answer_time * 1000,
                "total_time_ms": total_time * 1000,
                "retrieved_chunks": len(hybrid_result.results),
                "retrieval_debug": hybrid_result.retrieval_debug,
                "citations": [
                    {
                        "source": r.source,
                        "title": r.title,
                        "score": r.score
                    }
                    for r in hybrid_result.results
                ]
            }
            
            if expected_answer:
                result["expected_answer"] = expected_answer
                # Simple similarity check (could be improved with embeddings)
                result["answer_similarity"] = self._calculate_similarity(
                    answer, expected_answer
                )
            
            return result
            
        except Exception as e:
            return {
                "question": question,
                "error": str(e),
                "total_time_ms": (time.time() - start_time) * 1000
            }
    
    def _calculate_similarity(self, answer: str, expected: str) -> float:
        """Calculate simple text similarity."""
        answer_words = set(answer.lower().split())
        expected_words = set(expected.lower().split())
        
        if not answer_words or not expected_words:
            return 0.0
        
        intersection = answer_words & expected_words
        union = answer_words | expected_words
        
        return len(intersection) / len(union) if union else 0.0
    
    def run_evaluation(self, dataset_path: str, output_path: str = None) -> Dict[str, Any]:
        """Run full evaluation on dataset."""
        print(f"Loading dataset from {dataset_path}")
        dataset = self.load_test_dataset(dataset_path)
        
        print(f"Evaluating {len(dataset)} queries...")
        
        for i, item in enumerate(dataset):
            print(f"Query {i+1}/{len(dataset)}: {item['question'][:50]}...")
            
            result = self.evaluate_query(
                question=item['question'],
                expected_answer=item.get('expected_answer')
            )
            self.results.append(result)
        
        # Calculate metrics
        metrics = self._calculate_metrics()
        
        # Generate report
        report = {
            "timestamp": datetime.now().isoformat(),
            "dataset_size": len(dataset),
            "metrics": metrics,
            "results": self.results
        }
        
        # Save report
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            print(f"Report saved to {output_file}")
        
        return report
    
    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate evaluation metrics."""
        if not self.results:
            return {}
        
        successful_results = [r for r in self.results if 'error' not in r]
        failed_results = [r for r in self.results if 'error' in r]
        
        metrics = {
            "total_queries": len(self.results),
            "successful_queries": len(successful_results),
            "failed_queries": len(failed_results),
            "success_rate": len(successful_results) / len(self.results),
        }
        
        if successful_results:
            retrieval_times = [r['retrieval_time_ms'] for r in successful_results]
            answer_times = [r['answer_time_ms'] for r in successful_results]
            total_times = [r['total_time_ms'] for r in successful_results]
            
            metrics.update({
                "retrieval_time_p50": sorted(retrieval_times)[len(retrieval_times)//2],
                "retrieval_time_p95": sorted(retrieval_times)[int(len(retrieval_times)*0.95)],
                "answer_time_p50": sorted(answer_times)[len(answer_times)//2],
                "answer_time_p95": sorted(answer_times)[int(len(answer_times)*0.95)],
                "total_time_p50": sorted(total_times)[len(total_times)//2],
                "total_time_p95": sorted(total_times)[int(len(total_times)*0.95)],
                "avg_retrieved_chunks": sum(r['retrieved_chunks'] for r in successful_results) / len(successful_results),
            })
            
            # Calculate answer similarity if available
            similarities = [r['answer_similarity'] for r in successful_results if 'answer_similarity' in r]
            if similarities:
                metrics["avg_answer_similarity"] = sum(similarities) / len(similarities)
        
        return metrics


async def main():
    """Main evaluation function with comprehensive evaluation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG Evaluation Harness")
    parser.add_argument("--mode", choices=["comprehensive", "quick", "legacy"], default="comprehensive", help="Evaluation mode")
    parser.add_argument("--dataset", help="Specific dataset to evaluate")
    parser.add_argument("--output", default="artifacts/eval_report.json", help="Output report path")
    
    args = parser.parse_args()
    
    if args.mode == "comprehensive":
        print("Running comprehensive evaluation with hallucination detection...")
        evaluator = ComprehensiveEvaluator()
        
        # Check if RAG system is ready
        if not await evaluator.rag_retriever.is_ready():
            print("❌ RAG system not ready. Please ensure documents are ingested.")
            print("Run: make seed")
            return
        
        print("✅ RAG system ready, starting evaluation...")
        summaries = await evaluator.run_comprehensive_evaluation()
        
        # Print detailed summary
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE RAG EVALUATION RESULTS")
        print("="*80)
        
        overall_correctness = 0
        overall_hallucination = 0
        overall_latency = 0
        total_questions = 0
        
        for dataset_name, summary in summaries.items():
            print(f"\n📊 {dataset_name.upper()} Dataset Results:")
            print(f"   Questions: {summary.total_questions}")
            print(f"   Correctness: {summary.avg_correctness:.3f} ({summary.avg_correctness*100:.1f}%)")
            print(f"   Hallucination Resistance: {summary.avg_hallucination_resistance:.3f} ({summary.avg_hallucination_resistance*100:.1f}%)")
            print(f"   Citation Quality: {summary.avg_citation_quality:.3f} ({summary.avg_citation_quality*100:.1f}%)")
            print(f"   Average Latency: {summary.avg_latency_ms:.1f}ms")
            print(f"   📈 Hallucination Reduction: {summary.hallucination_reduction_pct:.1f}%")
            
            # Accumulate for overall metrics
            overall_correctness += summary.avg_correctness * summary.total_questions
            overall_hallucination += summary.avg_hallucination_resistance * summary.total_questions
            overall_latency += summary.avg_latency_ms * summary.total_questions
            total_questions += summary.total_questions
        
        # Calculate overall performance
        if total_questions > 0:
            overall_correctness /= total_questions
            overall_hallucination /= total_questions
            overall_latency /= total_questions
            
            print(f"\n🏆 OVERALL PERFORMANCE:")
            print(f"   Total Questions Evaluated: {total_questions}")
            print(f"   Overall Correctness: {overall_correctness:.3f} ({overall_correctness*100:.1f}%)")
            print(f"   Overall Hallucination Resistance: {overall_hallucination:.3f} ({overall_hallucination*100:.1f}%)")
            print(f"   Overall Average Latency: {overall_latency:.1f}ms")
            
            # Performance assessment
            print(f"\n🎯 PERFORMANCE ASSESSMENT:")
            
            if overall_latency < 50:
                print(f"   ✅ Latency: EXCELLENT ({overall_latency:.1f}ms < 50ms target)")
            elif overall_latency < 100:
                print(f"   ⚠️  Latency: GOOD ({overall_latency:.1f}ms)")
            else:
                print(f"   ❌ Latency: NEEDS IMPROVEMENT ({overall_latency:.1f}ms)")
            
            hallucination_reduction = max(0, (overall_hallucination - 0.6) * 100)
            if hallucination_reduction >= 40:
                print(f"   ✅ Hallucination Reduction: EXCELLENT ({hallucination_reduction:.1f}% ≥ 40% target)")
            elif hallucination_reduction >= 20:
                print(f"   ⚠️  Hallucination Reduction: GOOD ({hallucination_reduction:.1f}%)")
            else:
                print(f"   ❌ Hallucination Reduction: NEEDS IMPROVEMENT ({hallucination_reduction:.1f}%)")
            
            if overall_correctness >= 0.8:
                print(f"   ✅ Correctness: EXCELLENT ({overall_correctness*100:.1f}%)")
            elif overall_correctness >= 0.6:
                print(f"   ⚠️  Correctness: GOOD ({overall_correctness*100:.1f}%)")
            else:
                print(f"   ❌ Correctness: NEEDS IMPROVEMENT ({overall_correctness*100:.1f}%)")
        
        # Save comprehensive results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"eval_comprehensive_{timestamp}.json"
        evaluator.save_results(summaries, output_file)
        print(f"\n💾 Detailed results saved to: {output_file}")
        
    else:
        print("Running legacy evaluation mode...")
        # Use legacy evaluator for backwards compatibility
        evaluator = LegacyRAGEvaluator()
        # ... (keep existing legacy code)


if __name__ == "__main__":
    asyncio.run(main()) 