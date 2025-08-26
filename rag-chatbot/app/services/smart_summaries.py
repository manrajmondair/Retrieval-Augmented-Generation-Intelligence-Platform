"""
Smart Summaries Service - Generate different types of intelligent summaries.
"""
import asyncio
import time
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from app.services.fast_llm import get_fast_llm_service
from app.services.redis_pool import get_redis_pool
from app.rag.schemas import RetrievalResult


class SummaryType(Enum):
    """Different types of summaries available."""
    EXECUTIVE = "executive"          # 2-sentence executive summary
    BULLET_POINTS = "bullet_points"  # Key points as bullets
    ONE_LINER = "one_liner"         # Single sentence summary
    DETAILED = "detailed"           # Comprehensive summary
    ACTION_ITEMS = "action_items"   # Actionable items extracted
    KEY_INSIGHTS = "key_insights"   # Most important insights
    MEETING_NOTES = "meeting_notes" # Meeting-style notes
    RESEARCH_BRIEF = "research_brief" # Research paper brief


@dataclass
class SmartSummary:
    """Represents a generated smart summary."""
    summary_type: SummaryType
    content: str
    confidence: float
    word_count: int
    reading_time_seconds: int
    key_terms: List[str]
    generated_at: float
    source_doc_count: int


class SmartSummaryService:
    """Service for generating intelligent, context-aware summaries."""
    
    def __init__(self):
        self.llm_service = get_fast_llm_service()
        self.redis_pool = get_redis_pool()
        
        # Pre-built prompts for different summary types
        self.summary_prompts = {
            SummaryType.EXECUTIVE: {
                "prompt": "Create a 2-sentence executive summary that captures the most critical information and key takeaway. Be concise and impactful.",
                "max_length": 200
            },
            SummaryType.BULLET_POINTS: {
                "prompt": "Extract the 5 most important points as bullet points. Each point should be one clear, actionable sentence. Use • format.",
                "max_length": 300
            },
            SummaryType.ONE_LINER: {
                "prompt": "Summarize this in exactly one powerful sentence that captures the main point. Be direct and compelling.",
                "max_length": 100
            },
            SummaryType.DETAILED: {
                "prompt": "Create a comprehensive summary covering all major points, findings, and implications. Include context and significance.",
                "max_length": 500
            },
            SummaryType.ACTION_ITEMS: {
                "prompt": "Extract specific action items, recommendations, or next steps mentioned. Format as numbered list with clear actions.",
                "max_length": 300
            },
            SummaryType.KEY_INSIGHTS: {
                "prompt": "Identify the 3 most significant insights, discoveries, or conclusions. Explain why each is important.",
                "max_length": 400
            },
            SummaryType.MEETING_NOTES: {
                "prompt": "Format as meeting notes with key decisions, action items, and important discussions. Use clear headers.",
                "max_length": 400
            },
            SummaryType.RESEARCH_BRIEF: {
                "prompt": "Create a research brief covering methodology, key findings, and implications. Include significance and limitations.",
                "max_length": 500
            }
        }
    
    async def generate_summary(self, 
                             content: str, 
                             summary_type: SummaryType,
                             doc_id: Optional[str] = None) -> SmartSummary:
        """Generate a smart summary of the specified type."""
        start_time = time.time()
        
        # Check cache first if doc_id provided
        if doc_id:
            cached_summary = await self._get_cached_summary(doc_id, summary_type)
            if cached_summary:
                return cached_summary
        
        # Prepare content for processing
        processed_content = self._prepare_content(content, summary_type)
        
        # Get prompt configuration
        prompt_config = self.summary_prompts[summary_type]
        
        # Create mock retrieval result for LLM service
        mock_result = RetrievalResult(
            doc_id=doc_id or "unknown",
            chunk_id="summary_chunk_1",
            content=processed_content,
            source="document",
            score=1.0,
            title="Document Content",
            retriever="mock"
        )
        
        # Generate summary
        try:
            summary_text = await self.llm_service.generate_answer(
                prompt_config["prompt"],
                [mock_result]
            )
            
            # Clean and validate summary
            summary_text = summary_text.strip()
            if len(summary_text) > prompt_config["max_length"]:
                summary_text = summary_text[:prompt_config["max_length"]] + "..."
            
            # Calculate metrics
            word_count = len(summary_text.split())
            reading_time = max(5, word_count * 0.4)  # ~150 wpm reading speed
            
            # Extract key terms
            key_terms = self._extract_key_terms(summary_text)
            
            # Calculate confidence based on content quality
            confidence = self._calculate_confidence(content, summary_text, summary_type)
            
            summary = SmartSummary(
                summary_type=summary_type,
                content=summary_text,
                confidence=confidence,
                word_count=word_count,
                reading_time_seconds=int(reading_time),
                key_terms=key_terms,
                generated_at=time.time(),
                source_doc_count=1
            )
            
            # Cache the summary
            if doc_id:
                await self._cache_summary(doc_id, summary_type, summary)
            
            return summary
            
        except Exception as e:
            # Fallback summary
            return SmartSummary(
                summary_type=summary_type,
                content=f"Unable to generate {summary_type.value} summary. Content may be too complex or short.",
                confidence=0.1,
                word_count=0,
                reading_time_seconds=5,
                key_terms=[],
                generated_at=time.time(),
                source_doc_count=1
            )
    
    async def generate_multi_summary(self, 
                                   content: str, 
                                   summary_types: List[SummaryType],
                                   doc_id: Optional[str] = None) -> Dict[SummaryType, SmartSummary]:
        """Generate multiple summary types in parallel for efficiency."""
        tasks = [
            self.generate_summary(content, summary_type, doc_id)
            for summary_type in summary_types
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        summaries = {}
        for i, result in enumerate(results):
            if not isinstance(result, Exception):
                summaries[summary_types[i]] = result
        
        return summaries
    
    async def generate_summary_suite(self, content: str, doc_id: Optional[str] = None) -> Dict[str, SmartSummary]:
        """Generate a complete suite of summaries for comprehensive understanding."""
        priority_types = [
            SummaryType.EXECUTIVE,
            SummaryType.BULLET_POINTS,
            SummaryType.KEY_INSIGHTS,
            SummaryType.ACTION_ITEMS
        ]
        
        summaries = await self.generate_multi_summary(content, priority_types, doc_id)
        
        # Convert enum keys to strings for JSON serialization
        return {summary_type.value: summary for summary_type, summary in summaries.items()}
    
    def _prepare_content(self, content: str, summary_type: SummaryType) -> str:
        """Prepare content based on summary type requirements."""
        # Determine optimal content length based on summary type
        max_content_length = {
            SummaryType.EXECUTIVE: 2000,
            SummaryType.BULLET_POINTS: 1500,
            SummaryType.ONE_LINER: 800,
            SummaryType.DETAILED: 3000,
            SummaryType.ACTION_ITEMS: 2000,
            SummaryType.KEY_INSIGHTS: 2500,
            SummaryType.MEETING_NOTES: 2000,
            SummaryType.RESEARCH_BRIEF: 3000
        }
        
        target_length = max_content_length.get(summary_type, 2000)
        
        if len(content) <= target_length:
            return content
        
        # Intelligent truncation - prioritize beginning and end
        if summary_type in [SummaryType.EXECUTIVE, SummaryType.KEY_INSIGHTS]:
            # For executive summaries, take beginning and conclusion
            first_part = content[:target_length//2]
            last_part = content[-(target_length//2):]
            return first_part + "...\n[CONTENT CONTINUES]\n..." + last_part
        else:
            # For others, take beginning primarily
            return content[:target_length] + "..."
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from the summary text."""
        import re
        
        # Simple key term extraction
        words = re.findall(r'\b[A-Za-z]{4,}\b', text.lower())
        
        # Filter common words
        stop_words = {'this', 'that', 'with', 'have', 'will', 'been', 'from', 'they', 'them', 
                     'were', 'said', 'each', 'which', 'their', 'time', 'would', 'there', 
                     'make', 'more', 'very', 'what', 'know', 'just', 'first', 'into', 'over'}
        
        key_terms = [word for word in set(words) if word not in stop_words]
        
        # Return top 5 most relevant terms
        return sorted(key_terms)[:5]
    
    def _calculate_confidence(self, original_content: str, summary: str, summary_type: SummaryType) -> float:
        """Calculate confidence score for the summary quality."""
        base_confidence = 0.7
        
        # Length appropriateness
        expected_lengths = {
            SummaryType.EXECUTIVE: (50, 200),
            SummaryType.BULLET_POINTS: (100, 300),
            SummaryType.ONE_LINER: (20, 100),
            SummaryType.DETAILED: (200, 500),
            SummaryType.ACTION_ITEMS: (50, 300)
        }
        
        expected_range = expected_lengths.get(summary_type, (50, 300))
        summary_length = len(summary)
        
        if expected_range[0] <= summary_length <= expected_range[1]:
            length_bonus = 0.2
        else:
            length_bonus = 0.0
        
        # Content quality indicators
        has_specific_details = len([word for word in summary.split() if len(word) > 6]) > 0
        quality_bonus = 0.1 if has_specific_details else 0.0
        
        return min(1.0, base_confidence + length_bonus + quality_bonus)
    
    async def _get_cached_summary(self, doc_id: str, summary_type: SummaryType) -> Optional[SmartSummary]:
        """Get cached summary if available."""
        try:
            cache_key = f"summary:{doc_id}:{summary_type.value}"
            cached_data = await self.redis_pool.get_with_fallback(cache_key, "cache")
            
            if cached_data:
                summary_data = json.loads(cached_data.decode('utf-8'))
                
                return SmartSummary(
                    summary_type=SummaryType(summary_data["summary_type"]),
                    content=summary_data["content"],
                    confidence=summary_data["confidence"],
                    word_count=summary_data["word_count"],
                    reading_time_seconds=summary_data["reading_time_seconds"],
                    key_terms=summary_data["key_terms"],
                    generated_at=summary_data["generated_at"],
                    source_doc_count=summary_data["source_doc_count"]
                )
        except Exception:
            pass
        
        return None
    
    async def _cache_summary(self, doc_id: str, summary_type: SummaryType, summary: SmartSummary):
        """Cache summary for quick access."""
        try:
            cache_key = f"summary:{doc_id}:{summary_type.value}"
            summary_data = {
                "summary_type": summary.summary_type.value,
                "content": summary.content,
                "confidence": summary.confidence,
                "word_count": summary.word_count,
                "reading_time_seconds": summary.reading_time_seconds,
                "key_terms": summary.key_terms,
                "generated_at": summary.generated_at,
                "source_doc_count": summary.source_doc_count
            }
            
            await self.redis_pool.set_with_optimization(
                cache_key,
                json.dumps(summary_data).encode('utf-8'),
                1800,  # 30 minute TTL
                "cache"
            )
        except Exception:
            pass  # Continue without caching
    
    async def get_summary_analytics(self, doc_id: str) -> Dict[str, Any]:
        """Get analytics for all summaries of a document."""
        analytics = {
            "available_summaries": [],
            "total_summaries": 0,
            "average_confidence": 0.0,
            "total_reading_time": 0,
            "common_key_terms": []
        }
        
        all_key_terms = []
        all_confidences = []
        
        for summary_type in SummaryType:
            cached_summary = await self._get_cached_summary(doc_id, summary_type)
            if cached_summary:
                analytics["available_summaries"].append({
                    "type": summary_type.value,
                    "word_count": cached_summary.word_count,
                    "confidence": cached_summary.confidence,
                    "reading_time": cached_summary.reading_time_seconds
                })
                
                all_key_terms.extend(cached_summary.key_terms)
                all_confidences.append(cached_summary.confidence)
                analytics["total_reading_time"] += cached_summary.reading_time_seconds
        
        analytics["total_summaries"] = len(analytics["available_summaries"])
        
        if all_confidences:
            analytics["average_confidence"] = round(sum(all_confidences) / len(all_confidences), 2)
        
        if all_key_terms:
            from collections import Counter
            term_counts = Counter(all_key_terms)
            analytics["common_key_terms"] = [term for term, count in term_counts.most_common(5)]
        
        return analytics


# Global instance
_smart_summary_service = None

def get_smart_summary_service() -> SmartSummaryService:
    """Get or create the smart summary service singleton."""
    global _smart_summary_service
    if _smart_summary_service is None:
        _smart_summary_service = SmartSummaryService()
    return _smart_summary_service