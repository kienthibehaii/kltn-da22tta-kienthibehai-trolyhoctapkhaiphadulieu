# educational_engine/visual_generator.py
"""
Visual Explanation Generator

Creates visual representations of concepts:
- ASCII flowcharts
- Concept hierarchies/trees
- Comparison tables
- Step-by-step sequences
- Process diagrams
"""

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Dict, List
import re

load_dotenv()


class VisualGenerator:
    """
    Generates visual explanations using ASCII, Markdown tables, and diagrams
    """

    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.4,
            timeout=30
        )

    def generate_flowchart(self, process: str, steps: List[str] = None) -> str:
        """
        Generate ASCII flowchart for a process

        Example output:
        ```
              [Start]
                 |
                 v
           [Decision?]
            /       \\
           Y         N
          /           \\
         v             v
       [Yes Path]  [No Path]
        ```
        """

        prompt = f"""Create an ASCII flowchart (using ┌─┬─┐│└ characters or similar) for this process.
Make it simple, clear, and educational.
Include decision points if relevant.
Use proper box drawing characters.
Limit to 8-12 lines max.

Process: {process}
{f"Steps provided: {', '.join(steps)}" if steps else ""}

ASCII Flowchart:"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            # Clean up the response - it might have markdown code blocks
            content = content.replace('```', '')
            content = content.strip()
            return content
        except Exception as e:
            print(f"⚠️ Flowchart generation error: {e}")
            return self._simple_flowchart_fallback(process)

    def generate_hierarchy(self, concept: str, categories: List[str] = None) -> str:
        """
        Generate hierarchy/tree structure

        Example:
        ```
        Machine Learning
        ├── Supervised
        │   ├── Classification
        │   └── Regression
        └── Unsupervised
            ├── Clustering
            └── Dimensionality Reduction
        ```
        """

        prompt = f"""Create a hierarchical tree structure for this concept.
Use tree characters: ├──, │, └──
Make it clear and educational.
Show 2-3 levels of hierarchy.
Limit to 10-15 lines.

Main concept: {concept}
{f"Categories: {', '.join(categories)}" if categories else ""}

