import pickle
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict
import numpy as np
from rank_bm25 import BM25Okapi
from app.rag.retrievers.base import BaseRetriever
from app.rag.schemas import DocumentChunk, RetrievalResult


class BM25Retriever(BaseRetriever):
    """Memory-optimized BM25 sparse retriever with precomputed scores."""
    
    def __init__(self, k1: float = 1.2, b: float = 0.75, persist_path: str = "/tmp/bm25_index.pkl"):
        self.k1 = k1
        self.b = b
        self.persist_path = Path(persist_path)
        self.bm25: BM25Okapi | None = None
        self.documents: List[DocumentChunk] = []
        self.tokenized_docs: List[List[str]] = []
        
        # Memory-based optimizations
        self._precomputed_scores: Dict[str, np.ndarray] = {}
        self._term_doc_freq: Dict[str, List[int]] = defaultdict(list)
        self._doc_lengths: Optional[np.ndarray] = None
        self._avg_doc_length: float = 0.0
        self._score_cache: Dict[str, List[RetrievalResult]] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Temporarily disable index loading to debug
        # self._load_index()
    
    def _tokenize(self, text: str) -> List[str]:
        """Optimized tokenization with normalization."""
        if not text or not isinstance(text, str):
            return []
        
        try:
            # More aggressive preprocessing for better retrieval
            text = text.lower().replace('\n', ' ').replace('\t', ' ')
            # Remove punctuation except hyphens and periods for better tokenization
            import re
            text = re.sub(r'[^\w\s\-\.]', ' ', text)
            # Remove extra spaces and split
            tokens = [token.strip('.-') for token in text.split() if len(token.strip('.-')) > 1]
            return [token for token in tokens if token and len(token) > 1]
        except Exception as e:
            print(f"Tokenization error for text: {text[:50]}, error: {e}")
            return []
    
    def _load_index(self) -> None:
        """Load BM25 index from disk with memory optimizations."""
        if self.persist_path.exists():
            try:
                with open(self.persist_path, 'rb') as f:
                    data = pickle.load(f)
                    self.bm25 = data['bm25']
                    self.documents = data['documents']
                    self.tokenized_docs = data['tokenized_docs']
                    # Load optimizations if available
                    self._precomputed_scores = data.get('precomputed_scores', {})
                    self._term_doc_freq = data.get('term_doc_freq', defaultdict(list))
                    self._doc_lengths = data.get('doc_lengths')
                    self._avg_doc_length = data.get('avg_doc_length', 0.0)
                    
                    # Build memory optimizations if not loaded
                    if not self._precomputed_scores and self.bm25:
                        self._build_memory_optimizations()
            except Exception as e:
                print(f"Failed to load BM25 index: {e}")
                self._reset_index()
    
    def _reset_index(self):
        """Reset all index data."""
        self.bm25 = None
        self.documents = []
        self.tokenized_docs = []
        self._precomputed_scores = {}
        self._term_doc_freq = defaultdict(list)
        self._doc_lengths = None
        self._avg_doc_length = 0.0
        self._score_cache = {}
    
    def _save_index(self) -> None:
        """Save BM25 index with memory optimizations to disk."""
        if self.bm25 is not None:
            try:
                data = {
                    'bm25': self.bm25,
                    'documents': self.documents,
                    'tokenized_docs': self.tokenized_docs,
                    'precomputed_scores': self._precomputed_scores,
                    'term_doc_freq': dict(self._term_doc_freq),
                    'doc_lengths': self._doc_lengths,
                    'avg_doc_length': self._avg_doc_length
                }
                with open(self.persist_path, 'wb') as f:
                    pickle.dump(data, f)
            except Exception as e:
                print(f"Failed to save BM25 index: {e}")
    
    def _build_memory_optimizations(self) -> None:
        """Build memory-based optimizations for fast retrieval."""
        if not self.tokenized_docs or not self.bm25:
            return
        
        # Precompute document lengths
        self._doc_lengths = np.array([len(doc) for doc in self.tokenized_docs])
        self._avg_doc_length = np.mean(self._doc_lengths)
        
        # Build term-document frequency mapping
        self._term_doc_freq.clear()
        for doc_idx, tokens in enumerate(self.tokenized_docs):
            for token in set(tokens):  # Only unique tokens per document
                self._term_doc_freq[token].append(doc_idx)
    
    async def add_documents(self, chunks: List[DocumentChunk]) -> None:
        """Add documents to the BM25 index with memory optimizations."""
        # Filter out duplicates by content hash
        existing_hashes = {doc.content_hash for doc in self.documents}
        new_chunks = [chunk for chunk in chunks if chunk.content_hash not in existing_hashes]
        
        if not new_chunks:
            return
        
        # Clear cache when adding new documents
        self._score_cache.clear()
        
        # Tokenize new documents in parallel
        new_tokenized = [self._tokenize(chunk.content) for chunk in new_chunks]
        
        # Add to existing index or create new one
        if self.bm25 is None:
            self.bm25 = BM25Okapi(new_tokenized, k1=self.k1, b=self.b)
            self.documents = new_chunks
            self.tokenized_docs = new_tokenized
        else:
            # Rebuild index with all documents
            all_docs = self.documents + new_chunks
            all_tokenized = self.tokenized_docs + new_tokenized
            self.bm25 = BM25Okapi(all_tokenized, k1=self.k1, b=self.b)
            self.documents = all_docs
            self.tokenized_docs = all_tokenized
        
        # Build memory optimizations
        self._build_memory_optimizations()
        self._save_index()
    
    def _get_cache_key(self, query: str, top_k: int) -> str:
        """Generate cache key for query and parameters."""
        return f"{query.lower()}:{top_k}"
    
    async def retrieve(self, query: str, top_k: int) -> List[RetrievalResult]:
        """Fast BM25 retrieval with memory optimizations and caching."""
        if self.bm25 is None or not self.documents:
            return []
        
        # Check cache first
        cache_key = self._get_cache_key(query, top_k)
        if cache_key in self._score_cache:
            self._cache_hits += 1
            return self._score_cache[cache_key]
        
        # Tokenize query with same preprocessing
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        
        try:
            # Fast scoring with memory optimizations
            if self._doc_lengths is not None and len(query_tokens) <= 5:  # Use fast path for short queries
                scores = self._fast_score(query_tokens)
            else:
                scores = self.bm25.get_scores(query_tokens)
            
            # Use numpy for faster sorting
            if len(scores) > 100:  # Use numpy for large result sets
                score_indices = np.argsort(scores)[::-1]
                top_indices = score_indices[:top_k]
                top_scores = scores[top_indices]
            else:
                # Use simple sorting for small result sets
                scored_docs = [(score, i) for i, score in enumerate(scores) if score > 0.001]  # Filter very low scores
                scored_docs.sort(key=lambda x: x[0], reverse=True)
                top_indices = [idx for _, idx in scored_docs[:top_k]]
                top_scores = [score for score, _ in scored_docs[:top_k]]
            
            # Build results efficiently
            results = []
            for i, (idx, score) in enumerate(zip(top_indices, top_scores)):
                if i >= top_k or score <= 0.001:  # Early termination
                    break
                    
                doc = self.documents[idx]
                result = RetrievalResult(
                    doc_id=doc.doc_id,
                    chunk_id=doc.chunk_id,
                    source=doc.source,
                    title=doc.title,
                    content=doc.content,
                    score=float(score),
                    retriever="bm25",
                    metadata={
                        "chunk_index": doc.chunk_index,
                        "content_hash": doc.content_hash,
                        **doc.metadata
                    }
                )
                results.append(result)
            
            # Cache results (limit cache size)
            if len(self._score_cache) < 200:
                self._score_cache[cache_key] = results
            
            self._cache_misses += 1
            return results
            
        except Exception as e:
            print(f"BM25 retrieval error: {e}")
            return []
    
    def _fast_score(self, query_tokens: List[str]) -> np.ndarray:
        """Fast scoring for short queries using precomputed data."""
        if not self._doc_lengths is not None:
            return self.bm25.get_scores(query_tokens)
        
        scores = np.zeros(len(self.documents))
        
        for token in query_tokens:
            if token in self._term_doc_freq:
                # Get documents containing this term
                doc_indices = self._term_doc_freq[token]
                
                # Compute TF for each document containing the term
                for doc_idx in doc_indices:
                    tf = self.tokenized_docs[doc_idx].count(token)
                    doc_len = self._doc_lengths[doc_idx]
                    
                    # BM25 scoring formula
                    idf = np.log((len(self.documents) - len(doc_indices) + 0.5) / (len(doc_indices) + 0.5))
                    score = idf * (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * doc_len / self._avg_doc_length))
                    scores[doc_idx] += score
        
        return scores
    
    async def delete_documents(self, doc_ids: List[str]) -> None:
        """Delete documents from the BM25 index."""
        if not self.documents:
            return
        
        # Clear cache when deleting documents
        self._score_cache.clear()
        
        # Filter out documents to delete
        self.documents = [doc for doc in self.documents if doc.doc_id not in doc_ids]
        self.tokenized_docs = [self._tokenize(doc.content) for doc in self.documents]
        
        # Rebuild index and optimizations
        if self.documents:
            self.bm25 = BM25Okapi(self.tokenized_docs, k1=self.k1, b=self.b)
            self._build_memory_optimizations()
        else:
            self._reset_index()
        
        self._save_index()
    
    async def clear(self) -> None:
        """Clear all documents from the BM25 index."""
        self._reset_index()
        if self.persist_path.exists():
            self.persist_path.unlink()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get BM25 caching statistics."""
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0
        
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percent": round(hit_rate, 1),
            "cache_size": len(self._score_cache),
            "precomputed_terms": len(self._term_doc_freq),
            "memory_optimizations": self._doc_lengths is not None
        }
    
    async def is_ready(self) -> bool:
        """Check if the BM25 retriever is ready."""
        return self.bm25 is not None and len(self.documents) > 0 