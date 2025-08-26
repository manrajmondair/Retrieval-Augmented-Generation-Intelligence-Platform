"""
Smart Summaries API - Generate intelligent, context-aware summaries.
"""
import time
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from app.api.deps import require_api_key
from app.services.smart_summaries import get_smart_summary_service, SummaryType

router = APIRouter(prefix="/summaries", tags=["smart-summaries"])


@router.post("/generate/{doc_id}")
async def generate_smart_summary(
    doc_id: str,
    summary_type: str = "executive",
    api_key: str = Depends(require_api_key)
):
    """Generate a smart summary for a specific document."""
    summary_service = get_smart_summary_service()
    
    try:
        # Validate summary type
        try:
            summary_type_enum = SummaryType(summary_type)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid summary type. Options: {[t.value for t in SummaryType]}"
            )
        
        # Mock document content - in real implementation, get from database/retriever
        mock_content = """
        Artificial Intelligence Research Paper Summary
        
        This research paper explores the applications and implications of artificial intelligence 
        in modern computing systems. The study examines machine learning algorithms, neural networks, 
        and their practical implementations across various industries.
        
        Key Findings:
        - AI systems demonstrate 85% accuracy in pattern recognition tasks
        - Machine learning models reduce processing time by 60% compared to traditional methods
        - Deep learning architectures show superior performance in image classification with 94% accuracy
        - Natural language processing models achieve 78% accuracy in sentiment analysis
        
        The methodology employed a mixed-methods approach including quantitative analysis from 1,000 
        test cases, qualitative assessment with expert interviews, experimental design with A/B testing, 
        and data collection from multiple sources spanning 2019-2023.
        
        Applications demonstrate significant improvements across multiple domains:
        
        Healthcare applications show medical diagnosis accuracy improved by 45%, drug discovery 
        timelines reduced by 30%, and enhanced patient monitoring systems with predictive analytics.
        
        Finance sector implementations include fraud detection improved by 67%, algorithmic trading 
        showing 23% better returns, and risk assessment models with 89% precision.
        
        Technology developments feature computer vision achieving 96% object recognition, speech 
        recognition with 92% accuracy across languages, and autonomous systems demonstrating 
        safe navigation capabilities.
        
        Conclusions indicate that artificial intelligence represents a paradigm shift in computational 
        approaches. The research demonstrates significant improvements across multiple domains, with 
        particularly strong results in pattern recognition and predictive modeling. Future work should 
        focus on ethical AI development and bias mitigation strategies.
        """
        
        start_time = time.time()
        
        # Generate the summary
        summary = await summary_service.generate_summary(mock_content, summary_type_enum, doc_id)
        
        generation_time = (time.time() - start_time) * 1000
        
        return {
            "doc_id": doc_id,
            "summary_type": summary.summary_type.value,
            "content": summary.content,
            "metadata": {
                "confidence": summary.confidence,
                "word_count": summary.word_count,
                "reading_time_seconds": summary.reading_time_seconds,
                "key_terms": summary.key_terms,
                "source_doc_count": summary.source_doc_count
            },
            "performance": {
                "generation_time_ms": round(generation_time, 1),
                "cached": False  # Would check if from cache in real implementation
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")


@router.post("/suite/{doc_id}")
async def generate_summary_suite(
    doc_id: str,
    api_key: str = Depends(require_api_key)
):
    """Generate a complete suite of summaries for comprehensive understanding."""
    summary_service = get_smart_summary_service()
    
    try:
        # Mock document content
        mock_content = """
        Artificial Intelligence Research Paper Summary
        
        This research paper explores the applications and implications of artificial intelligence 
        in modern computing systems. The study examines machine learning algorithms, neural networks, 
        and their practical implementations across various industries.
        
        Key Findings:
        - AI systems demonstrate 85% accuracy in pattern recognition tasks
        - Machine learning models reduce processing time by 60% compared to traditional methods
        - Deep learning architectures show superior performance in image classification with 94% accuracy
        - Natural language processing models achieve 78% accuracy in sentiment analysis
        
        The methodology employed a mixed-methods approach including quantitative analysis, 
        qualitative assessment, experimental design, and comprehensive data collection.
        
        Applications show significant improvements in healthcare (45% better diagnosis accuracy), 
        finance (67% improved fraud detection), and technology (96% object recognition accuracy).
        
        The research concludes that AI represents a paradigm shift with particularly strong results 
        in pattern recognition and predictive modeling, while recommending focus on ethical 
        development and bias mitigation.
        """
        
        start_time = time.time()
        
        # Generate suite of summaries
        summaries = await summary_service.generate_summary_suite(mock_content, doc_id)
        
        generation_time = (time.time() - start_time) * 1000
        
        # Format response
        formatted_summaries = {}
        total_reading_time = 0
        
        for summary_type, summary in summaries.items():
            formatted_summaries[summary_type] = {
                "content": summary.content,
                "confidence": summary.confidence,
                "word_count": summary.word_count,
                "reading_time_seconds": summary.reading_time_seconds,
                "key_terms": summary.key_terms
            }
            total_reading_time += summary.reading_time_seconds
        
        return {
            "doc_id": doc_id,
            "summaries": formatted_summaries,
            "suite_metadata": {
                "total_summaries": len(summaries),
                "total_reading_time_seconds": total_reading_time,
                "average_confidence": round(
                    sum(s.confidence for s in summaries.values()) / len(summaries), 2
                ) if summaries else 0,
                "generation_time_ms": round(generation_time, 1)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate summary suite: {str(e)}")


@router.get("/types")
async def get_available_summary_types(
    api_key: str = Depends(require_api_key)
):
    """Get all available summary types with descriptions."""
    summary_descriptions = {
        "executive": {
            "name": "Executive Summary",
            "description": "2-sentence high-level overview for leadership",
            "ideal_for": "Quick briefings, presentations, executive reports",
            "reading_time": "5-10 seconds"
        },
        "bullet_points": {
            "name": "Key Points",
            "description": "5 most important points in bullet format",
            "ideal_for": "Meeting notes, quick reference, action planning",
            "reading_time": "15-30 seconds"
        },
        "one_liner": {
            "name": "One-Liner",
            "description": "Single powerful sentence capturing the essence",
            "ideal_for": "Headlines, social media, quick understanding",
            "reading_time": "5 seconds"
        },
        "detailed": {
            "name": "Detailed Summary",
            "description": "Comprehensive overview with context and implications",
            "ideal_for": "Research reviews, thorough analysis, documentation",
            "reading_time": "1-2 minutes"
        },
        "action_items": {
            "name": "Action Items",
            "description": "Specific actionable items and recommendations",
            "ideal_for": "Project planning, task management, follow-ups",
            "reading_time": "30-45 seconds"
        },
        "key_insights": {
            "name": "Key Insights",
            "description": "3 most significant insights with explanations",
            "ideal_for": "Strategic planning, decision making, analysis",
            "reading_time": "45-60 seconds"
        },
        "meeting_notes": {
            "name": "Meeting Notes",
            "description": "Structured format with decisions and action items",
            "ideal_for": "Meeting summaries, team communications, records",
            "reading_time": "1 minute"
        },
        "research_brief": {
            "name": "Research Brief",
            "description": "Academic-style brief with methodology and findings",
            "ideal_for": "Research papers, academic work, technical analysis",
            "reading_time": "1-2 minutes"
        }
    }
    
    return {
        "available_types": summary_descriptions,
        "total_types": len(summary_descriptions),
        "recommended_flow": [
            "one_liner",      # Quick understanding
            "executive",      # High-level overview
            "bullet_points",  # Key details
            "action_items"    # Next steps
        ]
    }


@router.get("/quick/{doc_id}")
async def get_quick_summary(
    doc_id: str,
    api_key: str = Depends(require_api_key)
):
    """Get the quickest possible summary (one-liner + executive)."""
    summary_service = get_smart_summary_service()
    
    try:
        # Mock content for demo
        mock_content = "AI research shows 85% accuracy in pattern recognition, 60% faster processing, and significant improvements across healthcare, finance, and technology sectors."
        
        start_time = time.time()
        
        # Generate quick summaries in parallel
        quick_summaries = await summary_service.generate_multi_summary(
            mock_content,
            [SummaryType.ONE_LINER, SummaryType.EXECUTIVE],
            doc_id
        )
        
        generation_time = (time.time() - start_time) * 1000
        
        response = {
            "doc_id": doc_id,
            "quick_insights": {},
            "performance": {
                "generation_time_ms": round(generation_time, 1),
                "total_reading_time_seconds": 0
            }
        }
        
        for summary_type, summary in quick_summaries.items():
            response["quick_insights"][summary_type.value] = {
                "content": summary.content,
                "confidence": summary.confidence,
                "reading_time_seconds": summary.reading_time_seconds
            }
            response["performance"]["total_reading_time_seconds"] += summary.reading_time_seconds
        
        return response
        
    except Exception as e:
        return {
            "doc_id": doc_id,
            "error": "Could not generate quick summary",
            "fallback": "Document analysis available through other endpoints"
        }


@router.get("/analytics/{doc_id}")
async def get_summary_analytics(
    doc_id: str,
    api_key: str = Depends(require_api_key)
):
    """Get comprehensive analytics for all summaries of a document."""
    summary_service = get_smart_summary_service()
    
    analytics = await summary_service.get_summary_analytics(doc_id)
    
    # Add usage recommendations
    analytics["recommendations"] = {
        "best_for_executives": "executive",
        "best_for_teams": "bullet_points", 
        "best_for_action": "action_items",
        "best_for_analysis": "key_insights"
    }
    
    return analytics


@router.post("/compare")
async def compare_summaries(
    doc_ids: List[str],
    summary_type: str = "executive",
    api_key: str = Depends(require_api_key)
):
    """Compare summaries across multiple documents."""
    if len(doc_ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 documents for comparison")
    
    summary_service = get_smart_summary_service()
    
    try:
        summary_type_enum = SummaryType(summary_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid summary type")
    
    # Mock comparison for demo
    comparisons = []
    
    for i, doc_id in enumerate(doc_ids):
        mock_content = f"Document {i+1} content about AI research findings..."
        summary = await summary_service.generate_summary(mock_content, summary_type_enum, doc_id)
        
        comparisons.append({
            "doc_id": doc_id,
            "summary": summary.content,
            "confidence": summary.confidence,
            "word_count": summary.word_count,
            "key_terms": summary.key_terms
        })
    
    # Analyze comparisons
    all_terms = []
    for comp in comparisons:
        all_terms.extend(comp["key_terms"])
    
    from collections import Counter
    common_themes = [term for term, count in Counter(all_terms).most_common(5)]
    
    return {
        "comparison_type": summary_type,
        "documents": comparisons,
        "analysis": {
            "total_documents": len(comparisons),
            "common_themes": common_themes,
            "avg_confidence": round(sum(c["confidence"] for c in comparisons) / len(comparisons), 2),
            "total_words": sum(c["word_count"] for c in comparisons)
        }
    }