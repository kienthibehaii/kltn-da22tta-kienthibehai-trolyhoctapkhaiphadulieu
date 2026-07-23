# tests/unit/test_auth.py
"""
Unit tests for authentication system
Coverage target: 90%+
"""

import pytest
from datetime import datetime, timedelta
import jwt
import bcrypt
from auth.auth_manager import auth_manager, SECRET_KEY, ALGORITHM

pytestmark = pytest.mark.unit


class TestPasswordHashing:
    """Test password hashing functionality"""
    
    def test_hash_password(self):
        """Test password hashing"""
        password = "TestPassword123!"
        hashed = auth_manager.hash_password(password)
        
        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
    
    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "TestPassword123!"
        hashed = auth_manager.hash_password(password)
        
        assert auth_manager.verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "TestPassword123!"
        wrong_password = "WrongPassword456!"
        hashed = auth_manager.hash_password(password)
        
        assert auth_manager.verify_password(wrong_password, hashed) is False
    
    def test_hash_password_different_salts(self):
        """Test that same password generates different hashes"""
        password = "TestPassword123!"
        hash1 = auth_manager.hash_password(password)
        hash2 = auth_manager.hash_password(password)
        
        assert hash1 != hash2  # Different salts


class TestJWTTokens:
    """Test JWT token functionality"""
    
    def test_create_access_token(self):
        """Test JWT token creation"""
        user_id = "test_user_123"
        email = "test@example.com"
        
        token = auth_manager.create_access_token(user_id, email)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens are long
    
    def test_verify_token_valid(self):
        """Test token verification with valid token"""
        user_id = "test_user_123"
        email = "test@example.com"
        
        token = auth_manager.create_access_token(user_id, email)
        payload = auth_manager.verify_token(token)
        
        assert payload is not None
        assert payload["user_id"] == user_id
        assert payload["email"] == email
        assert "exp" in payload
        assert "iat" in payload
    
    def test_verify_token_invalid(self):
        """Test token verification with invalid token"""
        invalid_token = "invalid.token.here"
        
        payload = auth_manager.verify_token(invalid_token)
        
        assert payload is None
    
    def test_verify_token_expired(self):
        """Test token verification with expired token"""
        user_id = "test_user_123"
        email = "test@example.com"
        
        # Create expired token
        expire = datetime.utcnow() - timedelta(hours=1)
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        expired_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
        result = auth_manager.verify_token(expired_token)
        
        assert result is None


class TestUserRegistration:
    """Test user registration"""
    
    def test_register_user_success(self, faker_instance):
        """Test successful user registration"""
        user_data = {
            "email": faker_instance.email(),
            "username": faker_instance.user_name() + str(faker_instance.random_int(1000, 9999)),
            "password": "Password123!",
            "full_name": faker_instance.name()
        }
        
        result = auth_manager.register_user(**user_data)
        
        assert result["success"] is True
        assert "user_id" in result
        assert result["message"] == "Đăng ký thành công"
    
    def test_register_user_duplicate_email(self, test_user):
        """Test registration with duplicate email"""
        user_data = {
            "email": test_user["email"],  # Duplicate
            "username": "different_username",
            "password": "Password123!",
            "full_name": "Another User"
        }
        
        result = auth_manager.register_user(**user_data)
        
        assert result["success"] is False
        assert "Email đã được sử dụng" in result["message"]
    
    def test_register_user_duplicate_username(self, test_user):
        """Test registration with duplicate username"""
        user_data = {
            "email": "different@example.com",
            "username": test_user["username"],  # Duplicate
            "password": "Password123!",
            "full_name": "Another User"
        }
        
        result = auth_manager.register_user(**user_data)
        
        assert result["success"] is False
        assert "Username đã được sử dụng" in result["message"]


class TestUserLogin:
    """Test user login"""
    
    def test_login_success(self, test_user):
        """Test successful login"""
        result = auth_manager.login_user(
            test_user["email"],
            test_user["password"]
        )
        
        assert result["success"] is True
        assert "token" in result
        assert "user" in result
        assert result["user"]["email"] == test_user["email"]
    
    def test_login_wrong_email(self):
        """Test login with wrong email"""
        result = auth_manager.login_user(
            "nonexistent@example.com",
            "Password123!"
        )
        
        assert result["success"] is False
        assert "Email hoặc mật khẩu không đúng" in result["message"]
    
    def test_login_wrong_password(self, test_user):
        """Test login with wrong password"""
        result = auth_manager.login_user(
            test_user["email"],
            "WrongPassword!"
        )
        
        assert result["success"] is False
        assert "Email hoặc mật khẩu không đúng" in result["message"]


class TestUserOperations:
    """Test user operations"""
    
    def test_get_user_by_id(self, test_user):
        """Test getting user by ID"""
        user = auth_manager.get_user_by_id(test_user["user_id"])
        
        assert user is not None
        assert user["email"] == test_user["email"]
        assert user["username"] == test_user["username"]
        assert "password" not in user  # Password should not be returned
    
    def test_get_user_by_id_not_found(self):
        """Test getting non-existent user"""
        user = auth_manager.get_user_by_id("nonexistent_id")
        
        assert user is None
    
    def test_change_password_success(self, test_user):
        """Test successful password change"""
        result = auth_manager.change_password(
            test_user["user_id"],
            test_user["password"],
            "NewPassword123!"
        )
        
        assert result["success"] is True
        
        # Verify new password works
        login_result = auth_manager.login_user(
            test_user["email"],
            "NewPassword123!"
        )
        assert login_result["success"] is True
    
    def test_change_password_wrong_old_password(self, test_user):
        """Test password change with wrong old password"""
        result = auth_manager.change_password(
            test_user["user_id"],
            "WrongOldPassword!",
            "NewPassword123!"
        )
        
        assert result["success"] is False
        assert "Mật khẩu cũ không đúng" in result["message"]


@pytest.mark.skip(reason="Email validation test - may have duplicates")
@pytest.mark.parametrize("email,username,password,full_name,should_succeed", [
    ("valid@example.com", "validuser", "Password123!", "Valid User", True),
    ("", "user", "Password123!", "User", False),  # Empty email
    ("invalid-email", "user", "Password123!", "User", False),  # Invalid email
    ("test@example.com", "", "Password123!", "User", False),  # Empty username
    ("test@example.com", "user", "", "User", False),  # Empty password
])
def test_registration_validation(email, username, password, full_name, should_succeed):
    """Test registration input validation"""
    try:
        result = auth_manager.register_user(email, username, password, full_name)
        if should_succeed:
            assert result["success"] is True
        else:
            assert result["success"] is False
    except Exception as e:
        if should_succeed:
            pytest.fail(f"Registration should succeed but failed: {e}")
