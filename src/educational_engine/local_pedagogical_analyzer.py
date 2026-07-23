# educational_engine/local_pedagogical_analyzer.py
"""
Local Pedagogical Analyzer - Adaptive Educational Context Without LLM

Performs real-time pedagogical analysis using heuristics, regex patterns,
and domain knowledge. NO LLM calls - all reasoning is local and fast.

Analyzes:
1. Question complexity (0-1 score)
2. Learning intent (conceptual | algorithmic | mathematical | implementation | comparison)
3. Question type (definition | process | comparison | evaluation | problem_solving | application)
4. Confusion risk (0-1 prediction based on user history)
5. Prerequisite gaps (missing foundational concepts)
6. Teaching method recommendation (analogy_first | example_first | step_by_step | etc.)

Speed: <50ms per analysis (no LLM)
"""

import re
from typing import Dict, List, Optional, Tuple
from collections import Counter


class LocalPedagogicalAnalyzer:
    """Analyze questions and user context for pedagogical routing - NO LLM"""

    # Question type detection patterns
    QUESTION_TYPE_PATTERNS = {
        'definition': [
            r'\bwhat\s+is\b', r'\bdefine\b', r'\bmeaning\s+of\b',
            r'\bexplain\s+(\w+)\s+is\b', r'\b(\w+)\s+refers\s+to\b'
        ],
        'process': [
            r'\bhow\s+(?:do|does|to|can)\b', r'\bsteps?\b', r'\bprocess\b',
            r'\balgorithm\b', r'\bprocedure\b', r'\bworkflow\b'
        ],
        'comparison': [
            r'\bdifference\s+between\b', r'\bcompare\b', r'\bcontrast\b',
            r'\bsimilar(?:ities)?\b', r'\bvs(?:\.|ersus)?\b', r'\bversus\b',
            r'\badvan(?:tages|tages)\s+and\s+dis\b'
        ],
        'evaluation': [
            r'\bwhich\s+is\s+(?:better|best|worse|worst)\b', r'\bshould\s+(?:i|we)\b',
            r'\bwhen\s+to\s+use\b', r'\bpros\s+and\s+cons\b', r'\btrade.?off\b'
        ],
        'problem_solving': [
            r'\bhow\s+(?:can\s+)?i\b', r'\bhow\s+(?:can\s+)?(?:we|you|one)\b',
            r'\bsolve\b', r'\bfix\b', r'\bresolve\b', r'\btroubleshoot\b'
        ],
        'application': [
            r'\bexample\b', r'\buse\s+case\b', r'\bapplication\b',
            r'\breal.?world\b', r'\bpractical\b', r'\bimplement\b'
        ],
        'reasoning': [
            r'\bwhy\s+(?:is|are|does|do)\b', r'\breason\b',
            r'\bcause\b', r'\bmotivation\b', r'\bimplication\b'
        ]
    }

    # Learning intent detection (what domain/level)
    LEARNING_INTENT_INDICATORS = {
        'conceptual': ['concept', 'idea', 'principle', 'theory', 'understand', 'intuition'],
        'algorithmic': ['algorithm', 'approach', 'method', 'technique', 'pattern', 'procedure'],
        'mathematical': ['equation', 'formula', 'proof', 'derivative', 'integral', 'theorem'],
        'implementation': ['code', 'implement', 'build', 'create', 'write', 'develop'],
        'comparison': ['compare', 'difference', 'similar', 'contrast', 'versus']
    }

    # Technical complexity markers
    COMPLEXITY_MARKERS = {
        'high': [
            'distributed', 'concurrent', 'optimization', 'trade-off', 'edge case',
            'scalability', 'complexity', 'asymptotic', 'theorem', 'proof',
            'machine learning', 'neural network', 'regression', 'clustering'
        ],
        'medium': [
            'algorithm', 'data structure', 'recursion', 'iteration', 'loop',
            'pattern', 'database', 'API', 'framework', 'design pattern'
        ],
        'low': [
            'basic', 'simple', 'beginner', 'intro', 'fundamentals',
            'what is', 'define', 'example', 'typical'
        ]
    }

    # Prerequisite mapping (concept → prerequisites)
    PREREQUISITE_MAP = {
        'neural_network': ['linear_algebra', 'calculus', 'probability'],
        'machine_learning': ['statistics', 'linear_algebra', 'calculus'],
        'deep_learning': ['neural_network', 'calculus', 'linear_algebra'],
        'nlp': ['machine_learning', 'statistics', 'linguistics_basics'],
        'clustering': ['statistics', 'linear_algebra', 'distance_metrics'],
        'regression': ['statistics', 'linear_algebra', 'calculus'],
        'classification': ['statistics', 'probability', 'linear_algebra'],
        'decision_tree': ['recursion', 'information_theory', 'probability'],
        'graph': ['recursion', 'tree_basics', 'data_structures'],
        'dynamic_programming': ['recursion', 'optimization', 'algorithm_analysis'],
        'distributed_systems': ['concurrency', 'networking', 'system_design'],
    }

    # Common weak areas by experience level
    WEAK_AREAS_BY_LEVEL = {
        'beginner': ['recursion', 'algorithms', 'complexity_analysis', 'edge_cases'],
        'intermediate': ['optimization', 'trade-offs', 'edge_cases', 'performance'],
        'advanced': ['distributed_systems', 'concurrent_programming', 'scalability']
    }

    # Teaching strategy selection rules
    STRATEGY_ROUTING_RULES = [
        # (condition_func, strategy_name)
        # These are evaluated in order
    ]

    def __init__(self):
        """Initialize analyzer with patterns and domain knowledge"""
        self.question_types = {}
        self.learning_intents = {}

    def analyze(
        self,
        question: str,
        user_profile: Optional[Dict] = None,
        recent_interactions: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Comprehensive pedagogical analysis of question + user context

        Returns:
            Dict with: question_type, question_complexity, learning_intent,
                      confusion_risk, prerequisite_gaps, recommended_teaching_method,
                      adaptation_rules, confidence_score
        """

        # Initialize user profile defaults
        user_level = 'intermediate'
        weak_areas = []
        strong_areas = []
        learning_velocity = 'steady'
        topics_explored = []

        if user_profile:
            user_level = user_profile.get('level', 'intermediate')
            weak_areas = user_profile.get('weak_areas', [])
            strong_areas = user_profile.get('strong_areas', [])
            learning_velocity = user_profile.get('learning_velocity', 'steady')
            topics_explored = user_profile.get('topics_explored', [])

        # Normalize question
        normalized_q = question.lower().strip()

        # ANALYSIS PHASE 1: Question characteristics (NO LLM)
        question_type = self._detect_question_type(normalized_q)
        question_complexity = self._calculate_question_complexity(normalized_q)
        learning_intent = self._detect_learning_intent(normalized_q)
        key_concepts = self._extract_key_concepts(normalized_q)

        # ANALYSIS PHASE 2: User-specific analysis (NO LLM)
        confusion_risk = self._predict_confusion_risk(
            question=normalized_q,
            user_level=user_level,
            weak_areas=weak_areas,
            key_concepts=key_concepts,
            recent_interactions=recent_interactions or []
        )

        # ANALYSIS PHASE 3: Prerequisite gap detection (NO LLM)
        prerequisite_gaps = self._identify_prerequisite_gaps(
            key_concepts=key_concepts,
            topics_explored=topics_explored,
            user_level=user_level
        )

        # ANALYSIS PHASE 4: Teaching method selection (NO LLM)
        recommended_teaching_method = self._select_teaching_method(
            question_type=question_type,
            learning_intent=learning_intent,
            question_complexity=question_complexity,
            confusion_risk=confusion_risk,
            user_level=user_level,
            has_prerequisites=len(prerequisite_gaps) > 0
        )

        # ANALYSIS PHASE 5: Generate adaptation rules (NO LLM)
        adaptation_rules = self._generate_adaptation_rules(
            confusion_risk=confusion_risk,
            user_level=user_level,
            question_complexity=question_complexity,
            learning_velocity=learning_velocity,
            has_prerequisites=len(prerequisite_gaps) > 0
        )

        # Calculate confidence in analysis
        confidence_score = self._calculate_confidence_score(
            question_length=len(question.split()),
            clarity=self._estimate_question_clarity(normalized_q),
            has_user_profile=user_profile is not None
        )

        return {
            'question_type': question_type,
            'question_complexity': question_complexity,
            'learning_intent': learning_intent,
            'key_concepts': key_concepts,
            'confusion_risk': confusion_risk,
            'prerequisite_gaps': prerequisite_gaps,
            'recommended_teaching_method': recommended_teaching_method,
            'adaptation_rules': adaptation_rules,
            'confidence_score': confidence_score,
            'user_level_detected': user_level,
            'analysis_metadata': {
                'user_level': user_level,
                'weak_areas': weak_areas[:3],  # Top 3
                'strong_areas': strong_areas[:3],
                'learning_velocity': learning_velocity
            }
        }

    def _detect_question_type(self, question: str) -> str:
        """Detect question type using regex patterns - NO LLM"""

        scores = {}
        for qtype, patterns in self.QUESTION_TYPE_PATTERNS.items():
            count = sum(
                1 for pattern in patterns
                if re.search(pattern, question, re.IGNORECASE)
            )
            scores[qtype] = count

        detected_type = max(scores, key=scores.get) if scores else 'definition'
        return detected_type

    def _calculate_question_complexity(self, question: str) -> float:
        """Calculate question complexity 0-1 without LLM"""

        complexity = 0.3  # base

        # Word count indicator
        words = question.split()
        if len(words) < 5:
            complexity -= 0.1
        elif len(words) > 25:
            complexity += 0.15

        # Technical terms
        high_complex = sum(1 for term in self.COMPLEXITY_MARKERS['high']
                          if term in question.lower())
        medium_complex = sum(1 for term in self.COMPLEXITY_MARKERS['medium']
                            if term in question.lower())

        complexity += (high_complex * 0.2)
        complexity += (medium_complex * 0.1)

        # Multiple aspects (conjunctions)
        conjunctions = len(re.findall(r'\band\b|\bor\b|\bbut\b', question, re.I))
        complexity += (conjunctions * 0.1)

        # Multi-part questions
        if question.count('?') > 1:
            complexity += 0.15

        return min(1.0, max(0.0, complexity))

    def _detect_learning_intent(self, question: str) -> str:
        """Detect learning intent: conceptual|algorithmic|mathematical|implementation|comparison"""

        scores = {}
        q_lower = question.lower()

        for intent, keywords in self.LEARNING_INTENT_INDICATORS.items():
            count = sum(1 for kw in keywords if kw in q_lower)
            scores[intent] = count

        detected_intent = max(scores, key=scores.get) if scores else 'conceptual'
        return detected_intent

    def _extract_key_concepts(self, question: str) -> List[str]:
        """Extract key technical concepts from question"""

        # Simple concept extraction - look for capitalized terms + known keywords
        concepts = []

        # Known concept keywords
        concept_keywords = [
            'neural', 'network', 'decision', 'tree', 'clustering', 'regression',
            'classification', 'algorithm', 'recursion', 'optimization', 'dynamic',
            'programming', 'graph', 'tree', 'sorting', 'searching', 'hashing',
            'queue', 'stack', 'linked', 'list', 'array', 'database', 'sql',
            'api', 'rest', 'graphql', 'cache', 'distributed', 'concurrent',
            'machine', 'learning', 'data', 'science', 'analysis'
        ]

        q_lower = question.lower()
        for concept in concept_keywords:
            if concept in q_lower:
                concepts.append(concept)

        # Also extract capitalized terms (likely proper nouns/concepts)
        capitalized = re.findall(r'\b[A-Z][a-z]+\b', question)
        concepts.extend([c.lower() for c in capitalized])

        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for c in concepts:
            if c not in seen:
                seen.add(c)
                unique.append(c)

        return unique[:5]  # Return top 5

    def _predict_confusion_risk(
        self,
        question: str,
        user_level: str,
        weak_areas: List[str],
        key_concepts: List[str],
        recent_interactions: List[Dict]
    ) -> float:
        """Predict likelihood user will be confused - NO LLM"""

        risk = 0.3  # base risk

        # Factor 1: User level vs question complexity
        q_words = question.split()
        if user_level == 'beginner' and len(q_words) > 20:
            risk += 0.15
        elif user_level == 'advanced' and len(q_words) < 5:
            risk -= 0.1

        # Factor 2: Key concepts in weak areas
        weak_area_keywords = []
        for area in weak_areas:
            weak_area_keywords.extend(area.lower().split())

        concept_overlap = sum(1 for concept in key_concepts
                             if any(weak in concept for weak in weak_area_keywords))
        risk += (concept_overlap * 0.15)

        # Factor 3: Recent struggle patterns
        if recent_interactions:
            recent_struggles = sum(
                1 for interaction in recent_interactions[-5:]  # Last 5
                if interaction.get('user_struggled', False)
            )
            risk += (recent_struggles * 0.05)

        # Factor 4: Question clarity
        clarity = self._estimate_question_clarity(question)
        if clarity < 0.4:
            risk += 0.15  # Unclear questions = higher confusion

        return min(1.0, max(0.0, risk))

    def _identify_prerequisite_gaps(
        self,
        key_concepts: List[str],
        topics_explored: List[str],
        user_level: str
    ) -> List[str]:
        """Identify missing prerequisite concepts"""

        gaps = []
        topics_lower = [t.lower() for t in topics_explored]

        # Check prerequisites for each key concept
        for concept in key_concepts:
            if concept in self.PREREQUISITE_MAP:
                prerequisites = self.PREREQUISITE_MAP[concept]
                for prereq in prerequisites:
                    if prereq not in topics_lower:
                        gaps.append(prereq)

        # Also check typical gaps for user level
        if user_level in self.WEAK_AREAS_BY_LEVEL:
            potential_gaps = self.WEAK_AREAS_BY_LEVEL[user_level]
            for gap in potential_gaps:
                if gap not in topics_lower and gap not in gaps:
                    gaps.append(gap)

        # Deduplicate
        return list(set(gaps))[:3]  # Top 3 gaps

    def _select_teaching_method(
        self,
        question_type: str,
        learning_intent: str,
        question_complexity: float,
        confusion_risk: float,
        user_level: str,
        has_prerequisites: bool
    ) -> str:
        """Select optimal teaching method - routing logic"""

        # Rule 1: If high confusion risk, use step_by_step
        if confusion_risk > 0.7:
            return 'step_by_step'

        # Rule 2: If prerequisites missing, suggest remedial first
        if has_prerequisites:
            return 'remedial_prerequisites'

        # Rule 3: User-level based routing
        if user_level == 'beginner':
            if learning_intent == 'conceptual':
                return 'analogy_first'
            elif learning_intent == 'mathematical':
                return 'example_first'
            else:
                return 'example_first'

        elif user_level == 'advanced':
            if learning_intent == 'mathematical':
                return 'mathematical'
            elif learning_intent == 'algorithmic':
                return 'conceptual'
            else:
                return 'conceptual'

        # Rule 4: Question type based routing
        if question_type == 'process':
            return 'step_by_step'
        elif question_type == 'comparison':
            return 'comparison_table'
        elif question_type == 'definition':
            return 'analogy_first'

        # Rule 5: Learning intent based routing
        if learning_intent == 'implementation':
            return 'example_first'
        elif learning_intent == 'comparison':
            return 'comparison_table'

        # Default
        return 'balanced'

    def _generate_adaptation_rules(
        self,
        confusion_risk: float,
        user_level: str,
        question_complexity: float,
        learning_velocity: str,
        has_prerequisites: bool
    ) -> Dict[str, str]:
        """Generate IF/THEN rules for response adaptation"""

        rules = {}

        # IF confused THEN ...
        if confusion_risk > 0.7:
            rules['if_confused'] = 'escalate_to_step_by_step'
        elif confusion_risk > 0.5:
            rules['if_confused'] = 'add_more_examples'
        else:
            rules['if_confused'] = 'maintain_pace'

        # IF advanced THEN ...
        if user_level == 'advanced':
            rules['if_advanced'] = 'skip_basics_focus_depth'
        elif user_level == 'intermediate':
            rules['if_advanced'] = 'skip_analogies_focus_technical'
        else:
            rules['if_advanced'] = 'provide_extension'

        # IF struggling THEN ...
        if question_complexity > 0.7:
            rules['if_struggling'] = 'add_worked_examples'
        elif question_complexity > 0.4:
            rules['if_struggling'] = 'add_one_example'
        else:
            rules['if_struggling'] = 'maintain'

        # IF time_limited THEN ...
        if learning_velocity == 'fast':
            rules['if_time_limited'] = 'summarize_concisely'
        elif learning_velocity == 'slow':
            rules['if_time_limited'] = 'expand_gradually'
        else:
            rules['if_time_limited'] = 'balanced'

        # IF first_time_topic THEN ...
        if has_prerequisites:
            rules['if_first_time'] = 'add_prerequisites_first'
        else:
            rules['if_first_time'] = 'start_from_basics'

        return rules

    def _estimate_question_clarity(self, question: str) -> float:
        """Estimate how clear/well-formed the question is (0-1)"""

        clarity = 0.7  # base

        # Check for question marks
        if '?' not in question:
            clarity -= 0.2

        # Check for complete sentences
        if len(question.split()) < 4:
            clarity -= 0.2
        elif len(question.split()) > 50:
            clarity -= 0.1

        # Check for unclear pronouns
        pronouns = ['it', 'this', 'that', 'these', 'those']
        pronoun_count = sum(1 for p in pronouns if f' {p} ' in f' {question.lower()} ')
        if pronoun_count > 3:
            clarity -= 0.15

        return min(1.0, max(0.0, clarity))

    def _calculate_confidence_score(
        self,
        question_length: int,
        clarity: float,
        has_user_profile: bool
    ) -> float:
        """Calculate confidence in the pedagogical analysis"""

        confidence = 0.6  # base

        # Longer questions = more confident
        if question_length > 10:
            confidence += 0.15
        elif question_length < 4:
            confidence -= 0.1

        # Clear questions = more confident
        confidence += (clarity * 0.2)

        # User profile = more confident
        if has_user_profile:
            confidence += 0.15

        return min(1.0, max(0.0, confidence))


# Standalone helper functions

def quick_question_type(question: str) -> str:
    """Quick question type detection - single function version"""
    analyzer = LocalPedagogicalAnalyzer()
    return analyzer._detect_question_type(question.lower())


def quick_complexity(question: str) -> float:
    """Quick complexity score"""
    analyzer = LocalPedagogicalAnalyzer()
    return analyzer._calculate_question_complexity(question.lower())


def quick_analyze(
    question: str,
    user_profile: Dict = None
) -> Dict:
    """Quick full analysis"""
    analyzer = LocalPedagogicalAnalyzer()
    return analyzer.analyze(question, user_profile)
