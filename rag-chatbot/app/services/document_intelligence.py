"""
Document Intelligence Service - Automatically generates insights, summaries, and analysis.
"""
import asyncio
import time
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from app.services.fast_llm import get_fast_llm_service
from app.services.redis_pool import get_redis_pool
from app.rag.schemas import DocumentChunk, RetrievalResult


@dataclass
class DocumentInsight:
    """Represents an automatically generated document insight."""
    type: str  # "key_finding", "risk", "opportunity", "trend", "action_item"
    title: str
    content: str
    confidence: float
    source_chunk: str
    priority: str  # "high", "medium", "low"


@dataclass
class DocumentIntelligence:
    """Complete document intelligence analysis."""
    doc_id: str
    filename: str
    executive_summary: str
    key_insights: List[DocumentInsight]
    document_score: Dict[str, float]  # completeness, clarity, actionability
    topic_tags: List[str]
    reading_time_minutes: int
    complexity_level: str  # "basic", "intermediate", "advanced"
    document_type: str  # "research", "report", "contract", "policy", etc.
    generated_at: float


class DocumentIntelligenceService:
    """Automatically analyzes documents and generates actionable insights."""
    
    def __init__(self):
        self.llm_service = get_fast_llm_service()
        self.redis_pool = get_redis_pool()
        
        # Pre-built analysis prompts for different document types
        self.analysis_prompts = {
            "executive_summary": (
                "Create a 2-sentence executive summary of this document. "
                "Focus on the most important takeaways and actionable insights."
            ),
            "key_findings": (
                "Extract the 3 most important findings, conclusions, or key points from this document. "
                "Format as bullet points. Be specific and actionable."
            ),
            "risks_opportunities": (
                "Identify any risks, challenges, opportunities, or action items mentioned in this document. "
                "Categorize each as RISK or OPPORTUNITY and provide brief explanation."
            ),
            "document_type": (
                "What type of document is this? Choose from: research_paper, business_report, "
                "contract, policy_document, meeting_notes, technical_spec, financial_report, "
                "academic_paper, legal_document, or other. Answer with one word only."
            ),
            "topic_tags": (
                "Generate 3-5 topic tags for this document. These should be single words or "
                "short phrases that capture the main subjects. Separate with commas."
            ),
            "complexity": (
                "Rate the complexity of this document as: basic, intermediate, or advanced. "
                "Consider technical language, concepts, and required background knowledge."
            )
        }
    
    async def analyze_document(self, chunks: List[DocumentChunk]) -> DocumentIntelligence:
        """Generate comprehensive document intelligence from chunks."""
        if not chunks:
            raise ValueError("No chunks provided for analysis")
        
        start_time = time.time()
        doc_id = chunks[0].doc_id
        filename = chunks[0].source.split('/')[-1] if '/' in chunks[0].source else chunks[0].source
        
        # Combine chunks into full document text (limited for performance)
        full_text = self._combine_chunks_intelligently(chunks)
        
        # Run multiple analyses in parallel for speed
        analysis_tasks = [
            self._generate_executive_summary(full_text),
            self._extract_key_insights(chunks),
            self._analyze_document_type(full_text),
            self._generate_topic_tags(full_text),
            self._assess_complexity(full_text),
            self._calculate_document_metrics(full_text)
        ]
        
        results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # Parse results (with error handling)
        executive_summary = results[0] if not isinstance(results[0], Exception) else "Summary unavailable"
        key_insights = results[1] if not isinstance(results[1], Exception) else []
        document_type = results[2] if not isinstance(results[2], Exception) else "other"
        topic_tags = results[3] if not isinstance(results[3], Exception) else []
        complexity_level = results[4] if not isinstance(results[4], Exception) else "intermediate"
        document_score = results[5] if not isinstance(results[5], Exception) else {"completeness": 0.5, "clarity": 0.5, "actionability": 0.5}
        
        # Calculate reading time
        word_count = len(full_text.split())
        reading_time = max(1, word_count // 250)  # Average reading speed
        
        intelligence = DocumentIntelligence(
            doc_id=doc_id,
            filename=filename,
            executive_summary=executive_summary,
            key_insights=key_insights,
            document_score=document_score,
            topic_tags=topic_tags,
            reading_time_minutes=reading_time,
            complexity_level=complexity_level,
            document_type=document_type,
            generated_at=time.time()
        )
        
        # Cache the intelligence for quick access
        await self._cache_intelligence(doc_id, intelligence)
        
        return intelligence
    
    def _combine_chunks_intelligently(self, chunks: List[DocumentChunk], max_chars: int = 3000) -> str:
        """Combine chunks intelligently, prioritizing beginnings and conclusions."""
        if not chunks:
            return ""
        
        # Take first few chunks (introduction) and last few (conclusion)
        priority_chunks = []
        
        # First 2 chunks (introduction/abstract)
        priority_chunks.extend(chunks[:2])
        
        # Last 2 chunks (conclusions/summary)
        if len(chunks) > 2:
            priority_chunks.extend(chunks[-2:])
        
        # Fill remaining space with middle chunks if needed
        remaining_chars = max_chars - sum(len(chunk.content) for chunk in priority_chunks)
        if remaining_chars > 0 and len(chunks) > 4:
            middle_chunks = chunks[2:-2]
            for chunk in middle_chunks:
                if len(chunk.content) <= remaining_chars:
                    priority_chunks.append(chunk)
                    remaining_chars -= len(chunk.content)
                else:
                    break
        
        # Combine and truncate if necessary
        combined_text = "\n\n".join([chunk.content for chunk in priority_chunks])
        return combined_text[:max_chars] + "..." if len(combined_text) > max_chars else combined_text
    
    async def _generate_executive_summary(self, text: str) -> str:
        """Generate executive summary."""
        try:
            # Create a mock retrieval result for the LLM service
            mock_results = [RetrievalResult(
                content=text[:1500],  # Limit for speed
                source="document",
                score=1.0,
                title="Document"
            )]
            
            summary = await self.llm_service.generate_answer(
                self.analysis_prompts["executive_summary"],
                mock_results
            )
            return summary.strip()
            
        except Exception:
            return "Executive summary could not be generated."
    
    async def _extract_key_insights(self, chunks: List[DocumentChunk]) -> List[DocumentInsight]:
        """Extract key insights from document chunks."""
        insights = []
        
        try:
            # Analyze top chunks for insights
            top_chunks = chunks[:5]  # Limit for performance
            
            for i, chunk in enumerate(top_chunks):
                mock_results = [RetrievalResult(
                    content=chunk.content[:800],
                    source=chunk.source,
                    score=1.0,
                    title=f"Section {i+1}"
                )]
                
                # Extract different types of insights
                findings_response = await self.llm_service.generate_answer(
                    "What are the key findings or important points in this text? Be specific and concise.",
                    mock_results
                )
                
                if findings_response and len(findings_response.strip()) > 20:
                    insight = DocumentInsight(
                        type="key_finding",
                        title=f"Key Finding from Section {i+1}",
                        content=findings_response.strip(),
                        confidence=0.8,
                        source_chunk=chunk.content[:200] + "...",
                        priority="medium"
                    )
                    insights.append(insight)
                
                # Limit insights for performance
                if len(insights) >= 3:
                    break
            
            return insights
            
        except Exception:
            return []
    
    async def _analyze_document_type(self, text: str) -> str:
        """Determine document type."""
        try:
            mock_results = [RetrievalResult(
                content=text[:500],
                source="document",
                score=1.0,
                title="Document"
            )]
            
            doc_type = await self.llm_service.generate_answer(
                self.analysis_prompts["document_type"],
                mock_results
            )
            
            # Clean and validate response
            doc_type = doc_type.strip().lower()
            valid_types = [
                "research_paper", "business_report", "contract", "policy_document",
                "meeting_notes", "technical_spec", "financial_report", "academic_paper",
                "legal_document", "other"
            ]
            
            return doc_type if doc_type in valid_types else "other"
            
        except Exception:
            return "other"
    
    async def _generate_topic_tags(self, text: str) -> List[str]:
        """Generate topic tags for the document."""
        try:
            mock_results = [RetrievalResult(
                content=text[:1000],
                source="document",
                score=1.0,
                title="Document"
            )]
            
            tags_response = await self.llm_service.generate_answer(
                self.analysis_prompts["topic_tags"],
                mock_results
            )
            
            # Parse and clean tags
            tags = [tag.strip().lower() for tag in tags_response.split(',')]
            tags = [tag for tag in tags if tag and len(tag) > 2]
            
            return tags[:5]  # Limit to 5 tags
            
        except Exception:
            return []
    
    async def _assess_complexity(self, text: str) -> str:
        """Assess document complexity level."""
        try:
            # Simple heuristics first (fast)
            word_count = len(text.split())
            avg_word_length = sum(len(word) for word in text.split()) / word_count if word_count > 0 else 0
            sentence_count = len(re.findall(r'[.!?]+', text))
            avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
            
            # Technical indicators
            technical_terms = len(re.findall(r'\b(?:algorithm|methodology|implementation|analysis|framework|architecture)\b', text.lower()))
            
            # Simple scoring
            complexity_score = 0
            complexity_score += min(avg_word_length - 4, 3) * 0.3  # Longer words = more complex
            complexity_score += min(avg_sentence_length - 15, 10) * 0.1  # Longer sentences = more complex
            complexity_score += min(technical_terms, 10) * 0.2  # Technical terms = more complex
            
            if complexity_score < 1.5:
                return "basic"
            elif complexity_score < 3.0:
                return "intermediate"
            else:
                return "advanced"
                
        except Exception:
            return "intermediate"
    
    async def _calculate_document_metrics(self, text: str) -> Dict[str, float]:
        """Calculate document quality metrics."""
        try:
            word_count = len(text.split())
            sentence_count = len(re.findall(r'[.!?]+', text))
            
            # Completeness score (based on length and structure)
            completeness = min(word_count / 500, 1.0)  # Up to 500 words = complete
            
            # Clarity score (based on readability)
            avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
            clarity = max(0.2, 1.0 - (avg_sentence_length - 15) * 0.05)  # Shorter sentences = clearer
            
            # Actionability score (based on action words)
            action_words = len(re.findall(r'\b(?:should|must|will|implement|develop|create|analyze|review|recommend)\b', text.lower()))
            actionability = min(action_words / 10, 1.0)  # Up to 10 action words = fully actionable
            
            return {
                "completeness": round(completeness, 2),
                "clarity": round(clarity, 2),
                "actionability": round(actionability, 2)
            }
            
        except Exception:
            return {"completeness": 0.5, "clarity": 0.5, "actionability": 0.5}
    
    async def _cache_intelligence(self, doc_id: str, intelligence: DocumentIntelligence):
        """Cache document intelligence for quick access."""
        try:
            cache_key = f"doc_intel:{doc_id}"
            intel_data = {
                "doc_id": intelligence.doc_id,
                "filename": intelligence.filename,
                "executive_summary": intelligence.executive_summary,
                "key_insights": [
                    {
                        "type": insight.type,
                        "title": insight.title,
                        "content": insight.content,
                        "confidence": insight.confidence,
                        "priority": insight.priority
                    }
                    for insight in intelligence.key_insights
                ],
                "document_score": intelligence.document_score,
                "topic_tags": intelligence.topic_tags,
                "reading_time_minutes": intelligence.reading_time_minutes,
                "complexity_level": intelligence.complexity_level,
                "document_type": intelligence.document_type,
                "generated_at": intelligence.generated_at
            }
            
            await self.redis_pool.set_with_optimization(
                cache_key,
                json.dumps(intel_data).encode('utf-8'),
                3600,  # 1 hour TTL
                "cache"
            )
            
        except Exception:
            pass  # Continue without caching
    
    async def get_cached_intelligence(self, doc_id: str) -> Optional[DocumentIntelligence]:
        """Get cached document intelligence."""
        try:
            cache_key = f"doc_intel:{doc_id}"
            cached_data = await self.redis_pool.get_with_fallback(cache_key, "cache")
            
            if cached_data:
                intel_data = json.loads(cached_data.decode('utf-8'))
                
                # Reconstruct insights
                insights = []
                for insight_data in intel_data.get("key_insights", []):
                    insight = DocumentInsight(
                        type=insight_data["type"],
                        title=insight_data["title"],
                        content=insight_data["content"],
                        confidence=insight_data["confidence"],
                        source_chunk="",
                        priority=insight_data["priority"]
                    )
                    insights.append(insight)
                
                return DocumentIntelligence(
                    doc_id=intel_data["doc_id"],
                    filename=intel_data["filename"],
                    executive_summary=intel_data["executive_summary"],
                    key_insights=insights,
                    document_score=intel_data["document_score"],
                    topic_tags=intel_data["topic_tags"],
                    reading_time_minutes=intel_data["reading_time_minutes"],
                    complexity_level=intel_data["complexity_level"],
                    document_type=intel_data["document_type"],
                    generated_at=intel_data["generated_at"]
                )
            
        except Exception:
            pass
        
        return None
    
    async def get_all_document_intelligence(self) -> List[Dict[str, Any]]:
        """Get intelligence for all documents."""
        try:
            # This would typically query a database
            # For now, return cached intelligence
            return []
        except Exception:
            return []


# Global instance
_doc_intelligence_service = None

def get_document_intelligence_service() -> DocumentIntelligenceService:
    """Get or create the document intelligence service singleton."""
    global _doc_intelligence_service
    if _doc_intelligence_service is None:
        _doc_intelligence_service = DocumentIntelligenceService()
    return _doc_intelligence_service