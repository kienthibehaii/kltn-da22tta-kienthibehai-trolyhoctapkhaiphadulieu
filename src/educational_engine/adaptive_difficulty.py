# educational_engine/adaptive_difficulty.py
"""
Adaptive Difficulty System

Generates multiple versions of answers at different complexity levels:
- Beginner: Simple vocabulary, many examples, concrete explanations
- Intermediate: Balanced technical and practical, some formulas
- Advanced: Technical vocabulary, deep explanations, research references
"""

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Dict

load_dotenv()


class AdaptiveDifficulty:
    """
    Generates answer versions at different difficulty levels
    """

    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.4,
            timeout=30
        )

        self.difficulty_levels = {
            'beginner': {
                'vocabulary': 'simple',
                'examples': 'many',
                'jargon': 'explain_all',
                'depth': 'surface_level',
                'formulas': 'none',
                'metaphors': 'many',
                'tone': 'friendly',
                'length': 'short'
            },
            'intermediate': {
                'vocabulary': 'mixed',
                'examples': 'some',
                'jargon': 'explain_new',
                'depth': 'moderate',
                'formulas': 'some',
                'metaphors': 'few',
                'tone': 'professional',
                'length': 'medium'
            },
            'advanced': {
                'vocabulary': 'technical',
                'examples': 'specific',
                'jargon': 'assume_knowledge',
                'depth': 'deep',
                'formulas': 'many',
                'metaphors': 'none',
                'tone': 'academic',
                'length': 'comprehensive'
            }
        }

    def simplify_for_beginners(self, answer: str) -> str:
        """
        Simplify answer for complete beginners

        - Replace technical terms with analogies
        - Use short sentences
        - Add concrete examples
        - Avoid formulas
        - Use conversational tone
        """

        prompt = f"""Rewrite this for a complete beginner who has no prior knowledge.
Rules:
1. Use simple, everyday vocabulary (8th grade level)
2. Replace technical terms with "it's like..." analogies
3. Use short sentences (under 15 words each)
4. Add 2-3 concrete real-world examples
5. No formulas or mathematics
6. Make it conversational and friendly
7. Keep under 200 words

Original: {answer}

Beginner version:"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            return content.strip()
        except Exception as e:
            print(f"⚠️ Beginner simplification error: {e}")
            return answer[:200] + "..."

    def enrich_for_advanced(self, answer: str) -> str:
        """
        Enrich answer for advanced learners

        - Add technical depth
        - Include mathematical notation
        - Reference research/algorithms
        - Discuss edge cases
        - Add implementation details
        """

        prompt = f"""Enrich this explanation for advanced learners/researchers.
Additions:
1. Include mathematical formulas where relevant
2. Reference specific algorithms or research papers if applicable
3. Discuss computational complexity or advanced concepts
4. Address edge cases and special considerations
5. Add implementation details or pseudo-code if relevant
6. Use technical terminology precisely
7. Maintain academic rigor

Original: {answer}

Advanced version:"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            return content.strip()
        except Exception as e:
            print(f"⚠️ Advanced enrichment error: {e}")
            return answer

    def create_intermediate_version(self, answer: str) -> str:
        """
        Create balanced intermediate version

        - Technical terms explained
        - Mix of theory and practice
        - Some formulas explained
        - Practical examples
        """

        prompt = f"""Create a well-balanced explanation for intermediate learners.
Balance:
1. Explain technical terms when first introduced
2. Mix theoretical concepts with practical examples
3. Include key formulas with brief explanations
4. Reference both "why" and "how"
5. Assume basic knowledge of the subject
6. Include 2-3 relevant examples
7. Professional but accessible tone

Original: {answer}

Intermediate version:"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            return content.strip()
        except Exception as e:
            print(f"⚠️ Intermediate creation error: {e}")
            return answer

    def detect_user_level_from_history(self, question_history: list = None, quiz_scores: list = None) -> str:
        """
        Detect user's proficiency level from history

        Based on:
        - Types of questions asked
        - Quiz performance
        - Interaction patterns
        """

        if not question_history:
            return "intermediate"  # Default

        # Simple heuristics
        advanced_keywords = ['algorithm', 'complexity', 'optimization', 'implementation', 'architecture']
        beginner_keywords = ['what is', 'explain', 'define', 'how to', 'basics']

        advanced_count = sum(1 for q in question_history if any(kw in q.lower() for kw in advanced_keywords))
        beginner_count = sum(1 for q in question_history if any(kw in q.lower() for kw in beginner_keywords))

        # Quiz scores
        if quiz_scores:
            avg_score = sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0.5
            if avg_score > 0.8:
                return "advanced"
            elif avg_score < 0.5:
                return "beginner"

        # Question-based detection
        if advanced_count > beginner_count:
            return "advanced"
        elif beginner_count > advanced_count:
            return "beginner"

        return "intermediate"

    def adjust_difficulty(self, answer: str, target_level: str) -> str:
        """
        Adjust answer to target difficulty level

        Maps to one of: beginner, intermediate, advanced
        """

        level = target_level.lower()

        if level == 'beginner':
            return self.simplify_for_beginners(answer)
        elif level == 'advanced':
            return self.enrich_for_advanced(answer)
        else:  # intermediate
            return self.create_intermediate_version(answer)

    def generate_versions(
        self,
        answer: str,
        teaching_answer: str = None,
        question_type: str = None,
        concepts: list = None
    ) -> Dict[str, str]:
        """
        Generate all three difficulty versions at once

        Returns dict with beginner, intermediate, advanced
        """

        # Use teaching answer if available (already conversational)
        base_answer = teaching_answer if teaching_answer else answer

        print("🔄 Generating difficulty versions...")

        beginner = self.simplify_for_beginners(base_answer)
        advanced = self.enrich_for_advanced(base_answer)
        intermediate = self.create_intermediate_version(base_answer)

        return {
            'beginner': beginner,
            'intermediate': intermediate,
            'advanced': advanced,
            'generated_at': self._get_timestamp()
        }

    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()

    def select_version(self, versions: Dict[str, str], user_level: str) -> str:
        """
        Select appropriate version for user

        Returns the text appropriate for user level
        """

        level = user_level.lower()
        return versions.get(level, versions['intermediate'])

    def get_difficulty_description(self, level: str) -> Dict:
        """
        Get description of difficulty level
        """

        descriptions = {
            'beginner': {
                'name': 'Beginner',
                'emoji': '🌱',
                'description': 'Simple explanation with everyday examples',
                'vocabulary': 'Simple',
                'includes': ['Analogies', 'Real-world examples', 'No formulas'],
                'target_audience': 'New to topic'
            },
            'intermediate': {
                'name': 'Intermediate',
                'emoji': '📚',
                'description': 'Balanced technical and practical content',
                'vocabulary': 'Mixed',
                'includes': ['Explained terms', 'Examples', 'Some formulas'],
                'target_audience': 'Some background knowledge'
            },
            'advanced': {
                'name': 'Advanced',
                'emoji': '🚀',
                'description': 'Deep technical explanation with research depth',
                'vocabulary': 'Technical',
                'includes': ['Formulas', 'Algorithms', 'Edge cases', 'Research references'],
                'target_audience': 'Expert level'
            }
        }

        return descriptions.get(level.lower(), descriptions['intermediate'])
