"""
Teaching Flow Orchestrator - 7-Step Tutor Teaching Flow

Structures AI Tutor responses according to proven pedagogical sequence:

1. Intuitive Explanation - Simple, non-technical overview
2. Real-World Example - Concrete, relatable example  
3. Technical Explanation - Full technical detail
4. How It Works - Step-by-step process/mechanism
5. Common Mistakes - Pitfalls and misconceptions
6. Quick Summary - Concise recap
7. Understanding Check - Quiz question or check

This ensures responses are:
- Beginner-friendly initially
- Progressively deeper
- Contextual and memorable
- Mistake-aware
- Actionable
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class TeachingFlowStep:
    """One step in the 7-step teaching flow"""
    step_number: int  # 1-7
    step_name: str
    content: str  # The actual content
    is_filled: bool = False


class TeachingFlowOrchestrator:
    """Orchestrate 7-step teaching flow for tutor-like responses"""

    # Template prompts for each step
    STEP_PROMPTS = {
        1: {
            'name': 'Intuitive Explanation',
            'instruction': '''Create a simple, intuitive explanation that a 10-year-old could understand.
Use everyday language. NO technical jargon. Focus on the "why" and "what" not "how".
1-2 sentences max.''',
            'quality_criteria': [
                'Avoids technical terms',
                'Uses familiar concepts',
                'Answers the core question simply',
                'Engaging and clear'
            ]
        },
        2: {
            'name': 'Real-World Example',
            'instruction': '''Give a concrete, real-world example the learner can visualize.
Use everyday scenarios. Not abstract. Make it relatable to their experience.
2-3 sentences max.''',
            'quality_criteria': [
                'Concrete and specific',
                'Relatable to target audience',
                'Illustrates the concept clearly',
                'Not oversimplified'
            ]
        },
        3: {
            'name': 'Technical Explanation',
            'instruction': '''Now provide the full technical explanation with proper terminology.
Define new concepts as you introduce them. Link back to the intuitive explanation.
3-4 sentences max.''',
            'quality_criteria': [
                'Uses correct technical terminology',
                'Precisely defined',
                'Logically structured',
                'Connects to Step 1'
            ]
        },
        4: {
            'name': 'How It Works (Process/Mechanism)',
            'instruction': '''Explain the step-by-step process or mechanism.
For algorithms/processes: break into clear steps (1, 2, 3...).
For concepts: explain the flow/relationships.
Include the "why" for each step.
4-6 bullet points or sentences.''',
            'quality_criteria': [
                'Logical progression',
                'Clear steps or phases',
                'Explains "why" for each step',
                'Handles edge cases if needed'
            ]
        },
        5: {
            'name': 'Common Mistakes & Misconceptions',
            'instruction': '''Highlight the most common pitfalls and misconceptions learners have.
Format: "❌ Mistake: X | ✓ Reality: Y"
Include 2-3 common mistakes specific to this topic.
Help learners avoid these errors.''',
            'quality_criteria': [
                'Identifies real misconceptions',
                'Explains why they\'re wrong',
                'Provides correct understanding',
                'Helps prevent future errors'
            ]
        },
        6: {
            'name': 'Quick Summary',
            'instruction': '''Create a concise 1-2 sentence summary that captures the essence.
Should be quotable and memorable. Think "TL;DR but useful."''',
            'quality_criteria': [
                'Captures core concept',
                'Concise (1-2 sentences)',
                'Memorable',
                'Actionable'
            ]
        },
        7: {
            'name': 'Understanding Check',
            'instruction': '''Ask a question to check if the learner understands.
Not too easy, not too hard. 
Avoid yes/no questions. Should require explaining or applying the concept.
Format: "Try this: [question]" or "Can you explain: [scenario]?"''',
            'quality_criteria': [
                'Tests real understanding',
                'Appropriate difficulty',
                'Requires application or explanation',
                'Provides good feedback opportunity'
            ]
        }
    }

    # Different flows for different learner levels
    LEVEL_CUSTOMIZATIONS = {
        'beginner': {
            1: {'emphasis': 'Make it very simple, almost childish analogies'},
            2: {'emphasis': 'Use very familiar, everyday scenarios'},
            3: {'emphasis': 'Introduce terms slowly, define each one'},
            4: {'emphasis': 'More granular steps, explain each step\'s purpose'},
            5: {'emphasis': 'Address their most likely misconceptions'},
            7: {'emphasis': 'Easy first, harder follow-up optional'},
        },
        'intermediate': {
            1: {'emphasis': 'Balance simplicity with some technical concepts'},
            2: {'emphasis': 'Real-world examples with some complexity'},
            3: {'emphasis': 'Full technical depth, assume some background'},
            4: {'emphasis': 'Include optimization considerations'},
            5: {'emphasis': 'Address intermediate-level pitfalls'},
            7: {'emphasis': 'Make them think about trade-offs'},
        },
        'advanced': {
            1: {'emphasis': 'Skip if obvious, or give elegant intuition'},
            2: {'emphasis': 'Complex real-world scenarios, possibly distributed'},
            3: {'emphasis': 'Assume deep technical knowledge, include complexity analysis'},
            4: {'emphasis': 'Include implementation details, optimization'},
            5: {'emphasis': 'Edge cases, performance pitfalls, scalability issues'},
            7: {'emphasis': 'Challenge them with open-ended questions'},
        }
    }

    # Question type specific customizations
    TYPE_CUSTOMIZATIONS = {
        'algorithm': {
            1: {'use': 'analogy to real-world task'},
            4: {'use': 'step-by-step walkthrough of algorithm'},
            7: {'use': 'trace through algorithm with example input'},
        },
        'definition': {
            1: {'use': 'simple definition'},
            2: {'use': 'concrete instance or object'},
            4: {'use': 'components and relationships'},
        },
        'process': {
            1: {'use': 'high-level flow'},
            4: {'use': 'detailed sequential steps'},
            5: {'use': 'wrong execution paths'},
        },
        'comparison': {
            1: {'use': 'simple trade-off'},
            2: {'use': 'when each is used'},
            3: {'use': 'technical differences'},
            4: {'use': 'when to choose which'},
            7: {'use': 'when would you use X vs Y?'},
        },
        'mathematical': {
            1: {'use': 'intuitive meaning of formula'},
            3: {'use': 'formula and proof'},
            4: {'use': 'derivation or application'},
            7: {'use': 'calculate or derive with example'},
        }
    }

    def __init__(self):
        """Initialize teaching flow orchestrator"""
        pass

    def generate_prompts_for_steps(
        self,
        question: str,
        answer: str,
        pedagogical_analysis: Dict,
        learner_level: str = 'intermediate',
        question_type: str = 'definition'
    ) -> Dict[int, str]:
        """
        Generate specific prompts for each of the 7 steps

        Args:
            question: Original learner question
            answer: Retrieved/generated answer
            pedagogical_analysis: From PedagogicalReasoner.analyze()
            learner_level: beginner|intermediate|advanced
            question_type: algorithm|definition|process|comparison|mathematical...

        Returns:
            Dict mapping step number (1-7) → specific prompt for LLM
        """

        prompts = {}

        for step_num in range(1, 8):
            base_prompt = self.STEP_PROMPTS[step_num]['instruction']

            # Apply learner level customization
            if step_num in self.LEVEL_CUSTOMIZATIONS[learner_level]:
                emphasis = self.LEVEL_CUSTOMIZATIONS[learner_level][step_num]['emphasis']
                base_prompt += f"\n\n💡 Hint for {learner_level} learner: {emphasis}"

            # Apply question type customization
            if question_type in self.TYPE_CUSTOMIZATIONS:
                if step_num in self.TYPE_CUSTOMIZATIONS[question_type]:
                    custom = self.TYPE_CUSTOMIZATIONS[question_type][step_num]['use']
                    base_prompt += f"\n📌 For {question_type} questions, {custom}."

            # Add context from pedagogical analysis
            if pedagogical_analysis:
                if step_num == 5 and pedagogical_analysis.get('potential_misconceptions'):
                    misconceptions = pedagogical_analysis.get('potential_misconceptions', [])
                    if misconceptions:
                        misconceptions_text = '\n'.join([
                            f"- {m.get('misconception', '')}"
                            for m in misconceptions[:3]
                        ])
                        base_prompt += f"\n\nCommon misconceptions to address:\n{misconceptions_text}"

            # Full step prompt
            full_prompt = f"""STEP {step_num}: {self.STEP_PROMPTS[step_num]['name'].upper()}

