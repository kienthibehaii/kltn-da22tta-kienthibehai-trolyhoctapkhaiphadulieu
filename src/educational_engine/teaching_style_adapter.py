# educational_engine/teaching_style_adapter.py
"""
Teaching Style Adapter

Converts academic answers into conversational, engaging teaching formats:
- Generate analogies for abstract concepts
- Create real-world examples
- Break processes into steps
- Add storytelling elements
- Adjust tone and vocabulary for engagement
"""

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import re
from typing import Dict, List

load_dotenv()


class TeachingStyleAdapter:
    """
    Adapts answer style for engaging educational delivery
    """

    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.5,  # More creative than synthesizer
            timeout=30
        )

    def generate_analogy(self, concept: str, context: str = "") -> str:
        """
        Generate an analogy to explain concept

        "Clustering is like..." for abstract concepts
        """

        prompt = f"""Create a simple, relatable analogy to explain this concept.
Use everyday objects or situations people understand.
Keep it to 1-2 sentences.
Start with "It's like..."

Concept: {concept}
Context: {context}

Analogy:"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            return content.strip()
        except Exception as e:
            print(f"⚠️ Analogy generation error: {e}")
            return f"It's a way to {concept.lower().split()[0]} data or information."

    def generate_real_world_example(self, concept: str, context: str = "") -> str:
        """
        Generate a real-world example to illustrate concept

        Uses familiar domains like shopping, sports, etc.
        """

        prompt = f"""Give a concrete, real-world example of {concept}.
Use a familiar domain like shopping, sports, social media, health, or school.
Make it relatable and easy to visualize.
Keep to 2-3 sentences.

Concept: {concept}
Context: {context}

Example:"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            return content.strip()
        except Exception as e:
            print(f"⚠️ Example generation error: {e}")
            return f"In practice, {concept} is used to..."

    def create_step_by_step(self, process: str) -> List[str]:
        """
        Break a process into numbered, simple steps
        """

        prompt = f"""Break down this process into 4-6 simple, numbered steps.
Each step should be clear and actionable.
Use simple vocabulary.
Number them 1, 2, 3, etc.

Process: {process}

Steps:"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            lines = content.split('\n')
            steps = []
            for line in lines:
                line = line.strip()
                if line:
                    # Remove numbering
                    line = re.sub(r'^[\d+.\-)\s]+', '', line).strip()
                    if line:
                        steps.append(line)

            return steps[:6]
        except Exception as e:
            print(f"⚠️ Step-by-step generation error: {e}")
            return [process]  # Fallback

    def create_comparison(self, concept1: str, concept2: str) -> str:
        """
        Create a clear comparison between two concepts
        """

        prompt = f"""Compare and contrast these two concepts.
Highlight the key differences in 1-2 sentences.
Be conversational.

Concept 1: {concept1}
Concept 2: {concept2}

Comparison:"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            return content.strip()
        except Exception as e:
            print(f"⚠️ Comparison generation error: {e}")
            return f"{concept1} and {concept2} are different approaches."

    def format_as_conversation(self, academic_answer: str, teaching_method: str = "Socratic") -> str:
        """
        Reformat academic answer as conversational dialogue

        Uses teaching methods:
        - Socratic: Question-based discovery
        - Storytelling: Narrative explanation
        - Exploratory: Building understanding progressively
        """

        prompt = f"""Rewrite this academic explanation in a conversational, engaging way.
Sound like a friendly tutor explaining to a student.
Use natural language, not formal academic style.
Make it sound like you're having a real conversation.
Keep it under 300 words.
Teaching method: {teaching_method}

Academic text: {academic_answer}

Conversational explanation:"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            return content.strip()
        except Exception as e:
            print(f"⚠️ Conversation format error: {e}")
            return academic_answer

    def add_metaphors(self, answer: str, count: int = 2) -> List[str]:
        """
        Add metaphors to illustrate abstract concepts
        """

        prompt = f"""Create {count} metaphors or metaphorical expressions for the main ideas in this text.
