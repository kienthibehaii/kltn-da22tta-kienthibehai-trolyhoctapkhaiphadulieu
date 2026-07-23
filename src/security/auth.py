# security/auth.py - Authentication and Authorization
"""
Authentication System

Features:
- User registration and login
- Password hashing (bcrypt)
- JWT token authentication
- Session management
- Role-based access control (RBAC)
- Password strength validation
- Account lockout after failed attempts
"""

import os
import jwt
import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from functools import wraps
import streamlit as st
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()


class AuthManager:
    """
    Authentication and authorization manager.
    """
    
    # User roles
    ROLE_ADMIN = 'admin'
    ROLE_USER = 'user'
    ROLE_GUEST = 'guest'
    
    # Security settings
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION = timedelta(minutes=30)
    SESSION_TIMEOUT = timedelta(hours=24)
    PASSWORD_MIN_LENGTH = 8
    
    def __init__(self):
        """Initialize auth manager"""
        # JWT settings
        self.jwt_secret = os.getenv('JWT_SECRET_KEY', self._generate_secret_key())
        self.jwt_algorithm = 'HS256'
        self.jwt_expiration = timedelta(hours=24)
        
        # MongoDB connection for user storage
        mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        self.mongo_client = MongoClient(mongo_uri)
        self.db = self.mongo_client['rag_system']
        self.users_collection = self.db['users']
        self.sessions_collection = self.db['sessions']
        
        # Create indexes
        self._create_indexes()
        
        print("✅ Auth Manager initialized")
    
    def _generate_secret_key(self) -> str:
        """Generate a secure secret key"""
        return secrets.token_urlsafe(32)
    
    def _create_indexes(self):
        """Create database indexes"""
        try:
            self.users_collection.create_index('username', unique=True)
            self.users_collection.create_index('email', unique=True)
            self.sessions_collection.create_index('token', unique=True)
            self.sessions_collection.create_index('expires_at')
        except Exception as e:
            print(f"⚠️  Index creation warning: {e}")
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def _validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """
        Validate password strength.
        
        Returns:
            (is_valid, error_message)
        """
        if len(password) < self.PASSWORD_MIN_LENGTH:
            return False, f"Password must be at least {self.PASSWORD_MIN_LENGTH} characters"
        
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"
        
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
            return False, "Password must contain at least one special character"
        
        return True, ""
    
    def register_user(self, 
                     username: str, 
                     email: str, 
                     password: str,
                     role: str = ROLE_USER) -> Tuple[bool, str]:
        """
        Register a new user.
        
        Args:
            username: Username
            email: Email address
            password: Password
            role: User role (default: user)
        
        Returns:
            (success, message)
        """
        # Validate inputs
        if not username or not email or not password:
            return False, "All fields are required"
        
        if len(username) < 3:
            return False, "Username must be at least 3 characters"
        
        # Validate password strength
        is_valid, error_msg = self._validate_password_strength(password)
        if not is_valid:
            return False, error_msg
        
        # Check if user exists
        if self.users_collection.find_one({'username': username}):
            return False, "Username already exists"
        
        if self.users_collection.find_one({'email': email}):
            return False, "Email already exists"
        
        # Hash password
        password_hash = self._hash_password(password)
        
        # Create user
        user = {
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'role': role,
            'created_at': datetime.utcnow(),
            'last_login': None,
            'failed_login_attempts': 0,
            'locked_until': None,
            'is_active': True
        }
        
        try:
            self.users_collection.insert_one(user)
            return True, "User registered successfully"
        except Exception as e:
            return False, f"Registration failed: {str(e)}"
    
    def login(self, username: str, password: str) -> Tuple[bool, str, Optional[str]]:
        """
        Login user.
        
        Args:
            username: Username
            password: Password
        
        Returns:
            (success, message, token)
        """
        # Find user
        user = self.users_collection.find_one({'username': username})
        
        if not user:
            return False, "Invalid username or password", None
        
        # Check if account is locked
        if user.get('locked_until'):
            if datetime.utcnow() < user['locked_until']:
                remaining = (user['locked_until'] - datetime.utcnow()).seconds // 60
                return False, f"Account locked. Try again in {remaining} minutes", None
            else:
                # Unlock account
                self.users_collection.update_one(
                    {'_id': user['_id']},
                    {'$set': {'locked_until': None, 'failed_login_attempts': 0}}
                )
        
        # Check if account is active
        if not user.get('is_active', True):
            return False, "Account is disabled", None
        
        # Verify password
        if not self._verify_password(password, user['password_hash']):
            # Increment failed attempts
            failed_attempts = user.get('failed_login_attempts', 0) + 1
            
            update_data = {'failed_login_attempts': failed_attempts}
            
            # Lock account if too many failed attempts
            if failed_attempts >= self.MAX_LOGIN_ATTEMPTS:
                update_data['locked_until'] = datetime.utcnow() + self.LOCKOUT_DURATION
                self.users_collection.update_one({'_id': user['_id']}, {'$set': update_data})
                return False, f"Too many failed attempts. Account locked for {self.LOCKOUT_DURATION.seconds // 60} minutes", None
            
            self.users_collection.update_one({'_id': user['_id']}, {'$set': update_data})
            return False, "Invalid username or password", None
        
        # Reset failed attempts
        self.users_collection.update_one(
            {'_id': user['_id']},
            {'$set': {
                'failed_login_attempts': 0,
                'last_login': datetime.utcnow()
            }}
        )
        
        # Generate JWT token
        token = self._generate_token(user)
        
        # Create session
        self._create_session(user, token)
        
        return True, "Login successful", token
    
    def _generate_token(self, user: Dict) -> str:
        """Generate JWT token"""
        payload = {
            'user_id': str(user['_id']),
            'username': user['username'],
            'role': user['role'],
            'exp': datetime.utcnow() + self.jwt_expiration,
            'iat': datetime.utcnow()
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        return token
    
    def _create_session(self, user: Dict, token: str):
        """Create user session"""
        session = {
            'user_id': str(user['_id']),
            'username': user['username'],
            'token': token,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + self.SESSION_TIMEOUT,
            'is_active': True
        }
        
        self.sessions_collection.insert_one(session)
    
    def verify_token(self, token: str) -> Tuple[bool, Optional[Dict]]:
        """
        Verify JWT token.
        
        Returns:
            (is_valid, payload)
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Check if session exists and is active
            session = self.sessions_collection.find_one({
                'token': token,
                'is_active': True
            })
            
            if not session:
                return False, None
            
            # Check if session expired
            if datetime.utcnow() > session['expires_at']:
                self._invalidate_session(token)
                return False, None
            
            return True, payload
        
        except jwt.ExpiredSignatureError:
            return False, None
        except jwt.InvalidTokenError:
            return False, None
    
    def logout(self, token: str) -> bool:
        """Logout user by invalidating session"""
        return self._invalidate_session(token)
    
    def _invalidate_session(self, token: str) -> bool:
        """Invalidate session"""
        result = self.sessions_collection.update_one(
            {'token': token},
            {'$set': {'is_active': False}}
        )
        return result.modified_count > 0
    
    def get_user_by_token(self, token: str) -> Optional[Dict]:
        """Get user info from token"""
        is_valid, payload = self.verify_token(token)
        
        if not is_valid:
            return None
        
        user = self.users_collection.find_one({'_id': payload['user_id']})
        
        if user:
            # Remove sensitive data
            user.pop('password_hash', None)
            user['_id'] = str(user['_id'])
        
        return user
    
    def has_permission(self, token: str, required_role: str) -> bool:
        """
        Check if user has required role.
        
        Role hierarchy: admin > user > guest
        """
        is_valid, payload = self.verify_token(token)
        
        if not is_valid:
            return False
        
        user_role = payload.get('role', self.ROLE_GUEST)
        
        # Role hierarchy
        role_levels = {
            self.ROLE_ADMIN: 3,
            self.ROLE_USER: 2,
            self.ROLE_GUEST: 1
        }
        
        user_level = role_levels.get(user_role, 0)
        required_level = role_levels.get(required_role, 0)
        
        return user_level >= required_level
    
    def change_password(self, 
                       username: str, 
                       old_password: str, 
                       new_password: str) -> Tuple[bool, str]:
        """Change user password"""
        # Find user
        user = self.users_collection.find_one({'username': username})
        
        if not user:
            return False, "User not found"
        
        # Verify old password
        if not self._verify_password(old_password, user['password_hash']):
            return False, "Invalid current password"
        
        # Validate new password
        is_valid, error_msg = self._validate_password_strength(new_password)
        if not is_valid:
            return False, error_msg
        
        # Hash new password
        new_password_hash = self._hash_password(new_password)
        
        # Update password
        self.users_collection.update_one(
            {'_id': user['_id']},
            {'$set': {'password_hash': new_password_hash}}
        )
        
        # Invalidate all sessions
        self.sessions_collection.update_many(
            {'user_id': str(user['_id'])},
            {'$set': {'is_active': False}}
        )
        
        return True, "Password changed successfully"


# Streamlit authentication decorators
def require_auth(role: str = AuthManager.ROLE_USER):
    """
    Decorator to require authentication for Streamlit pages.
    
    Usage:
        @require_auth(role=AuthManager.ROLE_USER)
        def my_page():
            st.write("Protected content")
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check if user is authenticated
            if 'auth_token' not in st.session_state:
                st.error("🔒 Please login to access this page")
                st.stop()
            
            # Verify token
            auth_manager = AuthManager()
            is_valid, payload = auth_manager.verify_token(st.session_state['auth_token'])
            
            if not is_valid:
                st.error("🔒 Session expired. Please login again")
                del st.session_state['auth_token']
                st.stop()
            
            # Check role
            if not auth_manager.has_permission(st.session_state['auth_token'], role):
                st.error("🔒 Insufficient permissions")
                st.stop()
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def get_current_user() -> Optional[Dict]:
    """Get current authenticated user"""
    if 'auth_token' not in st.session_state:
        return None
    
    auth_manager = AuthManager()
    return auth_manager.get_user_by_token(st.session_state['auth_token'])


# Test code
if __name__ == "__main__":
    print("="*60)
    print("TESTING AUTH MANAGER")
    print("="*60)
    
    auth = AuthManager()
    
    # Test registration
    print("\n# Test Registration")
    success, msg = auth.register_user(
        username="testuser",
        email="test@example.com",
        password="Test@123456",
        role=AuthManager.ROLE_USER
    )
    print(f"Registration: {msg}")
    
    # Test login
    print("\n# Test Login")
    success, msg, token = auth.login("testuser", "Test@123456")
    print(f"Login: {msg}")
    if token:
        print(f"Token: {token[:50]}...")
    
    # Test token verification
    if token:
        print("\n# Test Token Verification")
        is_valid, payload = auth.verify_token(token)
        print(f"Token valid: {is_valid}")
        if payload:
            print(f"User: {payload['username']}, Role: {payload['role']}")
    
    # Test permission check
    if token:
        print("\n# Test Permission Check")
        has_perm = auth.has_permission(token, AuthManager.ROLE_USER)
        print(f"Has USER permission: {has_perm}")
        has_admin = auth.has_permission(token, AuthManager.ROLE_ADMIN)
        print(f"Has ADMIN permission: {has_admin}")
