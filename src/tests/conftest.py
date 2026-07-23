# tests/conftest_simple.py
"""Simple pytest fixtures"""

import pytest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from faker import Faker

fake = Faker()


def _auth_manager():
    from auth.auth_manager import auth_manager
    return auth_manager


def _chat_history_manager():
    from auth.chat_history_manager import chat_history_manager
    return chat_history_manager

@pytest.fixture
def client():
    """FastAPI test client"""
    from fastapi.testclient import TestClient
    from backend_api import app
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

@pytest.fixture(autouse=True)
def cleanup_test_users(request):
    """Clean up any database trace of test users before and after each test"""
    if request.node.path.name == "test_rag_upgrade.py":
        yield
        return

    from auth.auth_manager import auth_manager
    from auth.chat_history_manager import chat_history_manager
    
    test_emails = ["apitest@example.com", "flowtest@example.com"]
    
    # 1. Find all user IDs for test emails
    try:
        test_users = list(auth_manager.users_collection.find({"email": {"$in": test_emails}}))
        test_user_ids = [str(u["_id"]) for u in test_users]
        
        # 2. Find all conversations for these user IDs
        if test_user_ids:
            test_convs = list(chat_history_manager.conversations_collection.find({"user_id": {"$in": test_user_ids}}))
            test_conv_ids = [str(c["_id"]) for c in test_convs]
            
            # 3. Delete messages for these conversations
            if test_conv_ids:
                chat_history_manager.messages_collection.delete_many({"conversation_id": {"$in": test_conv_ids}})
            
            # 4. Delete conversations
            chat_history_manager.conversations_collection.delete_many({"user_id": {"$in": test_user_ids}})
            
        # 5. Delete users
        auth_manager.users_collection.delete_many({"email": {"$in": test_emails}})
    except Exception:
        pass
    
    yield
    
    try:
        # Run the same cleanup after the test
        test_users = list(auth_manager.users_collection.find({"email": {"$in": test_emails}}))
        test_user_ids = [str(u["_id"]) for u in test_users]
        if test_user_ids:
            test_convs = list(chat_history_manager.conversations_collection.find({"user_id": {"$in": test_user_ids}}))
            test_conv_ids = [str(c["_id"]) for c in test_convs]
            if test_conv_ids:
                chat_history_manager.messages_collection.delete_many({"conversation_id": {"$in": test_conv_ids}})
            chat_history_manager.conversations_collection.delete_many({"user_id": {"$in": test_user_ids}})
        auth_manager.users_collection.delete_many({"email": {"$in": test_emails}})
    except Exception:
        pass

@pytest.fixture
def test_user(test_user_data):
    """Create test user with database cleanup"""
    auth_manager = _auth_manager()
    result = auth_manager.register_user(**test_user_data)
    if result["success"]:
        user_info = {
            **test_user_data,
            "user_id": result["user_id"]
        }
        yield user_info
        
        # Cleanup conversation history & messages for this user
        from auth.chat_history_manager import chat_history_manager
        from bson import ObjectId
        try:
            # Delete messages associated with this user's conversations
            convs = list(chat_history_manager.conversations_collection.find({"user_id": result["user_id"]}))
            conv_ids = [str(c["_id"]) for c in convs]
            if conv_ids:
                chat_history_manager.messages_collection.delete_many({"conversation_id": {"$in": conv_ids}})
                
            # Delete conversations
            chat_history_manager.conversations_collection.delete_many({"user_id": result["user_id"]})
            
            # Delete user
            auth_manager.users_collection.delete_one({"_id": ObjectId(result["user_id"])})
        except Exception:
            pass
    else:
        yield None


@pytest.fixture
def test_user_token(test_user):
    """Get JWT token"""
    if not test_user:
        return None
    auth_manager = _auth_manager()
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
    chat_history_manager = _chat_history_manager()
    return chat_history_manager.create_conversation(
        user_id=test_user["user_id"],
        title="Test Conversation"
    )

@pytest.fixture
def test_conversation_with_messages(test_user, test_conversation):
    """Conversation with messages"""
    if not test_user or not test_conversation:
        return None
    chat_history_manager = _chat_history_manager()
    
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
def faker_instance():
    """Faker instance for generating test data"""
    return Faker()


@pytest.fixture
def multiple_conversations(test_user):
    """Create multiple conversations"""
    if not test_user:
        return []
    chat_history_manager = _chat_history_manager()
    conversations = []
    for i in range(5):
        conv_id = chat_history_manager.create_conversation(
            user_id=test_user["user_id"],
            title=f"Conversation {i+1}"
        )
        conversations.append(conv_id)
    return conversations
