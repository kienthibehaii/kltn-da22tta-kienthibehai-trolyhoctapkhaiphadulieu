"""
Parse course syllabus and extract course knowledge graph
PHASE 2.1 - Day 1 Implementation
"""

import json
import re
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class LearningOutcome:
    """Learning outcome (CLO)"""
    id: str
    description: str
    bloom_level: str  # knowledge, comprehension, application, analysis, synthesis, evaluation
    competency_type: str  # theoretical, practical, soft_skill


@dataclass
class Topic:
    """Topic within a chapter"""
    id: str
    title: str
    description: Optional[str]
    keywords: List[str]
    learning_outcomes: List[str]  # LO IDs
    teaching_type: str  # lecture, lab, project
    hours: float


@dataclass
class Chapter:
    """Chapter/Module"""
    id: str
    number: int
    title: str
    description: Optional[str]
    hours: float
    topics: List[Topic]
    learning_outcomes: List[str]  # LO IDs
    assessment_types: List[str]  # quiz, exam, assignment
    importance: float  # 0-1


@dataclass
class AssessmentComponent:
    """Assessment component"""
    name: str
    weight: float
    type: str  # quiz, exam, assignment, project
    difficulty: str  # easy, medium, hard
    question_types: List[str]  # multiple-choice, essay, practical


@dataclass
class CourseKnowledgeGraph:
    """Complete course structure"""
    course_id: str
    course_name: str
    course_code: str
    credits: int
    total_hours: int
    semester: str
    instructor: Optional[str]
    learning_outcomes: List[LearningOutcome]
    chapters: List[Chapter]
    assessment: Dict[str, AssessmentComponent]
    prerequisites: List[str]
    created_at: str
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "course_id": self.course_id,
            "course_name": self.course_name,
            "course_code": self.course_code,
            "credits": self.credits,
            "total_hours": self.total_hours,
            "semester": self.semester,
            "instructor": self.instructor,
            "learning_outcomes": [asdict(lo) for lo in self.learning_outcomes],
            "chapters": [
                {
                    "id": ch.id,
                    "number": ch.number,
                    "title": ch.title,
                    "description": ch.description,
                    "hours": ch.hours,
                    "topics": [asdict(t) for t in ch.topics],
                    "learning_outcomes": ch.learning_outcomes,
                    "assessment_types": ch.assessment_types,
                    "importance": ch.importance
                }
                for ch in self.chapters
            ],
            "assessment": {
                k: {
                    "name": v.name,
                    "weight": v.weight,
                    "type": v.type,
                    "difficulty": v.difficulty,
                    "question_types": v.question_types
                }
                for k, v in self.assessment.items()
            },
            "prerequisites": self.prerequisites,
            "created_at": self.created_at
        }


