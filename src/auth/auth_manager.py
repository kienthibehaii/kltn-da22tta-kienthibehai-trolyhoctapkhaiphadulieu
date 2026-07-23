# auth/auth_manager.py - Authentication & User Management
"""
Complete authentication system with:
- User registration
- Login/Logout
- JWT tokens
- Password hashing
- Session management
"""

import os
import json
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

# JWT Configuration
_raw_secret = os.getenv("JWT_SECRET_KEY", "")
if not _raw_secret:
    import warnings
    warnings.warn(
        "JWT_SECRET_KEY not set — using insecure default. "
        "Set JWT_SECRET_KEY in your .env before deploying.",
        RuntimeWarning,
        stacklevel=2,
    )
    _raw_secret = "minerai-dev-secret-change-in-production"
SECRET_KEY = _raw_secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Fallback JSON storage path (khi MongoDB không có sẵn)
_LOCAL_USERS_PATH = os.path.join(os.path.dirname(__file__), "users_local.json")


def _load_local_users() -> Dict:
    if os.path.exists(_LOCAL_USERS_PATH):
        try:
            with open(_LOCAL_USERS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_local_users(data: Dict):
    try:
        with open(_LOCAL_USERS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        print(f"⚠️ Không thể lưu users local: {e}")


class AuthManager:
    """Manage user authentication (MongoDB with JSON fallback)"""

    def __init__(self):
        mongo_uri = os.getenv("MONGODB_URI")
        self.use_mongo = False

        if mongo_uri:
            try:
                from pymongo import MongoClient
                self.client = MongoClient(
                    mongo_uri,
                    serverSelectionTimeoutMS=3000,
                    connectTimeoutMS=3000,
                )
                # Kiểm tra kết nối thực sự
                self.client.admin.command("ping")
                self.db = self.client.get_database("rag_system")
                self.users_collection = self.db.users
                self.logs_collection = self.db.interaction_logs
                self.users_collection.create_index("email", unique=True)
                self.users_collection.create_index("username", unique=True)
                self.use_mongo = True
                print("✅ AuthManager: Kết nối MongoDB thành công")
            except Exception as e:
                print(f"⚠️ AuthManager: Không thể kết nối MongoDB ({e}) — dùng JSON local")
                self.use_mongo = False
        else:
            print("⚠️ AuthManager: MONGODB_URI không được đặt — dùng JSON local")
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed.encode('utf-8')
        )
    
    def create_access_token(self, user_id: str, email: str, role: str = "user") -> str:
        """Create JWT access token"""
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        payload = {
            "user_id": user_id,
            "email": email,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return token
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def register_user(
        self,
        email: str,
        username: str,
        password: str,
        full_name: str
    ) -> Dict:
        """Register new user"""
        if len(password) < 6:
            return {"success": False, "message": "Mật khẩu phải có ít nhất 6 ký tự"}

        hashed_password = self.hash_password(password)
        user_doc = {
            "email": email,
            "username": username,
            "password": hashed_password,
            "full_name": full_name,
            "created_at": datetime.utcnow(),
            "last_login": None,
            "is_active": True,
            "role": "user",
            "profile": {
                "avatar": None, "bio": None,
                "learning_level": "beginner", "interests": []
            },
            "settings": {"language": "vi", "theme": "light", "notifications": True}
        }

        if self.use_mongo:
            if self.users_collection.find_one({"email": email}):
                return {"success": False, "message": "Email đã được sử dụng"}
            if self.users_collection.find_one({"username": username}):
                return {"success": False, "message": "Username đã được sử dụng"}
            result = self.users_collection.insert_one(user_doc)
            return {"success": True, "message": "Đăng ký thành công", "user_id": str(result.inserted_id)}
        else:
            users = _load_local_users()
            if any(u.get("email") == email for u in users.values()):
                return {"success": False, "message": "Email đã được sử dụng"}
            if any(u.get("username") == username for u in users.values()):
                return {"success": False, "message": "Username đã được sử dụng"}
            import uuid
            user_id = str(uuid.uuid4())
            user_doc["created_at"] = user_doc["created_at"].isoformat()
            users[user_id] = user_doc
            _save_local_users(users)
            return {"success": True, "message": "Đăng ký thành công", "user_id": user_id}

    def login_user(self, email: str, password: str) -> Dict:
        """Login user"""
        if self.use_mongo:
            user = self.users_collection.find_one({"email": email})
            user_id = str(user["_id"]) if user else None
        else:
            users = _load_local_users()
            user = None
            user_id = None
            for uid, u in users.items():
                if u.get("email") == email:
                    user = u
                    user_id = uid
                    break

        if not user:
            return {"success": False, "message": "Email hoặc mật khẩu không đúng"}
        if not user.get("is_active", True):
            return {"success": False, "message": "Tài khoản đã bị khóa"}
        if not self.verify_password(password, user["password"]):
            return {"success": False, "message": "Email hoặc mật khẩu không đúng"}

        if self.use_mongo:
            self.users_collection.update_one(
                {"_id": user["_id"]}, 
                {
                    "$set": {"last_login": datetime.utcnow()},
                    "$inc": {"login_count": 1}
                }
            )
            try:
                self.log_interaction(user_id=user_id, question="User logged in", retrieved_chunks=[], action_type="login")
            except Exception as e:
                print(f"Lỗi log đăng nhập: {e}")
        else:
            users = _load_local_users()
            if user_id in users:
                users[user_id]["last_login"] = datetime.utcnow().isoformat()
                users[user_id]["login_count"] = int(users[user_id].get("login_count", 0)) + 1
                _save_local_users(users)

        role = user.get("role", "user")
        token = self.create_access_token(user_id, email, role)
        user_info = {
            "user_id": user_id,
            "email": user["email"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": role,
            "profile": user.get("profile", {}),
            "settings": user.get("settings", {})
        }
        return {"success": True, "message": "Đăng nhập thành công", "token": token, "user": user_info}

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        if self.use_mongo:
            try:
                from bson import ObjectId
                user = self.users_collection.find_one({"_id": ObjectId(user_id)})
                if user:
                    user["user_id"] = str(user["_id"])
                    del user["_id"]
                    del user["password"]
                    return user
            except Exception:
                pass
            return None
        else:
            users = _load_local_users()
            user = users.get(user_id)
            if user:
                result = dict(user)
                result["user_id"] = user_id
                result.pop("password", None)
                return result
            return None

    def touch_last_seen(self, user_id: str) -> bool:
        """Mark the user as actively viewing the app."""
        now = datetime.utcnow()
        if self.use_mongo:
            try:
                from bson import ObjectId
                result = self.users_collection.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {"last_seen": now}}
                )
                return result.matched_count > 0
            except Exception:
                return False

        users = _load_local_users()
        if user_id in users:
            users[user_id]["last_seen"] = now.isoformat()
            _save_local_users(users)
            return True
        return False

    def update_user_profile(self, user_id: str, updates: Dict) -> bool:
        """Update user profile information"""
        if not self.use_mongo:
            return True # Not supported in local mode yet
            
        try:
            from bson.objectid import ObjectId
            # Remove system fields from updates
            updates.pop("_id", None)
            updates.pop("password", None)
            updates.pop("email", None)
            updates.pop("username", None)
            
            result = self.users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Lỗi khi cập nhật user profile: {e}")
            return False

    def log_interaction(self, user_id: str, question: str, retrieved_chunks: list, action_type: str = "chat"):
        """Log user interaction for profiling"""
        if not self.use_mongo:
            return False
            
        try:
            # Extract topics and chapters from retrieved chunks
            chapters = []
            for doc in retrieved_chunks:
                if hasattr(doc, "metadata"):
                    # Fallback to source or title if topic/chapter doesn't exist
                    source = doc.metadata.get("source", "")
                    if source:
                        fname = os.path.basename(source)
                        chapters.append(fname)
                    # We might not have 'topic' in our metadata, so we can use filename as a proxy for now
                    
            # Deduplicate
            chapters = list(set(chapters))
            
            log_entry = {
                "user_id": user_id,
                "question": question,
                "action_type": action_type,
                "chapters": chapters,
                "timestamp": datetime.utcnow()
            }
            self.logs_collection.insert_one(log_entry)
            return True
        except Exception as e:
            print(f"Lỗi khi log_interaction: {e}")
            return False

    def get_weak_topics(self, user_id: str, days: int = 14) -> list:
        """Calculate weak topics based on interaction logs"""
        if not self.use_mongo:
            return []
            
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            logs = self.logs_collection.find({
                "user_id": user_id,
                "timestamp": {"$gte": cutoff}
            })
            
            from collections import Counter
            topic_counts = Counter()
            
            for log in logs:
                for chap in log.get("chapters", []):
                    # Clean up filename (e.g. user_id__Khai_Pha_Du_Lieu.pdf -> Khai Pha Du Lieu)
                    clean_name = chap.split("__")[-1].replace(".pdf", "").replace("_", " ")
                    topic_counts[clean_name] += 1
            
            # Simple heuristic: Top 3 most frequently asked chapters are "weak topics"
            # because the user asks about them the most.
            most_common = topic_counts.most_common(3)
            return [t[0] for t in most_common]
        except Exception as e:
            print(f"Lỗi khi get_weak_topics: {e}")
            return []

    def get_completed_topics(self, user_id: str) -> list:
        """Get topics that the user has completed quizzes for"""
        if not self.use_mongo:
            return []
            
        try:
            logs = self.logs_collection.find({
                "user_id": user_id,
                "action_type": "quiz_generated"
            })
            
            completed_topics = set()
            for log in logs:
                topic = log.get("question") # For quiz_generated, question field stores the topic
                if topic:
                    completed_topics.add(topic)
                    
            return list(completed_topics)
        except Exception as e:
            print(f"Lỗi khi get_completed_topics: {e}")
            return []

    def google_login(self, id_token: str) -> Dict:
        """Login or register with Google OAuth2 ID token"""
        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests

            client_id = os.getenv("GOOGLE_CLIENT_ID")
            if not client_id:
                return {"success": False, "message": "Google Client ID not configured"}

            info = google_id_token.verify_oauth2_token(
                id_token, google_requests.Request(), client_id, clock_skew_in_seconds=60
            )

            email = info.get("email")
            if not email:
                return {"success": False, "message": "Email không tồn tại trong tài khoản Google"}

            name = info.get("name", email.split("@")[0])
            google_id = info.get("sub", "")
            picture = info.get("picture", "")

            # Check if user exists by email
            existing = None
            existing_user_id = None
            if self.use_mongo:
                existing = self.users_collection.find_one({"email": email})
                if existing:
                    existing_user_id = str(existing["_id"])
            else:
                users = _load_local_users()
                for uid, u in users.items():
                    if u.get("email") == email:
                        existing = u
                        existing_user_id = uid
                        break

            if existing:
                # Update last login
                if self.use_mongo:
                    self.users_collection.update_one(
                        {"_id": existing["_id"]},
                        {
                            "$set": {"last_login": datetime.utcnow(), "google_id": google_id, "profile.avatar": picture},
                            "$inc": {"login_count": 1},
                        }
                    )
                    try:
                        self.log_interaction(user_id=existing_user_id, question="User logged in with Google", retrieved_chunks=[], action_type="login")
                    except Exception as e:
                        print(f"Lỗi log đăng nhập Google: {e}")
                else:
                    users = _load_local_users()
                    if existing_user_id in users:
                        users[existing_user_id]["last_login"] = datetime.utcnow().isoformat()
                        users[existing_user_id]["login_count"] = int(users[existing_user_id].get("login_count", 0)) + 1
                        users[existing_user_id]["google_id"] = google_id
                        users[existing_user_id].setdefault("profile", {})["avatar"] = picture
                        _save_local_users(users)
                role = existing.get("role", "user")
                token = self.create_access_token(existing_user_id, email, role)
                user_info = {
                    "user_id": existing_user_id,
                    "email": existing["email"],
                    "username": existing["username"],
                    "full_name": existing.get("full_name", name),
                    "role": role,
                    "profile": existing.get("profile", {}),
                    "settings": existing.get("settings", {})
                }
                return {"success": True, "message": "Đăng nhập thành công", "token": token, "user": user_info}
            else:
                # Create new user
                username = email.split("@")[0]
                import uuid
                user_doc = {
                    "email": email,
                    "username": username,
                    "password": "",
                    "full_name": name,
                    "google_id": google_id,
                    "created_at": datetime.utcnow(),
                    "last_login": datetime.utcnow(),
                    "login_count": 1,
                    "is_active": True,
                    "role": "user",
                    "profile": {
                        "avatar": picture, "bio": None,
                        "learning_level": "beginner", "interests": []
                    },
                    "settings": {"language": "vi", "theme": "light", "notifications": True}
                }

                if self.use_mongo:
                    result = self.users_collection.insert_one(user_doc)
                    new_user_id = str(result.inserted_id)
                    try:
                        self.log_interaction(user_id=new_user_id, question="User registered and logged in with Google", retrieved_chunks=[], action_type="login")
                    except Exception as e:
                        print(f"Lỗi log đăng nhập Google mới: {e}")
                else:
                    new_user_id = str(uuid.uuid4())
                    user_doc["created_at"] = user_doc["created_at"].isoformat()
                    user_doc["last_login"] = user_doc["last_login"].isoformat()
                    users = _load_local_users()
                    users[new_user_id] = user_doc
                    _save_local_users(users)

                token = self.create_access_token(new_user_id, email, "user")
                user_info = {
                    "user_id": new_user_id,
                    "email": email,
                    "username": username,
                    "full_name": name,
                    "role": "user",
                    "profile": user_doc.get("profile", {}),
                    "settings": user_doc.get("settings", {})
                }
                return {"success": True, "message": "Đăng ký thành công", "token": token, "user": user_info}

        except ValueError as e:
            return {"success": False, "message": f"Token không hợp lệ: {str(e)}"}
        except Exception as e:
            return {"success": False, "message": f"Lỗi xác thực Google: {str(e)}"}

    def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict:
        """Change user password"""
        if len(new_password) < 6:
            return {"success": False, "message": "Mật khẩu mới phải có ít nhất 6 ký tự"}

        if self.use_mongo:
            try:
                from bson import ObjectId
                user = self.users_collection.find_one({"_id": ObjectId(user_id)})
            except Exception as e:
                return {"success": False, "message": str(e)}
        else:
            users = _load_local_users()
            user = users.get(user_id)

        if not user:
            return {"success": False, "message": "Người dùng không tồn tại"}
        if not self.verify_password(old_password, user["password"]):
            return {"success": False, "message": "Mật khẩu cũ không đúng"}

        new_hashed = self.hash_password(new_password)
        if self.use_mongo:
            try:
                from bson import ObjectId
                self.users_collection.update_one(
                    {"_id": ObjectId(user_id)}, {"$set": {"password": new_hashed}}
                )
            except Exception as e:
                return {"success": False, "message": str(e)}
        else:
            users = _load_local_users()
            if user_id in users:
                users[user_id]["password"] = new_hashed
                _save_local_users(users)

        return {"success": True, "message": "Đổi mật khẩu thành công"}


# Global instance (lazy — không crash khi import nếu MongoDB không có)
try:
    auth_manager = AuthManager()
except Exception as _e:
    print(f"⚠️ AuthManager init error: {_e}")
    auth_manager = None
