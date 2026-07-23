# educational_engine/response_optimizer.py
"""
Response Optimizer

Optimizes responses for:
- Appropriate length (not too long, not too short)
- Clarity and readability
- Completeness of explanation
- Learning value and engagement
"""

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Dict, List
import re

load_dotenv()


class ResponseOptimizer:
    """
    Optimizes answer quality and pedagogical value
    """

    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.4,
            timeout=30
        )

    def calculate_optimal_length(self, question: str, question_type: str = "general") -> int:
        """
        Calculate optimal answer length in words

        Based on question type:
        - definition: 100-200 words
        - process: 200-400 words
        - comparison: 200-300 words
        - evaluation: 300-500 words
        - reasoning: 200-400 words
        """

        optimal_lengths = {
            'definition': 150,
            'process': 300,
            'comparison': 250,
            'evaluation': 400,
            'application': 250,
            'problem_solving': 300,
            'reasoning': 300
        }

        base_length = optimal_lengths.get(question_type, 250)

        # Adjust based on question complexity
        question_complexity = len(question.split()) / 10  # Rough estimate
        adjustment = 1 + (min(question_complexity - 1, 1) * 0.2)

        return int(base_length * adjustment)

    def count_words(self, text: str) -> int:
        """Count words in text"""
        return len(text.split())

    def summarize_answer(self, answer: str, target_words: int) -> str:
        """
        Summarize answer to target word count

        Preserves most important information
        """

        current_words = self.count_words(answer)

        if current_words <= target_words * 1.1:
            return answer  # Already good length

        # Calculate target percentage
        target_percentage = target_words / max(1, current_words)

        prompt = f"""Summarize this answer to approximately {target_words} words (currently {current_words} words).
Keep the most important information.
Maintain clarity and completeness.
Remove redundant or less important details.
Keep it conversational.

Original answer: {answer}

Summarized ({target_words} words):"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            return content.strip()
        except Exception as e:
            print(f"⚠️ Summarization error: {e}")
            # Fallback: truncate intelligently
            sentences = answer.split('. ')
            truncated = '. '.join(sentences[:3]) + '.'
            return truncated

    def expand_answer(self, answer: str, target_words: int) -> str:
        """
        Expand answer to target word count

        Adds details and examples while maintaining clarity
        """

        current_words = self.count_words(answer)

        if current_words >= target_words * 0.9:
            return answer  # Already good length

        prompt = f"""Expand this answer to approximately {target_words} words (currently {current_words} words).
Add:
1. More specific examples
2. Additional details or context
3. Relevant background information
4. Implications or applications
Maintain conversational tone.
Keep logical flow.

Original answer: {answer}

