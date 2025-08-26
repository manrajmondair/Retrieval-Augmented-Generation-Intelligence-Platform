"""
AI-Powered Recommendations Service - Intelligent content suggestions and personalization.
"""
import asyncio
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict, Counter

from app.services.redis_pool import get_redis_pool
from app.services.fast_llm import get_fast_llm_service


class RecommendationType(Enum):
    """Types of recommendations available."""
    SIMILAR_DOCUMENTS = "similar_documents"
    RELATED_ANALYSIS = "related_analysis"
    SUGGESTED_SUMMARIES = "suggested_summaries"
    COLLABORATION_OPPORTUNITIES = "collaboration_opportunities"
    WORKFLOW_OPTIMIZATION = "workflow_optimization"
    CONTENT_GAPS = "content_gaps"


@dataclass
class Recommendation:
    """Represents a content recommendation."""
    recommendation_id: str
    type: RecommendationType
    title: str
    description: str
    content_id: str
    confidence: float
    reasoning: str
    priority: str  # "high", "medium", "low"
    action_url: str
    metadata: Dict[str, Any]
    generated_at: float


@dataclass
class UserProfile:
    """User behavior profile for personalized recommendations."""
    user_id: str
    preferred_features: Dict[str, float]
    document_interests: List[str]
    collaboration_patterns: Dict[str, Any]
    usage_frequency: str
    expertise_level: str
    last_updated: float


