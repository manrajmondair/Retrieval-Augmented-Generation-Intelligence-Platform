"""
Analytics API - Advanced usage insights, user behavior tracking, and system analytics.
"""
import time
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.api.deps import require_api_key
from app.services.analytics import get_analytics_service


class TrackActionRequest(BaseModel):
    """Request to track a user action."""
    action: str
    metadata: Dict[str, Any] = {}


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
async def get_analytics_dashboard(
    days: int = Query(30, description="Number of days to analyze"),
    api_key: str = Depends(require_api_key)
):
    """Get comprehensive analytics dashboard."""
    analytics_service = get_analytics_service()
    
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 365")
    
    try:
        dashboard = await analytics_service.get_dashboard_analytics(days)
        return dashboard
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")


@router.post("/track")
async def track_user_action(
    request: TrackActionRequest,
    user_id: Optional[str] = Query(None),
    session_id: str = Query("demo_session"),
    api_key: str = Depends(require_api_key)
):
    """Track a user action for analytics."""
    analytics_service = get_analytics_service()
    
    try:
        await analytics_service.track_user_action(
            user_id=user_id,
            session_id=session_id,
            action=request.action,
            metadata=request.metadata
        )
        
        return {
            "status": "tracked",
            "action": request.action,
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track action: {str(e)}")


@router.get("/users/{user_id}/insights")
async def get_user_insights(
    user_id: str,
    days: int = Query(30, description="Number of days to analyze"),
    api_key: str = Depends(require_api_key)
):
    """Get detailed insights for a specific user."""
    analytics_service = get_analytics_service()
    
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 365")
    
    try:
        insights = await analytics_service.get_user_insights(user_id, days)
        return insights
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user insights: {str(e)}")


@router.get("/features/{feature}/performance")
async def get_feature_performance(
    feature: str,
    days: int = Query(7, description="Number of days to analyze"),
    api_key: str = Depends(require_api_key)
):
    """Get detailed performance analytics for a specific feature."""
    analytics_service = get_analytics_service()
    
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 90")
    
    try:
        performance = await analytics_service.get_feature_performance(feature, days)
        return performance
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get feature performance: {str(e)}")


@router.get("/health")
async def get_system_health_score(
    api_key: str = Depends(require_api_key)
):
    """Get overall system health score based on analytics."""
    analytics_service = get_analytics_service()
    
    try:
        health = await analytics_service.get_system_health_score()
        return health
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get health score: {str(e)}")


@router.get("/features")
async def get_feature_overview(
    api_key: str = Depends(require_api_key)
):
    """Get overview of all tracked features."""
    return {
        "tracked_features": [
            {
                "name": "document_intelligence",
                "display_name": "Document Intelligence",
                "description": "Automatic document analysis and insight generation",
                "category": "AI Analysis"
            },
            {
                "name": "knowledge_graph",
                "display_name": "Knowledge Graph",
                "description": "Visual representation of document relationships",
                "category": "Visualization"
            },
            {
                "name": "smart_summaries", 
                "display_name": "Smart Summaries",
                "description": "Intelligent summarization in multiple formats",
                "category": "AI Analysis"
            },
            {
                "name": "multimodal_analysis",
                "display_name": "Multimodal Analysis", 
                "description": "Analysis of images, charts, and visual content",
                "category": "AI Analysis"
            },
            {
                "name": "collaboration",
                "display_name": "Collaboration",
                "description": "Sharing, commenting, and team workspaces",
                "category": "Collaboration"
            },
            {
                "name": "search_query",
                "display_name": "Search & Query",
                "description": "Document search and Q&A functionality",
                "category": "Core Features"
            }
        ],
        "feature_categories": [
            "AI Analysis",
            "Visualization", 
            "Collaboration",
            "Core Features"
        ]
    }


@router.get("/trends")
async def get_usage_trends(
    period: str = Query("week", description="Trend period: day, week, month"),
    feature: Optional[str] = Query(None, description="Specific feature to analyze"),
    api_key: str = Depends(require_api_key)
):
    """Get usage trends over time."""
    if period not in ["day", "week", "month"]:
        raise HTTPException(status_code=400, detail="Period must be 'day', 'week', or 'month'")
    
    # Mock trend data - would come from actual analytics in real implementation
    trends = {
        "period": period,
        "feature": feature or "all_features",
        "data_points": []
    }
    
    if period == "day":
        # Hourly data for past 24 hours
        for hour in range(24):
            trends["data_points"].append({
                "timestamp": time.time() - ((23 - hour) * 3600),
                "usage_count": 50 + (hour * 3) + (hour % 4) * 10,
                "unique_users": 8 + (hour // 3),
                "hour": hour
            })
    elif period == "week":
        # Daily data for past 7 days
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, day in enumerate(days):
            trends["data_points"].append({
                "timestamp": time.time() - ((6 - i) * 86400),
                "usage_count": 200 + (i * 50) + (i % 3) * 30,
                "unique_users": 25 + (i * 5),
                "day": day
            })
    else:  # month
        # Weekly data for past 4 weeks
        for week in range(4):
            trends["data_points"].append({
                "timestamp": time.time() - ((3 - week) * 86400 * 7),
                "usage_count": 1200 + (week * 200),
                "unique_users": 150 + (week * 25),
                "week": f"Week {week + 1}"
            })
    
    trends["summary"] = {
        "total_usage": sum(dp["usage_count"] for dp in trends["data_points"]),
        "avg_daily_users": sum(dp["unique_users"] for dp in trends["data_points"]) / len(trends["data_points"]),
        "peak_usage": max(dp["usage_count"] for dp in trends["data_points"]),
        "trend_direction": "increasing"  # Would calculate from actual data
    }
    
    return trends


@router.get("/exports/csv")
async def export_analytics_csv(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    feature: Optional[str] = Query(None, description="Specific feature to export"),
    api_key: str = Depends(require_api_key)
):
    """Export analytics data as CSV."""
    try:
        # Validate dates
        from datetime import datetime
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        if start >= end:
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        
        # Mock CSV data - would generate from actual analytics
        csv_content = "Date,Feature,Usage Count,Unique Users,Success Rate\n"
        csv_content += f"{start_date},document_intelligence,45,12,94.2%\n"
        csv_content += f"{start_date},smart_summaries,67,18,96.8%\n"
        csv_content += f"{start_date},knowledge_graph,23,8,89.1%\n"
        csv_content += f"{end_date},document_intelligence,52,15,95.1%\n"
        csv_content += f"{end_date},smart_summaries,71,21,97.2%\n"
        csv_content += f"{end_date},knowledge_graph,28,11,91.3%\n"
        
        return {
            "export_info": {
                "format": "CSV",
                "date_range": f"{start_date} to {end_date}",
                "feature_filter": feature or "all_features",
                "generated_at": time.time()
            },
            "download_url": f"/analytics/downloads/analytics_{start_date}_{end_date}.csv",
            "preview": csv_content.split('\n')[:5],  # First 5 lines as preview
            "total_rows": len(csv_content.split('\n')) - 1  # Exclude header
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/alerts")
async def get_analytics_alerts(
    severity: str = Query("all", description="Alert severity: low, medium, high, all"),
    api_key: str = Depends(require_api_key)
):
    """Get analytics-based alerts and notifications."""
    if severity not in ["low", "medium", "high", "all"]:
        raise HTTPException(status_code=400, detail="Severity must be 'low', 'medium', 'high', or 'all'")
    
    # Mock alerts - would come from real analytics monitoring
    all_alerts = [
        {
            "id": "alert_001",
            "type": "performance",
            "severity": "medium",
            "title": "Response Time Increase",
            "message": "Smart summaries response time increased by 15% over last hour",
            "timestamp": time.time() - 3600,
            "feature": "smart_summaries",
            "metric": "response_time",
            "threshold": 3000,
            "current_value": 3450
        },
        {
            "id": "alert_002", 
            "type": "usage",
            "severity": "low",
            "title": "Feature Adoption Drop",
            "message": "Knowledge graph usage down 5% this week",
            "timestamp": time.time() - 7200,
            "feature": "knowledge_graph",
            "metric": "usage_count",
            "threshold": 100,
            "current_value": 95
        },
        {
            "id": "alert_003",
            "type": "error",
            "severity": "high", 
            "title": "Error Rate Spike",
            "message": "Multimodal analysis error rate exceeded 5%",
            "timestamp": time.time() - 1800,
            "feature": "multimodal_analysis",
            "metric": "error_rate",
            "threshold": 5.0,
            "current_value": 7.2
        }
    ]
    
    # Filter by severity
    if severity != "all":
        alerts = [alert for alert in all_alerts if alert["severity"] == severity]
    else:
        alerts = all_alerts
    
    return {
        "alerts": alerts,
        "summary": {
            "total_alerts": len(alerts),
            "high_priority": len([a for a in alerts if a["severity"] == "high"]),
            "medium_priority": len([a for a in alerts if a["severity"] == "medium"]),
            "low_priority": len([a for a in alerts if a["severity"] == "low"])
        },
        "alert_settings": {
            "monitoring_enabled": True,
            "notification_channels": ["email", "slack", "webhook"],
            "alert_frequency": "real_time"
        }
    }


@router.post("/demo")
async def demo_analytics_tracking(
    api_key: str = Depends(require_api_key)
):
    """Demonstrate analytics tracking with sample actions."""
    analytics_service = get_analytics_service()
    
    try:
        # Simulate various user actions
        demo_actions = [
            {"action": "intelligence/generate", "metadata": {"doc_id": "demo_doc_1", "success": True, "response_time": 1200}},
            {"action": "summaries/generate", "metadata": {"summary_type": "executive", "success": True, "response_time": 3200}},
            {"action": "knowledge/graph", "metadata": {"nodes": 23, "edges": 87, "success": True, "response_time": 850}},
            {"action": "multimodal/analyze", "metadata": {"media_type": "chart", "success": True, "response_time": 2100}},
            {"action": "collaborate/share", "metadata": {"content_type": "analysis", "permission": "comment", "success": True}}
        ]
        
        # Track each action
        for i, action in enumerate(demo_actions):
            await analytics_service.track_user_action(
                user_id=f"demo_user_{i % 3}",  # 3 different demo users
                session_id=f"demo_session_{i % 2}",  # 2 different sessions
                action=action["action"],
                metadata=action["metadata"]
            )
        
        # Get health score after tracking
        health_score = await analytics_service.get_system_health_score()
        
        return {
            "demo_results": {
                "actions_tracked": len(demo_actions),
                "features_demonstrated": [
                    "User action tracking",
                    "Feature usage analytics", 
                    "Performance monitoring",
                    "Health score calculation"
                ],
                "sample_actions": [
                    {"feature": action["action"], "metadata_keys": list(action["metadata"].keys())}
                    for action in demo_actions
                ]
            },
            "system_health": {
                "overall_score": health_score["overall_health_score"],
                "grade": health_score["health_grade"]
            },
            "next_steps": [
                "View dashboard at /analytics/dashboard",
                "Check feature performance at /analytics/features/{feature}/performance",
                "Monitor trends at /analytics/trends",
                "Set up alerts for proactive monitoring"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Demo failed: {str(e)}")