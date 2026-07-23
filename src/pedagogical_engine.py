"""
Pedagogical reasoning engine for adaptive learning
PHASE 2.1 - Day 2-3 Implementation
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import json


@dataclass
class StudentProfile:
    """Student learning profile"""
    student_id: str
    preferred_strategy: str  # analogy, example, conceptual, etc.
    learning_pace: str  # slow, medium, fast
    strengths: List[str]  # [practical, visual, mathematical]
    weaknesses: List[str]
    current_chapter: str
    mastery_levels: Dict[str, float]  # chapter -> mastery (0-1)


@dataclass
class PedagogicalContext:
    """Context for pedagogical decisions"""
    student_profile: StudentProfile
    current_topic: str
    learning_objectives: List[str]  # CLO IDs
    prerequisite_mastery: Dict[str, float]
    gaps: List[str]  # Weak concepts
    optimal_strategy: str
    response_structure: List[str]  # Order of components
    bloom_target: str  # Target Bloom's level
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "student_profile": asdict(self.student_profile),
            "current_topic": self.current_topic,
            "learning_objectives": self.learning_objectives,
            "prerequisite_mastery": self.prerequisite_mastery,
            "gaps": self.gaps,
            "optimal_strategy": self.optimal_strategy,
            "response_structure": self.response_structure,
            "bloom_target": self.bloom_target
        }


class PedagogicalEngine:
    """Reasoning engine for teaching decisions"""
    
    # 6 Teaching Strategies
    TEACHING_STRATEGIES = [
        "analogy-first",    # Use analogies to familiar concepts
        "example-first",    # Start with concrete examples
        "conceptual",       # Build conceptual understanding
        "mathematical",     # Use mathematical rigor
        "step-by-step",     # Detailed step-by-step explanation
        "visual"            # Visual/diagram-based explanation
    ]
    
    # 8-Part Response Structure
    RESPONSE_STRUCTURE_8_PART = [
        "quick_summary",        # 1-2 sentence overview
        "conceptual_explanation", # Core concept explanation
        "real_world_example",   # Practical example
        "implementation",       # How to implement/use
        "common_mistakes",      # Common misconceptions
        "learning_path",        # Next steps in learning
        "practice_hint",        # Practice suggestion
        "mastery_check"         # Self-check question
    ]
    
    def __init__(self, course_graph_path: str = "course_knowledge_graph.json"):
        """
        Initialize pedagogical engine
        
        Args:
            course_graph_path: Path to course knowledge graph JSON
        """
        self.course_graph = self._load_course_graph(course_graph_path)
        self.course_graph_path = course_graph_path
    
    def _load_course_graph(self, filepath: str) -> Dict:
        """Load course knowledge graph"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️  {filepath} not found. Using default structure.")
            return {"chapters": [], "learning_outcomes": []}
    
    def analyze_student_query(
        self,
        student_id: str,
        query: str,
        chapter_id: str,
        learning_history: Dict
    ) -> PedagogicalContext:
        """
        Analyze student query and determine pedagogical context
        
        This is the main method of the pedagogical engine.
        It makes 8 key pedagogical decisions:
        
        1. Build student learning profile
        2. Extract topic from query
        3. Get chapter learning outcomes (CLOs)
        4. Check if prerequisites are satisfied
        5. Identify knowledge gaps
        6. Select optimal teaching strategy
        7. Determine response structure
        8. Set target Bloom's taxonomy level
        
        Args:
            student_id: Unique student identifier
            query: Student's question/query
            chapter_id: Current chapter context
            learning_history: Dict with student's history
            
        Returns:
            PedagogicalContext: Detailed pedagogical decisions
        """
        
        # 1. Build student profile
        profile = self._build_student_profile(
            student_id, learning_history, chapter_id
        )
        
        # 2. Extract topic from query
        topic = self._extract_topic(query)
        
        # 3. Get chapter learning outcomes
        los = self._get_chapter_los(chapter_id)
        
        # 4. Check prerequisites
        prerequisites, prerequisite_mastery = self._check_prerequisites(
            chapter_id, profile
        )
        
        # 5. Identify knowledge gaps
        gaps = self._identify_gaps(profile, chapter_id)
        
        # 6. Select teaching strategy
        strategy = self._select_strategy(profile, topic, gaps)
        
        # 7. Determine response structure
        response_structure = self._determine_response_structure(
            strategy, profile.learning_pace
        )
        
        # 8. Determine target Bloom's level
        bloom_level = self._determine_bloom_level(los)
        
        context = PedagogicalContext(
            student_profile=profile,
            current_topic=topic,
            learning_objectives=los,
            prerequisite_mastery=prerequisite_mastery,
            gaps=gaps,
            optimal_strategy=strategy,
            response_structure=response_structure,
            bloom_target=bloom_level
        )
        
        return context
    
    def _build_student_profile(
        self,
        student_id: str,
        learning_history: Dict,
        current_chapter: str
    ) -> StudentProfile:
        """
        Build student learning profile from history
        
        Determines:
        - Preferred teaching strategy
        - Learning pace (slow/medium/fast)
        - Strengths and weaknesses
        - Current mastery levels
        """
        
        # Determine preferred strategy from interaction history
        strategy_counts = {}
        for interaction in learning_history.get("interactions", []):
            strat = interaction.get("strategy_used", "conceptual")
            strategy_counts[strat] = strategy_counts.get(strat, 0) + 1
        
        preferred_strategy = max(
            strategy_counts.keys(),
            key=lambda k: strategy_counts[k],
            default="conceptual"
        )
        
        # Determine learning pace
        pace = self._infer_learning_pace(learning_history)
        
        # Identify strengths and weaknesses
        strengths, weaknesses = self._analyze_interaction_quality(
            learning_history
        )
        
        # Get mastery levels
        mastery = learning_history.get("mastery_levels", {})
        
        profile = StudentProfile(
            student_id=student_id,
            preferred_strategy=preferred_strategy,
            learning_pace=pace,
            strengths=strengths,
            weaknesses=weaknesses,
            current_chapter=current_chapter,
            mastery_levels=mastery
        )
        
        return profile
    
    def _extract_topic(self, query: str) -> str:
        """
        Extract main topic from student query
        
        In production, would use NER (Named Entity Recognition)
        For now, uses simple keyword extraction
        """
        keywords = query.split()
        # Take the first meaningful word
        for word in keywords:
            if len(word) > 3 and word.lower() not in ["what", "how", "why", "when", "where"]:
                return word.lower()
        
        return "general" if keywords else "general"
    
    def _get_chapter_los(self, chapter_id: str) -> List[str]:
        """Get learning outcomes for a chapter"""
        chapters = self.course_graph.get("chapters", [])
        for chapter in chapters:
            if chapter.get("id") == chapter_id:
                return chapter.get("learning_outcomes", [])
        return []
    
    def _check_prerequisites(
        self,
        chapter_id: str,
        profile: StudentProfile
    ) -> Tuple[List[str], Dict[str, float]]:
        """
        Check if student has mastered prerequisites
        
        Prerequisites are all chapters before the current one
        """
        
        try:
            chapter_num = int(chapter_id.replace("CH", ""))
            prerequisites = [f"CH{i}" for i in range(1, chapter_num)]
        except:
            prerequisites = []
        
        prerequisite_mastery = {}
        for pre in prerequisites:
            mastery = profile.mastery_levels.get(pre, 0.0)
            prerequisite_mastery[pre] = mastery
        
        return prerequisites, prerequisite_mastery
    
    def _identify_gaps(self, profile: StudentProfile, chapter_id: str) -> List[str]:
        """
        Identify knowledge gaps
        
        Gaps are areas where mastery < 70% threshold
        """
        gaps = []
        
        # Low mastery means potential gap
        for chapter, mastery in profile.mastery_levels.items():
            if mastery < 0.7:  # 70% threshold
                gaps.append(chapter)
        
        # Also add from weaknesses
        gaps.extend(profile.weaknesses)
        
        return list(set(gaps))  # Remove duplicates
    
    def _select_strategy(
        self,
        profile: StudentProfile,
        topic: str,
        gaps: List[str]
    ) -> str:
        """
        Select optimal teaching strategy
        
        Logic:
        - If have gaps: use "step-by-step"
        - Otherwise: use preferred strategy
        """
        
        # If have knowledge gaps, use step-by-step approach
        if gaps:
            return "step-by-step"
        
        # Otherwise use student's preferred strategy
        return profile.preferred_strategy or "conceptual"
    
    def _determine_response_structure(
        self,
        strategy: str,
        pace: str
    ) -> List[str]:
        """
        Determine response structure based on strategy and pace
        
        Returns order of response components
        """
        
        # Different structures for different strategies
        structures = {
            "analogy-first": [
                "quick_summary",
                "conceptual_explanation",
                "real_world_example",
                "implementation",
                "common_mistakes",
                "practice_hint"
            ],
            "example-first": [
                "quick_summary",
                "real_world_example",
                "conceptual_explanation",
                "implementation",
                "common_mistakes",
                "learning_path",
                "practice_hint"
            ],
            "conceptual": [
                "quick_summary",
                "conceptual_explanation",
                "real_world_example",
                "implementation",
                "common_mistakes",
                "learning_path",
                "practice_hint",
                "mastery_check"
            ],
            "mathematical": [
                "quick_summary",
                "conceptual_explanation",
                "implementation",
                "common_mistakes",
                "practice_hint"
            ],
            "step-by-step": [
                "quick_summary",
                "conceptual_explanation",
                "implementation",
                "learning_path",
                "practice_hint",
                "mastery_check"
            ],
            "visual": [
                "quick_summary",
                "real_world_example",
                "conceptual_explanation",
                "implementation",
                "practice_hint"
            ]
        }
        
        structure = structures.get(strategy, ["quick_summary", "conceptual_explanation", "practice_hint"])
        
        # Adjust for learning pace
        if pace == "slow":
            return structure  # Full structure
        elif pace == "fast":
            # For fast learners, skip some basic steps
            return [s for s in structure if s != "common_mistakes"]
        else:  # medium
            return structure
    
    def _determine_bloom_level(self, los: List[str]) -> str:
        """
        Determine target Bloom's taxonomy level
        
        Returns: knowledge, comprehension, application, analysis, synthesis, evaluation
        """
        # In production, would look up Bloom levels for each LO in course graph
        # For now, return application as default
        
        if not los:
            return "comprehension"
        
        # Default: aim for application level
        return "application"
    
    def _infer_learning_pace(self, history: Dict) -> str:
        """
        Infer learning pace from interaction history
        
        Based on frequency of recent interactions
        """
        interactions = history.get("interactions", [])
        if not interactions:
            return "medium"
        
        # Count recent interactions
        recent_count = len([i for i in interactions[-10:] if i])
        
        if recent_count >= 8:
            return "fast"
        elif recent_count <= 3:
            return "slow"
        else:
            return "medium"
    
    def _analyze_interaction_quality(
        self,
        history: Dict
    ) -> Tuple[List[str], List[str]]:
        """
        Analyze interaction quality to find strengths/weaknesses
        
        Returns (strengths, weaknesses) lists
        """
        
        # Simple heuristic: look at feedback from interactions
        strengths = []
        weaknesses = []
        
        interactions = history.get("interactions", [])
        
        if interactions:
            # If many successful interactions with conceptual content
            if sum(1 for i in interactions if i.get("strategy_used") == "conceptual") > len(interactions) / 2:
                strengths.append("conceptual")
            else:
                weaknesses.append("conceptual")
            
            # Default strength: example-based learning
            strengths.append("example-based")
            
            # Default weakness: mathematical
            weaknesses.append("mathematical")
        else:
            # No history: assume balanced
            strengths = ["conceptual", "visual"]
            weaknesses = ["mathematical"]
        
        return strengths, weaknesses
    
    def demo_analyze(self):
        """Demo: Analyze a sample student query"""
        
        print("🧠 Demo: Pedagogical Analysis")
        print("=" * 50)
        
        # Sample student history
        learning_history = {
            "interactions": [
                {"strategy_used": "example-first", "success": True},
                {"strategy_used": "conceptual", "success": True},
                {"strategy_used": "visual", "success": False}
            ],
            "mastery_levels": {
                "CH1": 0.95,
                "CH2": 0.85,
                "CH3": 0.70,
                "CH4": 0.40  # Low mastery in current chapter
            }
        }
        
        # Analyze
        context = self.analyze_student_query(
            student_id="STU001",
            query="Decision Tree hoạt động như thế nào?",
            chapter_id="CH4",
            learning_history=learning_history
        )
        
        # Display results
        print(f"\n👤 Student Profile:")
        print(f"  Student ID: {context.student_profile.student_id}")
        print(f"  Preferred Strategy: {context.student_profile.preferred_strategy}")
        print(f"  Learning Pace: {context.student_profile.learning_pace}")
        print(f"  Strengths: {context.student_profile.strengths}")
        print(f"  Weaknesses: {context.student_profile.weaknesses}")
        
        print(f"\n🎯 Pedagogical Decisions:")
        print(f"  Topic: {context.current_topic}")
        print(f"  Optimal Strategy: {context.optimal_strategy}")
        print(f"  Bloom Target Level: {context.bloom_target}")
        
        print(f"\n⚙️  Response Structure (order of components):")
        for i, component in enumerate(context.response_structure, 1):
            print(f"  {i}. {component}")
        
        print(f"\n📊 Prerequisites & Gaps:")
        print(f"  Knowledge Gaps: {context.gaps}")
        print(f"  Prerequisite Mastery:")
        for ch, mastery in context.prerequisite_mastery.items():
            status = "✅" if mastery > 0.7 else "⚠️ "
            print(f"    {status} {ch}: {mastery*100:.0f}%")
        
        return context


# Usage:
if __name__ == "__main__":
    print("🔄 Phase 2.1 Task 3: Pedagogical Engine")
    print("=" * 50)
    
    # Create engine
    engine = PedagogicalEngine()
    
    # Run demo
    engine.demo_analyze()
    
    print("\n✅ Phase 2.1 Task 3 Complete!")
