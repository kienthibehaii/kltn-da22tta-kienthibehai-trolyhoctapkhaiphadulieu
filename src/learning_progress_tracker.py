"""
Learning Progress Tracker - Track student progress in MongoDB
Phase 2.2 - Component 6
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json


@dataclass
class StudentProfile:
    """Student learning profile"""
    student_id: str
    name: str
    email: str
    major: str
    created_at: datetime
    preferred_strategy: str = "example-first"
    learning_pace: str = "medium"
    current_chapter: str = "CH1"
    overall_mastery: float = 0.0
    total_interactions: int = 0
    last_active: datetime = None


@dataclass
class InteractionRecord:
    """Record of student-system interaction"""
    student_id: str
    interaction_id: str
    timestamp: datetime
    chapter_id: str
    topic: str
    query: str
    strategy_used: str
    response_quality: float  # 0-1
    student_feedback: Optional[str] = None
    mastery_gain: float = 0.0  # improvement


@dataclass
class QuizResponse:
    """Student's quiz response"""
    student_id: str
    quiz_id: str
    chapter_id: str
    question: str
    student_answer: str
    correct_answer: str
    score: float  # 0-1
    attempted_at: datetime
    time_taken: int  # seconds
    is_correct: bool


class LearningProgressTracker:
    """Track and manage student learning progress"""
    
    def __init__(self, mongodb_uri: Optional[str] = None):
        """
        Initialize progress tracker
        
        Args:
            mongodb_uri: MongoDB connection string
                        If None, uses in-memory storage for demo
        """
        self.mongodb_uri = mongodb_uri
        self.use_memory = mongodb_uri is None
        
        # In-memory storage for demo
        self.students: Dict[str, StudentProfile] = {}
        self.interactions: Dict[str, List[InteractionRecord]] = {}
        self.quiz_responses: Dict[str, List[QuizResponse]] = {}
        self.mastery_levels: Dict[str, Dict[str, float]] = {}  # student -> chapter -> mastery
        
        # MongoDB collections (for production)
        self.db = None
        if not self.use_memory:
            self._init_mongodb()
    
    def _init_mongodb(self):
        """Initialize MongoDB connection and collections"""
        try:
            from pymongo import MongoClient
            
            client = MongoClient(self.mongodb_uri)
            self.db = client["educational_ai"]
            
            # Create collections
            self.students_collection = self.db["student_profiles"]
            self.interactions_collection = self.db["interactions"]
            self.quiz_responses_collection = self.db["quiz_responses"]
            self.mastery_collection = self.db["mastery_levels"]
            
            # Create indexes
            self.students_collection.create_index("student_id", unique=True)
            self.interactions_collection.create_index("student_id")
            self.quiz_responses_collection.create_index("student_id")
            
            print("✅ MongoDB initialized successfully")
        except Exception as e:
            print(f"⚠️  MongoDB connection failed: {e}")
            print("   Falling back to in-memory storage")
            self.use_memory = True
            self.db = None
    
    def create_student_profile(
        self,
        student_id: str,
        name: str,
        email: str,
        major: str
    ) -> StudentProfile:
        """Create new student profile"""
        
        profile = StudentProfile(
            student_id=student_id,
            name=name,
            email=email,
            major=major,
            created_at=datetime.now(),
            last_active=datetime.now()
        )
        
        if self.use_memory:
            self.students[student_id] = profile
        else:
            try:
                self.students_collection.insert_one(
                    self._convert_to_serializable(profile)
                )
            except Exception as e:
                print(f"❌ Error creating student profile: {e}")
        
        return profile
    
    def record_interaction(
        self,
        student_id: str,
        chapter_id: str,
        topic: str,
        query: str,
        strategy_used: str,
        response_quality: float,
        mastery_gain: float = 0.1
    ) -> InteractionRecord:
        """
        Record student-system interaction
        
        Args:
            student_id: Student ID
            chapter_id: Chapter being studied
            topic: Topic in chapter
            query: Student's question
            strategy_used: Teaching strategy used
            response_quality: Quality of response (0-1)
            mastery_gain: Estimated learning gain (0-1)
            
        Returns:
            InteractionRecord: Created interaction record
        """
        
        interaction = InteractionRecord(
            student_id=student_id,
            interaction_id=f"{student_id}_{datetime.now().timestamp()}",
            timestamp=datetime.now(),
            chapter_id=chapter_id,
            topic=topic,
            query=query,
            strategy_used=strategy_used,
            response_quality=response_quality,
            mastery_gain=mastery_gain
        )
        
        if self.use_memory:
            if student_id not in self.interactions:
                self.interactions[student_id] = []
            self.interactions[student_id].append(interaction)
        else:
            try:
                self.interactions_collection.insert_one(
                    self._convert_to_serializable(interaction)
                )
            except Exception as e:
                print(f"❌ Error recording interaction: {e}")
        
        # Update mastery levels
        self._update_mastery(student_id, chapter_id, mastery_gain)
        
        # Update student last active
        self._update_last_active(student_id)
        
        return interaction
    
    def record_quiz_response(
        self,
        student_id: str,
        quiz_id: str,
        chapter_id: str,
        question: str,
        student_answer: str,
        correct_answer: str,
        score: float,
        time_taken: int
    ) -> QuizResponse:
        """
        Record student's quiz response
        
        Args:
            student_id: Student ID
            quiz_id: Quiz identifier
            chapter_id: Chapter being tested
            question: Quiz question
            student_answer: Student's answer
            correct_answer: Correct answer
            score: Score (0-1)
            time_taken: Time taken in seconds
            
        Returns:
            QuizResponse: Created quiz response record
        """
        
        response = QuizResponse(
            student_id=student_id,
            quiz_id=quiz_id,
            chapter_id=chapter_id,
            question=question,
            student_answer=student_answer,
            correct_answer=correct_answer,
            score=score,
            attempted_at=datetime.now(),
            time_taken=time_taken,
            is_correct=score >= 0.8  # >80% = correct
        )
        
        if self.use_memory:
            if student_id not in self.quiz_responses:
                self.quiz_responses[student_id] = []
            self.quiz_responses[student_id].append(response)
        else:
            try:
                self.quiz_responses_collection.insert_one(
                    self._convert_to_serializable(response)
                )
            except Exception as e:
                print(f"❌ Error recording quiz response: {e}")
        
        # Update mastery based on quiz score
        mastery_change = score * 0.2  # Quiz impacts mastery
        self._update_mastery(student_id, chapter_id, mastery_change)
        
        return response
    
    def _update_mastery(
        self,
        student_id: str,
        chapter_id: str,
        gain: float
    ):
        """Update mastery level for a chapter"""
        
        if self.use_memory:
            if student_id not in self.mastery_levels:
                self.mastery_levels[student_id] = {}
            
            current = self.mastery_levels[student_id].get(chapter_id, 0.0)
            new_mastery = min(1.0, current + gain)
            self.mastery_levels[student_id][chapter_id] = new_mastery
        else:
            try:
                self.mastery_collection.update_one(
                    {"student_id": student_id, "chapter_id": chapter_id},
                    {"$set": {f"{chapter_id}": gain}},
                    upsert=True
                )
            except Exception as e:
                print(f"❌ Error updating mastery: {e}")
    
    def _update_last_active(self, student_id: str):
        """Update student's last active timestamp"""
        
        if self.use_memory:
            if student_id in self.students:
                self.students[student_id].last_active = datetime.now()
                self.students[student_id].total_interactions += 1
    
    def get_student_progress(
        self,
        student_id: str
    ) -> Dict:
        """Get comprehensive progress report for student"""
        
        if student_id not in self.students:
            return {"error": "Student not found"}
        
        student = self.students[student_id]
        interactions = self.interactions.get(student_id, [])
        quiz_responses = self.quiz_responses.get(student_id, [])
        mastery = self.mastery_levels.get(student_id, {})
        
        # Calculate statistics
        total_interactions = len(interactions)
        correct_quiz_answers = sum(1 for q in quiz_responses if q.is_correct)
        total_quiz_attempts = len(quiz_responses)
        quiz_success_rate = (correct_quiz_answers / total_quiz_attempts 
                            if total_quiz_attempts > 0 else 0)
        
        avg_response_quality = (
            sum(i.response_quality for i in interactions) / total_interactions
            if total_interactions > 0 else 0
        )
        
        # Calculate overall mastery
        overall_mastery = (sum(mastery.values()) / len(mastery) 
                          if mastery else 0)
        
        return {
            "student_id": student_id,
            "name": student.name,
            "email": student.email,
            "major": student.major,
            "created_at": student.created_at.isoformat(),
            "last_active": student.last_active.isoformat() if student.last_active else None,
            "statistics": {
                "total_interactions": total_interactions,
                "avg_response_quality": avg_response_quality,
                "quiz_total_attempts": total_quiz_attempts,
                "quiz_correct_answers": correct_quiz_answers,
                "quiz_success_rate": quiz_success_rate
            },
            "mastery_levels": mastery,
            "overall_mastery": overall_mastery,
            "preferred_strategy": student.preferred_strategy,
            "learning_pace": student.learning_pace
        }
    
    def get_weak_areas(
        self,
        student_id: str,
        threshold: float = 0.6
    ) -> List[str]:
        """Get chapters/topics where student is weak (below threshold)"""
        
        mastery = self.mastery_levels.get(student_id, {})
        weak_areas = [
            chapter for chapter, level in mastery.items()
            if level < threshold
        ]
        
        return weak_areas
    
    def get_strong_areas(
        self,
        student_id: str,
        threshold: float = 0.8
    ) -> List[str]:
        """Get chapters/topics where student is strong (above threshold)"""
        
        mastery = self.mastery_levels.get(student_id, {})
        strong_areas = [
            chapter for chapter, level in mastery.items()
            if level >= threshold
        ]
        
        return strong_areas
    
    def _convert_to_serializable(self, obj):
        """Convert dataclass to serializable dict for MongoDB"""
        
        data = asdict(obj)
        
        # Convert datetime objects to ISO format strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        
        return data
    
    def demo_progress_tracking(self):
        """Demo progress tracking with sample data"""
        
        print("\n" + "="*70)
        print("📊 LEARNING PROGRESS TRACKER DEMO")
        print("="*70)
        
        # Create sample students
        print("\n👥 Creating student profiles...")
        
        tracker = LearningProgressTracker()
        
        students = [
            ("STU001", "Nguyễn Văn A", "a@student.edu", "CS"),
            ("STU002", "Trần Thị B", "b@student.edu", "IT"),
            ("STU003", "Lê Văn C", "c@student.edu", "CS")
        ]
        
        for student_id, name, email, major in students:
            tracker.create_student_profile(student_id, name, email, major)
            print(f"   ✅ {name} (ID: {student_id})")
        
        # Record interactions
        print("\n📝 Recording interactions...")
        
        interactions_data = [
            ("STU001", "CH1", "Variables", "Biến là gì?", "example-first", 0.9, 0.15),
            ("STU001", "CH1", "Loops", "For loop hoạt động thế nào?", "step-by-step", 0.85, 0.1),
            ("STU001", "CH2", "Functions", "Function là gì?", "analogy-first", 0.8, 0.12),
            ("STU002", "CH1", "Variables", "Phạm vi biến?", "conceptual", 0.75, 0.08),
            ("STU002", "CH2", "OOP", "Class là gì?", "example-first", 0.9, 0.14),
        ]
        
        for student_id, chapter, topic, query, strategy, quality, gain in interactions_data:
            tracker.record_interaction(
                student_id, chapter, topic, query, strategy, quality, gain
            )
            print(f"   ✅ {student_id}: {topic}")
        
        # Record quiz responses
        print("\n📋 Recording quiz responses...")
        
        quiz_data = [
            ("STU001", "Q1", "CH1", "Biến là gì?", "Nơi lưu trữ dữ liệu", "Nơi lưu trữ dữ liệu", 1.0, 30),
            ("STU001", "Q2", "CH1", "For loop dùng để?", "Lặp", "Lặp một khối mã", 0.8, 45),
            ("STU002", "Q1", "CH1", "Biến là gì?", "Container", "Nơi lưu trữ dữ liệu", 0.7, 60),
            ("STU002", "Q3", "CH2", "Class là?", "Blue print", "Bản thiết kế", 0.9, 40),
        ]
        
        for student_id, quiz_id, chapter, question, answer, correct, score, time in quiz_data:
            tracker.record_quiz_response(
                student_id, quiz_id, chapter, question, answer, correct, score, time
            )
            print(f"   ✅ {student_id}: Quiz {quiz_id}")
        
        # Display progress reports
        print("\n📈 PROGRESS REPORTS")
        print("="*70)
        
        for student_id, name, _, _ in students:
            progress = tracker.get_student_progress(student_id)
            
            if "error" not in progress:
                print(f"\n👤 {name}")
                print(f"   📊 Total Interactions: {progress['statistics']['total_interactions']}")
                print(f"   📝 Quiz Success Rate: {progress['statistics']['quiz_success_rate']*100:.1f}%")
                print(f"   🎯 Overall Mastery: {progress['overall_mastery']*100:.1f}%")
                
                weak = tracker.get_weak_areas(student_id)
                strong = tracker.get_strong_areas(student_id)
                
                if weak:
                    print(f"   ⚠️  Weak Areas: {', '.join(weak)}")
                if strong:
                    print(f"   ✨ Strong Areas: {', '.join(strong)}")


# Usage:
if __name__ == "__main__":
    tracker = LearningProgressTracker()
    tracker.demo_progress_tracking()
    print("\n✅ Component 6: Learning Progress Tracker - Ready!")