Context:
- Original question: "{question}"
- Topic: {question_type}
- Learner level: {learner_level}

{base_prompt}

Content to transform: {answer[:500]}

Provide ONLY the content for this step. No labels, no numbering."""

            prompts[step_num] = full_prompt

        return prompts

    def create_combined_prompt(
        self,
        question: str,
        answer: str,
        pedagogical_analysis: Dict,
        learner_level: str = 'intermediate',
        question_type: str = 'definition'
    ) -> str:
        """
        Create a SINGLE combined prompt that requests all 7 steps at once

        This is more efficient than 7 separate LLM calls.

        Args:
            question: Original learner question
            answer: Retrieved/generated answer
            pedagogical_analysis: From PedagogicalReasoner.analyze()
            learner_level: beginner|intermediate|advanced
            question_type: algorithm|definition|process|comparison|mathematical...

        Returns:
            Single prompt requesting all 7 steps as JSON
        """

        misconceptions_context = ""
        if pedagogical_analysis and isinstance(pedagogical_analysis, dict):
            misconceptions = pedagogical_analysis.get('potential_misconceptions', [])
            if misconceptions:
                misconceptions_context = "Common misconceptions learners have:\n"
                for m in misconceptions[:2]:
                    misconceptions_context += f"- {m}\n"

        combined_prompt = f"""You are an expert AI Tutor creating a teaching response.
