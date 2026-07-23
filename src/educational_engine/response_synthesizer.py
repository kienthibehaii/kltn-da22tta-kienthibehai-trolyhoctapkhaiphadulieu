# educational_engine/response_synthesizer.py
"""
Response Synthesizer

Analyzes RAG answers and structures them for educational delivery:
- Detect question type (definition, process, comparison, etc.)
- Extract key concepts and relationships
- Generate simplified explanation
- Create structured breakdown
- Identify prerequisites and follow-ups
"""

import re
from typing import Dict, List, Tuple
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


class ResponseSynthesizer:
    """
    Synthesizes raw answers into structured educational content
    """

    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.4,
            timeout=30
        )
        self.question_types = {
            'definition': r'(what is|define|explain|meaning of|is a)',
            'process': r'(how does|how to|steps|process|procedure|work)',
            'algorithm': r'(algorithm|sorting|searching|traversal|bfs|dfs|dynamic programming|greedy)',
            'comparison': r'(difference between|compare|vs|versus|similar|distinguish)',
            'evaluation': r'(evaluate|assess|which is better|pros and cons|advantages)',
            'problem_solving': r'(solve|fix|error|issue|wrong|problem|troubleshoot)',
            'application': r'(use|apply|when to use|where is|application of|example)',
            'reasoning': r'(why|reason|cause|because|explanation)',
            'mathematical': r'(equation|formula|proof|derive|derivation|entropy|gini|complexity)',
        }

    def detect_question_type(self, question: str) -> str:
        """
        Detect the type of question being asked

        Returns: 'definition' | 'process' | 'algorithm' | 'comparison' | 'evaluation' | 'problem_solving' | 'application' | 'reasoning' | 'mathematical'
        """

        question_lower = question.lower()

        for qtype, pattern in self.question_types.items():
            if re.search(pattern, question_lower):
                return qtype

        # Default based on length heuristic
        if len(question) < 30:
            return 'definition'
        else:
            return 'reasoning'

    def extract_key_concepts(self, answer: str, count: int = 5) -> List[str]:
        """
        Extract key concepts/terms from answer

        Uses simple heuristics:
        - Capitalized terms (proper nouns)
        - Terms in quotes
        - Single words between certain punctuation
        """

        concepts = []

        # Find capitalized phrases
        capitalized = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', answer)
        concepts.extend(capitalized[:count])

        # Find quoted terms
        quoted = re.findall(r'"([^"]+)"', answer)
        concepts.extend(quoted)

        # Remove duplicates while preserving order
        concepts = list(dict.fromkeys(concepts))

        return concepts[:count]

    def structure_by_type(self, answer: str, question_type: str) -> Dict:
        """
        Structure answer based on question type

        Breaks answer into logical components
        """

        structure = {
            'primary': '',  # Main explanation
            'details': [],  # Supporting details
            'examples': [],  # Examples
            'implications': [],  # What it means
            'conclusion': ''  # Summary
        }

        # Simple sentence-level breakdown
        sentences = re.split(r'[.!?]+', answer)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return structure

        # Heuristic distribution
        structure['primary'] = sentences[0]  # First sentence is primary

        for i, sent in enumerate(sentences[1:], 1):
            sent_lower = sent.lower()

            if any(word in sent_lower for word in ['example', 'instance', 'such as', 'like', 'including']):
                structure['examples'].append(sent)
            elif any(word in sent_lower for word in ['mean', 'imply', 'result', 'lead', 'cause']):
                structure['implications'].append(sent)
            else:
                structure['details'].append(sent)

        # Last meaningful sentence as conclusion
        if structure['details']:
            structure['conclusion'] = structure['details'][-1]
            structure['details'] = structure['details'][:-1]

        return structure

    def generate_simplified_explanation(self, answer: str, concepts: List[str]) -> str:
        """
        Generate a simplified version using LLM

        Simplifies technical terms, shortens sentences, adds clarity
        """

        prompt = f"""Simplify this explanation for a beginner who doesn't know technical terms.
Replace complex terms with simple analogies or everyday examples.
Keep it under 150 words.
Make it sound natural and conversational.

Original: {answer}

Simplified:"""

        try:
            response = self.llm.invoke(prompt)
            if hasattr(response, 'content'):
                return response.content
            return str(response)
        except Exception as e:
            print(f"⚠️ Simplification error: {e}")
            return answer[:300] + "..."  # Fallback to first 300 chars

    def generate_key_takeaways(self, answer: str, concepts: List[str]) -> List[str]:
        """
        Extract 3-5 key takeaways from answer
        """

        prompt = f"""Extract 3-5 key takeaways from this answer.
Each should be a short, punchy statement (under 15 words).
Format as a bullet list.

Answer: {answer}

Key takeaways:"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            # Parse bullet points
            lines = content.split('\n')
            takeaways = []
            for line in lines:
                line = line.strip()
                if line and len(takeaways) < 5:
                    # Remove bullet markers
                    line = re.sub(r'^[-•*]\s+', '', line).strip()
                    if line and len(line) > 5:
                        takeaways.append(line)

            return takeaways[:5]
        except Exception as e:
            print(f"⚠️ Takeaway generation error: {e}")
            return ["Key concepts: " + ", ".join(concepts[:3])]

    def identify_prerequisites(self, answer: str, concepts: List[str]) -> List[str]:
        """
        Identify prerequisite knowledge needed to understand answer
        """

        common_prerequisites = {
            'clustering': ['distance metrics', 'feature scaling'],
            'classification': ['supervised learning', 'labels'],
            'neural network': ['linear algebra', 'calculus'],
            'regression': ['statistics', 'correlation'],
            'decision tree': ['binary splits', 'information gain'],
        }

        prerequisites = []
        for concept in concepts:
            if concept.lower() in common_prerequisites:
                prerequisites.extend(common_prerequisites[concept.lower()])

        return list(set(prerequisites))

    def identify_related_concepts(self, answer: str, main_concept: str) -> List[str]:
        """
        Identify related concepts mentioned in answer
        """

        # Simple pattern matching for mentions of other concepts
        keywords = ['classification', 'clustering', 'regression', 'feature', 'model', 'training', 'evaluation', 'validation']

        related = []
        for keyword in keywords:
            if keyword.lower() in answer.lower() and keyword.lower() != main_concept.lower():
                related.append(keyword)

        return related[:5]

    def synthesize(self, answer: str, question: str) -> Dict:
        """
        Complete synthesis of answer into educational structure

        Returns comprehensive breakdown
        """

        # Detect question type
        qtype = self.detect_question_type(question)

        # Extract concepts
        concepts = self.extract_key_concepts(answer)

        # Structure answer
        structure = self.structure_by_type(answer, qtype)

        # Generate variations
        simplified = self.generate_simplified_explanation(answer, concepts)
        takeaways = self.generate_key_takeaways(answer, concepts)
        prerequisites = self.identify_prerequisites(answer, concepts)
        related = self.identify_related_concepts(answer, concepts[0] if concepts else "")

        return {
            'question_type': qtype,
            'key_concepts': concepts,
            'structure': structure,
            'simplified_explanation': simplified,
            'key_takeaways': takeaways,
            'prerequisites': prerequisites,
            'related_concepts': related,
            'concept_count': len(concepts),
            'is_complex': len(answer) > 500 or len(concepts) > 4
        }

    def generate_followups(
        self,
        question: str,
        answer: str,
        key_concepts: List[str],
        user_history: List[str] = None
    ) -> List[str]:
        """
        Generate follow-up questions based on answer and user history

        Helps guide learning pathway
        """

        prompt = f"""Based on this Q&A, suggest 2-3 natural follow-up questions
that deepen understanding or explore related concepts.
Make them conversational and engaging.
Format as a numbered list.

Question: {question}
Answer excerpt: {answer[:300]}...
Key concepts: {', '.join(key_concepts)}

Follow-up questions:"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            lines = content.split('\n')
            followups = []
            for line in lines:
                line = line.strip()
                if line and len(followups) < 3:
                    # Remove numbering
                    line = re.sub(r'^[\d+.\-)\s]+', '', line).strip()
                    if line and '?' in line and len(line) > 10:
                        followups.append(line)

            return followups[:3]
        except Exception as e:
            print(f"⚠️ Followup generation error: {e}")
            return [f"Can you explain {key_concepts[0]} in more detail?" if key_concepts else "What are the practical applications?"]
