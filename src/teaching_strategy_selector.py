"""
Teaching Strategy Selector - Select 1 of 6 strategies per student
Phase 2.2 - Component 4
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class StrategyContext:
    """Context for strategy selection"""
    student_id: str
    query: str
    chapter_id: str
    learning_pace: str  # slow/medium/fast
    preferred_strategy: str  # from learning history
    knowledge_gaps: List[str]
    current_mastery: float  # 0-1
    topic_difficulty: str  # easy/medium/hard


@dataclass
class SelectedStrategy:
    """Selected teaching strategy with parameters"""
    strategy_name: str  # 6 options
    confidence: float  # 0-1
    reasoning: str  # why this strategy
    parameters: Dict  # strategy-specific parameters
    expected_effectiveness: float  # 0-1
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "strategy_name": self.strategy_name,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "parameters": self.parameters,
            "expected_effectiveness": self.expected_effectiveness
        }


class TeachingStrategySelector:
    """Select optimal teaching strategy for student"""
    
    # 6 Teaching Strategies
    STRATEGIES = {
        "analogy-first": {
            "description": "Use analogies to familiar concepts",
            "best_for": ["visual", "conceptual"],
            "avoid_for": ["mathematical"],
            "effectiveness_multiplier": 1.0
        },
        "example-first": {
            "description": "Start with concrete examples",
            "best_for": ["practical", "example-based"],
            "avoid_for": ["theoretical"],
            "effectiveness_multiplier": 1.1
        },
        "conceptual": {
            "description": "Build conceptual understanding",
            "best_for": ["theoretical", "analytical"],
            "avoid_for": ["impatient"],
            "effectiveness_multiplier": 1.0
        },
        "mathematical": {
            "description": "Use mathematical formalism",
            "best_for": ["mathematical", "analytical"],
            "avoid_for": ["mathphobic"],
            "effectiveness_multiplier": 0.8
        },
        "step-by-step": {
            "description": "Detailed sequential steps",
            "best_for": ["slow-learners", "gaps"],
            "avoid_for": ["fast-learners"],
            "effectiveness_multiplier": 1.3
        },
        "visual": {
            "description": "Visual diagrams and illustrations",
            "best_for": ["visual", "spatial"],
            "avoid_for": ["abstract"],
            "effectiveness_multiplier": 1.2
        }
    }
    
    def __init__(self):
        """Initialize strategy selector"""
        self.strategy_history = {}  # track effectiveness per student/strategy
    
    def select_strategy(
        self,
        context: StrategyContext
    ) -> SelectedStrategy:
        """
        Select optimal teaching strategy based on context
        
        Decision Logic:
        1. If have knowledge gaps → step-by-step (best for remediation)
        2. If fast learner → example-first or visual (efficient)
        3. If slow learner → step-by-step (detailed)
        4. Otherwise → use preferred or conceptual (default)
        
        Args:
            context: Strategy context from pedagogical engine
            
        Returns:
            SelectedStrategy: Selected strategy with metadata
        """
        
        # Rule 1: If have knowledge gaps, use step-by-step
        if context.knowledge_gaps:
            selected = "step-by-step"
            confidence = 0.95
            reasoning = f"Knowledge gaps detected ({', '.join(context.knowledge_gaps[:2])}). Using step-by-step approach for remediation."
        
        # Rule 2: If fast learner, use example-first
        elif context.learning_pace == "fast":
            selected = "example-first"
            confidence = 0.85
            reasoning = "Fast learner detected. Using example-first for efficiency."
        
        # Rule 3: If slow learner, use step-by-step
        elif context.learning_pace == "slow":
            selected = "step-by-step"
            confidence = 0.90
            reasoning = "Slow learner detected. Using step-by-step for detailed guidance."
        
        # Rule 4: Use preferred strategy if known
        elif context.preferred_strategy in self.STRATEGIES:
            selected = context.preferred_strategy
            confidence = 0.85
            reasoning = f"Using student's preferred strategy: {context.preferred_strategy}"
        
        # Default: Conceptual approach
        else:
            selected = "conceptual"
            confidence = 0.70
            reasoning = "Using default conceptual approach."
        
        # Calculate parameters for selected strategy
        parameters = self._calculate_parameters(
            selected, context
        )
        
        # Estimate effectiveness
        effectiveness = self._estimate_effectiveness(
            selected, context
        )
        
        return SelectedStrategy(
            strategy_name=selected,
            confidence=confidence,
            reasoning=reasoning,
            parameters=parameters,
            expected_effectiveness=effectiveness
        )
    
    def _calculate_parameters(
        self,
        strategy: str,
        context: StrategyContext
    ) -> Dict:
        """Calculate strategy-specific parameters"""
        
        # Base parameters
        params = {
            "strategy": strategy,
            "depth": "shallow" if context.learning_pace == "fast" else "deep",
            "example_count": 1 if context.learning_pace == "fast" else (2 if context.learning_pace == "medium" else 3),
            "explanation_length": "brief" if context.learning_pace == "fast" else "detailed",
            "use_metaphors": strategy == "analogy-first",
            "use_mathematics": strategy == "mathematical",
            "step_by_step_detail": strategy == "step-by-step",
            "use_diagrams": strategy == "visual"
        }
        
        # Adjust for difficulty
        if context.topic_difficulty == "hard":
            params["explanation_length"] = "detailed"
            params["example_count"] = min(5, params["example_count"] + 1)
        
        # Adjust for mastery
        if context.current_mastery > 0.8:
            params["depth"] = "shallow"
        
        return params
    
    def _estimate_effectiveness(
        self,
        strategy: str,
        context: StrategyContext
    ) -> float:
        """
        Estimate effectiveness of strategy (0-1)
        
        Based on:
        - Match with preferred strategy
        - Match with learning pace
        - Topic difficulty
        - Known effectiveness history
        """
        
        base = 0.7
        
        # Boost if matches preferred strategy
        if strategy == context.preferred_strategy:
            base += 0.15
        
        # Adjust for learning pace matching
        if strategy == "step-by-step" and context.learning_pace == "slow":
            base += 0.15
        elif strategy in ["example-first", "visual"] and context.learning_pace == "fast":
            base += 0.10
        
        # Adjust for difficulty
        if context.topic_difficulty == "hard":
            base -= 0.05
        
        # Check history (if available)
        if context.student_id in self.strategy_history:
            history = self.strategy_history[context.student_id]
            if strategy in history:
                success_rate = (history[strategy]["successes"] / 
                               max(1, history[strategy]["total"]))
                base = (base + success_rate) / 2  # Blend with history
        
        return min(1.0, max(0.5, base))  # Keep in reasonable range
    
    def record_effectiveness(
        self,
        student_id: str,
        strategy: str,
        success: bool
    ):
        """
        Record strategy effectiveness for future personalization
        
        Args:
            student_id: Student identifier
            strategy: Strategy name
            success: Whether the strategy was effective
        """
        
        if student_id not in self.strategy_history:
            self.strategy_history[student_id] = {}
        
        if strategy not in self.strategy_history[student_id]:
            self.strategy_history[student_id][strategy] = {
                "successes": 0,
                "total": 0
            }
        
        self.strategy_history[student_id][strategy]["total"] += 1
        if success:
            self.strategy_history[student_id][strategy]["successes"] += 1
    
    def get_strategy_effectiveness(
        self,
        student_id: str,
        strategy: str
    ) -> Optional[float]:
        """Get historical effectiveness of strategy for student"""
        
        if student_id not in self.strategy_history:
            return None
        
        if strategy not in self.strategy_history[student_id]:
            return None
        
        history = self.strategy_history[student_id][strategy]
        if history["total"] == 0:
            return None
        
        return history["successes"] / history["total"]
    
    def demo_strategy_selection(self):
        """Demo strategy selection with different contexts"""
        
        print("\n" + "="*70)
        print("🎓 TEACHING STRATEGY SELECTOR DEMO")
        print("="*70)
        
        # Test cases
        test_cases = [
            StrategyContext(
                student_id="STU001",
                query="Decision Tree hoạt động như thế nào?",
                chapter_id="CH4",
                learning_pace="slow",
                preferred_strategy="example-first",
                knowledge_gaps=["CH3"],
                current_mastery=0.6,
                topic_difficulty="hard"
            ),
            StrategyContext(
                student_id="STU002",
                query="Giải thích Random Forest",
                chapter_id="CH4",
                learning_pace="fast",
                preferred_strategy="conceptual",
                knowledge_gaps=[],
                current_mastery=0.9,
                topic_difficulty="medium"
            ),
            StrategyContext(
                student_id="STU003",
                query="K-Means clustering là gì?",
                chapter_id="CH5",
                learning_pace="medium",
                preferred_strategy="visual",
                knowledge_gaps=[],
                current_mastery=0.7,
                topic_difficulty="medium"
            )
        ]
        
        for context in test_cases:
            print(f"\n📚 Student: {context.student_id}")
            print(f"   Learning Pace: {context.learning_pace}")
            print(f"   Current Mastery: {context.current_mastery*100:.0f}%")
            print(f"   Knowledge Gaps: {context.knowledge_gaps if context.knowledge_gaps else 'None'}")
            
            # Select strategy
            selected = self.select_strategy(context)
            
            print(f"\n✅ Selected Strategy: {selected.strategy_name}")
            print(f"   Confidence: {selected.confidence*100:.0f}%")
            print(f"   Reasoning: {selected.reasoning}")
            print(f"   Expected Effectiveness: {selected.expected_effectiveness*100:.0f}%")
            print(f"   Parameters:")
            for key, value in selected.parameters.items():
                if not key.startswith("use_"):
                    print(f"      - {key}: {value}")


# Usage:
if __name__ == "__main__":
    selector = TeachingStrategySelector()
    selector.demo_strategy_selection()
    print("\n✅ Component 4: Teaching Strategy Selector - Ready!")
