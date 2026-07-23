from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Any
from auth.api_routes import get_current_user, auth_manager
from quiz_system import load_static_quiz
from text_encoding import repair_mojibake_obj
import json
import os


def _move_correct_option(question: dict, target_key: str) -> dict:
    options = question.get("options")
    correct_key = question.get("correct_answer")
    if not isinstance(options, dict) or correct_key not in options or target_key not in options:
        return question
    if correct_key == target_key:
        return question

    moved_options = dict(options)
    moved_options[correct_key], moved_options[target_key] = moved_options[target_key], moved_options[correct_key]
    question["options"] = moved_options
    question["correct_answer"] = target_key
    return question

admin_router = APIRouter(prefix="/api/admin", tags=["admin"])

def get_current_admin(current_user: dict = Depends(get_current_user)):
    """Kiểm tra quyền admin"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Yêu cầu quyền quản trị viên (Admin)")
    return current_user

@admin_router.get("/questions")
async def get_all_questions(admin: dict = Depends(get_current_admin)):
    """Lấy danh sách toàn bộ câu hỏi trong hệ thống"""
    try:
        questions = []
        if auth_manager.use_mongo:
            questions = list(auth_manager.db.questions.find({}))
            for q in questions:
                q["_id"] = str(q["_id"])
                if "id" not in q:
                    q["id"] = q["_id"]

        existing_ids = {q.get("id") for q in questions}
        bank_path = os.path.join("data", "question_bank.json")
        if os.path.exists(bank_path):
            with open(bank_path, "r", encoding="utf-8") as f:
                bank_data = json.load(f)
            for q in bank_data.get("questions", []):
                if q.get("id") not in existing_ids:
                    q = dict(q)
                    q["created_by"] = q.get("created_by", "bundled_json")
                    questions.append(q)

        topic_positions = {}
        normalized_questions = []
        for q in questions:
            q = repair_mojibake_obj(q)
            topic = q.get("topic", "")
            idx = topic_positions.get(topic, 0)
            topic_positions[topic] = idx + 1
            normalized_questions.append(_move_correct_option(q, ["A", "B", "C", "D"][idx % 4]))
        questions = normalized_questions
        return {"success": True, "questions": questions, "count": len(questions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi truy vấn: {str(e)}")

@admin_router.get("/users/summary")
async def get_users_summary(admin: dict = Depends(get_current_admin)):
    """Return real user counts and a recent-user list for the admin dashboard."""
    try:
        auth_manager.touch_last_seen(admin.get("user_id", ""))
        users: List[Dict[str, Any]] = []

        if auth_manager.use_mongo:
            rows = auth_manager.users_collection.find({}, {"password": 0}).sort("created_at", -1)
            for row in rows:
                row["_id"] = str(row["_id"])
                row["user_id"] = row["_id"]
                users.append(row)
        else:
            from auth.auth_manager import _load_local_users

            for user_id, row in _load_local_users().items():
                item = dict(row)
                item["user_id"] = user_id
                users.append(item)

        def to_iso(value: Any) -> str:
            if hasattr(value, "isoformat"):
                return value.isoformat()
            return str(value or "")

        from datetime import datetime, timedelta

        def parse_dt(value: Any):
            if isinstance(value, datetime):
                return value
            if isinstance(value, str) and value:
                try:
                    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
                except ValueError:
                    return None
            return None

        online_cutoff = datetime.utcnow() - timedelta(minutes=2)

        def is_real_app_user(user: Dict[str, Any]) -> bool:
            role = user.get("role")
            email = str(user.get("email") or "").strip().lower()
            domain = email.rsplit("@", 1)[-1] if "@" in email else ""
            if role == "admin":
                return True
            if role != "user":
                return False
            if domain in {"example.com", "example.net", "example.org"}:
                return False
            if not email or "invalid" in email or "rag-upgrade-test" in email:
                return False
            if email.startswith("test") or email.endswith("@test.com"):
                return False
            return True

        countable_users = [user for user in users if is_real_app_user(user)]
        total_users = len(countable_users)
        admin_count = sum(1 for user in countable_users if user.get("role") == "admin")
        active_count = sum(1 for user in countable_users if user.get("is_active", True))
        online_count = sum(
            1
            for user in countable_users
            if (last_seen := parse_dt(user.get("last_seen"))) and last_seen >= online_cutoff
        )
        recent_users = sorted(countable_users, key=lambda user: to_iso(user.get("created_at")), reverse=True)[:8]

        return {
            "success": True,
            "summary": {
                "total_users": total_users,
                "admin_count": admin_count,
                "regular_count": total_users - admin_count,
                "active_count": active_count,
                "inactive_count": total_users - active_count,
                "online_count": online_count,
            },
            "recent_users": [
                {
                    "user_id": user.get("user_id", ""),
                    "email": user.get("email", ""),
                    "username": user.get("username", ""),
                    "full_name": user.get("full_name", ""),
                    "role": user.get("role", "user"),
                    "is_active": bool(user.get("is_active", True)),
                    "created_at": to_iso(user.get("created_at")),
                    "last_login": to_iso(user.get("last_login")),
                    "login_count": int(user.get("login_count", 0) or 0),
                }
                for user in recent_users
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading users summary: {str(e)}")

@admin_router.post("/questions")
async def add_question(question: dict, admin: dict = Depends(get_current_admin)):
    """Thêm một câu hỏi tĩnh mới vào MongoDB"""
    if not auth_manager.use_mongo:
        raise HTTPException(status_code=500, detail="Chức năng này cần MongoDB")
        
    try:
        # Thêm timestamp
        import datetime
        question["created_at"] = datetime.datetime.utcnow()
        question["created_by"] = admin.get("email")
        
        # Nếu chưa có ID thì tạo ID (đơn giản dùng timestamp hoặc tuỳ format)
        if "id" not in question:
            import uuid
            question["id"] = f"q_{uuid.uuid4().hex[:8]}"
            
        auth_manager.db.questions.insert_one(question)
        return {"success": True, "message": "Đã thêm câu hỏi thành công", "id": question["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi ghi database: {str(e)}")

@admin_router.post("/generate-questions")
async def admin_generate_questions(request: dict, admin: dict = Depends(get_current_admin)):
    """Gọi Gemini sinh câu hỏi và lưu thẳng vào MongoDB"""
    if not auth_manager.use_mongo:
        raise HTTPException(status_code=500, detail="Chức năng này cần MongoDB")
        
    topic = request.get("topic", "apriori")
    folder_topic = request.get("folder_topic", topic)
    num_questions = request.get("num_questions", 5)
    
    # Import retriever từ rag
    from backend_api import retriever
    from quiz_system import generate_interactive_quiz
    
    try:
        from quiz_system import load_static_quiz
        import quiz_system
        
        # Tạm thời monkey-patch hàm tĩnh để ép dùng AI
        original_load = quiz_system.load_static_quiz
        quiz_system.load_static_quiz = lambda t, n: None
        
        quiz_data = generate_interactive_quiz(retriever, topic=topic, num_questions=num_questions)
        
        # Khôi phục
        quiz_system.load_static_quiz = original_load
        
        if not quiz_data or not quiz_data.get("questions"):
            return {"success": False, "message": "AI không thể sinh được câu hỏi nào."}
            
        generated_questions = quiz_data.get("questions")
        
        # Lưu vào MongoDB
        import datetime
        import uuid
        answer_keys = ["A", "B", "C", "D"]
        for idx, q in enumerate(generated_questions):
            q = _move_correct_option(q, answer_keys[idx % len(answer_keys)])
            q["created_at"] = datetime.datetime.utcnow()
            q["created_by"] = "gemini_ai"
            if "id" not in q:
                q["id"] = f"ai_{uuid.uuid4().hex[:8]}"
            
            # Cập nhật thông tin topic vào folder
            q["topic"] = folder_topic
            
        auth_manager.db.questions.insert_many(generated_questions)
        
        return {
            "success": True, 
            "message": f"Đã sinh tự động {len(generated_questions)} câu hỏi.",
            "questions_added": len(generated_questions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi sinh câu hỏi: {str(e)}")

@admin_router.put("/questions/{question_id}")
async def update_question(question_id: str, question: dict, admin: dict = Depends(get_current_admin)):
    if not auth_manager.use_mongo:
        raise HTTPException(status_code=500, detail="Chức năng này cần MongoDB")
    try:
        # Loại bỏ trường _id nếu có
        if "_id" in question:
            del question["_id"]
            
        query = {"id": question_id}
        if len(question_id) == 24:
            from bson import ObjectId
            query = {"$or": [{"id": question_id}, {"_id": ObjectId(question_id)}]}
            
        result = auth_manager.db.questions.update_one(
            query,
            {"$set": question}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi")
        return {"success": True, "message": "Cập nhật thành công"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi cập nhật database: {str(e)}")

@admin_router.delete("/questions/{question_id}")
async def delete_question(question_id: str, admin: dict = Depends(get_current_admin)):
    if not auth_manager.use_mongo:
        raise HTTPException(status_code=500, detail="Chức năng này cần MongoDB")
    try:
        query = {"id": question_id}
        if len(question_id) == 24:
            from bson import ObjectId
            query = {"$or": [{"id": question_id}, {"_id": ObjectId(question_id)}]}
            
        result = auth_manager.db.questions.delete_one(query)
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi")
        return {"success": True, "message": "Xóa thành công"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xóa database: {str(e)}")