Transform the academic answer into a 7-step tutoring response.
Respond ONLY with valid JSON (no markdown, no code blocks).

LEARNER CONTEXT:
- Original question: "{question}"
- Learner level: {learner_level}
- Question type: {question_type}

{misconceptions_context}

ACADEMIC ANSWER:
{answer}

CREATE 7 TEACHING STEPS:

1. Intuitive Explanation (1-2 sentences, simple language, no jargon)
2. Real-World Example (2-3 sentences, concrete and relatable)
3. Technical Explanation (3-4 sentences, use proper terminology)
4. How It Works (4-6 steps/points, explain the process or mechanism)
5. Common Mistakes (2-3 misconceptions with corrections)
6. Quick Summary (1-2 sentences, memorable)
7. Understanding Check (A question or scenario to check comprehension)

RETURN THIS JSON ONLY:
{{
  "step_1_intuitive": "...",
  "step_2_example": "...",
  "step_3_technical": "...",
  "step_4_how_it_works": "...",
  "step_5_mistakes": "...",
  "step_6_summary": "...",
  "step_7_check": "...",
  "teaching_quality_score": 0.95,
  "optimal_for_level": "{learner_level}",
  "addressing_misconceptions": true
}}"""

        return combined_prompt

    def parse_teaching_flow_response(
        self,
        llm_response: str
    ) -> Dict[int, str]:
        """
        Parse LLM response into structured 7-step format

        Args:
            llm_response: JSON response from LLM

        Returns:
            Dict mapping step number (1-7) → content
        """
        import json
        import re

        # Clean JSON if wrapped in markdown
        json_text = llm_response
        if '```json' in json_text:
            json_text = json_text.split('```json')[1].split('```')[0]
        elif '```' in json_text:
            json_text = json_text.split('```')[1].split('```')[0]

        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError:
            # Fallback: create empty steps
            return {i: "" for i in range(1, 8)}

        # Extract steps
        steps = {}
        step_keys = [
            'step_1_intuitive', 'step_2_example', 'step_3_technical',
            'step_4_how_it_works', 'step_5_mistakes', 'step_6_summary',
            'step_7_check'
        ]

        for i, key in enumerate(step_keys, 1):
            steps[i] = parsed.get(key, f"[Step {i} content not provided]")

        return steps

    def format_teaching_response(
        self,
        steps: Dict[int, str],
        include_structure: bool = True
    ) -> str:
        """
        Format 7 steps into a coherent tutor response

        Args:
            steps: Dict from parse_teaching_flow_response
            include_structure: Whether to include structure labels

        Returns:
            Formatted response string
        """
        step_titles = {
            1: "💡 Intuitive Explanation",
            2: "🌍 Real-World Example",
            3: "🔬 Technical Explanation",
            4: "⚙️ How It Works",
            5: "⚠️ Common Mistakes to Avoid",
            6: "📝 Quick Summary",
            7: "✅ Check Your Understanding"
        }

        if not include_structure:
            # Return just the content, joined naturally
            content_only = []
            for i in range(1, 8):
                if steps.get(i):
                    content_only.append(steps[i])
            return "\n\n".join(content_only)

        # Format with structure
        formatted_parts = []
        for i in range(1, 8):
            if steps.get(i):
                title = step_titles[i]
                content = steps[i]
                formatted_parts.append(f"{title}\n{content}")

        return "\n\n---\n\n".join(formatted_parts)

    def get_level_adapted_instructions(
        self,
        base_instructions: str,
        learner_level: str,
        step_number: int
    ) -> str:
        """
        Adapt instructions based on learner level

        Args:
            base_instructions: The base instruction text
            learner_level: beginner|intermediate|advanced
            step_number: 1-7

        Returns:
            Adapted instruction text
        """
        if learner_level not in self.LEVEL_CUSTOMIZATIONS:
            return base_instructions

        if step_number not in self.LEVEL_CUSTOMIZATIONS[learner_level]:
            return base_instructions

        emphasis = self.LEVEL_CUSTOMIZATIONS[learner_level][step_number]['emphasis']
        return f"{base_instructions}\n💡 For {learner_level} learner: {emphasis}"

    def create_minimal_flow_prompt(
        self,
        question: str,
        answer: str,
        learner_level: str = 'intermediate',
        question_type: str = 'definition'
    ) -> str:
        """
        Create a minimal, efficient prompt for teaching flow

        Used for faster responses with fewer tokens

        Args:
            question: Original question
            answer: Academic answer
            learner_level: Student level
            question_type: Type of question

        Returns:
            Compact prompt
        """
        return f"""Teach like a tutor, not a textbook.

Question: {question}
Level: {learner_level}
Type: {question_type}

Content: {answer[:300]}

Return JSON with these 7 steps (each 1-3 sentences max):
1. Simple explanation (no jargon)
2. Real example (relatable)
3. Technical details
4. Step-by-step process
5. Common mistakes (2 items)
6. Summary (1 sentence)
7. Check question

JSON keys: step_1, step_2, step_3, step_4, step_5, step_6, step_7"""


if __name__ == '__main__':
    # Demo
    orchestrator = TeachingFlowOrchestrator()

    question = "What is recursion?"
    answer = """Recursion is when a function calls itself to solve a smaller version of the same problem.
    A recursive function must have a base case (when to stop) and a recursive case (how to break down the problem).
    Classic examples: factorial, fibonacci, tree traversal."""
    
    pedagogical_context = {
        'potential_misconceptions': [
            'Recursion is just calling a function multiple times',
            'Recursion is always less efficient than loops'
        ]
    }

    # Create combined prompt
    prompt = orchestrator.create_combined_prompt(
        question, answer, pedagogical_context,
        learner_level='beginner',
        question_type='definition'
    )

    print("="*60)
    print("GENERATED PROMPT FOR LLM:")
    print("="*60)
    print(prompt)
