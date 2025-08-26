"""
Real-time Collaboration Service - Enable sharing, comments, and team workspaces.
"""
import asyncio
import json
import time
import uuid
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from app.services.redis_pool import get_redis_pool


class SharePermission(Enum):
    """Permission levels for shared documents."""
    READ = "read"
    COMMENT = "comment" 
    EDIT = "edit"
    ADMIN = "admin"


class ShareType(Enum):
    """Types of shareable content."""
    DOCUMENT = "document"
    ANALYSIS = "analysis"
    SUMMARY = "summary"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    WORKSPACE = "workspace"


@dataclass
class ShareLink:
    """Represents a shareable link with permissions."""
    share_id: str
    content_type: ShareType
    content_id: str
    permission: SharePermission
    expires_at: Optional[float]
    created_by: str
    created_at: float
    access_count: int
    last_accessed: Optional[float]


@dataclass
class Comment:
    """User comment on shared content."""
    comment_id: str
    content_id: str
    user_id: str
    content: str
    created_at: float
    updated_at: Optional[float]
    parent_comment_id: Optional[str]
    reactions: Dict[str, int]  # emoji -> count


@dataclass
class Workspace:
    """Team workspace containing multiple documents."""
    workspace_id: str
    name: str
    description: str
    created_by: str
    members: List[Dict[str, Any]]  # user_id, role, joined_at
    documents: List[str]  # doc_ids
    created_at: float
    settings: Dict[str, Any]


