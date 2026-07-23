# intelligent_assistant/__init__.py
"""
Intelligent AI Learning Assistant Package

Complete system with:
- Query Understanding
- Agentic RAG
- Educational AI Features
- Anti-Hallucination
- Self-Improvement
- Analytics
"""

from .query_understanding import (
    QueryUnderstanding,
    QueryAnalysis,
    QueryType,
    Intent,
    understand_query
)

from .agentic_rag import (
    AgenticRAG,
    PlannerAgent,
    RetrievalAgent,
    SummarizationAgent,
    EvaluationAgent
)

__version__ = "1.0.0"

__all__ = [
    # Query Understanding
    "QueryUnderstanding",
    "QueryAnalysis",
    "QueryType",
    "Intent",
    "understand_query",
    
    # Agentic RAG
    "AgenticRAG",
    "PlannerAgent",
    "RetrievalAgent",
    "SummarizationAgent",
    "EvaluationAgent",
]