Hierarchy tree:"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            content = content.replace('```', '').strip()
            return content
        except Exception as e:
            print(f"⚠️ Hierarchy generation error: {e}")
            return f"{concept}\n├── Category 1\n├── Category 2\n└── Category 3"

    def generate_comparison_table(self, items: List[Dict], attributes: List[str] = None) -> str:
        """
        Generate Markdown comparison table

        Example:
        ```
        | Feature | Item1 | Item2 |
        |---------|-------|-------|
        | Speed   | Fast  | Slow  |
        | Cost    | High  | Low   |
        ```
        """

        if not items or not attributes:
            return ""

        # Build table
        table = []

        # Header
        header = ["| Attribute"]
        for item in items:
            name = item.get('name', 'Item')
            header.append(f" {name}")
        header.append(" |")
        table.append("".join(header))

        # Separator
        separator = ["|"]
        separator.append(" --- " * (len(items) + 1))
        separator.append("|")
        table.append("".join(separator))

        # Rows
        for attr in attributes:
            row = [f"| {attr}"]
            for item in items:
                value = item.get(attr, "-")
                row.append(f" {value}")
            row.append(" |")
            table.append("".join(row))

        return "\n".join(table)

    def generate_concept_map(self, concepts: List[str]) -> str:
        """
        Generate ASCII concept map showing relationships

        Example:
        ```
        [Concept1] --> [Concept2]
                       ^    |
                       |    v
                    [Concept3]
        ```
        """

        if len(concepts) < 2:
            return ""

        prompt = f"""Create a simple ASCII concept map showing relationships between these concepts.
Use arrows (-->, <--, <->) to show relationships.
Use [...] for concept boxes.
Make it educational and clear.
Limit to 8-12 lines.

Concepts: {', '.join(concepts)}

Concept map:"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            content = content.replace('```', '').strip()
            return content
        except Exception as e:
            print(f"⚠️ Concept map error: {e}")
            # Fallback: simple chain
            if concepts:
                return " --> ".join(f"[{c}]" for c in concepts)
            return ""

    def generate_step_sequence(self, steps: List[str]) -> str:
        """
        Generate visual step sequence

        Example:
        ```
        Step 1: Start          Step 2: Process
            |                      |
            v                      v
         [Input] ------>      [Action] ------>  [Output]
                             Step 3: End
        ```
        """

        if not steps:
            return ""

        # Simple numbered sequence
        sequence = []
        for i, step in enumerate(steps[:5], 1):
            sequence.append(f"Step {i}: {step}")
            if i < len(steps[:5]):
                sequence.append("    |")
                sequence.append("    v")

        return "\n".join(sequence)

    def generate_venn_diagram(self, concept1: str, concept2: str, common: str = "") -> str:
        """
        Generate simple Venn diagram representation

        Uses text-based representation
        """

        diagram = f"""
    {concept1}          {concept2}
       /\\                /\\
      /  \\______  ______/  \\
     /    \\  {common}  /    \\
    /______\\____  ____/______\\
        """

        return diagram.strip()

    def generate_timeline(self, events: List[str]) -> str:
        """
        Generate ASCII timeline

        Example:
        ```
        1900 --- 1950 --- 2000 --- 2020
         |        |         |       |
        [Event]  [Event]  [Event] [Event]
        ```
        """

        if not events:
            return ""

        timeline = "Timeline:\n\n"
        for i, event in enumerate(events[:5]):
            timeline += f"{'  ' * i}▪ {event}\n"

        return timeline.strip()

    def generate_matrix(self, rows: List[str], columns: List[str]) -> str:
        """
        Generate matrix representation

        Like a spreadsheet view
        """

        if not rows or not columns:
            return ""

        # Header
        matrix = "| " + " | ".join(columns[:4]) + " |\n"
        matrix += "|" + "|".join(["---" for _ in columns[:4]]) + "|\n"

        # Rows
        for row in rows[:5]:
            matrix += f"| {row} | | | |\n"

        return matrix

    def select_visual_type(self, question_type: str, concepts: List[str]) -> str:
        """
        Select appropriate visual type based on question type
        """

        visual_types = {
            'process': 'flowchart',
            'comparison': 'comparison_table',
            'definition': 'concept_map',
            'evaluation': 'comparison_table',
            'application': 'step_sequence',
            'reasoning': 'hierarchy',
        }

        return visual_types.get(question_type, 'concept_map')

    def generate(
        self,
        answer: str,
        question_type: str,
        concepts: List[str] = None
    ) -> Dict:
        """
        Generate appropriate visual(s) for answer

        Returns dict with visual representations
        """

        if not concepts:
            concepts = []

        visuals = {
            'primary_visual': '',
            'secondary_visual': '',
            'diagram_type': 'none',
            'has_flowchart': False,
            'has_comparison_table': False,
            'has_hierarchy': False,
            'has_concept_map': False,
            'suggested_visual': ''
        }

        # For process questions: generate flowchart
        if question_type == 'process':
            flowchart = self.generate_flowchart(answer[:200])
            if flowchart and len(flowchart) > 10:
                visuals['primary_visual'] = flowchart
                visuals['diagram_type'] = 'flowchart'
                visuals['has_flowchart'] = True

        # For comparison questions: generate table
        elif question_type == 'comparison':
            # Try to extract items to compare
            if 'vs' in answer.lower() or 'difference' in answer.lower():
                visuals['suggested_visual'] = 'comparison_table'
                visuals['has_comparison_table'] = True

        # For definition questions: concept map
        elif question_type in ['definition', 'reasoning']:
            if len(concepts) >= 2:
                concept_map = self.generate_concept_map(concepts)
                if concept_map:
                    visuals['primary_visual'] = concept_map
                    visuals['diagram_type'] = 'concept_map'
                    visuals['has_concept_map'] = True

        # For complex answers: hierarchy
        if not visuals['primary_visual'] and len(concepts) >= 2:
            hierarchy = self.generate_hierarchy(concepts[0], concepts[1:])
            if hierarchy and len(hierarchy) > 10:
                visuals['primary_visual'] = hierarchy
                visuals['diagram_type'] = 'hierarchy'
                visuals['has_hierarchy'] = True

        # Default: simple structure
        if not visuals['primary_visual']:
            visuals['primary_visual'] = self._generate_simple_structure(question_type, concepts)
            visuals['diagram_type'] = 'text_structure'

        return visuals

    def _simple_flowchart_fallback(self, process: str) -> str:
        """
        Simple fallback flowchart
        """

        return f"""
[START]
   |
   v
{process[:30]}...
   |
   v
[END]
"""

    def _generate_simple_structure(self, question_type: str, concepts: List[str]) -> str:
        """
        Generate simple text structure as fallback
        """

        if not concepts:
            return ""

        structure = f"**{concepts[0]}**\n\n"

        if len(concepts) > 1:
            for c in concepts[1:]:
                structure += f"• {c}\n"

        return structure.strip()
