from typing import List, Dict, Any
from app.rag.schemas import RetrievalResult, HybridRetrievalResult


class FusionEngine:
    """Fuse results from multiple retrievers."""
    
    @staticmethod
    def reciprocal_rank_fusion(
        bm25_results: List[RetrievalResult],
        vector_results: List[RetrievalResult],
        k: int = 60
    ) -> List[RetrievalResult]:
        """Fuse results using Reciprocal Rank Fusion (RRF)."""
        # Create lookup for ranks
        bm25_ranks = {result.chunk_id: rank for rank, result in enumerate(bm25_results)}
        vector_ranks = {result.chunk_id: rank for rank, result in enumerate(vector_results)}
        
        # Collect all unique chunk IDs
        all_chunk_ids = set(bm25_ranks.keys()) | set(vector_ranks.keys())
        
        # Calculate RRF scores
        rrf_scores = []
        for chunk_id in all_chunk_ids:
            bm25_rank = bm25_ranks.get(chunk_id, len(bm25_results))
            vector_rank = vector_ranks.get(chunk_id, len(vector_results))
            
            rrf_score = 1 / (k + bm25_rank) + 1 / (k + vector_rank)
            
            # Get the result with more details (prefer vector if available)
            if chunk_id in vector_ranks:
                result = next(r for r in vector_results if r.chunk_id == chunk_id)
            else:
                result = next(r for r in bm25_results if r.chunk_id == chunk_id)
            
            # Create new result with RRF score
            fused_result = RetrievalResult(
                doc_id=result.doc_id,
                chunk_id=result.chunk_id,
                source=result.source,
                title=result.title,
                content=result.content,
                score=rrf_score,
                retriever="hybrid",
                metadata={
                    **result.metadata,
                    "bm25_rank": bm25_rank,
                    "vector_rank": vector_rank,
                    "bm25_score": next((r.score for r in bm25_results if r.chunk_id == chunk_id), 0.0),
                    "vector_score": next((r.score for r in vector_results if r.chunk_id == chunk_id), 0.0),
                }
            )
            rrf_scores.append((rrf_score, fused_result))
        
        # Sort by RRF score and return
        rrf_scores.sort(key=lambda x: x[0], reverse=True)
        return [result for _, result in rrf_scores]
    
    @staticmethod
    def weighted_fusion(
        bm25_results: List[RetrievalResult],
        vector_results: List[RetrievalResult],
        bm25_weight: float = 0.4,
        vector_weight: float = 0.6
    ) -> List[RetrievalResult]:
        """Fuse results using weighted combination of normalized scores."""
        # Normalize scores to [0, 1] range
        bm25_scores = [r.score for r in bm25_results]
        vector_scores = [r.score for r in vector_results]
        
        bm25_max = max(bm25_scores) if bm25_scores else 1.0
        vector_max = max(vector_scores) if vector_scores else 1.0
        
        # Create lookup for normalized scores
        bm25_normalized = {r.chunk_id: r.score / bm25_max for r in bm25_results}
        vector_normalized = {r.chunk_id: r.score / vector_max for r in vector_results}
        
        # Collect all unique chunk IDs
        all_chunk_ids = set(bm25_normalized.keys()) | set(vector_normalized.keys())
        
        # Calculate weighted scores
        weighted_scores = []
        for chunk_id in all_chunk_ids:
            bm25_norm = bm25_normalized.get(chunk_id, 0.0)
            vector_norm = vector_normalized.get(chunk_id, 0.0)
            
            weighted_score = bm25_weight * bm25_norm + vector_weight * vector_norm
            
            # Get the result with more details
            if chunk_id in vector_normalized:
                result = next(r for r in vector_results if r.chunk_id == chunk_id)
            else:
                result = next(r for r in bm25_results if r.chunk_id == chunk_id)
            
            # Create new result with weighted score
            fused_result = RetrievalResult(
                doc_id=result.doc_id,
                chunk_id=result.chunk_id,
                source=result.source,
                title=result.title,
                content=result.content,
                score=weighted_score,
                retriever="hybrid",
                metadata={
                    **result.metadata,
                    "bm25_normalized": bm25_norm,
                    "vector_normalized": vector_norm,
                    "bm25_weight": bm25_weight,
                    "vector_weight": vector_weight,
                }
            )
            weighted_scores.append((weighted_score, fused_result))
        
        # Sort by weighted score and return
        weighted_scores.sort(key=lambda x: x[0], reverse=True)
        return [result for _, result in weighted_scores]
    
    @staticmethod
    def deduplicate_results(results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Remove duplicate results based on chunk_id."""
        seen = set()
        unique_results = []
        
        for result in results:
            if result.chunk_id not in seen:
                seen.add(result.chunk_id)
                unique_results.append(result)
        
        return unique_results
    
    @staticmethod
    def fuse_results(
        bm25_results: List[RetrievalResult],
        vector_results: List[RetrievalResult],
        method: str = "rrf",
        **kwargs
    ) -> HybridRetrievalResult:
        """Main fusion method that combines results from multiple retrievers."""
        if method == "rrf":
            k = kwargs.get("k", 60)
            fused_results = FusionEngine.reciprocal_rank_fusion(bm25_results, vector_results, k)
            fusion_params = {"k": k}
        elif method == "weighted":
            bm25_weight = kwargs.get("bm25_weight", 0.4)
            vector_weight = kwargs.get("vector_weight", 0.6)
            fused_results = FusionEngine.weighted_fusion(bm25_results, vector_results, bm25_weight, vector_weight)
            fusion_params = {"bm25_weight": bm25_weight, "vector_weight": vector_weight}
        else:
            raise ValueError(f"Unknown fusion method: {method}")
        
        # Deduplicate and limit results
        fused_results = FusionEngine.deduplicate_results(fused_results)
        
        # Create retrieval debug info
        retrieval_debug = {
            "bm25_count": len(bm25_results),
            "vector_count": len(vector_results),
            "fused_count": len(fused_results),
            "fusion_method": method,
            "fusion_params": fusion_params,
        }
        
        return HybridRetrievalResult(
            results=fused_results,
            fusion_method=method,
            fusion_params=fusion_params,
            retrieval_debug=retrieval_debug
        ) 