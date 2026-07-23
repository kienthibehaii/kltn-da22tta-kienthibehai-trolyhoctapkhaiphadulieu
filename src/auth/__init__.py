# auth/__init__.py
"""
Authentication & Chat History Module

Provides:
- User authentication (register, login, JWT)
- Chat history management
- API routes for auth & chat
"""

from .auth_manager import auth_manager, AuthManager
from .chat_history_manager import chat_history_manager, ChatHistoryManager
from .api_routes import router as auth_router

__all__ = [
    "auth_manager",
    "AuthManager",
    "chat_history_manager",
    "ChatHistoryManager",
    "auth_router"
]
