"""
Document Intelligence API - Auto-generated insights and analysis.
"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from app.api.deps import require_api_key
from app.api.routers.ingest import get_hybrid_retriever
from app.services.document_intelligence import get_document_intelligence_service
from app.services.performance_monitor import get_performance_monitor

router = APIRouter(prefix="/intelligence", tags=["document-intelligence"])


@router.get("/analyze/{doc_id}")
async def get_document_analysis(
    doc_id: str,
    api_key: str = Depends(require_api_key)
):
    """Get comprehensive analysis for a specific document."""
    intelligence_service = get_document_intelligence_service()
    
    # Check cache first
    cached_intelligence = await intelligence_service.get_cached_intelligence(doc_id)
    if cached_intelligence:
        return {
            "doc_id": cached_intelligence.doc_id,
            "filename": cached_intelligence.filename,
            "executive_summary": cached_intelligence.executive_summary,
            "key_insights": [
                {
                    "type": insight.type,
                    "title": insight.title,
                    "content": insight.content,
                    "confidence": insight.confidence,
                    "priority": insight.priority
                }
                for insight in cached_intelligence.key_insights
            ],
            "document_score": cached_intelligence.document_score,
            "topic_tags": cached_intelligence.topic_tags,
            "reading_time_minutes": cached_intelligence.reading_time_minutes,
            "complexity_level": cached_intelligence.complexity_level,
            "document_type": cached_intelligence.document_type,
            "analysis_age_hours": round((time.time() - cached_intelligence.generated_at) / 3600, 1),
            "status": "cached"
        }
    
    return {"error": f"No analysis found for document {doc_id}"}


@router.get("/dashboard")
async def get_intelligence_dashboard(
    api_key: str = Depends(require_api_key)
):
    """Get intelligence dashboard with overview of all documents."""
    intelligence_service = get_document_intelligence_service()
    retriever = get_hybrid_retriever()
    
    try:
        # Get all document intelligence
        all_intelligence = await intelligence_service.get_all_document_intelligence()
        
        # Calculate dashboard metrics
        total_docs = len(all_intelligence)
        avg_complexity = "intermediate"  # Would calculate from actual data
        most_common_type = "research_paper"  # Would calculate from actual data
        
        # Top insights across all documents
        top_insights = []
        for intel in all_intelligence[:5]:  # Top 5 documents
            if intel.get("key_insights"):
                top_insights.extend(intel["key_insights"][:2])  # Top 2 insights per doc
        
        return {
            "dashboard_metrics": {
                "total_documents": total_docs,
                "average_complexity": avg_complexity,
                "most_common_document_type": most_common_type,
                "total_insights_generated": sum(len(intel.get("key_insights", [])) for intel in all_intelligence)
            },
            "recent_analyses": all_intelligence[:10],  # Most recent 10
            "top_insights": top_insights[:10],  # Top 10 insights
            "document_types_breakdown": {
                "research_paper": 1,
                "business_report": 0,
                "other": 0
            }
        }
        
    except Exception as e:
        return {
            "dashboard_metrics": {
                "total_documents": 0,
                "average_complexity": "unknown",
                "most_common_document_type": "unknown",
                "total_insights_generated": 0
            },
            "recent_analyses": [],
            "top_insights": [],
            "document_types_breakdown": {},
            "error": "Dashboard temporarily unavailable"
        }


@router.post("/generate/{doc_id}")
async def generate_document_intelligence(
    doc_id: str,
    force_regenerate: bool = False,
    api_key: str = Depends(require_api_key)
):
    """Generate or regenerate intelligence for a specific document."""
    intelligence_service = get_document_intelligence_service()
    retriever = get_hybrid_retriever()
    monitor = get_performance_monitor()
    
    import time
    start_time = time.time()
    request_id = await monitor.start_request()
    
    try:
        # Check if we already have analysis and don't need to regenerate
        if not force_regenerate:
            cached_intelligence = await intelligence_service.get_cached_intelligence(doc_id)
            if cached_intelligence:
                await monitor.end_request(request_id, True, (time.time() - start_time) * 1000)
                return {
                    "status": "already_exists",
                    "doc_id": doc_id,
                    "message": "Intelligence already generated. Use force_regenerate=true to regenerate.",
                    "analysis_age_hours": round((time.time() - cached_intelligence.generated_at) / 3600, 1)
                }
        
        # We need to get document chunks from the retriever
        # For now, simulate this - in real implementation, you'd retrieve actual chunks
        from app.rag.schemas import DocumentChunk
        
        # Simulate getting chunks (in real implementation, get from retriever/database)
        mock_chunks = [
            DocumentChunk(
                doc_id=doc_id,
                chunk_id=f"{doc_id}_chunk_1",
                chunk_index=0,
                content="This is a sample document chunk for intelligence analysis. It contains detailed information about artificial intelligence research, machine learning algorithms, and their practical applications in various industries. Key findings include 85% accuracy in pattern recognition, 60% processing time improvement, and significant advances in healthcare, finance, and technology sectors.",
                content_hash="mock_hash_12345",
                source=f"{doc_id}.md",
                title="Sample Document",
                metadata={}
            )
        ]
        
        # Generate intelligence
        intelligence = await intelligence_service.analyze_document(mock_chunks)
        
        generation_time = (time.time() - start_time) * 1000
        await monitor.end_request(request_id, True, generation_time)
        
        return {
            "status": "generated",
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
            "performance": {
                "generation_time_ms": round(generation_time, 1),
                "insights_count": len(intelligence.key_insights)
            }
        }
        
    except Exception as e:
        await monitor.end_request(request_id, False, (time.time() - start_time) * 1000)
        raise HTTPException(status_code=500, detail=f"Failed to generate intelligence: {str(e)}")


@router.get("/insights/trending")
async def get_trending_insights(
    limit: int = 10,
    api_key: str = Depends(require_api_key)
):
    """Get trending insights across all documents."""
    
    # Mock trending insights - in real implementation, analyze across all docs
    trending_insights = [
        {
            "insight": "AI systems show 85% accuracy in pattern recognition",
            "relevance_score": 0.95,
            "mentioned_in_docs": ["ai_research.md"],
            "insight_type": "key_finding",
            "trend_direction": "up"
        },
        {
            "insight": "Machine learning reduces processing time by 60%",
            "relevance_score": 0.87,
            "mentioned_in_docs": ["ai_research.md"],
            "insight_type": "opportunity",
            "trend_direction": "up"
        },
        {
            "insight": "Deep learning achieves 94% accuracy in image classification",
            "relevance_score": 0.82,
            "mentioned_in_docs": ["ai_research.md"],
            "insight_type": "key_finding",
            "trend_direction": "stable"
        }
    ]
    
    return {
        "trending_insights": trending_insights[:limit],
        "generated_at": time.time(),
        "total_insights_analyzed": len(trending_insights)
    }


@router.get("/summary/quick/{doc_id}")
async def get_quick_summary(
    doc_id: str,
    api_key: str = Depends(require_api_key)
):
    """Get a quick 30-second summary of the document."""
    intelligence_service = get_document_intelligence_service()
    
    cached_intelligence = await intelligence_service.get_cached_intelligence(doc_id)
    
    if cached_intelligence:
        # Create a quick summary format
        quick_summary = {
            "document": cached_intelligence.filename,
            "type": cached_intelligence.document_type,
            "complexity": cached_intelligence.complexity_level,
            "reading_time": f"{cached_intelligence.reading_time_minutes} minutes",
            "executive_summary": cached_intelligence.executive_summary,
            "top_3_insights": [
                insight.content for insight in cached_intelligence.key_insights[:3]
            ],
            "key_topics": cached_intelligence.topic_tags[:3],
            "document_quality": {
                "overall_score": round(
                    sum(cached_intelligence.document_score.values()) / len(cached_intelligence.document_score) * 100, 1
                ),
                "completeness": f"{cached_intelligence.document_score['completeness']*100:.1f}%",
                "clarity": f"{cached_intelligence.document_score['clarity']*100:.1f}%",
                "actionability": f"{cached_intelligence.document_score['actionability']*100:.1f}%"
            }
        }
        
        return quick_summary
    
    return {"error": f"No analysis available for document {doc_id}"}


import time