Expanded ({target_words} words):"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            return content.strip()
        except Exception as e:
            print(f"⚠️ Expansion error: {e}")
            return answer

    def detect_clarity_issues(self, answer: str) -> List[str]:
        """
        Detect potential clarity issues

        Returns list of issues found
        """

        issues = []

        # Check for very long sentences
        sentences = answer.split('. ')
        long_sentences = [s for s in sentences if len(s.split()) > 25]
        if len(long_sentences) > 0:
            issues.append(f"Has {len(long_sentences)} very long sentences (>25 words) - hard to parse")

        # Check for undefined jargon
        technical_terms = re.findall(r'\b([A-Z][a-z]+(?:_[a-z]+)?)\b', answer)
        undefined = len(technical_terms)
        if undefined > 5:
            issues.append(f"Uses {undefined} technical terms without clear definitions")

        # Check for passive voice prevalence
        passive_patterns = re.findall(r'\bis\s+\w+ed\b|\bwas\s+\w+ed\b|\bbeing\s+\w+ed\b', answer)
        if len(passive_patterns) > len(answer.split()) * 0.1:
            issues.append("Heavy use of passive voice - makes text less engaging")

        # Check for lack of examples
        example_keywords = ['example', 'instance', 'such as', 'like', 'including', 'for instance']
        has_examples = any(kw in answer.lower() for kw in example_keywords)
        if not has_examples:
            issues.append("No examples or concrete illustrations")

        # Check for clarity of structure
        if answer.count('\n') == 0 and len(answer) > 500:
            issues.append("Dense paragraph with no breaks - hard to scan")

        return issues

    def improve_clarity(self, answer: str) -> str:
        """
        Improve clarity of answer

        Uses LLM to restructure and simplify
        """

        issues = self.detect_clarity_issues(answer)

        if not issues:
            return answer  # Already clear

        prompt = f"""Improve the clarity of this answer.
Issues to fix: {', '.join(issues)}

Improvements:
1. Use shorter sentences
2. Add specific examples
3. Use active voice where possible
4. Break into paragraphs
5. Use clear transitions between ideas
6. Simplify technical terms
Keep the same meaning and information.

Original: {answer}

Improved:"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            return content.strip()
        except Exception as e:
            print(f"⚠️ Clarity improvement error: {e}")
            return answer

    def calculate_completeness_score(self, answer: str, question: str) -> float:
        """
        Calculate completeness score (0.0-1.0)

        Checks:
        - Answers the question directly
        - Provides reasoning
        - Includes examples
        - Has conclusion
        """

        score = 0.5  # Start with baseline

        # Check if directly answers question
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        overlap = len(question_words & answer_words)
        if overlap >= 2:
            score += 0.15

        # Check for depth indicators
        depth_keywords = ['because', 'reason', 'cause', 'why', 'result', 'effect', 'since']
        if any(kw in answer.lower() for kw in depth_keywords):
            score += 0.1

        # Check for examples
        example_keywords = ['example', 'instance', 'such as', 'like', 'e.g.', 'illustration']
        if any(kw in answer.lower() for kw in example_keywords):
            score += 0.15

        # Check for conclusion
        if 'conclusion' in answer.lower() or 'summary' in answer.lower() or 'ultimately' in answer.lower():
            score += 0.1

        # Check length adequacy
        word_count = len(answer.split())
        if 100 <= word_count <= 500:
            score += 0.05

        return min(1.0, score)

    def calculate_learning_value_score(self, answer: str, teaching_answer: str = None) -> float:
        """
        Calculate learning value (educational quality)

        Checks:
        - Engagement (conversational elements)
        - Structure (organized)
        - Examples (concrete)
        - Clarity (understandable)
        """

        score = 0.5

        # Engagement
        engagement_words = ['actually', 'importantly', 'interesting', 'note that', 'think about']
        if any(kw in answer.lower() for kw in engagement_words):
            score += 0.15

        # Structure markers
        structure_markers = ['first', 'second', 'next', 'finally', 'importantly', 'however']
        if any(kw in answer.lower() for kw in structure_markers):
            score += 0.1

        # Concrete examples
        example_words = ['example', 'for instance', 'such as', 'like', 'consider']
        example_count = sum(answer.lower().count(kw) for kw in example_words)
        if example_count > 0:
            score += min(0.15, example_count * 0.05)

        # Simplicity (fewer complex terms)
        complex_terms = re.findall(r'\b[a-z]*tion\b|\b[a-z]*ment\b', answer.lower())
        if len(complex_terms) < len(answer.split()) * 0.05:
            score += 0.1

        return min(1.0, score)

    def optimize(
        self,
        answer: str,
        teaching_answer: str = None,
        visual_explanation: str = None,
        question_type: str = "general"
    ) -> Dict:
        """
        Complete optimization of answer

        Returns optimized answer with scores and metadata
        """

        # Use teaching answer if available
        base_answer = teaching_answer if teaching_answer else answer

        # Calculate optimal length
        optimal_length = self.calculate_optimal_length(question_type)
        current_length = self.count_words(base_answer)

        # Adjust length
        if current_length > optimal_length * 1.3:
            optimized = self.summarize_answer(base_answer, int(optimal_length * 1.1))
        elif current_length < optimal_length * 0.7:
            optimized = self.expand_answer(base_answer, int(optimal_length * 0.9))
        else:
            optimized = base_answer

        # Improve clarity if issues detected
        clarity_issues = self.detect_clarity_issues(optimized)
        if clarity_issues:
            optimized = self.improve_clarity(optimized)

        # Calculate quality scores
        completeness = self.calculate_completeness_score(optimized, question_type)
        clarity = 1.0 - min(1.0, len(clarity_issues) * 0.2)
        learning_value = self.calculate_learning_value_score(optimized)

        # Average score
        overall_quality = (completeness + clarity + learning_value) / 3

        result = {
            'optimized_answer': optimized,
            'original_length': current_length,
            'optimized_length': self.count_words(optimized),
            'optimal_length': optimal_length,
            'clarity_issues': clarity_issues,
            'clarity_score': clarity,
            'completeness_score': completeness,
            'learning_value': learning_value,
            'overall_quality': overall_quality,
            'optimizations_applied': {
                'length_adjusted': current_length != self.count_words(optimized),
                'clarity_improved': len(clarity_issues) > 0,
                'completeness_checked': True
            },
            'recommendations': self._generate_recommendations(
                clarity, completeness, learning_value, clarity_issues
            )
        }

        return result

    def _generate_recommendations(
        self,
        clarity: float,
        completeness: float,
        learning_value: float,
        issues: List[str]
    ) -> List[str]:
        """
        Generate recommendations for improvement
        """

        recommendations = []

        if clarity < 0.7:
            recommendations.append("Consider simplifying language for better clarity")

        if completeness < 0.6:
            recommendations.append("Add more concrete examples and explanations")

        if learning_value < 0.6:
            recommendations.append("Make the explanation more engaging and conversational")

        if issues:
            recommendations.extend([f"Address: {issue}" for issue in issues[:2]])

        return recommendations[:3]  # Max 3 recommendations
