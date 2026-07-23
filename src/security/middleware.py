# security/middleware.py - Security Middleware
"""
Security Middleware

Features:
- Request validation
- CSRF protection
- Security headers
- Input sanitization
- XSS protection
"""

import re
import html
from typing import Optional, Dict, Any
from functools import wraps
import streamlit as st


class SecurityMiddleware:
    """
    Security middleware for request processing.
    """
    
    # Dangerous patterns
    SQL_INJECTION_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(--|\#|\/\*|\*\/)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)"
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>"
    ]
    
    def __init__(self):
        """Initialize security middleware"""
        print("✅ Security Middleware initialized")
    
    def sanitize_input(self, text: str) -> str:
        """
        Sanitize user input.
        
        Args:
            text: Input text
        
        Returns:
            Sanitized text
        """
        if not text:
            return text
        
        # HTML escape
        sanitized = html.escape(text)
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        return sanitized
    
    def validate_input(self, text: str, max_length: int = 10000) -> tuple[bool, str]:
        """
        Validate user input for security threats.
        
        Args:
            text: Input text
            max_length: Maximum allowed length
        
        Returns:
            (is_valid, error_message)
        """
        if not text:
            return True, ""
        
        # Check length
        if len(text) > max_length:
            return False, f"Input too long (max {max_length} characters)"
        
        # Check for SQL injection
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return False, "Potential SQL injection detected"
        
        # Check for XSS
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return False, "Potential XSS attack detected"
        
        return True, ""
    
    def generate_csrf_token(self) -> str:
        """Generate CSRF token"""
        import secrets
        return secrets.token_urlsafe(32)
    
    def verify_csrf_token(self, token: str, expected_token: str) -> bool:
        """Verify CSRF token"""
        return token == expected_token
    
    def add_security_headers(self) -> Dict[str, str]:
        """
        Get security headers.
        
        Returns:
            Dict of security headers
        """
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
        }
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def validate_username(self, username: str) -> tuple[bool, str]:
        """
        Validate username.
        
        Returns:
            (is_valid, error_message)
        """
        if not username:
            return False, "Username is required"
        
        if len(username) < 3:
            return False, "Username must be at least 3 characters"
        
        if len(username) > 50:
            return False, "Username must be at most 50 characters"
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return False, "Username can only contain letters, numbers, underscores, and hyphens"
        
        return True, ""
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to prevent path traversal.
        
        Args:
            filename: Original filename
        
        Returns:
            Sanitized filename
        """
        # Remove path separators
        filename = filename.replace('/', '_').replace('\\', '_')
        
        # Remove parent directory references
        filename = filename.replace('..', '')
        
        # Remove special characters
        filename = re.sub(r'[^\w\s.-]', '', filename)
        
        return filename
    
    def check_file_type(self, filename: str, allowed_extensions: list) -> bool:
        """
        Check if file type is allowed.
        
        Args:
            filename: Filename
            allowed_extensions: List of allowed extensions (e.g., ['.pdf', '.txt'])
        
        Returns:
            True if allowed
        """
        import os
        ext = os.path.splitext(filename)[1].lower()
        return ext in allowed_extensions


def secure_input(middleware: SecurityMiddleware, max_length: int = 10000):
    """
    Decorator for securing input functions.
    
    Usage:
        @secure_input(middleware)
        def process_query(query: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(text: str, *args, **kwargs):
            # Validate input
            is_valid, error_msg = middleware.validate_input(text, max_length)
            
            if not is_valid:
                raise ValueError(f"Invalid input: {error_msg}")
            
            # Sanitize input
            sanitized_text = middleware.sanitize_input(text)
            
            # Call original function with sanitized input
            return func(sanitized_text, *args, **kwargs)
        
        return wrapper
    return decorator


# Streamlit security helpers
def validate_streamlit_input(text: str, middleware: SecurityMiddleware) -> bool:
    """
    Validate Streamlit input and show error if invalid.
    
    Returns:
        True if valid, False if invalid (shows error)
    """
    is_valid, error_msg = middleware.validate_input(text)
    
    if not is_valid:
        st.error(f"⚠️ Security Error: {error_msg}")
        return False
    
    return True


def sanitize_streamlit_input(text: str, middleware: SecurityMiddleware) -> str:
    """Sanitize Streamlit input"""
    return middleware.sanitize_input(text)


# Test code
if __name__ == "__main__":
    print("="*60)
    print("TESTING SECURITY MIDDLEWARE")
    print("="*60)
    
    middleware = SecurityMiddleware()
    
    # Test input validation
    print("\n# Test Input Validation")
    
    test_inputs = [
        ("Normal query", True),
        ("What is data mining?", True),
        ("SELECT * FROM users WHERE id=1 OR 1=1", False),
        ("<script>alert('XSS')</script>", False),
        ("DROP TABLE users;", False),
        ("javascript:alert('XSS')", False),
        ("A" * 10001, False)  # Too long
    ]
    
    for text, expected_valid in test_inputs:
        is_valid, error_msg = middleware.validate_input(text)
        status = "✅" if is_valid == expected_valid else "❌"
        print(f"{status} '{text[:50]}...': {is_valid} {f'({error_msg})' if error_msg else ''}")
    
    # Test input sanitization
    print("\n# Test Input Sanitization")
    
    dangerous_input = "<script>alert('XSS')</script> & <b>bold</b>"
    sanitized = middleware.sanitize_input(dangerous_input)
    print(f"Original: {dangerous_input}")
    print(f"Sanitized: {sanitized}")
    
    # Test email validation
    print("\n# Test Email Validation")
    
    emails = [
        ("test@example.com", True),
        ("user.name+tag@example.co.uk", True),
        ("invalid.email", False),
        ("@example.com", False),
        ("test@", False)
    ]
    
    for email, expected_valid in emails:
        is_valid = middleware.validate_email(email)
        status = "✅" if is_valid == expected_valid else "❌"
        print(f"{status} {email}: {is_valid}")
    
    # Test username validation
    print("\n# Test Username Validation")
    
    usernames = [
        ("validuser", True),
        ("user_123", True),
        ("ab", False),  # Too short
        ("user@name", False),  # Invalid character
        ("a" * 51, False)  # Too long
    ]
    
    for username, expected_valid in usernames:
        is_valid, error_msg = middleware.validate_username(username)
        status = "✅" if is_valid == expected_valid else "❌"
        print(f"{status} {username}: {is_valid} {f'({error_msg})' if error_msg else ''}")
    
    # Test filename sanitization
    print("\n# Test Filename Sanitization")
    
    filenames = [
        "../../etc/passwd",
        "file<script>.txt",
        "normal_file.pdf",
        "file with spaces.doc"
    ]
    
    for filename in filenames:
        sanitized = middleware.sanitize_filename(filename)
        print(f"Original: {filename}")
        print(f"Sanitized: {sanitized}")
        print()
