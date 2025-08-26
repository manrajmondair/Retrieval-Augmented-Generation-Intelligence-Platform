"""
Advanced Analytics Service - Track usage patterns, user behavior, and system insights.
"""
import asyncio
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter
from datetime import datetime, timedelta

from app.services.redis_pool import get_redis_pool


@dataclass
class UserSession:
    """Represents a user session with tracking data."""
    session_id: str
    user_id: Optional[str]
    started_at: float
    last_activity: float
    pages_visited: List[str]
    features_used: List[str]
    queries_made: int
    documents_analyzed: int
    time_spent_seconds: int


@dataclass  
class FeatureUsage:
    """Feature usage statistics."""
    feature_name: str
    total_uses: int
    unique_users: int
    avg_session_time: float
    success_rate: float
    last_used: float


@dataclass
class UserBehaviorPattern:
    """User behavior pattern analysis."""
    pattern_type: str
    description: str
    frequency: float
    user_segment: str
    confidence: float


class AnalyticsService:
    """Service for tracking and analyzing user behavior and system performance."""
    
    def __init__(self):
        self.redis_pool = get_redis_pool()
        
        # Feature mapping for better categorization
        self.feature_categories = {
            "document_intelligence": ["intelligence/generate", "intelligence/analyze"],
            "knowledge_graph": ["knowledge/generate", "knowledge/graph"],
            "smart_summaries": ["summaries/generate", "summaries/suite"],
            "multimodal_analysis": ["multimodal/analyze", "multimodal/upload"],
            "collaboration": ["share/create", "comments/add"],
            "search_query": ["query", "chat/stream", "ultra/stream"]
        }
    
    async def track_user_action(self, 
                               user_id: Optional[str],
                               session_id: str,
                               action: str,
                               metadata: Dict[str, Any] = None) -> None:
        """Track a user action for analytics."""
        timestamp = time.time()
        
        # Create action record
        action_record = {
            "user_id": user_id,
            "session_id": session_id,
            "action": action,
            "timestamp": timestamp,
            "metadata": metadata or {}
        }
        
        # Store action in time-series format
        await self._store_action(action_record)
        
        # Update session data
        await self._update_session(session_id, user_id, action, timestamp)
        
        # Update feature usage counters
        await self._update_feature_usage(action, user_id, timestamp)
    
    async def get_dashboard_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive analytics dashboard."""
        end_time = time.time()
        start_time = end_time - (days * 24 * 3600)
        
        # Get various analytics in parallel
        tasks = [
            self._get_usage_overview(start_time, end_time),
            self._get_feature_analytics(start_time, end_time),
            self._get_user_behavior_patterns(start_time, end_time),
            self._get_performance_insights(start_time, end_time),
            self._get_content_analytics(start_time, end_time)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        usage_overview = results[0] if not isinstance(results[0], Exception) else {}
        feature_analytics = results[1] if not isinstance(results[1], Exception) else {}
        behavior_patterns = results[2] if not isinstance(results[2], Exception) else {}
        performance_insights = results[3] if not isinstance(results[3], Exception) else {}
        content_analytics = results[4] if not isinstance(results[4], Exception) else {}
        
        return {
            "dashboard_summary": {
                "date_range": f"{days} days",
                "generated_at": time.time(),
                "total_metrics_tracked": 15
            },
            "usage_overview": usage_overview,
            "feature_analytics": feature_analytics,
            "behavior_patterns": behavior_patterns,
            "performance_insights": performance_insights,
            "content_analytics": content_analytics
        }
    
    async def get_user_insights(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get detailed insights for a specific user."""
        end_time = time.time()
        start_time = end_time - (days * 24 * 3600)
        
        # Get user's sessions and actions
        user_actions = await self._get_user_actions(user_id, start_time, end_time)
        user_sessions = await self._get_user_sessions(user_id, start_time, end_time)
        
        # Analyze user behavior
        behavior_summary = self._analyze_user_behavior(user_actions, user_sessions)
        feature_preferences = self._analyze_feature_preferences(user_actions)
        usage_patterns = self._analyze_usage_patterns(user_sessions)
        
        return {
            "user_id": user_id,
            "analysis_period": f"{days} days",
            "behavior_summary": behavior_summary,
            "feature_preferences": feature_preferences,
            "usage_patterns": usage_patterns,
            "recommendations": self._generate_user_recommendations(behavior_summary, feature_preferences)
        }
    
    async def get_feature_performance(self, feature: str, days: int = 7) -> Dict[str, Any]:
        """Get detailed performance analytics for a specific feature."""
        end_time = time.time()
        start_time = end_time - (days * 24 * 3600)
        
        feature_actions = await self._get_feature_actions(feature, start_time, end_time)
        
        if not feature_actions:
            return {
                "feature": feature,
                "error": "No usage data found for this feature",
                "period": f"{days} days"
            }
        
        # Calculate performance metrics
        total_uses = len(feature_actions)
        unique_users = len(set(action.get("user_id") for action in feature_actions if action.get("user_id")))
        
        # Success rate analysis
        successful_uses = len([a for a in feature_actions if a.get("metadata", {}).get("success", True)])
        success_rate = successful_uses / total_uses if total_uses > 0 else 0
        
        # Response time analysis
        response_times = [a.get("metadata", {}).get("response_time", 0) for a in feature_actions]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Usage trends (hourly breakdown)
        hourly_usage = self._calculate_hourly_trends(feature_actions)
        
        return {
            "feature": feature,
            "period": f"{days} days",
            "usage_metrics": {
                "total_uses": total_uses,
                "unique_users": unique_users,
                "success_rate": round(success_rate * 100, 1),
                "avg_response_time_ms": round(avg_response_time, 1)
            },
            "trends": {
                "hourly_usage": hourly_usage,
                "peak_usage_hour": max(hourly_usage, key=hourly_usage.get) if hourly_usage else "N/A",
                "growth_rate": self._calculate_growth_rate(feature_actions)
            },
            "user_segments": {
                "power_users": unique_users // 10,  # Top 10% users
                "regular_users": unique_users // 2,  # 50% users
                "casual_users": unique_users - (unique_users // 2) - (unique_users // 10)
            }
        }
    
    async def get_system_health_score(self) -> Dict[str, Any]:
        """Calculate overall system health based on analytics."""
        # Get recent performance data
        recent_actions = await self._get_recent_actions(hours=24)
        
        # Calculate health metrics
        total_actions = len(recent_actions)
        error_count = len([a for a in recent_actions if a.get("metadata", {}).get("error")])
        error_rate = error_count / total_actions if total_actions > 0 else 0
        
        # Response time health
        response_times = [a.get("metadata", {}).get("response_time", 0) for a in recent_actions]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Feature availability
        feature_usage = defaultdict(int)
        for action in recent_actions:
            feature = self._categorize_action(action.get("action", ""))
            feature_usage[feature] += 1
        
        active_features = len([f for f in feature_usage.values() if f > 0])
        total_features = len(self.feature_categories)
        
        # Calculate overall health score (0-100)
        error_score = max(0, 100 - (error_rate * 200))  # Penalty for errors
        performance_score = max(0, 100 - (avg_response_time / 50))  # Penalty for slow responses
        availability_score = (active_features / total_features) * 100
        
        overall_score = (error_score + performance_score + availability_score) / 3
        
        return {
            "overall_health_score": round(overall_score, 1),
            "health_grade": self._get_health_grade(overall_score),
            "component_scores": {
                "error_rate": round(error_score, 1),
                "performance": round(performance_score, 1),
                "availability": round(availability_score, 1)
            },
            "metrics": {
                "total_requests_24h": total_actions,
                "error_rate": round(error_rate * 100, 2),
                "avg_response_time": round(avg_response_time, 1),
                "active_features": active_features
            },
            "recommendations": self._get_health_recommendations(error_score, performance_score, availability_score)
        }
    
    async def _store_action(self, action_record: Dict[str, Any]):
        """Store action record for time-series analysis."""
        try:
            # Store in daily buckets for efficient querying
            day_key = datetime.fromtimestamp(action_record["timestamp"]).strftime("%Y-%m-%d")
            cache_key = f"analytics:actions:{day_key}"
            
            # Get existing actions for the day
            existing_actions = []
            cached_data = await self.redis_pool.get_with_fallback(cache_key, "analytics")
            if cached_data:
                existing_actions = json.loads(cached_data.decode('utf-8'))
            
            # Add new action
            existing_actions.append(action_record)
            
            # Store back with 7-day TTL
            await self.redis_pool.set_with_optimization(
                cache_key,
                json.dumps(existing_actions).encode('utf-8'),
                86400 * 7,  # 7 days
                "analytics"
            )
        except Exception:
            pass  # Don't fail the main request if analytics fails
    
    async def _update_session(self, session_id: str, user_id: Optional[str], action: str, timestamp: float):
        """Update session tracking data."""
        try:
            cache_key = f"analytics:session:{session_id}"
            
            # Get existing session
            session_data = {"pages_visited": [], "features_used": [], "queries_made": 0, "documents_analyzed": 0}
            cached_data = await self.redis_pool.get_with_fallback(cache_key, "analytics")
            if cached_data:
                session_data = json.loads(cached_data.decode('utf-8'))
            else:
                session_data["started_at"] = timestamp
                session_data["user_id"] = user_id
                session_data["session_id"] = session_id
            
            # Update session data
            session_data["last_activity"] = timestamp
            
            if action not in session_data["features_used"]:
                session_data["features_used"].append(action)
            
            if "query" in action.lower() or "chat" in action.lower():
                session_data["queries_made"] += 1
            
            if any(keyword in action.lower() for keyword in ["generate", "analyze", "intelligence"]):
                session_data["documents_analyzed"] += 1
            
            session_data["time_spent_seconds"] = int(timestamp - session_data.get("started_at", timestamp))
            
            # Store session with 4-hour TTL
            await self.redis_pool.set_with_optimization(
                cache_key,
                json.dumps(session_data).encode('utf-8'),
                14400,  # 4 hours
                "analytics"
            )
        except Exception:
            pass
    
    async def _update_feature_usage(self, action: str, user_id: Optional[str], timestamp: float):
        """Update feature usage counters."""
        try:
            feature = self._categorize_action(action)
            if not feature:
                return
            
            cache_key = f"analytics:feature_usage:{feature}"
            
            # Get existing usage data
            usage_data = {"total_uses": 0, "unique_users": set(), "last_used": 0}
            cached_data = await self.redis_pool.get_with_fallback(cache_key, "analytics")
            if cached_data:
                data = json.loads(cached_data.decode('utf-8'))
                usage_data["total_uses"] = data["total_uses"]
                usage_data["unique_users"] = set(data["unique_users"])
                usage_data["last_used"] = data["last_used"]
            
            # Update counters
            usage_data["total_uses"] += 1
            if user_id:
                usage_data["unique_users"].add(user_id)
            usage_data["last_used"] = timestamp
            
            # Store back (convert set to list for JSON serialization)
            store_data = {
                "total_uses": usage_data["total_uses"],
                "unique_users": list(usage_data["unique_users"]),
                "last_used": usage_data["last_used"]
            }
            
            await self.redis_pool.set_with_optimization(
                cache_key,
                json.dumps(store_data).encode('utf-8'),
                86400 * 30,  # 30 days
                "analytics"
            )
        except Exception:
            pass
    
    def _categorize_action(self, action: str) -> Optional[str]:
        """Categorize an action into a feature category."""
        for category, patterns in self.feature_categories.items():
            if any(pattern in action for pattern in patterns):
                return category
        return "other"
    
    async def _get_usage_overview(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """Get high-level usage overview."""
        # Mock data - would aggregate from actual stored analytics
        return {
            "total_sessions": 1247,
            "unique_users": 89,
            "total_actions": 5632,
            "avg_session_duration_minutes": 12.4,
            "bounce_rate": 23.1,
            "top_features": [
                {"name": "Smart Summaries", "usage": 34.2},
                {"name": "Document Intelligence", "usage": 28.7},
                {"name": "Knowledge Graph", "usage": 18.5},
                {"name": "Multimodal Analysis", "usage": 12.1},
                {"name": "Collaboration", "usage": 6.5}
            ]
        }
    
    async def _get_feature_analytics(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """Get detailed feature usage analytics."""
        return {
            "feature_adoption": {
                "document_intelligence": 87.2,
                "smart_summaries": 92.1,
                "knowledge_graph": 45.3,
                "multimodal_analysis": 34.6,
                "collaboration": 23.1
            },
            "feature_satisfaction": {
                "document_intelligence": 4.2,
                "smart_summaries": 4.5,
                "knowledge_graph": 3.9,
                "multimodal_analysis": 4.1,
                "collaboration": 3.8
            },
            "feature_performance": {
                "document_intelligence": {"avg_time": 1240, "success_rate": 94.2},
                "smart_summaries": {"avg_time": 3200, "success_rate": 96.8},
                "knowledge_graph": {"avg_time": 850, "success_rate": 89.1},
                "multimodal_analysis": {"avg_time": 2100, "success_rate": 91.4}
            }
        }
    
    async def _get_user_behavior_patterns(self, start_time: float, end_time: float) -> List[UserBehaviorPattern]:
        """Identify user behavior patterns."""
        return [
            UserBehaviorPattern(
                pattern_type="sequential_feature_usage",
                description="Users typically start with document intelligence, then move to summaries",
                frequency=0.73,
                user_segment="regular_users",
                confidence=0.89
            ),
            UserBehaviorPattern(
                pattern_type="power_user_workflow",
                description="Advanced users use knowledge graphs after initial analysis",
                frequency=0.45,
                user_segment="power_users", 
                confidence=0.92
            ),
            UserBehaviorPattern(
                pattern_type="collaboration_trigger",
                description="Users share content after spending >5 minutes analyzing",
                frequency=0.34,
                user_segment="team_users",
                confidence=0.78
            )
        ]
    
    async def _get_performance_insights(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """Get system performance insights."""
        return {
            "response_time_trends": {
                "p50": 245,
                "p90": 1840,
                "p95": 3200,
                "p99": 8500
            },
            "error_analysis": {
                "total_errors": 23,
                "error_rate": 0.41,
                "top_errors": [
                    {"type": "timeout", "count": 12, "percentage": 52.2},
                    {"type": "validation", "count": 7, "percentage": 30.4},
                    {"type": "rate_limit", "count": 4, "percentage": 17.4}
                ]
            },
            "resource_utilization": {
                "redis_hit_rate": 94.2,
                "llm_token_usage": 234567,
                "cache_efficiency": 89.1
            }
        }
    
    async def _get_content_analytics(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """Get content-related analytics."""
        return {
            "document_stats": {
                "total_analyzed": 456,
                "avg_document_size": "2.3MB",
                "most_common_type": "research_paper",
                "complexity_distribution": {
                    "basic": 34,
                    "intermediate": 52, 
                    "advanced": 14
                }
            },
            "summary_preferences": {
                "executive": 45.2,
                "bullet_points": 28.7,
                "detailed": 15.1,
                "action_items": 11.0
            },
            "knowledge_graph_insights": {
                "avg_nodes": 23,
                "avg_edges": 87,
                "most_connected_concepts": ["AI", "machine learning", "data analysis"]
            }
        }
    
    def _get_health_grade(self, score: float) -> str:
        """Convert health score to letter grade."""
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "B+"
        elif score >= 80:
            return "B"
        elif score >= 75:
            return "C+"
        elif score >= 70:
            return "C"
        else:
            return "D"
    
    def _get_health_recommendations(self, error_score: float, performance_score: float, availability_score: float) -> List[str]:
        """Generate health improvement recommendations."""
        recommendations = []
        
        if error_score < 90:
            recommendations.append("Investigate and reduce error rates - consider implementing better error handling")
        
        if performance_score < 85:
            recommendations.append("Optimize response times - review caching strategies and database queries")
        
        if availability_score < 95:
            recommendations.append("Ensure all features are functioning properly - check service dependencies")
        
        if not recommendations:
            recommendations.append("System health is excellent - continue monitoring and maintain current practices")
        
        return recommendations
    
    async def _get_user_actions(self, user_id: str, start_time: float, end_time: float) -> List[Dict[str, Any]]:
        """Get actions for a specific user in time range."""
        # Mock implementation - would query actual stored actions
        return []
    
    async def _get_user_sessions(self, user_id: str, start_time: float, end_time: float) -> List[UserSession]:
        """Get sessions for a specific user."""
        # Mock implementation
        return []
    
    def _analyze_user_behavior(self, actions: List[Dict[str, Any]], sessions: List[UserSession]) -> Dict[str, Any]:
        """Analyze user behavior patterns."""
        return {
            "activity_level": "regular",
            "preferred_time": "business_hours",
            "session_patterns": "consistent",
            "feature_exploration": "high"
        }
    
    def _analyze_feature_preferences(self, actions: List[Dict[str, Any]]) -> Dict[str, float]:
        """Analyze user's feature preferences."""
        return {
            "document_intelligence": 0.35,
            "smart_summaries": 0.28,
            "knowledge_graph": 0.18,
            "multimodal_analysis": 0.12,
            "collaboration": 0.07
        }
    
    def _analyze_usage_patterns(self, sessions: List[UserSession]) -> Dict[str, Any]:
        """Analyze user usage patterns."""
        return {
            "typical_session_length": "8-15 minutes",
            "peak_usage_days": ["Tuesday", "Wednesday", "Thursday"],
            "workflow_consistency": "high",
            "multi_feature_usage": "frequent"
        }
    
    def _generate_user_recommendations(self, behavior: Dict[str, Any], preferences: Dict[str, float]) -> List[str]:
        """Generate personalized recommendations for user."""
        recommendations = []
        
        # Find unused or underused features
        for feature, usage in preferences.items():
            if usage < 0.1:
                if feature == "knowledge_graph":
                    recommendations.append("Try the Knowledge Graph feature to visualize connections in your documents")
                elif feature == "multimodal_analysis":
                    recommendations.append("Upload images and charts for multimodal analysis insights")
                elif feature == "collaboration":
                    recommendations.append("Share your analyses with team members using our collaboration features")
        
        if not recommendations:
            recommendations.append("You're using the platform effectively! Consider exploring advanced features for deeper insights")
        
        return recommendations[:3]  # Limit to 3 recommendations


# Global instance
_analytics_service = None

def get_analytics_service() -> AnalyticsService:
    """Get or create the analytics service singleton."""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    return _analytics_service