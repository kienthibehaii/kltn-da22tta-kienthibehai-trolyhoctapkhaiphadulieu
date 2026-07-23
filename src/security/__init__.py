# security/__init__.py - Security Module
"""
RAG Security System

Modules:
- auth: Authentication and authorization (JWT, sessions, RBAC)
- encryption: Data encryption utilities
- rate_limiter: API rate limiting
- security_logger: Security event logging
- middleware: Security middleware
"""

from .auth import AuthManager, require_auth, get_current_user
from .encryption import EncryptionManager
from .rate_limiter import RateLimiter
from .security_logger import SecurityLogger

__all__ = [
    'AuthManager',
    'require_auth',
    'get_current_user',
    'EncryptionManager',
    'RateLimiter',
    'SecurityLogger'
]

__version__ = '1.0.0'
