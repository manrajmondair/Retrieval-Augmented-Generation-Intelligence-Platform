import re
import string
from typing import List, Dict, Set, Tuple, Optional
import asyncio
from functools import lru_cache
from dataclasses import dataclass
import hashlib


@dataclass
class ProcessedQuery:
    """Processed query with normalized text and metadata."""
    original: str
    normalized: str
    tokens: List[str]
    key_terms: List[str]
    query_type: str
    intent_score: float
    processing_time_ms: float


class QueryProcessor:
    """Advanced query preprocessing and normalization for optimal retrieval."""
    
    def __init__(self):
        # Common words that don't add much semantic value
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 
            'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }
        
        # Common question patterns
        self.question_patterns = {
            'what': ['what is', 'what are', 'what does', 'what can'],
            'how': ['how to', 'how do', 'how does', 'how can', 'how should'],
            'when': ['when is', 'when do', 'when does', 'when can'],
            'where': ['where is', 'where are', 'where can', 'where do'],
            'why': ['why is', 'why are', 'why do', 'why does'],
            'who': ['who is', 'who are', 'who can', 'who do']
        }
        
        # Domain-specific term expansions
        self.term_expansions = {
            'auth': ['authentication', 'authorize', 'login', 'signin', 'access'],
            'api': ['application programming interface', 'endpoint', 'service'],
            'db': ['database', 'data store', 'storage'],
            'vector': ['embedding', 'semantic search', 'similarity'],
            'ml': ['machine learning', 'artificial intelligence', 'ai'],
            'rag': ['retrieval augmented generation', 'retrieval'],
        }
        
        # Query type classifiers
        self.query_types = {
            'definition': ['what is', 'define', 'definition of', 'meaning of'],
            'procedure': ['how to', 'steps to', 'process for', 'way to'],
            'comparison': ['vs', 'versus', 'difference between', 'compare'],
            'troubleshooting': ['error', 'problem', 'issue', 'fix', 'solve'],
            'configuration': ['setup', 'configure', 'install', 'enable'],
            'policy': ['policy', 'rule', 'guideline', 'requirement']
        }
        
        # Cache for processed queries
        self._query_cache: Dict[str, ProcessedQuery] = {}
        self._cache_hits = 0
        self._cache_misses = 0
    
    @lru_cache(maxsize=1000)
    def _get_cache_key(self, query: str) -> str:
        """Generate cache key for query."""
        return hashlib.md5(query.encode()).hexdigest()
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for better matching."""
        # Convert to lowercase
        text = text.lower().strip()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove punctuation except for important ones
        text = re.sub(r'[^\w\s\-\.]', ' ', text)
        
        # Handle common contractions
        contractions = {
            "don't": "do not", "won't": "will not", "can't": "cannot",
            "shouldn't": "should not", "wouldn't": "would not",
            "couldn't": "could not", "isn't": "is not", "aren't": "are not",
            "wasn't": "was not", "weren't": "were not"
        }
        
        for contraction, expansion in contractions.items():
            text = text.replace(contraction, expansion)
        
        return text
    
    def _tokenize(self, text: str) -> List[str]:
        """Advanced tokenization with filtering."""
        # Split on whitespace and punctuation
        tokens = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out stop words and very short tokens
        filtered_tokens = [
            token for token in tokens 
            if token not in self.stop_words and len(token) > 1
        ]
        
        return filtered_tokens
    
    def _extract_key_terms(self, tokens: List[str]) -> List[str]:
        """Extract the most important terms from tokens."""
        # Remove stop words and get unique terms
        key_terms = list(set(tokens))
        
        # Prioritize longer terms
        key_terms.sort(key=len, reverse=True)
        
        # Expand domain-specific terms
        expanded_terms = []
        for term in key_terms:
            expanded_terms.append(term)
            if term in self.term_expansions:
                expanded_terms.extend(self.term_expansions[term])
        
        return expanded_terms[:10]  # Limit to top 10 terms
    
    def _classify_query_type(self, normalized_query: str) -> Tuple[str, float]:
        """Classify the query type and return confidence score."""
        scores = {}
        
        for query_type, patterns in self.query_types.items():
            score = 0
            for pattern in patterns:
                if pattern in normalized_query:
                    score += 1
            scores[query_type] = score / len(patterns)  # Normalize by pattern count
        
        if not scores or max(scores.values()) == 0:
            return 'general', 0.5
        
        best_type = max(scores, key=scores.get)
        confidence = scores[best_type]
        
        return best_type, min(confidence * 2, 1.0)  # Scale confidence
    
    def _expand_query_terms(self, tokens: List[str]) -> List[str]:
        """Expand query terms with synonyms and related terms."""
        expanded = tokens.copy()
        
        for token in tokens:
            if token in self.term_expansions:
                expanded.extend(self.term_expansions[token])
        
        return list(set(expanded))  # Remove duplicates
    
    def _detect_intent_strength(self, query: str, tokens: List[str]) -> float:
        """Detect how specific/intentional the query is."""
        intent_signals = 0
        total_signals = 5
        
        # 1. Has question words
        question_words = ['what', 'how', 'when', 'where', 'why', 'who']
        if any(word in tokens for word in question_words):
            intent_signals += 1
        
        # 2. Has specific technical terms
        technical_terms = ['api', 'auth', 'vector', 'database', 'config', 'setup']
        if any(term in tokens for term in technical_terms):
            intent_signals += 1
        
        # 3. Length indicates specificity
        if len(tokens) >= 3:
            intent_signals += 1
        
        # 4. Has action words
        action_words = ['configure', 'setup', 'install', 'create', 'delete', 'update']
        if any(word in tokens for word in action_words):
            intent_signals += 1
        
        # 5. Has proper nouns or specific entities
        if any(token.istitle() for token in query.split()):
            intent_signals += 1
        
        return intent_signals / total_signals
    
    async def process_query(self, query: str) -> ProcessedQuery:
        """Process a query with comprehensive normalization and analysis."""
        import time
        start_time = time.time()
        
        # Check cache first
        cache_key = self._get_cache_key(query)
        if cache_key in self._query_cache:
            self._cache_hits += 1
            cached_result = self._query_cache[cache_key]
            # Update processing time for cache hit
            cached_result.processing_time_ms = (time.time() - start_time) * 1000
            return cached_result
        
        # Normalize the query text
        normalized = self._normalize_text(query)
        
        # Tokenize
        tokens = self._tokenize(normalized)
        
        # Extract key terms
        key_terms = self._extract_key_terms(tokens)
        
        # Classify query type
        query_type, intent_score = self._classify_query_type(normalized)
        
        # Calculate intent strength
        intent_strength = self._detect_intent_strength(query, tokens)
        final_intent_score = (intent_score + intent_strength) / 2
        
        processing_time = (time.time() - start_time) * 1000
        
        # Create processed query
        processed = ProcessedQuery(
            original=query,
            normalized=normalized,
            tokens=tokens,
            key_terms=key_terms,
            query_type=query_type,
            intent_score=final_intent_score,
            processing_time_ms=processing_time
        )
        
        # Cache the result (limit cache size)
        if len(self._query_cache) < 500:
            self._query_cache[cache_key] = processed
        
        self._cache_misses += 1
        return processed
    
    def optimize_for_retrieval(self, processed_query: ProcessedQuery) -> str:
        """Optimize processed query for better retrieval performance."""
        # Start with normalized query
        optimized = processed_query.normalized
        
        # For procedural queries, emphasize action terms
        if processed_query.query_type == 'procedure':
            action_terms = [t for t in processed_query.tokens if t in ['setup', 'configure', 'install', 'create']]
            if action_terms:
                optimized = ' '.join(action_terms) + ' ' + optimized
        
        # For definition queries, emphasize the subject
        elif processed_query.query_type == 'definition':
            # Remove question words for cleaner search
            optimized = re.sub(r'\b(what is|what are|define)\b', '', optimized).strip()
        
        # For troubleshooting, emphasize problem terms
        elif processed_query.query_type == 'troubleshooting':
            problem_terms = [t for t in processed_query.tokens if t in ['error', 'problem', 'issue', 'fail']]
            if problem_terms:
                optimized = optimized + ' ' + ' '.join(problem_terms)
        
        # Boost key terms
        if processed_query.key_terms:
            top_terms = processed_query.key_terms[:3]  # Top 3 most important terms
            optimized = optimized + ' ' + ' '.join(top_terms)
        
        return optimized.strip()
    
    def get_query_variants(self, processed_query: ProcessedQuery) -> List[str]:
        """Generate query variants for better retrieval coverage."""
        variants = [processed_query.normalized]
        
        # Add optimized version
        optimized = self.optimize_for_retrieval(processed_query)
        if optimized != processed_query.normalized:
            variants.append(optimized)
        
        # Add key terms only version
        if len(processed_query.key_terms) >= 2:
            key_terms_query = ' '.join(processed_query.key_terms[:4])
            variants.append(key_terms_query)
        
        # Add expanded terms version
        expanded_tokens = self._expand_query_terms(processed_query.tokens)
        if len(expanded_tokens) > len(processed_query.tokens):
            expanded_query = ' '.join(expanded_tokens[:6])
            variants.append(expanded_query)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variants = []
        for variant in variants:
            if variant not in seen and len(variant.strip()) > 0:
                seen.add(variant)
                unique_variants.append(variant)
        
        return unique_variants[:3]  # Limit to 3 variants for performance
    
    def get_stats(self) -> Dict[str, any]:
        """Get query processing statistics."""
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0
        
        return {
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate_percent': round(hit_rate, 1),
            'cache_size': len(self._query_cache),
            'stop_words_count': len(self.stop_words),
            'term_expansions_count': len(self.term_expansions)
        }


# Global instance
_query_processor = None

def get_query_processor() -> QueryProcessor:
    """Get or create the query processor singleton."""
    global _query_processor
    if _query_processor is None:
        _query_processor = QueryProcessor()
    return _query_processor