Metaphors should be vivid and memorable.
Format as a list.

Text: {answer[:400]}...

Metaphors:"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            lines = content.split('\n')
            metaphors = []
            for line in lines:
                line = line.strip()
                if line and len(metaphors) < count:
                    line = re.sub(r'^[-•*]\s+', '', line).strip()
                    if line:
                        metaphors.append(line)

            return metaphors
        except Exception as e:
            print(f"⚠️ Metaphor generation error: {e}")
            return []

    def estimate_engagement_level(self, answer: str) -> str:
        """
        Estimate how engaging/conversational the current answer is

        Returns: 'low' (textbook), 'medium' (mixed), 'high' (engaging)
        """

        # Simple heuristics
        formal_words = len(re.findall(r'\b(therefore|moreover|furthermore|hence|thus|consequently)\b', answer, re.I))
        conversational_words = len(re.findall(r'\b(so|but|actually|basically|really|just|like)\b', answer, re.I))
        questions = answer.count('?')
        exclamations = answer.count('!')

        engagement_score = (conversational_words * 2 + questions * 3 + exclamations * 2) / max(1, (formal_words + 1))

        if engagement_score > 0.5:
            return 'high'
        elif engagement_score > 0.2:
            return 'medium'
        else:
            return 'low'

    def adapt_style(
        self,
        answer: str,
        question_type: str,
        teaching_strategies: List[str] = None,
        target_engagement: str = "high"
    ) -> Dict:
        """
        Complete style adaptation based on question type

        Returns adapted answer with multiple teaching elements
        """

        if teaching_strategies is None:
            teaching_strategies = self._default_strategies_for_type(question_type)

        # Analyze current engagement
        current_engagement = self.estimate_engagement_level(answer)

        # Build conversational version
        conversational = self.format_as_conversation(answer, teaching_method="Socratic")

        # Generate teaching elements based on strategy
        analogies = []
        examples = []
        steps = []
        comparison = ""
        metaphors = []

        main_concept = self._extract_main_concept(answer)

        if 'analogy' in teaching_strategies:
            analogies = [self.generate_analogy(main_concept)]

        if 'examples' in teaching_strategies:
            examples = [self.generate_real_world_example(main_concept)]

        if 'steps' in teaching_strategies and question_type == 'process':
            steps = self.create_step_by_step(answer)

        if 'metaphor' in teaching_strategies:
            metaphors = self.add_metaphors(answer, count=2)

        result = {
            'method': 'socratic_dialogue' if 'analogy' in teaching_strategies else 'direct_instruction',
            'conversational_answer': conversational,
            'analogies': analogies,
            'examples': examples,
            'steps': steps,
            'metaphors': metaphors,
            'current_engagement': current_engagement,
            'target_engagement': target_engagement,
            'engagement_level': target_engagement,
            'needs_enhancement': current_engagement != target_engagement
        }

        return result

    def _default_strategies_for_type(self, question_type: str) -> List[str]:
        """
        Default teaching strategies based on question type
        """

        strategies = {
            'definition': ['analogy', 'examples', 'metaphor'],
            'process': ['steps', 'examples', 'analogy'],
            'comparison': ['comparison', 'examples'],
            'evaluation': ['examples', 'analogy'],
            'problem_solving': ['steps', 'examples'],
            'application': ['examples', 'steps'],
            'reasoning': ['analogy', 'examples', 'metaphor']
        }

        return strategies.get(question_type, ['analogy', 'examples'])

    def _extract_main_concept(self, answer: str) -> str:
        """
        Extract the main concept from answer

        Simple heuristic: first capitalized term or first sentence's subject
        """

        # Find first capitalized term
        matches = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', answer)
        if matches:
            return matches[0]

        # Fallback: first 2-3 words
        words = answer.split()[:3]
        return ' '.join(words) if words else "this concept"
