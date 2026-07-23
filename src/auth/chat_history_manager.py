# auth/chat_history_manager.py - Chat History Management
"""
Manage chat conversations:
- Create new conversations
- Save messages
- Load conversation history
- List user conversations
- Delete conversations
"""

import os
from datetime import datetime
from typing import List, Dict, Optional
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()


class ChatHistoryManager:
    """Manage chat conversations and history"""
    
    def __init__(self):
        # MongoDB connection
        mongo_uri = os.getenv("MONGODB_URI")
        self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        self.db = self.client.get_database("rag_system")
        self.conversations_collection = self.db.conversations
        self.messages_collection = self.db.messages
        
        # Create indexes
        self.conversations_collection.create_index("user_id")
        self.conversations_collection.create_index("created_at")
        self.messages_collection.create_index("conversation_id")
        self.messages_collection.create_index("created_at")
    
    def create_conversation(
        self,
        user_id: str,
        title: str = "New Conversation"
    ) -> str:
        """
        Create new conversation
        
        Returns:
            conversation_id
        """
        conversation_doc = {
            "user_id": user_id,
            "title": title,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "message_count": 0,
            "is_active": True,
            "metadata": {
                "topics": [],
                "difficulty_level": "beginner"
            }
        }
        
        result = self.conversations_collection.insert_one(conversation_doc)
        return str(result.inserted_id)
    
    def add_message(
        self,
        conversation_id: str,
        role: str,  # "user" or "assistant"
        content: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Add message to conversation
        
        Returns:
            message_id
        """
        message_doc = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "created_at": datetime.utcnow(),
            "metadata": metadata or {}
        }
        
        # Insert message
        result = self.messages_collection.insert_one(message_doc)
        message_id = str(result.inserted_id)
        
        # Update conversation
        self.conversations_collection.update_one(
            {"_id": ObjectId(conversation_id)},
            {
                "$set": {"updated_at": datetime.utcnow()},
                "$inc": {"message_count": 1}
            }
        )
        
        # Auto-update title if first user message
        if role == "user":
            conv = self.conversations_collection.find_one({"_id": ObjectId(conversation_id)})
            if conv and conv.get("message_count", 0) == 1:
                # Use first 50 chars of first message as title
                title = content[:50] + "..." if len(content) > 50 else content
                self.conversations_collection.update_one(
                    {"_id": ObjectId(conversation_id)},
                    {"$set": {"title": title}}
                )
        
        return message_id
    
    def get_conversation_messages(
        self,
        conversation_id: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get all messages in a conversation
        
        Returns:
            List of messages
        """
        messages = self.messages_collection.find(
            {"conversation_id": conversation_id}
        ).sort("created_at", 1).limit(limit)
        
        result = []
        for msg in messages:
            result.append({
                "message_id": str(msg["_id"]),
                "role": msg["role"],
                "content": msg["content"],
                "created_at": msg["created_at"].isoformat(),
                "metadata": msg.get("metadata", {})
            })
        
        return result
    
    def get_user_conversations(
        self,
        user_id: str,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict]:
        """
        Get all conversations for a user
        
        Returns:
            List of conversations
        """
        conversations = self.conversations_collection.find(
            {"user_id": user_id, "is_active": True}
        ).sort("updated_at", -1).skip(skip).limit(limit)
        
        result = []
        for conv in conversations:
            # Get last message
            last_message = self.messages_collection.find_one(
                {"conversation_id": str(conv["_id"])},
                sort=[("created_at", -1)]
            )
            
            result.append({
                "conversation_id": str(conv["_id"]),
                "title": conv["title"],
                "message_count": conv.get("message_count", 0),
                "created_at": conv["created_at"].isoformat(),
                "updated_at": conv["updated_at"].isoformat(),
                "last_message": last_message["content"][:100] if last_message else None,
                "metadata": conv.get("metadata", {})
            })
        
        return result
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation details"""
        try:
            conv = self.conversations_collection.find_one({"_id": ObjectId(conversation_id)})
            
            if not conv:
                return None
            
            return {
                "conversation_id": str(conv["_id"]),
                "user_id": conv["user_id"],
                "title": conv["title"],
                "message_count": conv.get("message_count", 0),
                "created_at": conv["created_at"].isoformat(),
                "updated_at": conv["updated_at"].isoformat(),
                "metadata": conv.get("metadata", {})
            }
        except:
            return None
    
    def update_conversation_title(
        self,
        conversation_id: str,
        title: str
    ) -> bool:
        """Update conversation title"""
        try:
            result = self.conversations_collection.update_one(
                {"_id": ObjectId(conversation_id)},
                {"$set": {"title": title, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except:
            return False
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Soft delete conversation (mark as inactive)
        """
        try:
            result = self.conversations_collection.update_one(
                {"_id": ObjectId(conversation_id)},
                {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except:
            return False

    def clear_conversation_messages(self, conversation_id: str) -> bool:
        """Delete all messages in an active conversation."""
        try:
            self.messages_collection.delete_many({"conversation_id": conversation_id})
            self.conversations_collection.update_one(
                {"_id": ObjectId(conversation_id)},
                {
                    "$set": {
                        "message_count": 0,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
            return True
        except:
            return False
    
    def search_conversations(
        self,
        user_id: str,
        query: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        Search conversations by title or content
        """
        # Search in conversation titles
        conversations = self.conversations_collection.find({
            "user_id": user_id,
            "is_active": True,
            "title": {"$regex": query, "$options": "i"}
        }).sort("updated_at", -1).limit(limit)
        
        result = []
        for conv in conversations:
            result.append({
                "conversation_id": str(conv["_id"]),
                "title": conv["title"],
                "message_count": conv.get("message_count", 0),
                "updated_at": conv["updated_at"].isoformat()
            })
        
        return result
    
    def get_conversation_stats(self, user_id: str) -> Dict:
        """Get user's conversation statistics"""
        total_conversations = self.conversations_collection.count_documents({
            "user_id": user_id,
            "is_active": True
        })
        
        total_messages = self.messages_collection.count_documents({
            "conversation_id": {"$in": [
                str(c["_id"]) for c in self.conversations_collection.find(
                    {"user_id": user_id, "is_active": True}
                )
            ]}
        })
        
        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "avg_messages_per_conversation": total_messages / max(1, total_conversations)
        }


# Global instance
chat_history_manager = ChatHistoryManager()
