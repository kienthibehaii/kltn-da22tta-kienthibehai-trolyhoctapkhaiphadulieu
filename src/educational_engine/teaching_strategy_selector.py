# educational_engine/teaching_strategy_selector.py
"""
Teaching Strategy Selector - Adaptive Teaching Route Selection

Routes to optimal teaching strategy based on:
- Question type and complexity
- User level and learning velocity
- Confusion risk prediction
- Learning intent
- Prerequisite gaps

NO LLM - pure routing logic with scoring matrix.

Strategy Options:
1. analogy_first - Start with a familiar comparison
2. example_first - Show a concrete example immediately
3. conceptual - Focus on core principles and mental models
4. mathematical - Equations, notation, and formal reasoning
5. step_by_step - Break the idea into clear steps
6. visual_first - Start with diagrams, tables, or flow visualizations
"""

from typing import Dict, List, Optional


class TeachingStrategySelector:
    """Route to optimal teaching strategy based on pedagogical context"""

    # Strategy scoring matrix: (user_level, question_complexity) → strategy_scores
    STRATEGY_SCORES = {
        'analogy_first': {
            'beginner': {'conceptual': 0.95, 'algorithmic': 0.70, 'mathematical': 0.50},
            'intermediate': {'conceptual': 0.80, 'algorithmic': 0.60, 'mathematical': 0.40},
            'advanced': {'conceptual': 0.40, 'algorithmic': 0.30, 'mathematical': 0.20}
        },
        'example_first': {
            'beginner': {'conceptual': 0.80, 'algorithmic': 0.90, 'mathematical': 0.60},
            'intermediate': {'conceptual': 0.70, 'algorithmic': 0.85, 'mathematical': 0.70},
            'advanced': {'conceptual': 0.50, 'algorithmic': 0.70, 'mathematical': 0.50}
        },
        'conceptual': {
            'beginner': {'conceptual': 0.55},
            'intermediate': {'conceptual': 0.85, 'reasoning': 0.80},
            'advanced': {'conceptual': 0.95, 'reasoning': 0.90}
        },
        'visual_first': {
            'beginner': {'comparison': 0.85, 'process': 0.80, 'conceptual': 0.70},
            'intermediate': {'comparison': 0.90, 'process': 0.85, 'conceptual': 0.75},
            'advanced': {'comparison': 0.78, 'process': 0.75, 'conceptual': 0.70}
        },
        'step_by_step': {
            'beginner': {'process': 0.95, 'algorithmic': 0.90, 'implementation': 0.85},
            'intermediate': {'process': 0.85, 'algorithmic': 0.80, 'implementation': 0.80},
            'advanced': {'process': 0.60, 'algorithmic': 0.70, 'implementation': 0.75}
        },
        'mathematical': {
            'beginner': {'mathematical': 0.30},
            'intermediate': {'mathematical': 0.70},
            'advanced': {'mathematical': 0.95, 'conceptual': 0.80}
        },
        'remedial_prerequisites': {
            'beginner': {'any': 0.90},
            'intermediate': {'any': 0.75},
            'advanced': {'any': 0.50}
        }
    }

    # Question type → best strategies (in priority order)
    QUESTION_TYPE_PREFERENCES = {
        'definition': ['analogy_first', 'example_first', 'conceptual'],
        'process': ['step_by_step', 'example_first', 'conceptual'],
        'comparison': ['visual_first', 'conceptual', 'example_first'],
        'evaluation': ['visual_first', 'step_by_step', 'conceptual'],
        'problem_solving': ['example_first', 'step_by_step', 'conceptual'],
        'application': ['example_first', 'conceptual', 'analogy_first'],
        'reasoning': ['conceptual', 'analogy_first', 'example_first'],
        'mathematical': ['mathematical', 'step_by_step', 'conceptual'],
        'algorithm': ['visual_first', 'step_by_step', 'example_first']
    }

    def __init__(self):
        """Initialize strategy selector"""
        pass

    def select_strategy(
        self,
        pedagogical_context: Dict
    ) -> Dict:
        """
        Select optimal teaching strategy based on pedagogical analysis

        Args:
            pedagogical_context: Output from LocalPedagogicalAnalyzer.analyze()
            Contains: question_type, question_complexity, learning_intent,
                     confusion_risk, prerequisite_gaps, etc.

        Returns:
            Dict with: primary_strategy, fallback_strategy, strategy_parameters,
                      strategy_reasoning, confidence
        """

        # Extract context
        question_type = pedagogical_context.get('question_type', 'definition')
        question_complexity = pedagogical_context.get('question_complexity', 0.5)
        learning_intent = pedagogical_context.get('learning_intent', 'conceptual')
        confusion_risk = pedagogical_context.get('confusion_risk', 0.3)
        prerequisite_gaps = pedagogical_context.get('prerequisite_gaps', [])
        user_level = pedagogical_context.get('user_level_detected', 'intermediate')

        question_type = self._normalize_question_type(question_type)
        learning_intent = self._normalize_learning_intent(learning_intent)

        # Route through decision rules (priority order)
        strategy = self._apply_routing_rules(
            question_type=question_type,
            question_complexity=question_complexity,
            learning_intent=learning_intent,
            confusion_risk=confusion_risk,
            prerequisite_gaps=prerequisite_gaps,
            user_level=user_level
        )

        # Get fallback strategy
        fallback = self._get_fallback_strategy(strategy, question_type)

        # Generate strategy parameters
        parameters = self._generate_strategy_parameters(
            strategy=strategy,
            learning_intent=learning_intent,
            user_level=user_level,
            question_complexity=question_complexity,
            confusion_risk=confusion_risk
        )
        parameters['comparison_table_required'] = question_type == 'comparison'
        parameters['visual_summary_required'] = strategy == 'visual_first' or question_type == 'comparison'

        # Generate reasoning string
        reasoning = self._generate_reasoning(
            strategy=strategy,
            question_type=question_type,
            learning_intent=learning_intent,
            confusion_risk=confusion_risk,
            user_level=user_level
        )

        return {
            'primary_strategy': strategy,
            'fallback_strategy': fallback,
            'strategy_parameters': parameters,
            'strategy_reasoning': reasoning,
            'confidence': self._calculate_strategy_confidence(pedagogical_context)
        }

    def _apply_routing_rules(
        self,
        question_type: str,
        question_complexity: float,
        learning_intent: str,
        confusion_risk: float,
        prerequisite_gaps: List[str],
        user_level: str
    ) -> str:
        """Apply routing rules in priority order - NO LLM"""

        # RULE 1: If high confusion risk, use step_by_step (always clear)
        if confusion_risk > 0.7:
            return 'step_by_step'

        # RULE 2: If prerequisites missing, lean on step_by_step with prerequisite scaffolding
        if prerequisite_gaps and len(prerequisite_gaps) > 0:
            if user_level == 'beginner':
                return 'step_by_step'
            if question_type in ('comparison', 'algorithm'):
                return 'visual_first'

        # RULE 3: Question type based routing (highest priority after above)
        if question_type in self.QUESTION_TYPE_PREFERENCES:
            preferred_strategies = self.QUESTION_TYPE_PREFERENCES[question_type]
            # Return first preference that works for user level
            for strat in preferred_strategies:
                if self._is_strategy_viable(strat, user_level, question_complexity):
                    return strat

        # RULE 4: User level vs question complexity
        if user_level == 'beginner':
            if question_complexity > 0.7:
                return 'step_by_step'  # High complexity = break into steps
            else:
                return 'example_first'  # Low complexity = examples work

        elif user_level == 'advanced':
            if learning_intent == 'mathematical' and question_complexity > 0.6:
                return 'mathematical'
            elif learning_intent == 'conceptual':
                return 'conceptual'

        # RULE 5: Learning intent routing
        if learning_intent == 'implementation':
            return 'example_first'
        elif learning_intent == 'comparison':
            return 'visual_first'
        elif learning_intent == 'mathematical':
            return 'mathematical' if user_level == 'advanced' else 'step_by_step'

        # Default
        return 'conceptual'

    def _is_strategy_viable(
        self,
        strategy: str,
        user_level: str,
        question_complexity: float
    ) -> bool:
        """Check if strategy is viable for user level and complexity"""

        # Advanced users can use any strategy
        if user_level == 'advanced':
            return True

        # Beginner with high complexity shouldn't default to conceptual-only answers
        if user_level == 'beginner' and question_complexity > 0.8:
            return strategy != 'conceptual'

        return True

    def _get_fallback_strategy(self, primary: str, question_type: str) -> str:
        """Get fallback strategy if primary fails"""

        if question_type in self.QUESTION_TYPE_PREFERENCES:
            preferences = self.QUESTION_TYPE_PREFERENCES[question_type]
            # Return next preference
            for i, strat in enumerate(preferences):
                if strat == primary and i + 1 < len(preferences):
                    return preferences[i + 1]

        # Default fallback
        return 'example_first'

    def _generate_strategy_parameters(
        self,
        strategy: str,
        learning_intent: str,
        user_level: str,
        question_complexity: float,
        confusion_risk: float
    ) -> Dict:
        """Generate strategy-specific parameters"""

        parameters = {
            'num_examples': 2,
            'include_analogies': True,
            'include_math': False,
            'include_steps': True,
            'include_visuals': False,
            'comparison_table_required': False,
            'depth_level': 'moderate'
        }

        # Adjust based on strategy
        if strategy == 'analogy_first':
            parameters['num_examples'] = 1
            parameters['include_analogies'] = True
            parameters['depth_level'] = 'shallow'

        elif strategy == 'example_first':
            parameters['num_examples'] = 3
            parameters['include_analogies'] = False
            parameters['include_steps'] = False
            parameters['include_visuals'] = False

        elif strategy == 'step_by_step':
            parameters['include_steps'] = True
            parameters['num_examples'] = 1
            parameters['include_analogies'] = False
            if confusion_risk > 0.7:
                parameters['num_examples'] = 2  # Add examples if confused

        elif strategy == 'conceptual':
            parameters['include_analogies'] = True
            parameters['num_examples'] = 1
            parameters['depth_level'] = 'deep'

        elif strategy == 'mathematical':
            parameters['include_math'] = True
            parameters['include_analogies'] = False
            parameters['depth_level'] = 'deep'
            parameters['include_visuals'] = True

        elif strategy == 'visual_first':
            parameters['num_examples'] = 1
            parameters['include_analogies'] = True
            parameters['include_visuals'] = True
            parameters['depth_level'] = 'moderate'

        elif strategy == 'remedial_prerequisites':
            parameters['num_examples'] = 2
            parameters['include_analogies'] = True
            parameters['depth_level'] = 'shallow'

        # Adjust depth level based on user
        if user_level == 'advanced':
            parameters['depth_level'] = 'deep'
        elif user_level == 'beginner':
            parameters['depth_level'] = 'shallow'

        if strategy == 'visual_first' and user_level == 'beginner':
            parameters['include_steps'] = True
            parameters['num_examples'] = 2

        return parameters

    def _generate_reasoning(
        self,
        strategy: str,
        question_type: str,
        learning_intent: str,
        confusion_risk: float,
        user_level: str
    ) -> str:
        """Generate human-readable reasoning for strategy selection"""

        reasons = []

        # High confusion
        if confusion_risk > 0.7:
            reasons.append(f"High confusion risk ({confusion_risk:.1%}) → step-by-step breakdown")

        # Question type based
        if question_type == 'process':
            reasons.append(f"Process question → step-by-step approach")
        elif question_type == 'comparison':
            reasons.append(f"Comparison question → visual-first contrast and table support")
        elif question_type == 'definition':
            reasons.append(f"Definition question → start with analogy")
        elif question_type == 'mathematical':
            reasons.append(f"Mathematical question → formal reasoning and formulas")

        # Learning intent based
        if learning_intent == 'implementation':
            reasons.append(f"Implementation focus → real code examples")
        elif learning_intent == 'mathematical':
            reasons.append(f"Mathematical intent → formal notation" if user_level == 'advanced'
                          else f"Mathematical intent → step-by-step derivation")

        # User level based
        if user_level == 'beginner':
            reasons.append(f"Beginner level → conversational tone, many examples")
        elif user_level == 'advanced':
            reasons.append(f"Advanced level → focus on depth and edge cases")

        # Strategy adjustment
        if strategy != 'conceptual':
            reasons.append(f"Selected strategy: {strategy}")

        return ' | '.join(reasons) if reasons else f"Strategy: {strategy}"

    def _normalize_question_type(self, question_type: str) -> str:
        """Map legacy question types into the strategy routing vocabulary."""

        aliases = {
            'comparison_table': 'comparison',
            'remedial_prerequisites': 'process',
            'balanced': 'conceptual',
            'why_question': 'reasoning',
            'problem_solving': 'process',
        }
        return aliases.get(question_type, question_type)

    def _normalize_learning_intent(self, learning_intent: str) -> str:
        """Map legacy intent labels to routing labels."""

        aliases = {
            'algorithmic': 'process',
            'implementation': 'implementation',
            'conceptual': 'conceptual',
            'mathematical': 'mathematical',
            'comparison': 'comparison'
        }
        return aliases.get(learning_intent, 'conceptual')

    def _calculate_strategy_confidence(self, pedagogical_context: Dict) -> float:
        """Calculate confidence in strategy selection"""

        confidence = 0.7  # base

        # More confident if we have clear analysis
        if pedagogical_context.get('confidence_score', 0) > 0.8:
            confidence += 0.15

        # More confident if clear question type
        question_type = pedagogical_context.get('question_type')
        if question_type != 'definition':  # definition is catch-all
            confidence += 0.1

        # Less confident if mixed signals
        confusion_risk = pedagogical_context.get('confusion_risk', 0)
        if 0.3 < confusion_risk < 0.7:  # Moderate risk = unclear
            confidence -= 0.1

        return min(1.0, max(0.0, confidence))


# Standalone helpers

def quick_select_strategy(pedagogical_context: Dict) -> Dict:
    """Quick strategy selection"""
    selector = TeachingStrategySelector()
    return selector.select_strategy(pedagogical_context)


def get_strategy_parameters(
    strategy: str,
    user_level: str = 'intermediate'
) -> Dict:
    """Get strategy parameters for display/debugging"""
    selector = TeachingStrategySelector()
    return selector._generate_strategy_parameters(
        strategy=strategy,
        learning_intent='conceptual',
        user_level=user_level,
        question_complexity=0.5,
        confusion_risk=0.3
    )
