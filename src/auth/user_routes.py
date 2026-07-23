from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Any
from auth.api_routes import get_current_user, auth_manager
from text_encoding import repair_mojibake_obj
import datetime
import json
import os
import random
import uuid

user_router = APIRouter(prefix="/api/user", tags=["user"])

def _load_bank_questions_by_topic(topic: str) -> List[dict]:
    questions = []
    seen_ids = set()

    if auth_manager.use_mongo:
        cursor = auth_manager.db.questions.find(
            {
                "topic": {"$regex": f"^{topic}$", "$options": "i"},
                "created_by_user_id": {"$exists": False},
            },
            {"_id": 0},
        )
        for q in cursor:
            q_id = q.get("id")
            if q_id:
                seen_ids.add(q_id)
            questions.append(repair_mojibake_obj(q))

    bank_path = os.path.join("data", "question_bank.json")
    if os.path.exists(bank_path):
        with open(bank_path, "r", encoding="utf-8") as f:
            bank_data = json.load(f)
        for q in bank_data.get("questions", []):
            if q.get("topic", "").lower() != topic.lower():
                continue
            q_id = q.get("id")
            if q_id and q_id in seen_ids:
                continue
            if q_id:
                seen_ids.add(q_id)
            questions.append(repair_mojibake_obj(dict(q)))

    return questions

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

@user_router.get("/my-questions")
async def get_my_questions(current_user: dict = Depends(get_current_user)):
    """Lấy danh sách toàn bộ câu hỏi do người dùng tự tạo"""
    if not auth_manager.use_mongo:
        raise HTTPException(status_code=500, detail="Chức năng này cần MongoDB")
        
    try:
        user_id = current_user.get("user_id", current_user.get("email"))
        # Load from MongoDB
        questions = [
            repair_mojibake_obj(q)
            for q in auth_manager.db.questions.find({"created_by_user_id": user_id}, {"_id": 0})
        ]
        return {"success": True, "questions": questions, "count": len(questions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi truy vấn: {str(e)}")

@user_router.post("/my-questions")
async def add_my_question(question: dict, current_user: dict = Depends(get_current_user)):
    """Thêm một câu hỏi tĩnh mới vào ngân hàng cá nhân"""
    if not auth_manager.use_mongo:
        raise HTTPException(status_code=500, detail="Chức năng này cần MongoDB")
        
    try:
        user_id = current_user.get("user_id", current_user.get("email"))
        
        # Thêm metadata
        question["created_at"] = datetime.datetime.utcnow()
        question["created_by"] = current_user.get("email")
        question["created_by_user_id"] = user_id
        
        if "id" not in question:
            question["id"] = f"myq_{uuid.uuid4().hex[:8]}"
            
        auth_manager.db.questions.insert_one(question)
        return {"success": True, "message": "Đã lưu câu hỏi cá nhân thành công", "id": question["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi ghi database: {str(e)}")

@user_router.post("/import-bank-questions")
async def import_bank_questions(payload: dict, current_user: dict = Depends(get_current_user)):
    """Copy questions from the shared question bank into the current user's personal bank."""
    if not auth_manager.use_mongo:
        raise HTTPException(status_code=500, detail="Chức năng này cần MongoDB")

    topic = (payload.get("topic") or "").strip()
    target_topic = (payload.get("target_topic") or topic).strip()
    num_questions = payload.get("num_questions")
    if not topic or not target_topic:
        raise HTTPException(status_code=400, detail="Thiếu topic cần nhập")

    try:
        num_questions = int(num_questions) if num_questions is not None else None
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Số câu hỏi không hợp lệ")
    if num_questions is not None and num_questions <= 0:
        raise HTTPException(status_code=400, detail="Số câu hỏi phải lớn hơn 0")

    try:
        user_id = current_user.get("user_id", current_user.get("email"))
        user_email = current_user.get("email")
        bank_questions = _load_bank_questions_by_topic(topic)

        if not bank_questions:
            raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi trong ngân hàng")

        requested_count = num_questions or len(bank_questions)
        used_docs = auth_manager.db.questions.find(
            {
                "created_by_user_id": user_id,
                "original_topic": topic,
                "imported_from": "question_bank",
                "source_question_id": {"$exists": True},
            },
            {"source_question_id": 1, "_id": 0},
        )
        used_source_ids = {doc.get("source_question_id") for doc in used_docs if doc.get("source_question_id")}
        unused_questions = [q for q in bank_questions if not q.get("id") or q.get("id") not in used_source_ids]

        if len(unused_questions) < requested_count:
            raise HTTPException(
                status_code=409,
                detail=f"Ngân hàng chỉ còn {len(unused_questions)} câu hỏi mới cho phạm vi này. Hãy chọn số câu ít hơn hoặc bổ sung thêm câu hỏi.",
            )

        random.shuffle(unused_questions)
        selected_questions = unused_questions[:requested_count]

        existing_same_titles = auth_manager.db.questions.distinct(
            "topic",
            {
                "created_by_user_id": user_id,
                "topic": {"$regex": f"^{target_topic}( \\([0-9]+\\))?$", "$options": "i"},
            },
        )
        final_topic = target_topic if not existing_same_titles else f"{target_topic} ({len(existing_same_titles) + 1})"

        now = datetime.datetime.utcnow()
        docs_to_insert = []
        answer_keys = ["A", "B", "C", "D"]
        for idx, q in enumerate(selected_questions):
            source_id = q.get("id")
            copied = dict(q)
            copied = _move_correct_option(copied, answer_keys[idx % len(answer_keys)])
            copied.pop("_id", None)
            copied["id"] = f"myq_{uuid.uuid4().hex[:8]}"
            copied["topic"] = final_topic
            copied["original_topic"] = topic
            copied["source_question_id"] = source_id
            copied["created_at"] = now
            copied["created_by"] = user_email
            copied["created_by_user_id"] = user_id
            copied["imported_from"] = "question_bank"
            docs_to_insert.append(copied)

        if docs_to_insert:
            auth_manager.db.questions.insert_many(docs_to_insert)

        return {
            "success": True,
            "imported": len(docs_to_insert),
            "skipped": 0,
            "topic": final_topic,
            "message": f"Đã nhập {len(docs_to_insert)} câu hỏi mới vào đề {final_topic}",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi nhập câu hỏi: {str(e)}")

@user_router.delete("/my-questions/{q_id}")
async def delete_my_question(q_id: str, current_user: dict = Depends(get_current_user)):
    """Xoá một câu hỏi cá nhân"""
    if not auth_manager.use_mongo:
        raise HTTPException(status_code=500, detail="Chức năng này cần MongoDB")
        
    try:
        user_id = current_user.get("user_id", current_user.get("email"))
        result = auth_manager.db.questions.delete_one({"id": q_id, "created_by_user_id": user_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi hoặc không có quyền xoá")
            
        return {"success": True, "message": "Đã xoá câu hỏi"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xoá database: {str(e)}")
