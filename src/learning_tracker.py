import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from collections import Counter

os.environ["KMP_DUPLICATE_LIB_OK"] = "True"


class LearningTracker:
    def __init__(self, storage_path: str = "learning_data"):
        self.storage_path = storage_path
        self.mongodb_uri = os.getenv("MONGODB_URI")
        self.use_mongo = False
        self.client = None
        self.db = None

        if self.mongodb_uri:
            try:
                from pymongo import MongoClient

                self.client = MongoClient(
                    self.mongodb_uri,
                    serverSelectionTimeoutMS=2000,
                    connectTimeoutMS=2000,
                    socketTimeoutMS=2000,
                )
                self.client.admin.command("ping")
                self.db = self.client.get_database("rag_system")
                self.learning_events = self.db.learning_events
                self.topic_mastery = self.db.topic_mastery
                self.learning_events.create_index([("user_id", 1), ("created_at", -1)])
                self.topic_mastery.create_index([("user_id", 1), ("topic", 1)], unique=True)
                self.use_mongo = True
                print("✅ LearningTracker: connected to MongoDB")
            except Exception as exc:
                print(f"⚠️ LearningTracker: MongoDB unavailable ({exc}) — using JSON fallback")

        os.makedirs(storage_path, exist_ok=True)

    def _user_file(self, user_id: str) -> str:
        safe_user_id = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in user_id)
        return os.path.join(self.storage_path, f"{safe_user_id}.json")

    def _load_user_data(self, user_id: str) -> Dict:
        path = self._user_file(user_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        return {
            "user_id": user_id,
            "questions_asked": [],
            "quiz_attempts": [],
            "learning_events": [],
            "weak_topics": {},
            "strong_topics": {},
            "topic_mastery": {},
            "total_questions": 0,
            "total_quizzes": 0,
        }

    def _save_user_data(self, user_id: str, data: Dict):
        with open(self._user_file(user_id), "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)

    def log_learning_event(
        self,
        user_id: str,
        event_type: str,
        topic: Optional[str] = None,
        payload: Optional[Dict] = None,
    ) -> bool:
        event = {
            "user_id": user_id,
            "event_type": event_type,
            "topic": topic or "general",
            "payload": payload or {},
            "created_at": datetime.utcnow(),
        }

        if self.use_mongo:
            self.learning_events.insert_one(event)
            return True

        data = self._load_user_data(user_id)
        event["created_at"] = event["created_at"].isoformat()
        data["learning_events"].append(event)
        self._save_user_data(user_id, data)
        return True

    def log_question(self, user_id: str, question: str, answer: str, topics: Optional[List[str]] = None):
        self.log_learning_event(
            user_id=user_id,
            event_type="chat_question",
            topic=(topics or ["general"])[0],
            payload={
                "question": question,
                "answer_preview": answer[:500],
                "topics": topics or [],
            },
        )

        if not self.use_mongo:
            data = self._load_user_data(user_id)
            data["questions_asked"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "question": question,
                "answer": answer[:200],
                "topics": topics or [],
            })
            data["total_questions"] += 1
            self._save_user_data(user_id, data)

    def log_quiz_attempt(
        self,
        user_id: str,
        quiz_topic: str,
        questions: List[Dict],
        results: List[Dict],
        score: float,
    ):
        wrong_questions = []
        for question, result in zip(questions, results):
            if not result.get("is_correct", False):
                wrong_questions.append({
                    "question": question.get("question", ""),
                    "user_answer": result.get("user_answer", ""),
                    "correct_answer": result.get("correct_answer", ""),
                    "category": question.get("category", quiz_topic),
                })

        payload = {
            "total_questions": len(questions),
            "correct": sum(1 for result in results if result.get("is_correct", False)),
            "wrong": len(wrong_questions),
            "score": score,
            "wrong_questions": wrong_questions,
        }
        self.log_learning_event(user_id, "quiz_attempt", quiz_topic, payload)
        self.update_topic_mastery(user_id, quiz_topic, score)

        if not self.use_mongo:
            data = self._load_user_data(user_id)
            data["quiz_attempts"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "topic": quiz_topic,
                **payload,
            })
            data["total_quizzes"] += 1
            self._save_user_data(user_id, data)

    def update_topic_mastery(self, user_id: str, topic: str, score_percentage: float):
        score = score_percentage / 100 if score_percentage > 1 else score_percentage
        score = max(0.0, min(1.0, float(score or 0)))
        status = "strong" if score >= 0.8 else "weak" if score < 0.7 else "developing"

        if self.use_mongo:
            self.topic_mastery.update_one(
                {"user_id": user_id, "topic": topic},
                {
                    "$set": {
                        "latest_score": score,
                        "status": status,
                        "updated_at": datetime.utcnow(),
                    },
                    "$inc": {"attempts": 1, "score_total": score},
                    "$setOnInsert": {"created_at": datetime.utcnow()},
                },
                upsert=True,
            )
            return

        data = self._load_user_data(user_id)
        mastery = data["topic_mastery"].setdefault(topic, {"attempts": 0, "score_total": 0})
        mastery["attempts"] += 1
        mastery["score_total"] += score
        mastery["latest_score"] = score
        mastery["status"] = status
        self._save_user_data(user_id, data)

    def analyze_weak_areas(self, user_id: str):
        if self.use_mongo:
            rows = self.topic_mastery.find({"user_id": user_id, "status": "weak"}).sort("latest_score", 1)
            weak_topics = [
                {
                    "topic": row.get("topic"),
                    "attempts": row.get("attempts", 0),
                    "avg_score": row.get("score_total", 0) / max(1, row.get("attempts", 0)),
                    "severity": "high" if row.get("latest_score", 0) < 0.5 else "medium",
                }
                for row in rows
            ]
            return {"weak_topics": weak_topics, "weak_categories": [], "recommendations": self._generate_recommendations(weak_topics)}

        data = self._load_user_data(user_id)
        weak_topics = []
        for topic, mastery in data.get("topic_mastery", {}).items():
            if mastery.get("status") == "weak":
                weak_topics.append({
                    "topic": topic,
                    "attempts": mastery.get("attempts", 0),
                    "avg_score": mastery.get("score_total", 0) / max(1, mastery.get("attempts", 0)),
                    "severity": "high" if mastery.get("latest_score", 0) < 0.5 else "medium",
                })
        weak_topics.sort(key=lambda item: item["avg_score"])
        return {"weak_topics": weak_topics, "weak_categories": [], "recommendations": self._generate_recommendations(weak_topics)}

    def _generate_recommendations(self, weak_topics: List[Dict]):
        if not weak_topics:
            return ["Ban dang hoc tot!"]
        first = weak_topics[0]
        recommendations = [f"Uu tien on tap: '{first['topic']}' ({first['avg_score'] * 100:.0f}%)"]
        recommendations.extend(f"On tap them: '{topic['topic']}'" for topic in weak_topics[1:3])
        return recommendations

    def get_learning_stats(self, user_id: str):
        if self.use_mongo:
            total_questions = self.learning_events.count_documents({"user_id": user_id, "event_type": "chat_question"})
            total_quizzes = self.learning_events.count_documents({"user_id": user_id, "event_type": "quiz_attempt"})
            weak_topics_count = self.topic_mastery.count_documents({"user_id": user_id, "status": "weak"})
            strong_topics_count = self.topic_mastery.count_documents({"user_id": user_id, "status": "strong"})
            return {
                "total_questions": total_questions,
                "total_quizzes": total_quizzes,
                "weak_topics_count": weak_topics_count,
                "strong_topics_count": strong_topics_count,
            }

        data = self._load_user_data(user_id)
        mastery_statuses = Counter(item.get("status") for item in data.get("topic_mastery", {}).values())
        return {
            "total_questions": data.get("total_questions", 0),
            "total_quizzes": data.get("total_quizzes", 0),
            "weak_topics_count": mastery_statuses.get("weak", 0),
            "strong_topics_count": mastery_statuses.get("strong", 0),
        }


_tracker = None


def get_tracker() -> LearningTracker:
    global _tracker
    if _tracker is None:
        _tracker = LearningTracker()
    return _tracker