class CollaborationService:
    """Service for real-time collaboration and sharing features."""
    
    def __init__(self):
        self.redis_pool = get_redis_pool()
        
        # WebSocket connections for real-time features
        self.active_connections: Dict[str, Set[str]] = {}  # content_id -> set of user_ids
        
    async def create_share_link(self, 
                              content_type: ShareType,
                              content_id: str, 
                              permission: SharePermission,
                              user_id: str,
                              expires_hours: Optional[int] = None) -> ShareLink:
        """Create a shareable link with specified permissions."""
        share_id = str(uuid.uuid4())[:12]  # Short, shareable ID
        
        expires_at = None
        if expires_hours:
            expires_at = time.time() + (expires_hours * 3600)
        
        share_link = ShareLink(
            share_id=share_id,
            content_type=content_type,
            content_id=content_id,
            permission=permission,
            expires_at=expires_at,
            created_by=user_id,
            created_at=time.time(),
            access_count=0,
            last_accessed=None
        )
        
        # Cache the share link
        await self._cache_share_link(share_link)
        
        return share_link
    
    async def access_shared_content(self, share_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Access content via share link and return with user's permission level."""
        share_link = await self._get_share_link(share_id)
        
        if not share_link:
            return {"error": "Share link not found or expired"}
        
        # Check if link has expired
        if share_link.expires_at and time.time() > share_link.expires_at:
            return {"error": "Share link has expired"}
        
        # Update access tracking
        share_link.access_count += 1
        share_link.last_accessed = time.time()
        await self._cache_share_link(share_link)
        
        # Get the actual content based on type
        content = await self._get_shared_content(share_link.content_type, share_link.content_id)
        
        # Add collaboration metadata
        collaboration_data = await self._get_collaboration_data(share_link.content_id)
        
        return {
            "content": content,
            "share_info": {
                "share_id": share_id,
                "content_type": share_link.content_type.value,
                "permission": share_link.permission.value,
                "created_at": share_link.created_at,
                "access_count": share_link.access_count
            },
            "collaboration": collaboration_data,
            "user_permission": share_link.permission.value
        }
    
    async def add_comment(self, 
                         content_id: str, 
                         user_id: str, 
                         content: str,
                         parent_comment_id: Optional[str] = None) -> Comment:
        """Add a comment to shared content."""
        comment = Comment(
            comment_id=str(uuid.uuid4()),
            content_id=content_id,
            user_id=user_id,
            content=content,
            created_at=time.time(),
            updated_at=None,
            parent_comment_id=parent_comment_id,
            reactions={}
        )
        
        # Cache the comment
        await self._cache_comment(comment)
        
        # Notify other users in real-time
        await self._notify_users(content_id, {
            "type": "new_comment",
            "comment": {
                "comment_id": comment.comment_id,
                "user_id": user_id,
                "content": content,
                "created_at": comment.created_at
            }
        })
        
        return comment
    
    async def get_comments(self, content_id: str) -> List[Comment]:
        """Get all comments for a piece of content."""
        try:
            cache_key = f"comments:{content_id}"
            cached_comments = await self.redis_pool.get_with_fallback(cache_key, "cache")
            
            if cached_comments:
                comments_data = json.loads(cached_comments.decode('utf-8'))
                comments = []
                for comment_data in comments_data:
                    comment = Comment(
                        comment_id=comment_data["comment_id"],
                        content_id=comment_data["content_id"],
                        user_id=comment_data["user_id"],
                        content=comment_data["content"],
                        created_at=comment_data["created_at"],
                        updated_at=comment_data.get("updated_at"),
                        parent_comment_id=comment_data.get("parent_comment_id"),
                        reactions=comment_data.get("reactions", {})
                    )
                    comments.append(comment)
                return comments
        except Exception:
            pass
        
        return []
    
    async def create_workspace(self, 
                             name: str, 
                             description: str, 
                             created_by: str,
                             initial_members: List[str] = None) -> Workspace:
        """Create a team workspace."""
        workspace_id = str(uuid.uuid4())
        
        members = [{"user_id": created_by, "role": "admin", "joined_at": time.time()}]
        if initial_members:
            for member_id in initial_members:
                members.append({
                    "user_id": member_id, 
                    "role": "member", 
                    "joined_at": time.time()
                })
        
        workspace = Workspace(
            workspace_id=workspace_id,
            name=name,
            description=description,
            created_by=created_by,
            members=members,
            documents=[],
            created_at=time.time(),
            settings={
                "default_permission": SharePermission.COMMENT.value,
                "allow_public_sharing": False,
                "require_approval": False
            }
        )
        
        # Cache the workspace
        await self._cache_workspace(workspace)
        
        return workspace
    
    async def add_document_to_workspace(self, workspace_id: str, doc_id: str, user_id: str) -> bool:
        """Add a document to a workspace."""
        workspace = await self._get_workspace(workspace_id)
        if not workspace:
            return False
        
        # Check user permission
        user_role = None
        for member in workspace.members:
            if member["user_id"] == user_id:
                user_role = member["role"]
                break
        
        if user_role not in ["admin", "member"]:
            return False
        
        # Add document if not already present
        if doc_id not in workspace.documents:
            workspace.documents.append(doc_id)
            await self._cache_workspace(workspace)
            
            # Notify workspace members
            await self._notify_workspace_members(workspace_id, {
                "type": "document_added",
                "doc_id": doc_id,
                "added_by": user_id
            })
        
        return True
    
    async def get_workspace_activity(self, workspace_id: str) -> Dict[str, Any]:
        """Get recent activity in a workspace."""
        workspace = await self._get_workspace(workspace_id)
        if not workspace:
            return {"error": "Workspace not found"}
        
        # Mock activity data - would come from activity log in real implementation
        activity = [
            {
                "type": "document_added",
                "user_id": workspace.created_by,
                "doc_id": "research_paper_1",
                "timestamp": time.time() - 3600,
                "message": "Added research paper to workspace"
            },
            {
                "type": "comment_added", 
                "user_id": workspace.members[0]["user_id"],
                "content_id": "research_paper_1",
                "timestamp": time.time() - 1800,
                "message": "Added comment on document analysis"
            },
            {
                "type": "analysis_shared",
                "user_id": workspace.created_by,
                "share_id": "abc123def456",
                "timestamp": time.time() - 900,
                "message": "Shared intelligence analysis with team"
            }
        ]
        
        return {
            "workspace": {
                "workspace_id": workspace.workspace_id,
                "name": workspace.name,
                "member_count": len(workspace.members),
                "document_count": len(workspace.documents)
            },
            "recent_activity": activity,
            "active_users": len(self.active_connections.get(workspace_id, set())),
            "activity_summary": {
                "documents_added_today": 1,
                "comments_added_today": 3,
                "shares_created_today": 1
            }
        }
    
    async def get_collaboration_stats(self) -> Dict[str, Any]:
        """Get overall collaboration statistics."""
        # Mock stats - would aggregate from Redis/database in real implementation
        return {
            "platform_stats": {
                "total_shared_links": 156,
                "total_comments": 2341,
                "total_workspaces": 47,
                "active_collaborations": 23
            },
            "sharing_breakdown": {
                "document_shares": 89,
                "analysis_shares": 34,
                "summary_shares": 21,
                "graph_shares": 12
            },
            "permission_distribution": {
                "read_only": "45%",
                "comment_access": "35%", 
                "edit_access": "15%",
                "admin_access": "5%"
            },
            "engagement_metrics": {
                "avg_comments_per_share": 3.2,
                "avg_shares_per_workspace": 8.5,
                "daily_active_collaborators": 127
            }
        }
    
    async def _cache_share_link(self, share_link: ShareLink):
        """Cache a share link."""
        try:
            cache_key = f"share_link:{share_link.share_id}"
            share_data = {
                "share_id": share_link.share_id,
                "content_type": share_link.content_type.value,
                "content_id": share_link.content_id,
                "permission": share_link.permission.value,
                "expires_at": share_link.expires_at,
                "created_by": share_link.created_by,
                "created_at": share_link.created_at,
                "access_count": share_link.access_count,
                "last_accessed": share_link.last_accessed
            }
            
            # Cache for longer if no expiry, shorter if has expiry
            ttl = 86400 * 30  # 30 days default
            if share_link.expires_at:
                ttl = min(ttl, int(share_link.expires_at - time.time()))
            
            await self.redis_pool.set_with_optimization(
                cache_key,
                json.dumps(share_data).encode('utf-8'),
                ttl,
                "cache"
            )
        except Exception:
            pass
    
    async def _get_share_link(self, share_id: str) -> Optional[ShareLink]:
        """Get a share link from cache."""
        try:
            cache_key = f"share_link:{share_id}"
            cached_data = await self.redis_pool.get_with_fallback(cache_key, "cache")
            
            if cached_data:
                share_data = json.loads(cached_data.decode('utf-8'))
                return ShareLink(
                    share_id=share_data["share_id"],
                    content_type=ShareType(share_data["content_type"]),
                    content_id=share_data["content_id"],
                    permission=SharePermission(share_data["permission"]),
                    expires_at=share_data["expires_at"],
                    created_by=share_data["created_by"],
                    created_at=share_data["created_at"],
                    access_count=share_data["access_count"],
                    last_accessed=share_data["last_accessed"]
                )
        except Exception:
            pass
        
        return None
    
    async def _get_shared_content(self, content_type: ShareType, content_id: str) -> Dict[str, Any]:
        """Get the actual content being shared."""
        # This would integrate with other services to get actual content
        # For now, return mock content based on type
        
        if content_type == ShareType.DOCUMENT:
            return {
                "type": "document",
                "id": content_id,
                "title": "Sample Research Document",
                "content": "This is the full document content that has been shared...",
                "metadata": {"word_count": 2500, "reading_time": "10 minutes"}
            }
        elif content_type == ShareType.ANALYSIS:
            return {
                "type": "analysis",
                "id": content_id, 
                "executive_summary": "Key insights from document intelligence analysis...",
                "insights": ["Insight 1", "Insight 2", "Insight 3"],
                "document_score": {"completeness": 0.9, "clarity": 0.85}
            }
        elif content_type == ShareType.SUMMARY:
            return {
                "type": "summary",
                "id": content_id,
                "summary_type": "executive",
                "content": "Executive summary of the document highlighting key points...",
                "confidence": 0.92
            }
        else:
            return {"type": "unknown", "id": content_id}
    
    async def _get_collaboration_data(self, content_id: str) -> Dict[str, Any]:
        """Get collaboration data for content (comments, activity, etc.)."""
        comments = await self.get_comments(content_id)
        
        return {
            "comment_count": len(comments),
            "recent_comments": [
                {
                    "user_id": comment.user_id,
                    "content": comment.content[:100] + "..." if len(comment.content) > 100 else comment.content,
                    "created_at": comment.created_at
                }
                for comment in comments[-3:]  # Last 3 comments
            ],
            "active_users": len(self.active_connections.get(content_id, set())),
            "share_stats": {
                "total_views": 45,
                "unique_visitors": 12,
                "last_accessed": time.time() - 300
            }
        }
    
    async def _cache_comment(self, comment: Comment):
        """Cache a comment."""
        try:
            # Get existing comments
            comments = await self.get_comments(comment.content_id)
            comments.append(comment)
            
            # Cache updated comments list
            cache_key = f"comments:{comment.content_id}"
            comments_data = []
            for c in comments:
                comments_data.append({
                    "comment_id": c.comment_id,
                    "content_id": c.content_id,
                    "user_id": c.user_id,
                    "content": c.content,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                    "parent_comment_id": c.parent_comment_id,
                    "reactions": c.reactions
                })
            
            await self.redis_pool.set_with_optimization(
                cache_key,
                json.dumps(comments_data).encode('utf-8'),
                86400,  # 24 hours
                "cache"
            )
        except Exception:
            pass
    
    async def _cache_workspace(self, workspace: Workspace):
        """Cache a workspace."""
        try:
            cache_key = f"workspace:{workspace.workspace_id}"
            workspace_data = {
                "workspace_id": workspace.workspace_id,
                "name": workspace.name,
                "description": workspace.description,
                "created_by": workspace.created_by,
                "members": workspace.members,
                "documents": workspace.documents,
                "created_at": workspace.created_at,
                "settings": workspace.settings
            }
            
            await self.redis_pool.set_with_optimization(
                cache_key,
                json.dumps(workspace_data).encode('utf-8'),
                86400 * 7,  # 7 days
                "cache"
            )
        except Exception:
            pass
    
    async def _get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Get a workspace from cache."""
        try:
            cache_key = f"workspace:{workspace_id}"
            cached_data = await self.redis_pool.get_with_fallback(cache_key, "cache")
            
            if cached_data:
                workspace_data = json.loads(cached_data.decode('utf-8'))
                return Workspace(
                    workspace_id=workspace_data["workspace_id"],
                    name=workspace_data["name"],
                    description=workspace_data["description"],
                    created_by=workspace_data["created_by"],
                    members=workspace_data["members"],
                    documents=workspace_data["documents"],
                    created_at=workspace_data["created_at"],
                    settings=workspace_data["settings"]
                )
        except Exception:
            pass
        
        return None
    
    async def _notify_users(self, content_id: str, message: Dict[str, Any]):
        """Notify active users about updates (would use WebSocket in real implementation)."""
        # Mock notification - in real implementation, would send via WebSocket
        active_users = self.active_connections.get(content_id, set())
        print(f"Notifying {len(active_users)} users about {message['type']} on {content_id}")
    
    async def _notify_workspace_members(self, workspace_id: str, message: Dict[str, Any]):
        """Notify workspace members about updates."""
        # Mock notification
        print(f"Notifying workspace {workspace_id} members about {message['type']}")


# Global instance
_collaboration_service = None

def get_collaboration_service() -> CollaborationService:
    """Get or create the collaboration service singleton."""
    global _collaboration_service
    if _collaboration_service is None:
        _collaboration_service = CollaborationService()
    return _collaboration_service