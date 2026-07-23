"""
Pedagogical Reasoner - Advanced Pedagogical Analysis for AI Tutoring

Performs deep pedagogical reasoning to understand:
1. What exactly is the learner asking?
2. What foundational knowledge are they missing?
3. What misconceptions might they have?
4. Question type classification (definition, process, math, algorithm, etc.)
5. Optimal learning sequence
6. Common pitfalls for this question type

NO LLM - pure domain knowledge-based reasoning using heuristics and patterns.
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass


@dataclass
class LearnerMisunderstanding:
    """Represents a potential learner misconception"""
    concept: str
    misconception: str
    why_common: str
    correction: str
    confidence: float  # 0-1


@dataclass
class PrerequisiteGap:
    """Represents missing foundational knowledge"""
    concept: str
    importance: float  # 0-1: how critical
    difficulty: float  # 0-1: how hard to learn
    teaching_time_minutes: int


@dataclass
class PedagogicalAnalysis:
    """Complete pedagogical reasoning output"""
    # Core question analysis
    question_core: str  # What is really being asked
    question_type: str  # definition|process|comparison|math|algorithm|application
    question_complexity: float  # 0-1
    question_specificity: str  # specific|vague|multi_part
    
    # Learner knowledge model
    prerequisite_gaps: List[PrerequisiteGap]  # Missing foundational knowledge
    potential_misconceptions: List[LearnerMisunderstanding]
    confusion_risk: float  # 0-1: risk of learner misunderstanding
    
    # Optimal teaching strategy
    learning_sequence: List[str]  # Order to teach: ["foundation1", "concept", "application"]
    teaching_approach: str  # analogy|example|step_by_step|mathematical|visual
    
    # Response structure
    response_flow: List[str]  # 7-step teaching flow
    emphasis_areas: List[str]  # What to highlight
    pitfalls_to_address: List[str]  # Common errors to prevent
    
    # Confidence and metadata
    confidence: float  # 0-1: confidence in this analysis
    reasoning: str  # Why this analysis was chosen


class PedagogicalReasoner:
    """Advanced pedagogical reasoning without LLM"""

    # Common misconceptions by concept
    COMMON_MISCONCEPTIONS = {
        'recursion': [
            LearnerMisunderstanding(
                concept='recursion',
                misconception='Recursion is just calling the function multiple times',
                why_common='Confuses iteration with recursion; doesn\'t understand base case',
                correction='Recursion requires: base case (when to stop) + recursive case (break down problem)',
                confidence=0.9
            ),
            LearnerMisunderstanding(
                concept='recursion',
                misconception='Recursive functions are always less efficient than loops',
                why_common='Missing understanding of memoization and optimization',
                correction='With memoization, recursion can be as efficient as iteration; often more elegant',
                confidence=0.8
            ),
        ],
        'algorithm': [
            LearnerMisunderstanding(
                concept='algorithm_design',
                misconception='All algorithms for the same problem have same complexity',
                why_common='Conflates "solving the problem" with "optimal solution"',
                correction='Different algorithms have different trade-offs: time vs space vs readability',
                confidence=0.85
            ),
        ],
        'machine_learning': [
            LearnerMisunderstanding(
                concept='overfitting',
                misconception='Lower training loss is always better',
                why_common='Doesn\'t understand test set vs training set',
                correction='High training loss vs low validation loss = overfitting; need test data',
                confidence=0.9
            ),
        ],
        'data_structure': [
            LearnerMisunderstanding(
                concept='array_vs_linked_list',
                misconception='Linked lists are always better for insertion',
                why_common='Missing analysis of access time: O(n) lookup + O(1) insert',
                correction='Depends on use case: arrays fast access, linked lists fast insertion at head',
                confidence=0.85
            ),
        ],
    }

    # Prerequisites by concept
    CONCEPT_PREREQUISITES = {
        'recursion': ['loops', 'function_calls', 'stack_basics'],
        'algorithm': ['recursion', 'complexity_analysis', 'data_structures'],
        'dynamic_programming': ['recursion', 'optimization', 'memoization'],
        'sorting': ['comparison_operators', 'loops', 'big_o'],
        'graph': ['recursion', 'dfs_bfs', 'tree_basics'],
        'machine_learning': ['statistics', 'linear_algebra', 'probability'],
        'neural_network': ['machine_learning', 'calculus', 'linear_algebra'],
        'deep_learning': ['neural_network', 'backpropagation', 'optimization'],
        'api': ['http_basics', 'json', 'client_server'],
        'database': ['sql_basics', 'normalization', 'queries'],
    }

    # Teaching approaches by question type
    TYPE_TO_APPROACH = {
        'definition': 'analogy',  # Start with analogy
        'process': 'step_by_step',  # Step-by-step breakdown
        'algorithm': 'visual',  # Visualize the algorithm
        'comparison': 'table',  # Comparison table
        'mathematical': 'formula',  # Formulas and proofs
        'application': 'example',  # Real examples
        'why_question': 'conceptual',  # Deep explanation
        'problem_solving': 'step_by_step',  # Guide through solving
    }

    # Common pitfalls by concept and learner level
    PITFALLS_BY_LEVEL = {
        'beginner': {
            'recursion': [
                'Missing base case (infinite recursion)',
                'Not understanding the call stack',
                'Thinking recursion is always worse than loops',
            ],
            'loops': [
                'Off-by-one errors (<=  vs <)',
                'Infinite loops due to missing increment',
                'Not initializing loop counter properly',
            ],
            'algorithm': [
                'Mistaking explanation with implementation',
                'Not considering edge cases',
                'Assuming first solution is optimal',
            ],
        },
        'intermediate': {
            'algorithm': [
                'Missing trade-offs between approaches',
                'Not analyzing space complexity',
                'Edge case handling incomplete',
            ],
            'data_structure': [
                'Choosing wrong data structure for use case',
                'Missing understanding of access patterns',
                'Performance implications ignored',
            ],
        },
        'advanced': {
            'distributed_systems': [
                'Overlooking consistency vs availability trade-offs',
                'Network partition handling',
                'Clock synchronization issues',
            ],
        },
    }

    def __init__(self):
        """Initialize pedagogical reasoner"""
        self.misconceptions = self.COMMON_MISCONCEPTIONS
        self.prerequisites = self.CONCEPT_PREREQUISITES

    def analyze(
        self,
        question: str,
        learner_level: str = 'intermediate',
        learner_profile: Optional[Dict] = None,
        document_context: Optional[str] = None
    ) -> PedagogicalAnalysis:
        """
        Comprehensive pedagogical reasoning about the question and learner

        Args:
            question: The learner's question
            learner_level: beginner|intermediate|advanced
            learner_profile: Dict with learner's strong/weak areas
            document_context: Retrieved context from documents

        Returns:
            PedagogicalAnalysis with complete reasoning
        """

        # Step 1: Identify core question
        core_question = self._extract_core_question(question)

        # Step 2: Classify question type
        question_type = self._classify_question_type(question)

        # Step 3: Assess question complexity
        complexity = self._assess_complexity(question, question_type, learner_level)

        # Step 4: Identify prerequisite gaps
        prerequisites = self._identify_prerequisites(question_type, learner_level, learner_profile)

        # Step 5: Predict misconceptions
        misconceptions = self._predict_misconceptions(question_type, learner_level, learner_profile)

        # Step 6: Calculate confusion risk
        confusion_risk = self._calculate_confusion_risk(
            question_type, complexity, prerequisites, misconceptions
        )

        # Step 7: Determine teaching approach
        teaching_approach = self._select_teaching_approach(
            question_type, complexity, learner_level, confusion_risk
        )

        # Step 8: Create learning sequence
        learning_sequence = self._create_learning_sequence(
            question_type, teaching_approach, prerequisites, learner_level
        )

        # Step 9: Define teaching flow
        response_flow = self._define_teaching_flow(
            question_type, teaching_approach, learner_level
        )

        # Step 10: Identify pitfalls
        pitfalls = self._identify_pitfalls(question_type, learner_level)

        # Step 11: Generate reasoning
        reasoning = self._generate_reasoning(
            question_type, learner_level, complexity, prerequisites, misconceptions
        )

        return PedagogicalAnalysis(
            question_core=core_question,
            question_type=question_type,
            question_complexity=complexity,
            question_specificity=self._assess_specificity(question),
            prerequisite_gaps=prerequisites,
            potential_misconceptions=misconceptions,
            confusion_risk=confusion_risk,
            learning_sequence=learning_sequence,
            teaching_approach=teaching_approach,
            response_flow=response_flow,
            emphasis_areas=self._identify_emphasis_areas(
                question_type, misconceptions, prerequisites
            ),
            pitfalls_to_address=pitfalls,
            confidence=self._calculate_confidence(
                question_type, complexity, learner_level, misconceptions
            ),
            reasoning=reasoning
        )

    def _extract_core_question(self, question: str) -> str:
        """Extract the core question from potentially verbose question"""
        # Remove leading/trailing whitespace and punctuation
        core = question.strip().rstrip('?!.,')

        # If very long, extract key phrases
        if len(core) > 200:
            # Look for the main clause
            clauses = core.split('?')
            if clauses:
                core = clauses[0].strip()

        return core

    def _classify_question_type(self, question: str) -> str:
        """Classify question into one of the predefined types"""
        question_lower = question.lower()

        # Pattern matching for question types
        patterns = {
            'definition': [r'\bwhat\s+is\b', r'\bdefine\b', r'\bmeaning\b'],
            'process': [r'\bhow\s+(?:to|do|does)\b', r'\bsteps?\b', r'\bprocess\b', r'\bworkflow\b'],
            'algorithm': [r'\balgorithm\b', r'\bsorting\b', r'\bsearch\b', r'\btraversal\b'],
            'comparison': [r'\bvs\.?\b', r'\bversus\b', r'\bdifference\b', r'\bcompare\b'],
            'mathematical': [r'\bequation\b', r'\bformula\b', r'\bcalculate?\b', r'\bproof\b'],
            'application': [r'\bexample\b', r'\buse\s+case\b', r'\bapplication\b', r'\bpractical\b'],
            'why_question': [r'\bwhy\b', r'\breason\b', r'\bcause\b'],
            'problem_solving': [r'\bhow\s+(?:can|to)\s+(?:i|we)\b', r'\bsolve\b', r'\bfix\b'],
        }

        for qtype, patterns_list in patterns.items():
            for pattern in patterns_list:
                if re.search(pattern, question_lower):
                    return qtype

        # Default to definition if no pattern matches
        return 'definition'

    def _assess_complexity(
        self,
        question: str,
        question_type: str,
        learner_level: str
    ) -> float:
        """Assess question complexity on 0-1 scale"""
        complexity = 0.5  # Default middle ground

        # Increase complexity for certain keywords
        complex_markers = [
            'distributed', 'concurrent', 'optimization', 'trade-off',
            'edge case', 'scalability', 'proof', 'theorem'
        ]

        for marker in complex_markers:
            if marker.lower() in question.lower():
                complexity += 0.1

        # Adjust by question type
        if question_type == 'mathematical':
            complexity += 0.2
        elif question_type == 'algorithm':
            complexity += 0.15
        elif question_type == 'process':
            complexity -= 0.1

        # Adjust by learner level (same question is "easier" for advanced)
        if learner_level == 'beginner':
            complexity += 0.15
        elif learner_level == 'advanced':
            complexity -= 0.15

        return min(1.0, max(0.0, complexity))  # Clamp to 0-1

    def _identify_prerequisites(
        self,
        question_type: str,
        learner_level: str,
        learner_profile: Optional[Dict]
    ) -> List[PrerequisiteGap]:
        """Identify prerequisites needed to understand answer"""
        gaps = []

        # Lookup prerequisites by question type
        base_prerequisites = []
        for concept, prereqs in self.prerequisites.items():
            if concept in question_type.lower():
                base_prerequisites.extend(prereqs)

        # Check learner weak areas
        if learner_profile and 'weak_areas' in learner_profile:
            weak_areas = learner_profile['weak_areas']
            for prereq in base_prerequisites:
                if any(weak in prereq.lower() for weak in weak_areas):
                    gaps.append(PrerequisiteGap(
                        concept=prereq,
                        importance=0.8,
                        difficulty=0.6,
                        teaching_time_minutes=15
                    ))

        # Add common prerequisites for beginners
        if learner_level == 'beginner':
            gaps.append(PrerequisiteGap(
                concept='fundamentals',
                importance=0.9,
                difficulty=0.4,
                teaching_time_minutes=20
            ))

        return gaps

    def _predict_misconceptions(
        self,
        question_type: str,
        learner_level: str,
        learner_profile: Optional[Dict]
    ) -> List[LearnerMisunderstanding]:
        """Predict likely misconceptions"""
        misconceptions = []

        # Find misconceptions matching question type
        for concept, misunderstandings in self.misconceptions.items():
            if concept in question_type.lower():
                # Adjust confidence by learner level
                for misunderstanding in misunderstandings:
                    adjusted_confidence = misunderstanding.confidence
                    if learner_level == 'beginner':
                        adjusted_confidence += 0.1
                    else:
                        adjusted_confidence -= 0.1

                    misconceptions.append(LearnerMisunderstanding(
                        concept=misunderstanding.concept,
                        misconception=misunderstanding.misconception,
                        why_common=misunderstanding.why_common,
                        correction=misunderstanding.correction,
                        confidence=min(1.0, adjusted_confidence)
                    ))

        return misconceptions

    def _calculate_confusion_risk(
        self,
        question_type: str,
        complexity: float,
        prerequisites: List[PrerequisiteGap],
        misconceptions: List[LearnerMisunderstanding]
    ) -> float:
        """Calculate risk of learner confusion (0-1)"""
        risk = 0.0

        # Base risk from complexity
        risk += complexity * 0.3

        # Risk from prerequisite gaps
        if prerequisites:
            risk += len(prerequisites) * 0.15

        # Risk from misconceptions
        high_confidence_misconceptions = [
            m for m in misconceptions if m.confidence > 0.8
        ]
        risk += len(high_confidence_misconceptions) * 0.2

        # Question type specific risk
        risky_types = ['algorithm', 'mathematical', 'process']
        if question_type in risky_types:
            risk += 0.2

        return min(1.0, risk)

    def _select_teaching_approach(
        self,
        question_type: str,
        complexity: float,
        learner_level: str,
        confusion_risk: float
    ) -> str:
        """Select optimal teaching approach"""
        # If high confusion risk, use step-by-step always
        if confusion_risk > 0.7:
            return 'step_by_step'

        # Use type-based approach
        if question_type in self.TYPE_TO_APPROACH:
            approach = self.TYPE_TO_APPROACH[question_type]

            # Beginner gets step-by-step for complex topics
            if learner_level == 'beginner' and complexity > 0.7:
                return 'step_by_step'

            return approach

        # Default balanced approach
        return 'step_by_step' if complexity > 0.6 else 'example'

    def _create_learning_sequence(
        self,
        question_type: str,
        teaching_approach: str,
        prerequisites: List[PrerequisiteGap],
        learner_level: str
    ) -> List[str]:
        """Create optimal learning sequence"""
        sequence = []

        # Step 1: Address critical prerequisites first
        for prereq in prerequisites:
            if prereq.importance > 0.7:
                sequence.append(f'review_{prereq.concept}')

        # Step 2: Build intuition
        sequence.append('intuition')

        # Step 3: Present examples
        sequence.append('examples')

        # Step 4: Technical details
        sequence.append('technical')

        # Step 5: Applications
        sequence.append('applications')

        # Step 6: Edge cases and mistakes
        sequence.append('pitfalls')

        return sequence

    def _define_teaching_flow(
        self,
        question_type: str,
        teaching_approach: str,
        learner_level: str
    ) -> List[str]:
        """Define the 7-step teaching flow"""
        return [
            '1_intuitive_explanation',
            '2_real_world_example',
            '3_technical_explanation',
            '4_how_it_works',
            '5_common_mistakes',
            '6_quick_summary',
            '7_understanding_check'
        ]

    def _identify_emphasis_areas(
        self,
        question_type: str,
        misconceptions: List[LearnerMisunderstanding],
        prerequisites: List[PrerequisiteGap]
    ) -> List[str]:
        """Identify areas to emphasize in response"""
        areas = []

        # Emphasize common misconceptions
        for misconception in misconceptions:
            if misconception.confidence > 0.8:
                areas.append(f'avoid_{misconception.misconception}')

        # Emphasize critical prerequisites
        for prereq in prerequisites:
            if prereq.importance > 0.8:
                areas.append(f'build_{prereq.concept}')

        return areas

    def _identify_pitfalls(self, question_type: str, learner_level: str) -> List[str]:
        """Identify common pitfalls for this question type and level"""
        pitfalls = self.PITFALLS_BY_LEVEL.get(learner_level, {}).get(question_type, [])
        return pitfalls

    def _assess_specificity(self, question: str) -> str:
        """Assess how specific vs vague the question is"""
        # Count specific indicators
        specific_indicators = len(re.findall(r'\b(?:this|that|specific|particular|example)\b', question.lower()))

        if specific_indicators > 2:
            return 'specific'
        elif specific_indicators < 1 and len(question) < 50:
            return 'vague'
        else:
            return 'moderate'

    def _calculate_confidence(
        self,
        question_type: str,
        complexity: float,
        learner_level: str,
        misconceptions: List[LearnerMisunderstanding]
    ) -> float:
        """Calculate confidence in pedagogical analysis"""
        confidence = 0.8  # Base confidence

        # Higher confidence for clear question types
        if question_type in ['definition', 'process', 'comparison']:
            confidence += 0.1

        # Lower confidence for very complex questions
        if complexity > 0.8:
            confidence -= 0.1

        # Adjust for misconceptions we know about
        if misconceptions:
            confidence += 0.05

        return min(1.0, max(0.5, confidence))

    def _generate_reasoning(
        self,
        question_type: str,
        learner_level: str,
        complexity: float,
        prerequisites: List[PrerequisiteGap],
        misconceptions: List[LearnerMisunderstanding]
    ) -> str:
        """Generate human-readable reasoning for pedagogical analysis"""
        parts = []

        parts.append(f"Question is a '{question_type}' type question.")

        if complexity > 0.7:
            parts.append(f"This is a complex topic ({complexity:.1%}).")
        else:
            parts.append(f"This is a {['simple', 'moderate'][int(complexity > 0.5)]} topic.")

        if prerequisites:
            prereq_names = ', '.join([p.concept for p in prerequisites if p.importance > 0.7])
            if prereq_names:
                parts.append(f"Learner should understand {prereq_names} first.")

        if misconceptions:
            high_conf = [m for m in misconceptions if m.confidence > 0.8]
            if high_conf:
                parts.append(f"Common misconceptions: {high_conf[0].misconception}")

        return ' '.join(parts)


if __name__ == '__main__':
    # Demo: Analyze a few questions
    reasoner = PedagogicalReasoner()

    test_questions = [
        "What is recursion?",
        "How does quicksort work?",
        "Why does this algorithm have O(n log n) complexity?",
        "What's the difference between supervised and unsupervised learning?",
    ]

    for question in test_questions:
        print(f"\n{'='*60}")
        print(f"Question: {question}")
        print('='*60)

        analysis = reasoner.analyze(question, learner_level='intermediate')

        print(f"Type: {analysis.question_type}")
        print(f"Complexity: {analysis.question_complexity:.2f}")
        print(f"Confusion Risk: {analysis.confusion_risk:.2f}")
        print(f"Teaching Approach: {analysis.teaching_approach}")
        print(f"\nPotential Misconceptions:")
        for m in analysis.potential_misconceptions:
            print(f"  - {m.misconception} (confidence: {m.confidence:.1%})")
        print(f"\nTeaching Flow: {' → '.join(analysis.response_flow)}")
        print(f"\nReasoning: {analysis.reasoning}")
