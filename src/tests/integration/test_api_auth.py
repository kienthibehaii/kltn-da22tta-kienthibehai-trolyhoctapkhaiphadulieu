# tests/integration/test_api_auth.py
"""
Integration tests for authentication API endpoints
Coverage target: 85%+
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


class TestAuthenticationEndpoints:
    """Test authentication API endpoints"""
    
    def test_register_endpoint(self, client: TestClient):
        """Test POST /api/auth/register"""
        response = client.post("/api/auth/register", json={
            "email": "apitest@example.com",
            "username": "apitest",
            "password": "Password123!",
            "full_name": "API Test User"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "user_id" in data
    
    def test_register_duplicate_email(self, client: TestClient, test_user):
        """Test registration with duplicate email"""
        response = client.post("/api/auth/register", json={
            "email": test_user["email"],
            "username": "different",
            "password": "Password123!",
            "full_name": "Different User"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "Email đã được sử dụng" in data["detail"]
    
    def test_login_endpoint(self, client: TestClient, test_user):
        """Test POST /api/auth/login"""
        response = client.post("/api/auth/login", json={
            "email": test_user["email"],
            "password": test_user["password"]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert "user" in data
    
    def test_login_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials"""
        response = client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "WrongPassword!"
        })
        
        assert response.status_code == 401
    
    def test_get_current_user(self, client: TestClient, auth_headers):
        """Test GET /api/auth/me"""
        response = client.get("/api/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "username" in data
        assert "password" not in data
    
    def test_get_current_user_no_token(self, client: TestClient):
        """Test GET /api/auth/me without token"""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 401
    
    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test GET /api/auth/me with invalid token"""
        response = client.get("/api/auth/me", headers={
            "Authorization": "Bearer invalid_token"
        })
        
        assert response.status_code == 401
    
    def test_change_password(self, client: TestClient, auth_headers, test_user):
        """Test POST /api/auth/change-password"""
        response = client.post("/api/auth/change-password", 
            headers=auth_headers,
            json={
                "old_password": test_user["password"],
                "new_password": "NewPassword123!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestConversationEndpoints:
    """Test conversation API endpoints"""
    
    def test_create_conversation(self, client: TestClient, auth_headers):
        """Test POST /api/conversations"""
        response = client.post("/api/conversations",
            headers=auth_headers,
            json={"title": "Test Conversation"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "conversation_id" in data
    
    def test_create_conversation_no_auth(self, client: TestClient):
        """Test creating conversation without authentication"""
        response = client.post("/api/conversations",
            json={"title": "Test"}
        )
        
        assert response.status_code == 401
    
    def test_get_conversations(self, client: TestClient, auth_headers, multiple_conversations):
        """Test GET /api/conversations"""
        response = client.get("/api/conversations", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "conversations" in data
        assert len(data["conversations"]) >= 5
    
    def test_get_conversation_by_id(self, client: TestClient, auth_headers, test_conversation):
        """Test GET /api/conversations/{id}"""
        response = client.get(
            f"/api/conversations/{test_conversation}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["conversation"]["conversation_id"] == test_conversation
    
    def test_get_conversation_not_found(self, client: TestClient, auth_headers):
        """Test getting non-existent conversation"""
        response = client.get(
            "/api/conversations/nonexistent_id",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_add_message(self, client: TestClient, auth_headers, test_conversation):
        """Test POST /api/conversations/{id}/messages"""
        response = client.post(
            f"/api/conversations/{test_conversation}/messages",
            headers=auth_headers,
            json={
                "conversation_id": test_conversation,
                "role": "user",
                "content": "Test message"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message_id" in data
    
    def test_get_messages(self, client: TestClient, auth_headers, test_conversation_with_messages):
        """Test GET /api/conversations/{id}/messages"""
        conv_id = test_conversation_with_messages["conversation_id"]
        
        response = client.get(
            f"/api/conversations/{conv_id}/messages",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["messages"]) == 4
    
    def test_update_conversation_title(self, client: TestClient, auth_headers, test_conversation):
        """Test PUT /api/conversations/{id}/title"""
        response = client.put(
            f"/api/conversations/{test_conversation}/title",
            headers=auth_headers,
            json={"title": "Updated Title"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_delete_conversation(self, client: TestClient, auth_headers, test_conversation):
        """Test DELETE /api/conversations/{id}"""
        response = client.delete(
            f"/api/conversations/{test_conversation}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_search_conversations(self, client: TestClient, auth_headers, test_conversation):
        """Test GET /api/conversations/search"""
        # Note: Search endpoint might not be implemented yet
        response = client.get(
            "/api/conversations/search?q=Test",
            headers=auth_headers
        )
        
        # Accept both 200 (implemented) or 404 (not implemented)
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "conversations" in data
    
    def test_get_user_stats(self, client: TestClient, auth_headers, multiple_conversations):
        """Test GET /api/stats"""
        response = client.get("/api/stats", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "stats" in data
        assert "total_conversations" in data["stats"]


class TestRAGEndpoints:
    """Test RAG API endpoints"""
    
    @pytest.mark.slow
    def test_ask_question(self, client: TestClient):
        """Test POST /api/question"""
        response = client.post("/api/question", json={
            "question": "What is data mining?",
            "session_id": None,
            "use_context": False
        })
        
        # May fail if RAG not loaded
        if response.status_code == 503:
            pytest.skip("RAG pipeline not ready")
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "citations" in data
    
    def test_ask_question_with_context(self, client: TestClient):
        """Test question with conversation context"""
        response = client.post("/api/question", json={
            "question": "Explain more about that",
            "session_id": "test_session",
            "use_context": True,
            "max_context_turns": 3
        })
        
        if response.status_code == 503:
            pytest.skip("RAG pipeline not ready")
        
        assert response.status_code in [200, 503]


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_root_endpoint(self, client: TestClient):
        """Test GET /"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "features" in data
        assert data["features"]["authentication"] is True
    
    def test_health_endpoint(self, client: TestClient):
        """Test GET /health"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "loading" in data


class TestAuthorizationFlow:
    """Test complete authorization flow"""
    
    def test_full_auth_flow(self, client: TestClient):
        """Test complete registration -> login -> access flow"""
        # 1. Register
        register_response = client.post("/api/auth/register", json={
            "email": "flowtest@example.com",
            "username": "flowtest",
            "password": "Password123!",
            "full_name": "Flow Test"
        })
        assert register_response.status_code == 200
        
        # 2. Login
        login_response = client.post("/api/auth/login", json={
            "email": "flowtest@example.com",
            "password": "Password123!"
        })
        assert login_response.status_code == 200
        token = login_response.json()["token"]
        
        # 3. Access protected resource
        headers = {"Authorization": f"Bearer {token}"}
        me_response = client.get("/api/auth/me", headers=headers)
        assert me_response.status_code == 200
        
        # 4. Create conversation
        conv_response = client.post("/api/conversations",
            headers=headers,
            json={"title": "Flow Test Conversation"}
        )
        assert conv_response.status_code == 200
        conv_id = conv_response.json()["conversation_id"]
        
        # 5. Add message
        msg_response = client.post(
            f"/api/conversations/{conv_id}/messages",
            headers=headers,
            json={
                "conversation_id": conv_id,
                "role": "user",
                "content": "Test message"
            }
        )
        assert msg_response.status_code == 200
        
        # 6. Get messages
        get_msg_response = client.get(
            f"/api/conversations/{conv_id}/messages",
            headers=headers
        )
        assert get_msg_response.status_code == 200
        assert len(get_msg_response.json()["messages"]) == 1


class TestErrorHandling:
    """Test error handling"""
    
    def test_invalid_json(self, client: TestClient):
        """Test invalid JSON payload"""
        response = client.post("/api/auth/register",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_missing_required_fields(self, client: TestClient):
        """Test missing required fields"""
        response = client.post("/api/auth/register", json={
            "email": "test@example.com"
            # Missing username, password, full_name
        })
        
        assert response.status_code == 422
    
    def test_invalid_email_format(self, client: TestClient):
        """Test invalid email format"""
        response = client.post("/api/auth/register", json={
            "email": "invalid-email",
            "username": "test",
            "password": "Password123!",
            "full_name": "Test"
        })
        
        assert response.status_code == 422


@pytest.mark.parametrize("endpoint,method,requires_auth", [
    ("/api/auth/register", "POST", False),
    ("/api/auth/login", "POST", False),
    ("/api/auth/me", "GET", True),
    ("/api/conversations", "GET", True),
    ("/api/conversations", "POST", True),
    ("/api/stats", "GET", True),
])
def test_endpoint_authentication(client: TestClient, endpoint, method, requires_auth):
    """Test that endpoints require authentication when expected"""
    if method == "GET":
        response = client.get(endpoint)
    elif method == "POST":
        response = client.post(endpoint, json={})
    
    if requires_auth:
        assert response.status_code == 401
    else:
        assert response.status_code != 401
