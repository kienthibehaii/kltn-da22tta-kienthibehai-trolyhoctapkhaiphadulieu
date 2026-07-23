# conversation_history.py - Quản lý lịch sử hội thoại với MongoDB
import os
from datetime import datetime
from typing import List, Dict, Optional
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

class ConversationHistory:
    """
    Quản lý lịch sử hội thoại với MongoDB
    """
    
    def __init__(self, max_history=10):
        """
        Khởi tạo connection đến MongoDB
        
        Args:
            max_history: Số lượng lượt hội thoại tối đa giữ lại (mặc định: 10)
        """
        self.max_history = max_history
        self.mongodb_uri = os.getenv("MONGODB_URI")
        
        self.file_path = "conversation_history.json"
        if self.mongodb_uri:
            try:
                self.client = MongoClient(self.mongodb_uri, serverSelectionTimeoutMS=2000, connectTimeoutMS=2000, socketTimeoutMS=2000)
                self.db = self.client['chatbot_db']
                self.conversations = self.db['conversations']
                self.use_mongodb = True
                print("✅ Đã kết nối MongoDB")
            except Exception as e:
                print(f"⚠️ Không thể kết nối MongoDB: {e}")
                print("📝 Sử dụng lưu trữ local")
                self.use_mongodb = False
                self.local_history = self._load_local_history()
        else:
            print("⚠️ Không tìm thấy MONGODB_URI")
            print("📝 Sử dụng lưu trữ local")
            self.use_mongodb = False
            self.local_history = self._load_local_history()
            
    def _load_local_history(self) -> List[Dict]:
        import json
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
                    # Convert timestamp strings back to datetime objects
                    for msg in history:
                        if 'timestamp' in msg and isinstance(msg['timestamp'], str):
                            try:
                                msg['timestamp'] = datetime.fromisoformat(msg['timestamp'])
                            except:
                                msg['timestamp'] = datetime.utcnow()
                    return history
            except Exception as e:
                print(f"⚠️ Không thể đọc file lịch sử: {e}")
        return []

    def _save_local_history(self):
        import json
        try:
            # Convert datetime objects to string for serialization
            serializable_history = []
            for msg in self.local_history:
                msg_copy = msg.copy()
                if 'timestamp' in msg_copy and isinstance(msg_copy['timestamp'], datetime):
                    msg_copy['timestamp'] = msg_copy['timestamp'].isoformat()
                serializable_history.append(msg_copy)
                
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(serializable_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Không thể ghi file lịch sử: {e}")
    
    def save_message(self, session_id: str, role: str, content: str, 
                     citations: Optional[List[Dict]] = None):
        """
        Lưu một message vào lịch sử
        
        Args:
            session_id: ID của session (user)
            role: 'user' hoặc 'assistant'
            content: Nội dung message
            citations: Danh sách trích dẫn (nếu có)
        """
        message = {
            'session_id': session_id,
            'role': role,
            'content': content,
            'citations': citations or [],
            'timestamp': datetime.utcnow()
        }
        
        if self.use_mongodb:
            try:
                self.conversations.insert_one(message)
                # Giữ chỉ max_history messages gần nhất cho mỗi session
                self._trim_history(session_id)
            except Exception as e:
                print(f"⚠️ Lỗi lưu message: {e}")
                self.local_history.append(message)
                if len(self.local_history) > self.max_history * 2:
                    self.local_history = self.local_history[-(self.max_history * 2):]
                self._save_local_history()
        else:
            self.local_history.append(message)
            # Giữ chỉ max_history messages gần nhất
            if len(self.local_history) > self.max_history * 2:  # *2 vì có cả user và assistant
                self.local_history = self.local_history[-(self.max_history * 2):]
            self._save_local_history()
    
    def get_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Lấy lịch sử hội thoại của một session
        
        Args:
            session_id: ID của session
            limit: Số lượng messages tối đa (mặc định: max_history * 2)
        
        Returns:
            Danh sách messages
        """
        if limit is None:
            limit = self.max_history * 2  # *2 vì có cả user và assistant
        
        if self.use_mongodb:
            try:
                messages = list(self.conversations.find(
                    {'session_id': session_id}
                ).sort('timestamp', -1).limit(limit))
                # Đảo ngược để có thứ tự từ cũ đến mới
                messages.reverse()
                return messages
            except Exception as e:
                print(f"⚠️ Lỗi lấy history: {e}")
                return []
        else:
            # Lọc theo session_id và lấy limit messages gần nhất
            session_messages = [m for m in self.local_history if m['session_id'] == session_id]
            return session_messages[-limit:] if session_messages else []
    
    def get_context_for_llm(self, session_id: str, max_turns: int = 5) -> str:
        """
        Tạo context string từ lịch sử để gửi cho LLM
        
        Args:
            session_id: ID của session
            max_turns: Số lượt hội thoại tối đa (mặc định: 5)
        
        Returns:
            Context string formatted cho LLM
        """
        messages = self.get_history(session_id, limit=max_turns * 2)
        
        if not messages:
            return ""
        
        context_parts = ["Previous conversation:"]
        for msg in messages:
            role = "User" if msg['role'] == 'user' else "Assistant"
            # Giữ 500 ký tự đầu (đủ dài để capture chủ đề chính + code snippets ngắn)
            content = msg['content'][:500]
            if len(msg['content']) > 500:
                content += "..."
            context_parts.append(f"{role}: {content}")
        
        return "\n".join(context_parts)
    
    def get_recent_messages(self, session_id: str, n: int = 5) -> List[Dict]:
        """
        Lấy n messages gần nhất
        
        Args:
            session_id: ID của session
            n: Số lượng messages
        
        Returns:
            Danh sách messages
        """
        return self.get_history(session_id, limit=n)
    
    def clear_history(self, session_id: str):
        """
        Xóa toàn bộ lịch sử của một session
        
        Args:
            session_id: ID của session
        """
        if self.use_mongodb:
            try:
                result = self.conversations.delete_many({'session_id': session_id})
                print(f"✅ Đã xóa {result.deleted_count} messages")
            except Exception as e:
                print(f"⚠️ Lỗi xóa history: {e}")
                self.local_history = [m for m in self.local_history if m['session_id'] != session_id]
                self._save_local_history()
        else:
            self.local_history = [m for m in self.local_history if m['session_id'] != session_id]
            self._save_local_history()
            print(f"✅ Đã xóa lịch sử local")
    
    def _trim_history(self, session_id: str):
        """
        Giữ chỉ max_history messages gần nhất cho một session
        
        Args:
            session_id: ID của session
        """
        if not self.use_mongodb:
            return
        
        try:
            # Đếm số messages
            count = self.conversations.count_documents({'session_id': session_id})
            
            if count > self.max_history * 2:
                # Lấy timestamp của message cũ nhất cần giữ
                messages = list(self.conversations.find(
                    {'session_id': session_id}
                ).sort('timestamp', -1).limit(self.max_history * 2))
                
                if messages:
                    oldest_to_keep = messages[-1]['timestamp']
                    # Xóa các messages cũ hơn
                    self.conversations.delete_many({
                        'session_id': session_id,
                        'timestamp': {'$lt': oldest_to_keep}
                    })
        except Exception as e:
            print(f"⚠️ Lỗi trim history: {e}")
    
    def get_all_sessions(self) -> List[str]:
        """
        Lấy danh sách tất cả session IDs
        
        Returns:
            Danh sách session IDs
        """
        if self.use_mongodb:
            try:
                return self.conversations.distinct('session_id')
            except Exception as e:
                print(f"⚠️ Lỗi lấy sessions: {e}")
                return []
        else:
            return list(set(m['session_id'] for m in self.local_history))
    
    def get_session_summary(self, session_id: str) -> Dict:
        """
        Lấy thông tin tóm tắt về một session
        
        Args:
            session_id: ID của session
        
        Returns:
            Dict chứa thông tin tóm tắt
        """
        messages = self.get_history(session_id)
        
        if not messages:
            return {
                'session_id': session_id,
                'message_count': 0,
                'first_message': None,
                'last_message': None
            }
        
        return {
            'session_id': session_id,
            'message_count': len(messages),
            'first_message': messages[0]['timestamp'] if messages else None,
            'last_message': messages[-1]['timestamp'] if messages else None,
            'user_messages': len([m for m in messages if m['role'] == 'user']),
            'assistant_messages': len([m for m in messages if m['role'] == 'assistant'])
        }
    
    def close(self):
        """
        Đóng connection đến MongoDB
        """
        if self.use_mongodb and hasattr(self, 'client'):
            self.client.close()
            print("✅ Đã đóng kết nối MongoDB")

# Singleton instance
_conversation_history = None

def get_conversation_history(max_history=10) -> ConversationHistory:
    """
    Lấy singleton instance của ConversationHistory
    
    Args:
        max_history: Số lượng lượt hội thoại tối đa
    
    Returns:
        ConversationHistory instance
    """
    global _conversation_history
    if _conversation_history is None:
        _conversation_history = ConversationHistory(max_history=max_history)
    return _conversation_history
