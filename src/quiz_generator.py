"""
Quiz Generator - Auto-generate quizzes with multiple question types
Phase 2.3 - Component 7
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import random


class QuestionType(Enum):
    """Question types"""
    MULTIPLE_CHOICE = "multiple_choice"
    SHORT_ANSWER = "short_answer"
    TRUE_FALSE = "true_false"
    ESSAY = "essay"


class BloomLevel(Enum):
    """Bloom's taxonomy levels"""
    KNOWLEDGE = 1
    COMPREHENSION = 2
    APPLICATION = 3
    ANALYSIS = 4
    SYNTHESIS = 5
    EVALUATION = 6


@dataclass
class Question:
    """Quiz question"""
    question_id: str
    question_text: str
    question_type: QuestionType
    bloom_level: BloomLevel
    difficulty: str  # easy/medium/hard
    correct_answer: str
    options: Optional[List[str]] = None  # for multiple choice
    explanation: str = ""
    points: int = 1


@dataclass
class Quiz:
    """Complete quiz"""
    quiz_id: str
    chapter_id: str
    title: str
    questions: List[Question]
    difficulty: str
    total_points: int
    estimated_time: int  # minutes
    bloom_levels: List[BloomLevel]


class QuizGenerator:
    """Generate quizzes from course content"""
    
    QUESTION_TEMPLATES = {
        BloomLevel.KNOWLEDGE: [
            "What is {concept}?",
            "Define {concept}.",
            "List the main characteristics of {concept}.",
        ],
        BloomLevel.COMPREHENSION: [
            "Explain how {concept} works.",
            "Summarize the key points about {concept}.",
            "Describe the relationship between {concept1} and {concept2}.",
        ],
        BloomLevel.APPLICATION: [
            "How would you apply {concept} to {context}?",
            "Give an example of {concept} in {domain}.",
            "Solve this problem using {concept}.",
        ],
        BloomLevel.ANALYSIS: [
            "Compare and contrast {concept1} with {concept2}.",
            "What are the advantages and disadvantages of {concept}?",
            "Break down {concept} into its components.",
        ],
        BloomLevel.SYNTHESIS: [
            "How would you combine {concept1} and {concept2}?",
            "Design a solution using {concept}.",
            "Create a new approach based on {concept}.",
        ],
        BloomLevel.EVALUATION: [
            "Evaluate the effectiveness of {concept}.",
            "Which approach is better: {option1} or {option2}?",
            "Justify your choice of {concept}.",
        ]
    }
    
    def __init__(self):
        """Initialize quiz generator"""
        self.question_bank = {}  # chapter_id -> list of questions
    
    def generate_quiz(
        self,
        chapter_id: str,
        num_questions: int = 5,
        difficulty: str = "medium",
        question_types: Optional[List[QuestionType]] = None
    ) -> Quiz:
        """
        Generate a quiz for a chapter
        
        Args:
            chapter_id: Chapter to generate quiz for
            num_questions: Number of questions
            difficulty: easy/medium/hard
            question_types: Limit to specific types (default: all types)
            
        Returns:
            Quiz: Generated quiz
        """
        
        if question_types is None:
            question_types = list(QuestionType)
        
        # Generate questions
        questions = []
        total_points = 0
        bloom_levels = []
        
        for i in range(num_questions):
            # Select question type
            q_type = random.choice(question_types)
            
            # Select Bloom level (mix of levels)
            bloom_level = BloomLevel(
                (i % 6) + 1  # Cycle through Bloom levels
            )
            
            # Generate question
            question = self._generate_question(
                chapter_id, bloom_level, difficulty, q_type
            )
            
            questions.append(question)
            total_points += question.points
            bloom_levels.append(question.bloom_level)
        
        # Create quiz
        quiz = Quiz(
            quiz_id=f"{chapter_id}_Q{random.randint(1000, 9999)}",
            chapter_id=chapter_id,
            title=f"Quiz: {chapter_id}",
            questions=questions,
            difficulty=difficulty,
            total_points=total_points,
            estimated_time=num_questions * 2,  # 2 min per question
            bloom_levels=bloom_levels
        )
        
        return quiz
    
    def _generate_question(
        self,
        chapter_id: str,
        bloom_level: BloomLevel,
        difficulty: str,
        question_type: QuestionType
    ) -> Question:
        """Generate a single question"""
        
        # Sample concepts (in real implementation, load from knowledge graph)
        concepts = ["Algorithm", "Data Structure", "Complexity", "Optimization"]
        concept = random.choice(concepts)
        
        # Select template
        templates = self.QUESTION_TEMPLATES.get(bloom_level, [])
        template = random.choice(templates) if templates else "What is {concept}?"
        
        # Create question text
        question_text = template.format(
            concept=concept,
            concept1=random.choice(concepts),
            concept2=random.choice(concepts),
            domain="Computer Science",
            context="real-world applications",
            option1="Approach A",
            option2="Approach B"
        )
        
        # Generate based on type
        if question_type == QuestionType.MULTIPLE_CHOICE:
            question = self._generate_multiple_choice(
                question_text, bloom_level, difficulty
            )
        elif question_type == QuestionType.TRUE_FALSE:
            question = self._generate_true_false(
                question_text, bloom_level, difficulty
            )
        elif question_type == QuestionType.SHORT_ANSWER:
            question = self._generate_short_answer(
                question_text, bloom_level, difficulty
            )
        else:
            question = self._generate_essay(
                question_text, bloom_level, difficulty
            )
        
        return question
    
    def _generate_multiple_choice(
        self,
        question_text: str,
        bloom_level: BloomLevel,
        difficulty: str
    ) -> Question:
        """Generate multiple choice question"""
        
        correct_answer = "Correct option"
        options = [
            correct_answer,
            "Incorrect option 1",
            "Incorrect option 2",
            "Incorrect option 3"
        ]
        random.shuffle(options)
        
        return Question(
            question_id=f"Q_{random.randint(1000, 9999)}",
            question_text=question_text,
            question_type=QuestionType.MULTIPLE_CHOICE,
            bloom_level=bloom_level,
            difficulty=difficulty,
            correct_answer=correct_answer,
            options=options,
            explanation="This is the correct answer because...",
            points=1 if difficulty == "easy" else (2 if difficulty == "medium" else 3)
        )
    
    def _generate_true_false(
        self,
        question_text: str,
        bloom_level: BloomLevel,
        difficulty: str
    ) -> Question:
        """Generate true/false question"""
        
        return Question(
            question_id=f"Q_{random.randint(1000, 9999)}",
            question_text=question_text,
            question_type=QuestionType.TRUE_FALSE,
            bloom_level=bloom_level,
            difficulty=difficulty,
            correct_answer="True",
            options=["True", "False"],
            explanation="The statement is true because...",
            points=1
        )
    
    def _generate_short_answer(
        self,
        question_text: str,
        bloom_level: BloomLevel,
        difficulty: str
    ) -> Question:
        """Generate short answer question"""
        
        return Question(
            question_id=f"Q_{random.randint(1000, 9999)}",
            question_text=question_text,
            question_type=QuestionType.SHORT_ANSWER,
            bloom_level=bloom_level,
            difficulty=difficulty,
            correct_answer="Sample answer text",
            explanation="Accept answers that mention the key concepts.",
            points=2 if difficulty == "easy" else (3 if difficulty == "medium" else 5)
        )
    
    def _generate_essay(
        self,
        question_text: str,
        bloom_level: BloomLevel,
        difficulty: str
    ) -> Question:
        """Generate essay question"""
        
        return Question(
            question_id=f"Q_{random.randint(1000, 9999)}",
            question_text=question_text,
            question_type=QuestionType.ESSAY,
            bloom_level=bloom_level,
            difficulty=difficulty,
            correct_answer="Comprehensive essay answer",
            explanation="Grade based on: understanding, depth, examples, clarity",
            points=5 if difficulty == "easy" else (10 if difficulty == "medium" else 15)
        )
    
    def evaluate_answer(
        self,
        question: Question,
        student_answer: str
    ) -> Tuple[bool, float]:
        """
        Evaluate student answer
        
        Args:
            question: Question object
            student_answer: Student's answer
            
        Returns:
            (is_correct, score) - Boolean and score 0-1
        """
        
        if question.question_type == QuestionType.MULTIPLE_CHOICE:
            is_correct = student_answer.lower() == question.correct_answer.lower()
            score = 1.0 if is_correct else 0.0
        
        elif question.question_type == QuestionType.TRUE_FALSE:
            is_correct = student_answer.lower() == question.correct_answer.lower()
            score = 1.0 if is_correct else 0.0
        
        elif question.question_type == QuestionType.SHORT_ANSWER:
            # Keyword matching
            keywords = set(question.correct_answer.lower().split())
            student_keywords = set(student_answer.lower().split())
            overlap = len(keywords & student_keywords) / len(keywords) if keywords else 0
            is_correct = overlap > 0.5
            score = overlap
        
        else:  # ESSAY
            # Manual grading or AI-based (simplified: 0.7 if non-empty)
            is_correct = len(student_answer.strip()) > 20
            score = 0.7 if is_correct else 0.2
        
        return is_correct, score
    
    def demo_quiz_generation(self):
        """Demo quiz generation"""
        
        print("\n" + "="*70)
        print("📝 QUIZ GENERATOR DEMO")
        print("="*70)
        
        # Generate quiz
        quiz = self.generate_quiz("CH1", num_questions=4, difficulty="medium")
        
        print(f"\n✅ Quiz Generated: {quiz.quiz_id}")
        print(f"   Chapter: {quiz.chapter_id}")
        print(f"   Total Points: {quiz.total_points}")
        print(f"   Estimated Time: {quiz.estimated_time} minutes")
        print(f"   Questions: {len(quiz.questions)}")
        
        print(f"\n📋 Questions:")
        for i, q in enumerate(quiz.questions, 1):
            print(f"\n   {i}. {q.question_text} ({q.difficulty}, {q.bloom_level.name})")
            print(f"      Type: {q.question_type.value}")
            print(f"      Points: {q.points}")
            
            if q.options:
                for opt in q.options:
                    print(f"      - {opt}")


if __name__ == "__main__":
    generator = QuizGenerator()
    generator.demo_quiz_generation()
    print("\n✅ Component 7: Quiz Generator - Ready!")