class RecommendationsService:
    """Service for generating intelligent content recommendations."""
    
    def __init__(self):
        self.redis_pool = get_redis_pool()
        self.llm_service = get_fast_llm_service()
        
        # Recommendation templates for different types
        self.recommendation_templates = {
            RecommendationType.SIMILAR_DOCUMENTS: {
                "title_prefix": "Similar Document",
                "description_template": "Based on your interest in {source_topic}, you might find this {document_type} relevant",
                "action_template": "/intelligence/analyze/{content_id}"
            },
            RecommendationType.RELATED_ANALYSIS: {
                "title_prefix": "Related Analysis",
                "description_template": "This {analysis_type} complements your recent work on {related_topic}",
                "action_template": "/intelligence/analyze/{content_id}"
            },
            RecommendationType.SUGGESTED_SUMMARIES: {
                "title_prefix": "Recommended Summary",
                "description_template": "Try a {summary_type} summary for deeper insights into {document_topic}",
                "action_template": "/summaries/generate/{content_id}?type={summary_type}"
            },
            RecommendationType.COLLABORATION_OPPORTUNITIES: {
                "title_prefix": "Collaboration Opportunity",
                "description_template": "Share this {content_type} with {team_member} who works on similar topics",
                "action_template": "/collaborate/share?content_id={content_id}"
            },
            RecommendationType.WORKFLOW_OPTIMIZATION: {
                "title_prefix": "Workflow Suggestion",
                "description_template": "Streamline your analysis by {optimization_tip}",
                "action_template": "/features/{feature_name}"
            },
            RecommendationType.CONTENT_GAPS: {
                "title_prefix": "Content Gap Identified",
                "description_template": "Your knowledge graph shows missing connections around {topic}",
                "action_template": "/knowledge/search/{topic}"
            }
        }
    
    async def get_personalized_recommendations(self, 
                                            user_id: str, 
                                            context: Optional[Dict[str, Any]] = None,
                                            limit: int = 10) -> List[Recommendation]:
        """Get personalized recommendations for a user."""
        # Get user profile
        user_profile = await self._get_user_profile(user_id)
        
        # Get user's recent activity
        recent_activity = await self._get_recent_activity(user_id, days=7)
        
        # Generate different types of recommendations
        tasks = [
            self._generate_similar_documents(user_profile, recent_activity, context),
            self._generate_related_analysis(user_profile, recent_activity, context),
            self._generate_suggested_summaries(user_profile, recent_activity, context),
            self._generate_collaboration_opportunities(user_profile, recent_activity, context),
            self._generate_workflow_optimizations(user_profile, recent_activity, context),
            self._generate_content_gaps(user_profile, recent_activity, context)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine all recommendations
        all_recommendations = []
        for result in results:
            if not isinstance(result, Exception) and result:
                all_recommendations.extend(result)
        
        # Score and rank recommendations
        scored_recommendations = self._score_recommendations(all_recommendations, user_profile, context)
        
        # Return top recommendations
        return sorted(scored_recommendations, key=lambda x: x.confidence, reverse=True)[:limit]
    
    async def get_content_recommendations(self, content_id: str, content_type: str) -> List[Recommendation]:
        """Get recommendations related to specific content."""
        # Analyze the content to understand its characteristics
        content_analysis = await self._analyze_content(content_id, content_type)
        
        # Generate content-specific recommendations
        recommendations = []
        
        # Similar content recommendations
        similar_content = await self._find_similar_content(content_analysis)
        for similar in similar_content[:3]:
            rec = Recommendation(
                recommendation_id=f"similar_{content_id}_{similar['id']}",
                type=RecommendationType.SIMILAR_DOCUMENTS,
                title=f"Similar: {similar['title']}",
                description=f"This {similar['type']} shares {similar['similarity_reason']} with your current content",
                content_id=similar['id'],
                confidence=similar['similarity_score'],
                reasoning=f"Content similarity based on {similar['matching_features']}",
                priority="medium",
                action_url=f"/intelligence/analyze/{similar['id']}",
                metadata=similar,
                generated_at=time.time()
            )
            recommendations.append(rec)
        
        # Analysis recommendations
        if content_type in ["document", "text"]:
            analysis_recs = await self._suggest_analysis_types(content_analysis)
            recommendations.extend(analysis_recs)
        
        # Summary recommendations
        if content_analysis.get("word_count", 0) > 500:
            summary_recs = await self._suggest_summary_types(content_analysis)
            recommendations.extend(summary_recs)
        
        return recommendations[:8]  # Return top 8 content-specific recommendations
    
    async def get_trending_recommendations(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Get trending content and popular recommendations."""
        # Mock trending data - would come from actual analytics
        trending_content = [
            {
                "id": "trending_doc_1",
                "title": "Latest AI Research Breakthrough",
                "type": "research_paper",
                "popularity_score": 0.95,
                "engagement_metrics": {"views": 1247, "shares": 89, "comments": 34},
                "trending_reason": "High engagement in AI community"
            },
            {
                "id": "trending_analysis_1", 
                "title": "Market Analysis Q4 2024",
                "type": "business_report",
                "popularity_score": 0.88,
                "engagement_metrics": {"views": 892, "shares": 156, "comments": 67},
                "trending_reason": "Shared frequently across teams"
            },
            {
                "id": "trending_summary_1",
                "title": "Executive Brief: Climate Technology",
                "type": "executive_summary",
                "popularity_score": 0.82,
                "engagement_metrics": {"views": 678, "shares": 234, "comments": 45},
                "trending_reason": "Popular with leadership teams"
            }
        ]
        
        # Filter by category if specified
        if category:
            trending_content = [item for item in trending_content if category.lower() in item["type"].lower()]
        
        return {
            "trending_content": trending_content,
            "trending_features": [
                {"feature": "Smart Summaries", "growth": "+23%", "reason": "Increased executive usage"},
                {"feature": "Knowledge Graph", "growth": "+18%", "reason": "Better visualization needs"},
                {"feature": "Multimodal Analysis", "growth": "+34%", "reason": "More image/chart uploads"}
            ],
            "popular_workflows": [
                {"workflow": "Document → Intelligence → Summary → Share", "usage": "67% of users"},
                {"workflow": "Upload → Multimodal → Knowledge Graph", "usage": "34% of users"},
                {"workflow": "Analysis → Collaborate → Iterate", "usage": "28% of users"}
            ],
            "recommendation_stats": {
                "total_recommendations_generated": 15624,
                "click_through_rate": "34.2%",
                "user_satisfaction": "4.3/5.0",
                "most_popular_type": "similar_documents"
            }
        }
    
    async def track_recommendation_interaction(self, 
                                            recommendation_id: str,
                                            user_id: str,
                                            interaction_type: str,
                                            metadata: Dict[str, Any] = None):
        """Track user interaction with recommendations for learning."""
        interaction_record = {
            "recommendation_id": recommendation_id,
            "user_id": user_id,
            "interaction_type": interaction_type,  # "viewed", "clicked", "dismissed", "helpful"
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        
        # Store interaction for machine learning
        await self._store_interaction(interaction_record)
        
        # Update user profile based on interaction
        await self._update_user_profile_from_interaction(user_id, interaction_record)
    
    async def _generate_similar_documents(self, user_profile: UserProfile, recent_activity: List[Dict], context: Optional[Dict]) -> List[Recommendation]:
        """Generate similar document recommendations."""
        recommendations = []
        
        # Mock similar documents based on user interests
        if user_profile and user_profile.document_interests:
            for interest in user_profile.document_interests[:3]:
                rec = Recommendation(
                    recommendation_id=f"similar_doc_{interest}_{int(time.time())}",
                    type=RecommendationType.SIMILAR_DOCUMENTS,
                    title=f"Research on {interest.title()}",
                    description=f"Based on your interest in {interest}, this document provides complementary insights",
                    content_id=f"similar_doc_{interest}",
                    confidence=0.82,
                    reasoning=f"User has shown consistent engagement with {interest} content",
                    priority="medium",
                    action_url=f"/intelligence/analyze/similar_doc_{interest}",
                    metadata={"topic": interest, "similarity_basis": "user_interests"},
                    generated_at=time.time()
                )
                recommendations.append(rec)
        
        return recommendations
    
    async def _generate_related_analysis(self, user_profile: UserProfile, recent_activity: List[Dict], context: Optional[Dict]) -> List[Recommendation]:
        """Generate related analysis recommendations."""
        recommendations = []
        
        # Look for incomplete analysis workflows
        if recent_activity:
            for activity in recent_activity[-3:]:  # Last 3 activities
                if activity.get("action") == "intelligence/generate" and not activity.get("followed_by_summary"):
                    rec = Recommendation(
                        recommendation_id=f"followup_analysis_{activity.get('content_id')}",
                        type=RecommendationType.RELATED_ANALYSIS,
                        title="Complete Your Analysis",
                        description=f"Generate a summary for your recent analysis of {activity.get('content_id', 'document')}",
                        content_id=activity.get("content_id", "unknown"),
                        confidence=0.75,
                        reasoning="User generated intelligence but didn't create summary",
                        priority="high",
                        action_url=f"/summaries/generate/{activity.get('content_id')}",
                        metadata={"workflow_stage": "post_analysis", "original_action": activity.get("action")},
                        generated_at=time.time()
                    )
                    recommendations.append(rec)
        
        return recommendations
    
    async def _generate_suggested_summaries(self, user_profile: UserProfile, recent_activity: List[Dict], context: Optional[Dict]) -> List[Recommendation]:
        """Generate summary type recommendations."""
        recommendations = []
        
        # Recommend different summary types based on user role/preferences
        if user_profile and user_profile.preferred_features.get("smart_summaries", 0) > 0.3:
            summary_suggestions = [
                ("executive", "Quick executive overview for leadership presentations"),
                ("action_items", "Extract actionable items for project planning"),
                ("key_insights", "Deep insights for strategic decision making")
            ]
            
            for summary_type, description in summary_suggestions:
                rec = Recommendation(
                    recommendation_id=f"summary_suggest_{summary_type}_{int(time.time())}",
                    type=RecommendationType.SUGGESTED_SUMMARIES,
                    title=f"Try {summary_type.replace('_', ' ').title()} Summary",
                    description=description,
                    content_id="recent_document",  # Would be actual content ID
                    confidence=0.68,
                    reasoning=f"User frequently uses summaries and would benefit from {summary_type}",
                    priority="low",
                    action_url=f"/summaries/generate/recent_document?type={summary_type}",
                    metadata={"summary_type": summary_type, "personalization": "usage_pattern"},
                    generated_at=time.time()
                )
                recommendations.append(rec)
        
        return recommendations[:2]  # Limit to 2 summary recommendations
    
    async def _generate_collaboration_opportunities(self, user_profile: UserProfile, recent_activity: List[Dict], context: Optional[Dict]) -> List[Recommendation]:
        """Generate collaboration recommendations."""
        recommendations = []
        
        # Recommend sharing based on content quality and user behavior
        if user_profile and user_profile.collaboration_patterns.get("sharing_frequency", 0) < 0.3:
            rec = Recommendation(
                recommendation_id=f"collab_share_{int(time.time())}",
                type=RecommendationType.COLLABORATION_OPPORTUNITIES,
                title="Share Your Analysis",
                description="Your recent document analysis has high-quality insights that would benefit your team",
                content_id="recent_analysis",
                confidence=0.71,
                reasoning="User has valuable content but low sharing frequency",
                priority="medium",
                action_url="/collaborate/share?content_id=recent_analysis",
                metadata={"sharing_motivation": "value_sharing", "team_benefit": True},
                generated_at=time.time()
            )
            recommendations.append(rec)
        
        return recommendations
    
    async def _generate_workflow_optimizations(self, user_profile: UserProfile, recent_activity: List[Dict], context: Optional[Dict]) -> List[Recommendation]:
        """Generate workflow optimization recommendations."""
        recommendations = []
        
        # Identify workflow inefficiencies
        if user_profile and user_profile.preferred_features.get("knowledge_graph", 0) < 0.2:
            rec = Recommendation(
                recommendation_id=f"workflow_kg_{int(time.time())}",
                type=RecommendationType.WORKFLOW_OPTIMIZATION,
                title="Visualize Document Connections",
                description="Use Knowledge Graphs to better understand relationships in your documents",
                content_id="workflow_optimization",
                confidence=0.64,
                reasoning="User would benefit from visual relationship mapping",
                priority="low",
                action_url="/knowledge/generate",
                metadata={"optimization_type": "feature_adoption", "feature": "knowledge_graph"},
                generated_at=time.time()
            )
            recommendations.append(rec)
        
        return recommendations
    
    async def _generate_content_gaps(self, user_profile: UserProfile, recent_activity: List[Dict], context: Optional[Dict]) -> List[Recommendation]:
        """Identify content gaps and suggest filling them."""
        recommendations = []
        
        # Mock content gap analysis
        if user_profile and len(user_profile.document_interests) < 3:
            rec = Recommendation(
                recommendation_id=f"content_gap_{int(time.time())}",
                type=RecommendationType.CONTENT_GAPS,
                title="Expand Your Knowledge Base",
                description="Consider exploring related topics to get more comprehensive insights",
                content_id="knowledge_expansion",
                confidence=0.58,
                reasoning="User has limited topic diversity in their content",
                priority="low",
                action_url="/search?q=related_topics",
                metadata={"gap_type": "topic_diversity", "current_topics": user_profile.document_interests},
                generated_at=time.time()
            )
            recommendations.append(rec)
        
        return recommendations
    
    def _score_recommendations(self, recommendations: List[Recommendation], user_profile: UserProfile, context: Optional[Dict]) -> List[Recommendation]:
        """Score and rank recommendations based on relevance."""
        for rec in recommendations:
            # Base confidence score
            score = rec.confidence
            
            # Boost based on user preferences
            if user_profile and rec.type.value in user_profile.preferred_features:
                preference_weight = user_profile.preferred_features[rec.type.value]
                score *= (1 + preference_weight * 0.3)
            
            # Context boost
            if context and rec.metadata.get("context_match"):
                score *= 1.2
            
            # Priority adjustment
            if rec.priority == "high":
                score *= 1.3
            elif rec.priority == "low":
                score *= 0.8
            
            # Update confidence with final score
            rec.confidence = min(1.0, score)
        
        return recommendations
    
    async def _get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile from cache."""
        try:
            cache_key = f"user_profile:{user_id}"
            cached_data = await self.redis_pool.get_with_fallback(cache_key, "recommendations")
            
            if cached_data:
                profile_data = json.loads(cached_data.decode('utf-8'))
                return UserProfile(
                    user_id=profile_data["user_id"],
                    preferred_features=profile_data["preferred_features"],
                    document_interests=profile_data["document_interests"],
                    collaboration_patterns=profile_data["collaboration_patterns"],
                    usage_frequency=profile_data["usage_frequency"],
                    expertise_level=profile_data["expertise_level"],
                    last_updated=profile_data["last_updated"]
                )
        except Exception:
            pass
        
        # Return default profile if not found
        return UserProfile(
            user_id=user_id,
            preferred_features={"document_intelligence": 0.8, "smart_summaries": 0.6, "knowledge_graph": 0.3},
            document_interests=["artificial intelligence", "machine learning", "data analysis"],
            collaboration_patterns={"sharing_frequency": 0.2, "comment_frequency": 0.1},
            usage_frequency="regular",
            expertise_level="intermediate",
            last_updated=time.time()
        )
    
    async def _get_recent_activity(self, user_id: str, days: int) -> List[Dict[str, Any]]:
        """Get user's recent activity."""
        # Mock recent activity - would come from analytics service
        return [
            {"action": "intelligence/generate", "content_id": "doc_123", "timestamp": time.time() - 3600},
            {"action": "summaries/generate", "content_id": "doc_123", "timestamp": time.time() - 1800},
            {"action": "knowledge/graph", "content_id": "workspace_1", "timestamp": time.time() - 900}
        ]
    
    async def _analyze_content(self, content_id: str, content_type: str) -> Dict[str, Any]:
        """Analyze content to understand its characteristics."""
        # Mock content analysis
        return {
            "content_id": content_id,
            "type": content_type,
            "topics": ["artificial intelligence", "machine learning"],
            "complexity": "intermediate",
            "word_count": 2500,
            "key_concepts": ["neural networks", "algorithms", "data processing"],
            "sentiment": "neutral",
            "technical_level": "high"
        }
    
    async def _find_similar_content(self, content_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find content similar to the analyzed content."""
        # Mock similar content
        return [
            {
                "id": "similar_doc_1",
                "title": "Deep Learning Applications",
                "type": "research_paper",
                "similarity_score": 0.87,
                "similarity_reason": "shared AI/ML topics",
                "matching_features": "key concepts and technical level"
            },
            {
                "id": "similar_doc_2",
                "title": "Algorithm Optimization Study",
                "type": "technical_report",
                "similarity_score": 0.74,
                "similarity_reason": "algorithmic focus",
                "matching_features": "technical complexity and domain"
            }
        ]
    
    async def _suggest_analysis_types(self, content_analysis: Dict[str, Any]) -> List[Recommendation]:
        """Suggest appropriate analysis types for content."""
        recommendations = []
        
        if content_analysis.get("technical_level") == "high":
            rec = Recommendation(
                recommendation_id=f"analysis_suggest_{content_analysis['content_id']}",
                type=RecommendationType.RELATED_ANALYSIS,
                title="Technical Deep Dive Analysis",
                description="This technical content would benefit from detailed intelligence analysis",
                content_id=content_analysis["content_id"],
                confidence=0.79,
                reasoning="High technical content complexity indicates need for thorough analysis",
                priority="medium",
                action_url=f"/intelligence/generate/{content_analysis['content_id']}",
                metadata={"analysis_reason": "technical_complexity"},
                generated_at=time.time()
            )
            recommendations.append(rec)
        
        return recommendations
    
    async def _suggest_summary_types(self, content_analysis: Dict[str, Any]) -> List[Recommendation]:
        """Suggest appropriate summary types for content."""
        recommendations = []
        
        word_count = content_analysis.get("word_count", 0)
        if word_count > 2000:
            rec = Recommendation(
                recommendation_id=f"summary_suggest_{content_analysis['content_id']}",
                type=RecommendationType.SUGGESTED_SUMMARIES,
                title="Executive Summary Recommended",
                description="This lengthy document would benefit from an executive summary",
                content_id=content_analysis["content_id"],
                confidence=0.81,
                reasoning=f"Document length ({word_count} words) suggests executive summary would be valuable",
                priority="medium",
                action_url=f"/summaries/generate/{content_analysis['content_id']}?type=executive",
                metadata={"summary_reason": "document_length", "word_count": word_count},
                generated_at=time.time()
            )
            recommendations.append(rec)
        
        return recommendations
    
    async def _store_interaction(self, interaction_record: Dict[str, Any]):
        """Store recommendation interaction for learning."""
        try:
            cache_key = f"recommendation_interactions:{interaction_record['user_id']}"
            
            # Get existing interactions
            interactions = []
            cached_data = await self.redis_pool.get_with_fallback(cache_key, "recommendations")
            if cached_data:
                interactions = json.loads(cached_data.decode('utf-8'))
            
            # Add new interaction
            interactions.append(interaction_record)
            
            # Keep only last 100 interactions
            interactions = interactions[-100:]
            
            # Store back
            await self.redis_pool.set_with_optimization(
                cache_key,
                json.dumps(interactions).encode('utf-8'),
                86400 * 30,  # 30 days
                "recommendations"
            )
        except Exception:
            pass
    
    async def _update_user_profile_from_interaction(self, user_id: str, interaction: Dict[str, Any]):
        """Update user profile based on recommendation interaction."""
        # This would implement machine learning to update preferences
        # For now, it's a placeholder
        pass


# Global instance
_recommendations_service = None

def get_recommendations_service() -> RecommendationsService:
    """Get or create the recommendations service singleton."""
    global _recommendations_service
    if _recommendations_service is None:
        _recommendations_service = RecommendationsService()
    return _recommendations_service