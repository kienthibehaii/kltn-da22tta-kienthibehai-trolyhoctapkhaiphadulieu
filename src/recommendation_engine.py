"""
Recommendation Engine - Personalized learning recommendations
Phase 2.3 - Component 8
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class RecommendationType(Enum):
    """Types of recommendations"""
    REMEDIAL = "remedial"      # Weak areas to focus on
    NEXT_TOPIC = "next_topic"  # Logical progression
    SIMILAR = "similar"        # Related topics
    CHALLENGE = "challenge"    # Advanced topics
    REVIEW = "review"          # Topics to review


@dataclass
class Recommendation:
    """Learning recommendation"""
    recommendation_type: RecommendationType
    chapter_id: str
    reason: str
    priority: float  # 0-1, higher = more important
    estimated_time: int  # minutes
    difficulty: str  # easy/medium/hard
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "type": self.recommendation_type.value,
            "chapter": self.chapter_id,
            "reason": self.reason,
            "priority": self.priority,
            "time": self.estimated_time,
            "difficulty": self.difficulty
        }


class RecommendationEngine:
    """Generate personalized learning recommendations"""
    
    # Course structure (in real app, load from knowledge graph)
    COURSE_STRUCTURE = {
        "CH1": {"name": "Basics", "prerequisites": [], "next": ["CH2", "CH3"]},
        "CH2": {"name": "Fundamentals", "prerequisites": ["CH1"], "next": ["CH4", "CH5"]},
        "CH3": {"name": "Data Structures", "prerequisites": ["CH1"], "next": ["CH4"]},
        "CH4": {"name": "Algorithms", "prerequisites": ["CH2", "CH3"], "next": ["CH5"]},
        "CH5": {"name": "Advanced", "prerequisites": ["CH4"], "next": []},
    }
    
    def __init__(self):
        """Initialize recommendation engine"""
        pass
    
    def get_recommendations(
        self,
        student_id: str,
        mastery_levels: Dict[str, float],
        num_recommendations: int = 5
    ) -> List[Recommendation]:
        """
        Get personalized recommendations
        
        Args:
            student_id: Student identifier
            mastery_levels: Dict of chapter_id -> mastery (0-1)
            num_recommendations: Number of recommendations
            
        Returns:
            List of recommendations sorted by priority
        """
        
        recommendations = []
        
        # 1. Identify weak areas (mastery < 0.6)
        weak_chapters = [ch for ch, m in mastery_levels.items() if m < 0.6]
        for chapter in weak_chapters:
            rec = Recommendation(
                recommendation_type=RecommendationType.REMEDIAL,
                chapter_id=chapter,
                reason=f"You need to strengthen your understanding of {chapter}",
                priority=1.0 - mastery_levels[chapter],  # Lower mastery = higher priority
                estimated_time=60,
                difficulty="medium"
            )
            recommendations.append(rec)
        
        # 2. Identify next topics (prerequisites met)
        for chapter_id, info in self.COURSE_STRUCTURE.items():
            if chapter_id not in mastery_levels:
                # Check if prerequisites are met
                prereqs_met = all(
                    mastery_levels.get(p, 0) >= 0.7
                    for p in info["prerequisites"]
                )
                
                if prereqs_met:
                    rec = Recommendation(
                        recommendation_type=RecommendationType.NEXT_TOPIC,
                        chapter_id=chapter_id,
                        reason=f"You're ready for {chapter_id}",
                        priority=0.8,
                        estimated_time=90,
                        difficulty="medium"
                    )
                    recommendations.append(rec)
        
        # 3. Identify strong areas (mastery > 0.85) -> challenge
        strong_chapters = [ch for ch, m in mastery_levels.items() if m > 0.85]
        for chapter in strong_chapters:
            # Find advanced topics
            for next_ch in self.COURSE_STRUCTURE.get(chapter, {}).get("next", []):
                if next_ch not in mastery_levels:
                    rec = Recommendation(
                        recommendation_type=RecommendationType.CHALLENGE,
                        chapter_id=next_ch,
                        reason=f"Challenge: Move to advanced topics",
                        priority=0.7,
                        estimated_time=120,
                        difficulty="hard"
                    )
                    recommendations.append(rec)
        
        # 4. Review recommendations (low activity)
        review_candidates = [
            ch for ch, m in mastery_levels.items()
            if 0.6 <= m < 0.8
        ]
        for chapter in review_candidates[:2]:  # Limit to 2
            rec = Recommendation(
                recommendation_type=RecommendationType.REVIEW,
                chapter_id=chapter,
                reason=f"Review {chapter} to solidify understanding",
                priority=0.5,
                estimated_time=45,
                difficulty="easy"
            )
            recommendations.append(rec)
        
        # Sort by priority (descending)
        recommendations.sort(key=lambda r: r.priority, reverse=True)
        
        # Return top N
        return recommendations[:num_recommendations]
    
    def recommend_next_topic(
        self,
        current_chapter: str,
        mastery_level: float
    ) -> Optional[str]:
        """Recommend next topic to study"""
        
        if mastery_level < 0.7:
            return current_chapter  # Need to master current first
        
        info = self.COURSE_STRUCTURE.get(current_chapter, {})
        next_topics = info.get("next", [])
        
        return next_topics[0] if next_topics else None
    
    def get_learning_path(
        self,
        current_chapter: str,
        mastery_levels: Dict[str, float]
    ) -> List[str]:
        """Get recommended learning path"""
        
        path = [current_chapter]
        current = current_chapter
        
        for _ in range(5):  # Max 5 chapters ahead
            next_ch = self.recommend_next_topic(
                current,
                mastery_levels.get(current, 0.5)
            )
            
            if next_ch and next_ch not in path:
                path.append(next_ch)
                current = next_ch
            else:
                break
        
        return path
    
    def get_personalized_path(
        self,
        student_id: str,
        mastery_levels: Dict[str, float],
        learning_pace: str = "medium"
    ) -> Dict:
        """
        Get complete personalized learning path
        
        Args:
            student_id: Student ID
            mastery_levels: Current mastery levels
            learning_pace: Student's pace (slow/medium/fast)
            
        Returns:
            Dict with path and recommendations
        """
        
        # Get current chapter (last studied with < 1.0 mastery)
        current = None
        for ch in sorted(mastery_levels.keys()):
            if mastery_levels[ch] < 1.0:
                current = ch
                break
        
        if not current:
            current = list(mastery_levels.keys())[0] if mastery_levels else "CH1"
        
        path = self.get_learning_path(current, mastery_levels)
        recommendations = self.get_recommendations(student_id, mastery_levels, 5)
        
        # Calculate estimated completion time
        total_time = sum(r.estimated_time for r in recommendations)
        if learning_pace == "slow":
            total_time *= 1.5
        elif learning_pace == "fast":
            total_time *= 0.7
        
        return {
            "current_chapter": current,
            "learning_path": path,
            "recommendations": [r.to_dict() for r in recommendations],
            "estimated_completion_hours": total_time / 60,
            "learning_pace": learning_pace
        }
    
    def demo_recommendations(self):
        """Demo recommendation generation"""
        
        print("\n" + "="*70)
        print("🎯 RECOMMENDATION ENGINE DEMO")
        print("="*70)
        
        # Sample mastery levels
        mastery = {
            "CH1": 0.9,
            "CH2": 0.85,
            "CH3": 0.5,
            "CH4": 0.3
        }
        
        print(f"\n📊 Student Mastery Levels:")
        for ch, m in mastery.items():
            status = "✅" if m > 0.8 else ("⚠️" if m > 0.6 else "❌")
            print(f"   {status} {ch}: {m*100:.0f}%")
        
        # Get recommendations
        recommendations = self.get_recommendations("STU001", mastery)
        
        print(f"\n💡 Recommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"\n   {i}. {rec.chapter_id}")
            print(f"      Type: {rec.recommendation_type.value}")
            print(f"      Reason: {rec.reason}")
            print(f"      Priority: {rec.priority*100:.0f}%")
            print(f"      Time: {rec.estimated_time} min")
        
        # Learning path
        path = self.get_learning_path("CH1", mastery)
        print(f"\n📚 Learning Path: {' → '.join(path)}")
        
        # Personalized path
        personalized = self.get_personalized_path("STU001", mastery, "medium")
        print(f"\n🎓 Personalized Learning Plan:")
        print(f"   Current: {personalized['current_chapter']}")
        print(f"   Pace: {personalized['learning_pace']}")
        print(f"   Est. Time: {personalized['estimated_completion_hours']:.1f} hours")


if __name__ == "__main__":
    engine = RecommendationEngine()
    engine.demo_recommendations()
    print("\n✅ Component 8: Recommendation Engine - Ready!")
