# intelligent_assistant/query_understanding.py
"""
Intelligent Query Understanding System
- Query classification
- Intent detection
- Difficulty estimation
- Entity extraction
"""

import re
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of queries"""
    FACTUAL = "factual"  # "What is...?"
    CONCEPTUAL = "conceptual"  # "Explain..."
    PROCEDURAL = "procedural"  # "How to...?"
    COMPARATIVE = "comparative"  # "Compare X and Y"
    EXAMPLE = "example"  # "Give me an example"
    PRACTICE = "practice"  # "Quiz me on..."
    REVIEW = "review"  # "Summarize..."
    CLARIFICATION = "clarification"  # "I don't understand..."


class Intent(Enum):
    """User intents"""
    LEARN = "learn"  # Want to learn new concept
    UNDERSTAND = "understand"  # Need deeper understanding
    PRACTICE = "practice"  # Want to practice
    TEST = "test"  # Want to test knowledge
    REVIEW = "review"  # Want to review
    EXPLORE = "explore"  # Want to explore related topics
    CLARIFY = "clarify"  # Need clarification


@dataclass
class QueryAnalysis:
    """Query analysis result"""
    original_query: str
    query_type: QueryType
    intent: Intent
    difficulty: float  # 0.0 to 1.0
    entities: List[str]
    concepts: List[str]
    keywords: List[str]
    confidence: float
    metadata: Dict


class QueryClassifier:
    """Classify query type"""
    
    def __init__(self):
        self.patterns = {
            QueryType.FACTUAL: [
                r"^what is",
                r"^what are",
                r"^define",
                r"^definition of",
                r"là gì",
                r"nghĩa là gì"
            ],
            QueryType.CONCEPTUAL: [
                r"^explain",
                r"^describe",
                r"^why",
                r"^how does",
                r"giải thích",
                r"mô tả",
                r"tại sao"
            ],
            QueryType.PROCEDURAL: [
                r"^how to",
                r"^how do i",
                r"^steps to",
                r"^process of",
                r"làm thế nào",
                r"các bước"
            ],
            QueryType.COMPARATIVE: [
                r"compare",
                r"difference between",
                r"vs",
                r"versus",
                r"so sánh",
                r"khác nhau"
            ],
            QueryType.EXAMPLE: [
                r"example",
                r"give me an example",
                r"show me",
                r"ví dụ",
                r"cho tôi ví dụ"
            ],
            QueryType.PRACTICE: [
                r"quiz",
                r"test me",
                r"practice",
                r"exercise",
                r"kiểm tra",
                r"luyện tập"
            ],
            QueryType.REVIEW: [
                r"summarize",
                r"summary",
                r"review",
                r"recap",
                r"tóm tắt",
                r"ôn tập"
            ],
            QueryType.CLARIFICATION: [
                r"don't understand",
                r"confused",
                r"clarify",
                r"không hiểu",
                r"chưa rõ"
            ]
        }
    
    def classify(self, query: str) -> Tuple[QueryType, float]:
        """
        Classify query type
        
        Returns:
            (query_type, confidence)
        """
        query_lower = query.lower().strip()
        
        # Check patterns
        for query_type, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return query_type, 0.9
        
        # Default: factual
        return QueryType.FACTUAL, 0.5


class IntentDetector:
    """Detect user intent"""
    
    def __init__(self):
        self.intent_keywords = {
            Intent.LEARN: [
                "learn", "teach", "introduce", "new",
                "học", "dạy", "giới thiệu", "mới"
            ],
            Intent.UNDERSTAND: [
                "understand", "explain", "why", "how",
                "hiểu", "giải thích", "tại sao", "như thế nào"
            ],
            Intent.PRACTICE: [
                "practice", "exercise", "try", "do",
                "luyện tập", "bài tập", "thử", "làm"
            ],
            Intent.TEST: [
                "test", "quiz", "exam", "assess",
                "kiểm tra", "thi", "đánh giá"
            ],
            Intent.REVIEW: [
                "review", "revise", "recap", "summarize",
                "ôn tập", "xem lại", "tóm tắt"
            ],
            Intent.EXPLORE: [
                "explore", "discover", "related", "more",
                "khám phá", "tìm hiểu", "liên quan", "thêm"
            ],
            Intent.CLARIFY: [
                "clarify", "confused", "don't understand",
                "làm rõ", "bối rối", "không hiểu"
            ]
        }
    
    def detect(self, query: str, query_type: QueryType) -> Tuple[Intent, float]:
        """
        Detect intent from query
        
        Returns:
            (intent, confidence)
        """
        query_lower = query.lower()
        
        # Count keyword matches
        intent_scores = {}
        for intent, keywords in self.intent_keywords.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                intent_scores[intent] = score
        
        # Get best match
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            confidence = min(0.9, intent_scores[best_intent] * 0.3)
            return best_intent, confidence
        
        # Fallback based on query type
        type_to_intent = {
            QueryType.FACTUAL: Intent.LEARN,
            QueryType.CONCEPTUAL: Intent.UNDERSTAND,
            QueryType.PROCEDURAL: Intent.LEARN,
            QueryType.COMPARATIVE: Intent.UNDERSTAND,
            QueryType.EXAMPLE: Intent.UNDERSTAND,
            QueryType.PRACTICE: Intent.PRACTICE,
            QueryType.REVIEW: Intent.REVIEW,
            QueryType.CLARIFICATION: Intent.CLARIFY
        }
        
        return type_to_intent.get(query_type, Intent.LEARN), 0.6


class DifficultyEstimator:
    """Estimate query difficulty"""
    
    def __init__(self):
        # Technical terms indicating higher difficulty
        self.advanced_terms = [
            "algorithm", "complexity", "optimization", "theorem",
            "proof", "mathematical", "statistical", "probabilistic",
            "thuật toán", "độ phức tạp", "tối ưu", "định lý"
        ]
        
        # Beginner indicators
        self.beginner_terms = [
            "basic", "simple", "introduction", "beginner",
            "what is", "define",
            "cơ bản", "đơn giản", "giới thiệu", "là gì"
        ]
    
    def estimate(self, query: str, entities: List[str]) -> float:
        """
        Estimate difficulty (0.0 = easy, 1.0 = hard)
        
        Factors:
        - Query length and complexity
        - Technical terms
        - Number of concepts
        - Question depth
        """
        query_lower = query.lower()
        difficulty = 0.5  # Start at medium
        
        # Query length factor
        word_count = len(query.split())
        if word_count > 20:
            difficulty += 0.1
        elif word_count < 5:
            difficulty -= 0.1
        
        # Technical terms
        advanced_count = sum(1 for term in self.advanced_terms if term in query_lower)
        beginner_count = sum(1 for term in self.beginner_terms if term in query_lower)
        
        difficulty += advanced_count * 0.1
        difficulty -= beginner_count * 0.1
        
        # Multiple concepts = harder
        if len(entities) > 3:
            difficulty += 0.15
        
        # Question depth indicators
        if any(word in query_lower for word in ["why", "how", "explain", "compare"]):
            difficulty += 0.1
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, difficulty))


class EntityExtractor:
    """Extract entities and concepts from query"""
    
    def __init__(self):
        # Data mining concepts
        self.known_concepts = {
            "classification", "clustering", "association rules",
            "decision tree", "neural network", "svm", "knn",
            "apriori", "k-means", "dbscan", "regression",
            "phân loại", "phân cụm", "luật kết hợp",
            "cây quyết định", "mạng nơ-ron"
        }
    
    def extract(self, query: str) -> Tuple[List[str], List[str], List[str]]:
        """
        Extract entities, concepts, and keywords
        
        Returns:
            (entities, concepts, keywords)
        """
        query_lower = query.lower()
        
        # Extract known concepts
        concepts = [
            concept for concept in self.known_concepts
            if concept in query_lower
        ]
        
        # Extract capitalized words as entities
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        
        # Extract keywords (important words)
        # Remove stop words
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were",
            "in", "on", "at", "to", "for", "of", "with",
            "là", "của", "và", "hoặc", "thì", "được"
        }
        
        words = query_lower.split()
        keywords = [
            word for word in words
            if len(word) > 3 and word not in stop_words
        ][:10]  # Top 10 keywords
        
        return entities, concepts, keywords


class QueryUnderstanding:
    """Complete query understanding system"""
    
    def __init__(self):
        self.classifier = QueryClassifier()
        self.intent_detector = IntentDetector()
        self.difficulty_estimator = DifficultyEstimator()
        self.entity_extractor = EntityExtractor()
    
    def analyze(self, query: str, context: Optional[Dict] = None) -> QueryAnalysis:
        """
        Analyze query comprehensively
        
        Args:
            query: User query
            context: Optional context (previous queries, user profile)
        
        Returns:
            QueryAnalysis object
        """
        logger.info(f"Analyzing query: {query}")
        
        # 1. Classify query type
        query_type, type_confidence = self.classifier.classify(query)
        logger.debug(f"Query type: {query_type.value} (confidence: {type_confidence})")
        
        # 2. Detect intent
        intent, intent_confidence = self.intent_detector.detect(query, query_type)
        logger.debug(f"Intent: {intent.value} (confidence: {intent_confidence})")
        
        # 3. Extract entities and concepts
        entities, concepts, keywords = self.entity_extractor.extract(query)
        logger.debug(f"Entities: {entities}, Concepts: {concepts}")
        
        # 4. Estimate difficulty
        difficulty = self.difficulty_estimator.estimate(query, entities)
        logger.debug(f"Difficulty: {difficulty:.2f}")
        
        # 5. Overall confidence
        overall_confidence = (type_confidence + intent_confidence) / 2
        
        # 6. Build metadata
        metadata = {
            "word_count": len(query.split()),
            "has_question_mark": "?" in query,
            "language": "vietnamese" if any(c in query for c in "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ") else "english",
            "context_provided": context is not None
        }
        
        # Add context if available
        if context:
            metadata["previous_topic"] = context.get("current_topic")
            metadata["user_level"] = context.get("user_level", "intermediate")
        
        return QueryAnalysis(
            original_query=query,
            query_type=query_type,
            intent=intent,
            difficulty=difficulty,
            entities=entities,
            concepts=concepts,
            keywords=keywords,
            confidence=overall_confidence,
            metadata=metadata
        )
    
    def get_retrieval_strategy(self, analysis: QueryAnalysis) -> Dict:
        """
        Determine optimal retrieval strategy based on analysis
        
        Returns:
            Strategy configuration
        """
        strategy = {
            "method": "hybrid",  # hybrid, vector, bm25
            "k": 10,
            "rerank": True,
            "filters": {}
        }
        
        # Adjust based on query type
        if analysis.query_type == QueryType.FACTUAL:
            strategy["method"] = "vector"
            strategy["k"] = 5
        elif analysis.query_type == QueryType.CONCEPTUAL:
            strategy["method"] = "hybrid"
            strategy["k"] = 15
            strategy["rerank"] = True
        elif analysis.query_type == QueryType.EXAMPLE:
            strategy["filters"]["has_examples"] = True
        
        # Adjust based on difficulty
        if analysis.difficulty > 0.7:
            strategy["k"] = 20  # More context for hard questions
        elif analysis.difficulty < 0.3:
            strategy["k"] = 5  # Less context for easy questions
        
        # Filter by concepts if available
        if analysis.concepts:
            strategy["filters"]["concepts"] = analysis.concepts
        
        return strategy


# Convenience function
def understand_query(query: str, context: Optional[Dict] = None) -> QueryAnalysis:
    """Analyze query and return understanding"""
    understanding = QueryUnderstanding()
    return understanding.analyze(query, context)
