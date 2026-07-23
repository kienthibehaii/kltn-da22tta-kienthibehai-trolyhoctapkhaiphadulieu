# auth/api_routes.py - API Routes for Auth & Chat History
"""
FastAPI routes for:
- Authentication (register, login, logout)
- User profile
- Chat history management
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from .auth_manager import auth_manager
from .chat_history_manager import chat_history_manager

router = APIRouter()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class GoogleAuthRequest(BaseModel):
    id_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Conversation"


class AddMessageRequest(BaseModel):
    conversation_id: str
    role: str  # "user" or "assistant"
    content: str
    metadata: Optional[dict] = None


class UpdateConversationTitleRequest(BaseModel):
    title: str


# ============================================================================
# AUTHENTICATION DEPENDENCY
# ============================================================================

def get_current_user(authorization: Optional[str] = Header(None)):
    """Verify JWT token and return user info"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Extract token from "Bearer <token>"
        token = authorization.split(" ")[1] if " " in authorization else authorization
        
        # Verify token
        payload = auth_manager.verify_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@router.post("/auth/register")
async def register(request: RegisterRequest):
    """Register new user"""
    result = auth_manager.register_user(
        email=request.email,
        username=request.username,
        password=request.password,
        full_name=request.full_name
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.post("/auth/google")
async def google_login(request: GoogleAuthRequest):
    """Login or register with Google OAuth2"""
    result = auth_manager.google_login(
        id_token=request.id_token
    )

    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])

    return result


@router.post("/auth/login")
async def login(request: LoginRequest):
    """Login user"""
    result = auth_manager.login_user(
        email=request.email,
        password=request.password
    )
    
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])
    
    return result


@router.get("/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    user = auth_manager.get_user_by_id(current_user["user_id"])
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.post("/auth/heartbeat")
async def heartbeat(current_user: dict = Depends(get_current_user)):
    """Update last_seen while the user is actively using the app."""
    updated = auth_manager.touch_last_seen(current_user["user_id"])
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True}


@router.post("/auth/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """Change user password"""
    result = auth_manager.change_password(
        user_id=current_user["user_id"],
        old_password=request.old_password,
        new_password=request.new_password
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


# ============================================================================
# USER STATS & TOPICS ROUTES
# ============================================================================

@router.get("/user/weak-topics")
async def get_weak_topics(current_user: dict = Depends(get_current_user)):
    """Get weak topics based on user interaction"""
    topics = auth_manager.get_weak_topics(current_user["user_id"])
    return {
        "success": True,
        "weak_topics": topics
    }

@router.get("/user/completed-topics")
async def get_completed_topics(current_user: dict = Depends(get_current_user)):
    """Get topics the user has already practiced"""
    topics = auth_manager.get_completed_topics(current_user["user_id"])
    return {
        "success": True,
        "completed_topics": topics
    }


# ============================================================================
# CHAT HISTORY ROUTES
# ============================================================================

@router.post("/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create new conversation"""
    conversation_id = chat_history_manager.create_conversation(
        user_id=current_user["user_id"],
        title=request.title
    )
    
    return {
        "success": True,
        "conversation_id": conversation_id,
        "message": "Conversation created"
    }


@router.get("/conversations")
async def get_conversations(
    limit: int = 50,
    skip: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get user's conversations"""
    conversations = chat_history_manager.get_user_conversations(
        user_id=current_user["user_id"],
        limit=limit,
        skip=skip
    )
    
    return {
        "success": True,
        "conversations": conversations,
        "count": len(conversations)
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get conversation details"""
    conversation = chat_history_manager.get_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Check ownership
    if conversation["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "success": True,
        "conversation": conversation
    }


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """Get conversation messages"""
    # Verify ownership
    conversation = chat_history_manager.get_conversation(conversation_id)
    if not conversation or conversation["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    messages = chat_history_manager.get_conversation_messages(
        conversation_id=conversation_id,
        limit=limit
    )
    
    return {
        "success": True,
        "messages": messages,
        "count": len(messages)
    }


@router.post("/conversations/{conversation_id}/messages")
async def add_message(
    conversation_id: str,
    request: AddMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add message to conversation"""
    # Verify ownership
    conversation = chat_history_manager.get_conversation(conversation_id)
    if not conversation or conversation["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    message_id = chat_history_manager.add_message(
        conversation_id=conversation_id,
        role=request.role,
        content=request.content,
        metadata=request.metadata
    )
    
    return {
        "success": True,
        "message_id": message_id
    }


@router.put("/conversations/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: str,
    request: UpdateConversationTitleRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update conversation title"""
    # Verify ownership
    conversation = chat_history_manager.get_conversation(conversation_id)
    if not conversation or conversation["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    success = chat_history_manager.update_conversation_title(
        conversation_id=conversation_id,
        title=request.title
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update title")
    
    return {
        "success": True,
        "message": "Title updated"
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete conversation"""
    # Verify ownership
    conversation = chat_history_manager.get_conversation(conversation_id)
    if not conversation or conversation["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    success = chat_history_manager.delete_conversation(conversation_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete conversation")
    
    return {
        "success": True,
        "message": "Conversation deleted"
    }


@router.delete("/conversations/{conversation_id}/messages")
async def clear_conversation_messages(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Clear all messages in a conversation while keeping the conversation."""
    conversation = chat_history_manager.get_conversation(conversation_id)
    if not conversation or conversation["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    success = chat_history_manager.clear_conversation_messages(conversation_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to clear conversation messages")

    return {
        "success": True,
        "message": "Conversation messages cleared"
    }


@router.get("/conversations/search")
async def search_conversations(
    q: str,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Search conversations"""
    conversations = chat_history_manager.search_conversations(
        user_id=current_user["user_id"],
        query=q,
        limit=limit
    )
    
    return {
        "success": True,
        "conversations": conversations,
        "count": len(conversations)
    }


@router.get("/stats")
async def get_user_stats(current_user: dict = Depends(get_current_user)):
    """Get user statistics"""
    stats = chat_history_manager.get_conversation_stats(current_user["user_id"])
    
    return {
        "success": True,
        "stats": stats
    }
