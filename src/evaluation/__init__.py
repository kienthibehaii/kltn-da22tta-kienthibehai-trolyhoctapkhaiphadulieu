# evaluation/__init__.py - RAG Evaluation System
"""
RAG Evaluation System

Modules:
- retrieval_eval: Retrieval metrics (Precision@K, Recall@K, MRR, NDCG, Hit Rate)
- generation_eval: Generation metrics (BLEU, ROUGE, BERTScore, Semantic Similarity)
- citation_eval: Citation metrics (Accuracy, Relevance, Hallucination Detection)
- benchmark: Automatic benchmarking and experiment tracking
- dataset: Test dataset management
"""

from .retrieval_eval import RetrievalEvaluator
from .generation_eval import GenerationEvaluator
from .citation_eval import CitationEvaluator
from .benchmark import RAGBenchmark

__all__ = [
    'RetrievalEvaluator',
    'GenerationEvaluator',
    'CitationEvaluator',
    'RAGBenchmark'
]

__version__ = '1.0.0'
