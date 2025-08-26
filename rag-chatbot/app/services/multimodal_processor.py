"""
Multi-modal Document Processor - Analyze images, tables, charts, and visual content.
"""
import asyncio
import base64
import io
import json
import time
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import hashlib

from app.services.redis_pool import get_redis_pool
from app.services.fast_llm import get_fast_llm_service
from app.rag.schemas import RetrievalResult


class MediaType(Enum):
    """Types of media content that can be processed."""
    IMAGE = "image"
    TABLE = "table"
    CHART = "chart"
    DIAGRAM = "diagram"
    SCREENSHOT = "screenshot"
    DOCUMENT_PAGE = "document_page"


@dataclass
class MediaAnalysis:
    """Results from analyzing visual/media content."""
    media_type: MediaType
    content_description: str
    extracted_text: Optional[str]
    key_insights: List[str]
    confidence: float
    processing_time_ms: int
    metadata: Dict[str, Any]


@dataclass
class TableData:
    """Structured representation of table content."""
    headers: List[str]
    rows: List[List[str]]
    summary: str
    key_metrics: Dict[str, Any]


@dataclass
class ChartAnalysis:
    """Analysis results for charts and graphs."""
    chart_type: str  # "bar", "line", "pie", "scatter", etc.
    title: Optional[str]
    data_points: List[Dict[str, Any]]
    trends: List[str]
    key_takeaways: List[str]


