"""
Collaboration API - Real-time sharing, comments, and team workspaces.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.api.deps import require_api_key
from app.services.collaboration import get_collaboration_service, ShareType, SharePermission


class CreateShareLinkRequest(BaseModel):
    """Request to create a share link."""
    content_type: str
    content_id: str
    permission: str
    expires_hours: Optional[int] = None


class AddCommentRequest(BaseModel):
    """Request to add a comment."""
    content: str
    parent_comment_id: Optional[str] = None


class CreateWorkspaceRequest(BaseModel):
    """Request to create a workspace."""
    name: str
    description: str
    initial_members: List[str] = []


class AddToWorkspaceRequest(BaseModel):
    """Request to add document to workspace."""
    doc_id: str


router = APIRouter(prefix="/collaborate", tags=["collaboration"])


@router.post("/share")
async def create_share_link(
    request: CreateShareLinkRequest,
    user_id: str = Query("demo_user"),
    api_key: str = Depends(require_api_key)
):
    """Create a shareable link with specified permissions."""
    collaboration_service = get_collaboration_service()
    
    try:
        # Validate content type
        try:
            content_type = ShareType(request.content_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content type. Options: {[t.value for t in ShareType]}"
            )
        
        # Validate permission
        try:
            permission = SharePermission(request.permission)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid permission. Options: {[p.value for p in SharePermission]}"
            )
        
        # Create share link
        share_link = await collaboration_service.create_share_link(
            content_type=content_type,
            content_id=request.content_id,
            permission=permission,
            user_id=user_id,
            expires_hours=request.expires_hours
        )
        
        return {
            "share_link": {
                "share_id": share_link.share_id,
                "url": f"/shared/{share_link.share_id}",
                "content_type": share_link.content_type.value,
                "permission": share_link.permission.value,
                "expires_at": share_link.expires_at,
                "created_at": share_link.created_at
            },
            "sharing_info": {
                "shareable_url": f"https://your-domain.com/shared/{share_link.share_id}",
                "qr_code_available": True,
                "embed_code_available": True
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create share link: {str(e)}")


@router.get("/shared/{share_id}")
async def access_shared_content(
    share_id: str,
    user_id: Optional[str] = Query(None),
    api_key: str = Depends(require_api_key)
):
    """Access shared content via share link."""
    collaboration_service = get_collaboration_service()
    
    result = await collaboration_service.access_shared_content(share_id, user_id)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.post("/comments/{content_id}")
async def add_comment(
    content_id: str,
    request: AddCommentRequest,
    user_id: str = Query("demo_user"),
    api_key: str = Depends(require_api_key)
):
    """Add a comment to shared content."""
    collaboration_service = get_collaboration_service()
    
    try:
        comment = await collaboration_service.add_comment(
            content_id=content_id,
            user_id=user_id,
            content=request.content,
            parent_comment_id=request.parent_comment_id
        )
        
        return {
            "comment": {
                "comment_id": comment.comment_id,
                "user_id": comment.user_id,
                "content": comment.content,
                "created_at": comment.created_at,
                "parent_comment_id": comment.parent_comment_id
            },
            "status": "added"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add comment: {str(e)}")


@router.get("/comments/{content_id}")
async def get_comments(
    content_id: str,
    api_key: str = Depends(require_api_key)
):
    """Get all comments for content."""
    collaboration_service = get_collaboration_service()
    
    comments = await collaboration_service.get_comments(content_id)
    
    return {
        "content_id": content_id,
        "comments": [
            {
                "comment_id": c.comment_id,
                "user_id": c.user_id,
                "content": c.content,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
                "parent_comment_id": c.parent_comment_id,
                "reactions": c.reactions
            }
            for c in comments
        ],
        "comment_count": len(comments)
    }


@router.post("/workspaces")
async def create_workspace(
    request: CreateWorkspaceRequest,
    created_by: str = Query("demo_user"),
    api_key: str = Depends(require_api_key)
):
    """Create a new team workspace."""
    collaboration_service = get_collaboration_service()
    
    try:
        workspace = await collaboration_service.create_workspace(
            name=request.name,
            description=request.description,
            created_by=created_by,
            initial_members=request.initial_members
        )
        
        return {
            "workspace": {
                "workspace_id": workspace.workspace_id,
                "name": workspace.name,
                "description": workspace.description,
                "created_by": workspace.created_by,
                "member_count": len(workspace.members),
                "created_at": workspace.created_at
            },
            "join_link": f"/workspaces/{workspace.workspace_id}/join",
            "status": "created"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create workspace: {str(e)}")


@router.post("/workspaces/{workspace_id}/documents")
async def add_document_to_workspace(
    workspace_id: str,
    request: AddToWorkspaceRequest,
    user_id: str = Query("demo_user"),
    api_key: str = Depends(require_api_key)
):
    """Add a document to a workspace."""
    collaboration_service = get_collaboration_service()
    
    success = await collaboration_service.add_document_to_workspace(
        workspace_id=workspace_id,
        doc_id=request.doc_id,
        user_id=user_id
    )
    
    if not success:
        raise HTTPException(status_code=403, detail="Permission denied or workspace not found")
    
    return {
        "status": "added",
        "workspace_id": workspace_id,
        "doc_id": request.doc_id
    }


@router.get("/workspaces/{workspace_id}/activity")
async def get_workspace_activity(
    workspace_id: str,
    api_key: str = Depends(require_api_key)
):
    """Get recent activity in a workspace."""
    collaboration_service = get_collaboration_service()
    
    activity = await collaboration_service.get_workspace_activity(workspace_id)
    
    if "error" in activity:
        raise HTTPException(status_code=404, detail=activity["error"])
    
    return activity


@router.get("/stats")
async def get_collaboration_stats(
    api_key: str = Depends(require_api_key)
):
    """Get overall collaboration statistics."""
    collaboration_service = get_collaboration_service()
    
    stats = await collaboration_service.get_collaboration_stats()
    
    return stats


@router.get("/share-options/{content_type}")
async def get_share_options(
    content_type: str,
    api_key: str = Depends(require_api_key)
):
    """Get available sharing options for a content type."""
    try:
        ShareType(content_type)  # Validate content type
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content type. Options: {[t.value for t in ShareType]}"
        )
    
    return {
        "content_type": content_type,
        "permissions": [
            {
                "level": "read",
                "name": "View Only",
                "description": "Can view content but not comment or edit"
            },
            {
                "level": "comment",
                "name": "Can Comment",
                "description": "Can view and add comments to content"
            },
            {
                "level": "edit",
                "name": "Can Edit",
                "description": "Can view, comment, and make changes to content"
            },
            {
                "level": "admin",
                "name": "Full Access",
                "description": "Complete control including sharing and deletion"
            }
        ],
        "expiry_options": [
            {"hours": 1, "label": "1 hour"},
            {"hours": 24, "label": "1 day"},
            {"hours": 168, "label": "1 week"},
            {"hours": 720, "label": "1 month"},
            {"hours": None, "label": "Never expires"}
        ],
        "sharing_features": {
            "password_protection": True,
            "download_control": True,
            "access_analytics": True,
            "notification_settings": True
        }
    }


@router.post("/demo")
async def demo_collaboration_features(
    api_key: str = Depends(require_api_key)
):
    """Demonstrate collaboration features with sample data."""
    collaboration_service = get_collaboration_service()
    
    try:
        # Create demo workspace
        demo_workspace = await collaboration_service.create_workspace(
            name="Demo Team Workspace",
            description="Demonstration workspace showcasing collaboration features",
            created_by="demo_admin",
            initial_members=["demo_user1", "demo_user2"]
        )
        
        # Create demo share link
        demo_share = await collaboration_service.create_share_link(
            content_type=ShareType.ANALYSIS,
            content_id="demo_analysis_123",
            permission=SharePermission.COMMENT,
            user_id="demo_admin",
            expires_hours=24
        )
        
        # Add demo comments
        demo_comment = await collaboration_service.add_comment(
            content_id="demo_analysis_123",
            user_id="demo_user1",
            content="This analysis looks great! The insights are very actionable."
        )
        
        return {
            "demo_results": {
                "workspace_created": {
                    "workspace_id": demo_workspace.workspace_id,
                    "name": demo_workspace.name,
                    "members": len(demo_workspace.members)
                },
                "share_link_created": {
                    "share_id": demo_share.share_id,
                    "shareable_url": f"/shared/{demo_share.share_id}",
                    "permission": demo_share.permission.value
                },
                "comment_added": {
                    "comment_id": demo_comment.comment_id,
                    "content_preview": demo_comment.content[:50] + "..."
                }
            },
            "features_demonstrated": [
                "Workspace creation and management",
                "Secure link sharing with permissions",
                "Real-time commenting system",
                "Team collaboration workflows"
            ],
            "next_steps": [
                "Try accessing the demo share link",
                "Add more comments to see threading",
                "Explore workspace activity feeds",
                "Test different permission levels"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Demo failed: {str(e)}")