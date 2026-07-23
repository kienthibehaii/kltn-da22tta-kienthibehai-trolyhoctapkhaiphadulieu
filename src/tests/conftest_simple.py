# tests/conftest_simple.py
"""Simple pytest fixtures"""

import pytest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from backend_api import app
from auth.auth_manager import auth_manager
from auth.chat_history_manager import chat_history_manager
from faker import Faker

fake = Faker()

@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)

@pytest.fixture
def test_user_data():
    """Generate test user data"""
    return {
        "email": fake.email(),
        "username": fake.user_name(),
        "password": "TestPassword123!",
        "full_name": fake.name()
    }

@pytest.fixture
def test_user(test_user_data):
    """Create test user"""
    result = auth_manager.register_user(**test_user_data)
    if result["success"]:
        return {
            **test_user_data,
            "user_id": result["user_id"]
        }
    return None

@pytest.fixture
def test_user_token(test_user):
    """Get JWT token"""
    if not test_user:
        return None
    result = auth_manager.login_user(test_user["email"], test_user["password"])
    if result["success"]:
        return result["token"]
    return None

@pytest.fixture
def auth_headers(test_user_token):
    """Authorization headers"""
    if not test_user_token:
        return {}
    return {"Authorization": f"Bearer {test_user_token}"}

@pytest.fixture
def test_conversation(test_user):
    """Create test conversation"""
    if not test_user:
        return None
    return chat_history_manager.create_conversation(
        user_id=test_user["user_id"],
        title="Test Conversation"
    )

@pytest.fixture
def test_conversation_with_messages(test_user, test_conversation):
    """Conversation with messages"""
    if not test_user or not test_conversation:
        return None
    
    messages = [
        {"role": "user", "content": "What is data mining?"},
        {"role": "assistant", "content": "Data mining is..."},
        {"role": "user", "content": "Explain classification"},
        {"role": "assistant", "content": "Classification is..."}
    ]
    
    message_ids = []
    for msg in messages:
        msg_id = chat_history_manager.add_message(
            conversation_id=test_conversation,
            role=msg["role"],
            content=msg["content"]
        )
        message_ids.append(msg_id)
    
    return {
        "conversation_id": test_conversation,
        "message_ids": message_ids,
        "messages": messages
    }

@pytest.fixture
def multiple_conversations(test_user):
    """Create multiple conversations"""
    if not test_user:
        return []
    conversations = []
    for i in range(5):
        conv_id = chat_history_manager.create_conversation(
            user_id=test_user["user_id"],
            title=f"Conversation {i+1}"
        )
        conversations.append(conv_id)
    return conversations