class MultimodalProcessor:
    """Service for processing and analyzing multi-modal document content."""
    
    def __init__(self):
        self.redis_pool = get_redis_pool()
        self.llm_service = get_fast_llm_service()
        
        # Vision model settings for different analysis types
        self.analysis_prompts = {
            MediaType.IMAGE: {
                "prompt": "Analyze this image and provide: 1) Detailed description 2) Any visible text 3) Key insights or important elements 4) Context or purpose",
                "max_tokens": 300
            },
            MediaType.TABLE: {
                "prompt": "Extract and analyze this table: 1) All data in structured format 2) Key metrics and patterns 3) Summary of findings 4) Important trends",
                "max_tokens": 400
            },
            MediaType.CHART: {
                "prompt": "Analyze this chart/graph: 1) Chart type and title 2) Data trends and patterns 3) Key insights 4) Conclusions or takeaways",
                "max_tokens": 300
            },
            MediaType.DIAGRAM: {
                "prompt": "Describe this diagram: 1) Overall structure and components 2) Relationships shown 3) Process or concept illustrated 4) Key information",
                "max_tokens": 350
            }
        }
    
    async def process_image(self, 
                          image_data: Union[bytes, str], 
                          media_type: MediaType = MediaType.IMAGE,
                          doc_id: Optional[str] = None) -> MediaAnalysis:
        """Process and analyze image content using vision models."""
        start_time = time.time()
        
        # Check cache first
        if doc_id and image_data:
            cache_key = self._generate_cache_key(image_data, media_type)
            cached_result = await self._get_cached_analysis(cache_key)
            if cached_result:
                return cached_result
        
        try:
            # Convert image data to base64 if needed
            if isinstance(image_data, bytes):
                image_b64 = base64.b64encode(image_data).decode('utf-8')
            else:
                image_b64 = image_data
            
            # Get analysis configuration
            config = self.analysis_prompts.get(media_type, self.analysis_prompts[MediaType.IMAGE])
            
            # Mock vision analysis (in real implementation, would use GPT-4V or similar)
            analysis_result = await self._mock_vision_analysis(image_b64, config, media_type)
            
            processing_time = (time.time() - start_time) * 1000
            
            media_analysis = MediaAnalysis(
                media_type=media_type,
                content_description=analysis_result["description"],
                extracted_text=analysis_result.get("extracted_text"),
                key_insights=analysis_result["insights"],
                confidence=analysis_result["confidence"],
                processing_time_ms=int(processing_time),
                metadata={
                    "image_size": len(image_data) if isinstance(image_data, bytes) else len(image_b64),
                    "analysis_method": "vision_llm",
                    "processed_at": time.time()
                }
            )
            
            # Cache the result
            if doc_id:
                await self._cache_analysis(cache_key, media_analysis)
            
            return media_analysis
            
        except Exception as e:
            # Return fallback analysis
            return MediaAnalysis(
                media_type=media_type,
                content_description=f"Unable to analyze {media_type.value} content",
                extracted_text=None,
                key_insights=[],
                confidence=0.1,
                processing_time_ms=int((time.time() - start_time) * 1000),
                metadata={"error": str(e)}
            )
    
    async def extract_table_data(self, table_image: Union[bytes, str]) -> TableData:
        """Extract structured data from table images."""
        try:
            # Mock table extraction (would use OCR + structure analysis)
            mock_table = TableData(
                headers=["Metric", "Q1 2023", "Q2 2023", "Q3 2023", "Growth %"],
                rows=[
                    ["Revenue", "$2.1M", "$2.5M", "$2.8M", "33%"],
                    ["Users", "15K", "22K", "28K", "87%"],
                    ["Conversion", "3.2%", "4.1%", "4.7%", "47%"]
                ],
                summary="Quarterly performance showing strong growth across all metrics",
                key_metrics={
                    "total_revenue_growth": "33%",
                    "user_growth": "87%",
                    "conversion_improvement": "47%"
                }
            )
            
            return mock_table
            
        except Exception:
            return TableData(
                headers=[],
                rows=[],
                summary="Unable to extract table data",
                key_metrics={}
            )
    
    async def analyze_chart(self, chart_image: Union[bytes, str]) -> ChartAnalysis:
        """Analyze charts and extract insights."""
        try:
            # Mock chart analysis (would use specialized chart recognition)
            mock_analysis = ChartAnalysis(
                chart_type="line",
                title="Revenue Growth Over Time",
                data_points=[
                    {"period": "Q1", "value": 2100000},
                    {"period": "Q2", "value": 2500000},
                    {"period": "Q3", "value": 2800000}
                ],
                trends=["Consistent upward trend", "Accelerating growth rate", "Strong Q3 performance"],
                key_takeaways=[
                    "33% revenue growth over 3 quarters",
                    "Growth rate increasing each quarter",
                    "Strong business momentum"
                ]
            )
            
            return mock_analysis
            
        except Exception:
            return ChartAnalysis(
                chart_type="unknown",
                title=None,
                data_points=[],
                trends=[],
                key_takeaways=[]
            )
    
    async def process_document_batch(self, 
                                   media_items: List[Dict[str, Any]], 
                                   doc_id: Optional[str] = None) -> Dict[str, MediaAnalysis]:
        """Process multiple media items in parallel for efficiency."""
        tasks = []
        item_keys = []
        
        for i, item in enumerate(media_items):
            media_type = MediaType(item.get("type", "image"))
            image_data = item["data"]
            
            task = self.process_image(image_data, media_type, doc_id)
            tasks.append(task)
            item_keys.append(f"item_{i}")
        
        # Process in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Compile results
        processed_results = {}
        for i, result in enumerate(results):
            if not isinstance(result, Exception):
                processed_results[item_keys[i]] = result
        
        return processed_results
    
    async def generate_multimodal_summary(self, 
                                        text_content: str, 
                                        media_analyses: List[MediaAnalysis]) -> Dict[str, Any]:
        """Generate comprehensive summary combining text and visual content."""
        start_time = time.time()
        
        # Prepare combined content for analysis
        visual_insights = []
        for analysis in media_analyses:
            visual_insights.extend(analysis.key_insights)
        
        # Create enriched summary
        try:
            # Mock enriched analysis combining text + visual
            enriched_summary = {
                "executive_summary": f"Document analysis reveals comprehensive insights from {len(media_analyses)} visual elements and text content.",
                "key_findings": [
                    "Text and visual content are well-aligned",
                    "Visual elements support main arguments",
                    "Data visualization enhances understanding"
                ] + visual_insights[:3],
                "visual_content_summary": {
                    "total_media_items": len(media_analyses),
                    "media_types": list(set([analysis.media_type.value for analysis in media_analyses])),
                    "average_confidence": round(sum(a.confidence for a in media_analyses) / len(media_analyses), 2) if media_analyses else 0
                },
                "actionable_insights": [
                    "Review visual data trends for strategic planning",
                    "Consider expanding successful metrics shown in charts",
                    "Leverage visual evidence in presentations"
                ],
                "content_quality": {
                    "text_length": len(text_content),
                    "visual_elements": len(media_analyses),
                    "comprehensiveness_score": min(100, (len(text_content) // 100) + (len(media_analyses) * 10)),
                    "multimodal_richness": "High" if len(media_analyses) > 3 else "Medium" if len(media_analyses) > 1 else "Low"
                }
            }
            
            processing_time = (time.time() - start_time) * 1000
            enriched_summary["processing_metrics"] = {
                "generation_time_ms": round(processing_time, 1),
                "combined_elements": len(media_analyses) + 1  # +1 for text
            }
            
            return enriched_summary
            
        except Exception as e:
            return {
                "error": "Could not generate multimodal summary",
                "text_available": bool(text_content),
                "media_count": len(media_analyses)
            }
    
    async def _mock_vision_analysis(self, 
                                  image_b64: str, 
                                  config: Dict[str, Any], 
                                  media_type: MediaType) -> Dict[str, Any]:
        """Mock vision analysis - would use GPT-4V or similar in production."""
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        # Generate mock analysis based on media type
        if media_type == MediaType.TABLE:
            return {
                "description": "Financial performance table showing quarterly metrics with revenue, user growth, and conversion rates across Q1-Q3 2023.",
                "extracted_text": "Revenue Q1: $2.1M, Q2: $2.5M, Q3: $2.8M | Users: 15K → 28K | Conversion: 3.2% → 4.7%",
                "insights": [
                    "33% revenue growth over 3 quarters",
                    "User base nearly doubled (87% growth)", 
                    "Conversion rate improved by 47%",
                    "Strong acceleration in Q3 performance"
                ],
                "confidence": 0.88
            }
        elif media_type == MediaType.CHART:
            return {
                "description": "Line chart displaying upward revenue trend from Q1 to Q3 2023, showing consistent growth with steeper curve in Q3.",
                "extracted_text": None,
                "insights": [
                    "Clear upward trend in revenue growth",
                    "Accelerating growth rate each quarter",
                    "Q3 shows steepest growth curve",
                    "Projected growth trajectory looks promising"
                ],
                "confidence": 0.91
            }
        elif media_type == MediaType.DIAGRAM:
            return {
                "description": "Process diagram showing workflow from data input through analysis to insights generation with feedback loops.",
                "extracted_text": "Input → Processing → Analysis → Insights → Feedback",
                "insights": [
                    "Well-structured process flow",
                    "Includes important feedback mechanisms",
                    "Clear separation of processing stages",
                    "Scalable architecture design"
                ],
                "confidence": 0.85
            }
        else:  # Generic image
            return {
                "description": "Business-related visual content showing data, metrics, or process information relevant to document analysis.",
                "extracted_text": "Various business metrics and data points",
                "insights": [
                    "Contains quantitative business data",
                    "Shows performance indicators",
                    "Supports document's main themes",
                    "Professional presentation quality"
                ],
                "confidence": 0.75
            }
    
    def _generate_cache_key(self, image_data: Union[bytes, str], media_type: MediaType) -> str:
        """Generate unique cache key for image analysis."""
        if isinstance(image_data, bytes):
            data_hash = hashlib.md5(image_data).hexdigest()
        else:
            data_hash = hashlib.md5(image_data.encode()).hexdigest()
        
        return f"multimodal:{media_type.value}:{data_hash[:16]}"
    
    async def _get_cached_analysis(self, cache_key: str) -> Optional[MediaAnalysis]:
        """Get cached media analysis if available."""
        try:
            cached_data = await self.redis_pool.get_with_fallback(cache_key, "cache")
            
            if cached_data:
                analysis_data = json.loads(cached_data.decode('utf-8'))
                
                return MediaAnalysis(
                    media_type=MediaType(analysis_data["media_type"]),
                    content_description=analysis_data["content_description"],
                    extracted_text=analysis_data["extracted_text"],
                    key_insights=analysis_data["key_insights"],
                    confidence=analysis_data["confidence"],
                    processing_time_ms=analysis_data["processing_time_ms"],
                    metadata=analysis_data["metadata"]
                )
        except Exception:
            pass
        
        return None
    
    async def _cache_analysis(self, cache_key: str, analysis: MediaAnalysis):
        """Cache media analysis for quick access."""
        try:
            analysis_data = {
                "media_type": analysis.media_type.value,
                "content_description": analysis.content_description,
                "extracted_text": analysis.extracted_text,
                "key_insights": analysis.key_insights,
                "confidence": analysis.confidence,
                "processing_time_ms": analysis.processing_time_ms,
                "metadata": analysis.metadata
            }
            
            await self.redis_pool.set_with_optimization(
                cache_key,
                json.dumps(analysis_data).encode('utf-8'),
                1800,  # 30 minute TTL
                "cache"
            )
        except Exception:
            pass  # Continue without caching
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get statistics about multimodal processing performance."""
        # Mock stats - would track real metrics in production
        return {
            "total_processed": 156,
            "processing_times": {
                "images": "avg 120ms",
                "tables": "avg 180ms", 
                "charts": "avg 150ms",
                "diagrams": "avg 140ms"
            },
            "accuracy_rates": {
                "table_extraction": "94%",
                "chart_analysis": "91%",
                "text_extraction": "96%",
                "insight_generation": "88%"
            },
            "cache_hit_rate": "73%",
            "supported_formats": ["PNG", "JPG", "PDF pages", "Base64 encoded"]
        }


# Global instance
_multimodal_processor = None

def get_multimodal_processor() -> MultimodalProcessor:
    """Get or create the multimodal processor singleton."""
    global _multimodal_processor
    if _multimodal_processor is None:
        _multimodal_processor = MultimodalProcessor()
    return _multimodal_processor