class CourseParser:
    """Parse syllabus and extract course structure"""
    
    def __init__(self):
        self.graph: Optional[CourseKnowledgeGraph] = None
    
    def parse_syllabus_json(self, syllabus_data: Dict) -> CourseKnowledgeGraph:
        """
        Parse syllabus from JSON format
        
        Input format:
        {
            "course": {...},
            "learning_outcomes": [...],
            "chapters": [...],
            "assessment": {...}
        }
        
        Returns:
            CourseKnowledgeGraph: Structured course representation
        """
        
        # Parse learning outcomes
        los = self._parse_learning_outcomes(
            syllabus_data.get("learning_outcomes", [])
        )
        
        # Parse chapters
        chapters = self._parse_chapters(
            syllabus_data.get("chapters", []),
            los
        )
        
        # Parse assessment
        assessment = self._parse_assessment(
            syllabus_data.get("assessment", {})
        )
        
        # Create knowledge graph
        self.graph = CourseKnowledgeGraph(
            course_id=syllabus_data["course"]["id"],
            course_name=syllabus_data["course"]["name"],
            course_code=syllabus_data["course"]["code"],
            credits=syllabus_data["course"]["credits"],
            total_hours=syllabus_data["course"]["total_hours"],
            semester=syllabus_data["course"].get("semester", ""),
            instructor=syllabus_data["course"].get("instructor"),
            learning_outcomes=los,
            chapters=chapters,
            assessment=assessment,
            prerequisites=syllabus_data["course"].get("prerequisites", []),
            created_at=datetime.now().isoformat()
        )
        
        return self.graph
    
    def _parse_learning_outcomes(self, los_data: List[Dict]) -> List[LearningOutcome]:
        """Parse learning outcomes from data"""
        los = []
        for lo in los_data:
            los.append(LearningOutcome(
                id=lo["id"],
                description=lo["description"],
                bloom_level=lo.get("bloom_level", "knowledge"),
                competency_type=lo.get("competency_type", "theoretical")
            ))
        return los
    
    def _parse_chapters(self, chapters_data: List[Dict], los: List[LearningOutcome]) -> List[Chapter]:
        """Parse chapters and topics"""
        chapters = []
        lo_ids = {lo.id: lo for lo in los}
        
        for i, ch_data in enumerate(chapters_data):
            topics = self._parse_topics(ch_data.get("topics", []))
            
            chapter = Chapter(
                id=ch_data.get("id", f"CH{i+1}"),
                number=i + 1,
                title=ch_data["title"],
                description=ch_data.get("description"),
                hours=ch_data.get("hours", 3),
                topics=topics,
                learning_outcomes=ch_data.get("learning_outcomes", []),
                assessment_types=ch_data.get("assessment_types", ["quiz"]),
                importance=ch_data.get("importance", 0.5)
            )
            chapters.append(chapter)
        
        return chapters
    
    def _parse_topics(self, topics_data: List[Dict]) -> List[Topic]:
        """Parse topics"""
        topics = []
        for t_data in topics_data:
            topic = Topic(
                id=t_data.get("id", ""),
                title=t_data["title"],
                description=t_data.get("description"),
                keywords=t_data.get("keywords", []),
                learning_outcomes=t_data.get("learning_outcomes", []),
                teaching_type=t_data.get("teaching_type", "lecture"),
                hours=t_data.get("hours", 1)
            )
            topics.append(topic)
        
        return topics
    
    def _parse_assessment(self, assessment_data: Dict) -> Dict[str, AssessmentComponent]:
        """Parse assessment components"""
        assessment = {}
        
        for key, comp_data in assessment_data.items():
            assessment[key] = AssessmentComponent(
                name=comp_data["name"],
                weight=comp_data["weight"],
                type=comp_data["type"],
                difficulty=comp_data.get("difficulty", "medium"),
                question_types=comp_data.get("question_types", [])
            )
        
        return assessment
    
    def save_to_json(self, filepath: str):
        """Save knowledge graph to JSON file"""
        if not self.graph:
            raise ValueError("No graph to save. Run parse_syllabus_json first.")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.graph.to_dict(), f, ensure_ascii=False, indent=2)
        
        print(f"✅ Knowledge graph saved to {filepath}")
    
    def get_graph(self) -> CourseKnowledgeGraph:
        """Get current knowledge graph"""
        return self.graph


# Example usage:
if __name__ == "__main__":
    parser = CourseParser()
    
    # Load syllabus data from JSON file or provide inline
    # In production, this would come from PDF extraction
    
    # For testing, you can run: python course_parser.py
    # Then create a sample_syllabus.json and use it
    
    try:
        with open("sample_syllabus.json", 'r', encoding='utf-8') as f:
            syllabus = json.load(f)
        
        # Parse
        graph = parser.parse_syllabus_json(syllabus)
        print(f"✅ Parsed {len(graph.chapters)} chapters")
        print(f"✅ Parsed {len(graph.learning_outcomes)} learning outcomes")
        
        # Save
        parser.save_to_json("course_knowledge_graph.json")
        print("✅ Phase 2.1 Task 1 Complete!")
        
    except FileNotFoundError:
        print("⚠️  sample_syllabus.json not found. Please create it first.")
        print("See PHASE2_1_IMPLEMENTATION_GUIDE.md for example format.")
