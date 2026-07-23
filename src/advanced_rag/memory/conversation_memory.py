"""
Advanced Conversation Memory
Implements short-term, long-term, and semantic memory
"""

from typing import List, Dict, Optional
import numpy as np
from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer
from collections import deque


class ConversationMemory:
    """
    Multi-level conversation memory system
    """
    
    def __init__(
        self,
        short_term_size: int = 5,
        long_term_size: int = 50,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        self.short_term_size = short_term_size
        self.long_term_size = long_term_size
        self.model = SentenceTransformer(model_name)
        
        # Short-term memory (recent messages)
        self.short_term = deque(maxlen=short_term_size)
        
        # Long-term memory (important messages)
        self.long_term = []
        
        # Semantic memory (key concepts)
        self.semantic_memory = {}
    
    def add_message(
        self,
        role: str,
        content: str,
        metadata: Dict = None
    ):
        """
        Add message to memory
        """
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now(),
            'metadata': metadata or {},
            'embedding': self.model.encode([content])[0]
        }
        
        # Add to short-term
        self.short_term.append(message)
        
        # Check if important enough for long-term
        if self._is_important(message):
            self._add_to_long_term(message)
        
        # Extract concepts for semantic memory
        self._update_semantic_memory(message)
    
    def get_context(
        self,
        query: str,
        max_messages: int = 5,
        include_semantic: bool = True
    ) -> str:
        """
        Get relevant context for query
        """
        context_parts = []
        
        # Get recent messages from short-term
        recent_messages = list(self.short_term)[-max_messages:]
        
        # Get relevant messages from long-term
        if query:
            relevant_long_term = self._retrieve_relevant_long_term(
                query,
                k=3
            )
        else:
            relevant_long_term = []
        
        # Combine and format
        all_messages = relevant_long_term + recent_messages
        
        for msg in all_messages:
            role = msg['role'].capitalize()
            content = msg['content']
            context_parts.append(f"{role}: {content}")
        
        # Add semantic memory if requested
        if include_semantic and query:
            relevant_concepts = self._get_relevant_concepts(query)
            if relevant_concepts:
                concepts_str = ", ".join(relevant_concepts)
                context_parts.insert(0, f"Key concepts: {concepts_str}")
        
        return "\n".join(context_parts)
    
    def _is_important(self, message: Dict) -> bool:
        """
        Determine if message is important for long-term memory
        """
        content = message['content']
        
        # Criteria for importance
        criteria = [
            len(content.split()) > 20,  # Substantial content
            any(word in content.lower() for word in ['definition', 'algorithm', 'theorem', 'formula']),  # Key concepts
            message['role'] == 'assistant' and len(content) > 100,  # Detailed answers
        ]
        
        return sum(criteria) >= 2
    
    def _add_to_long_term(self, message: Dict):
        """
        Add message to long-term memory
        """
        # Check if similar message already exists
        if self._has_similar_in_long_term(message):
            return
        
        self.long_term.append(message)
        
        # Prune if exceeds size
        if len(self.long_term) > self.long_term_size:
            # Remove oldest or least important
            self.long_term = self._prune_long_term()
    
    def _has_similar_in_long_term(self, message: Dict) -> bool:
        """
        Check if similar message exists in long-term memory
        """
        if not self.long_term:
            return False
        
        from sklearn.metrics.pairwise import cosine_similarity
        
        message_embedding = message['embedding']
        long_term_embeddings = [msg['embedding'] for msg in self.long_term]
        
        similarities = cosine_similarity(
            [message_embedding],
            long_term_embeddings
        )[0]
        
        return np.max(similarities) > 0.9
    
    def _prune_long_term(self) -> List[Dict]:
        """
        Prune long-term memory to keep most important
        """
        # Score each message by importance
        scored = []
        for msg in self.long_term:
            score = self._calculate_importance_score(msg)
            scored.append((score, msg))
        
        # Sort by score and keep top N
        scored.sort(reverse=True, key=lambda x: x[0])
        return [msg for score, msg in scored[:self.long_term_size]]
    
    def _calculate_importance_score(self, message: Dict) -> float:
        """
        Calculate importance score for message
        """
        score = 0.0
        content = message['content']
        
        # Length factor
        score += min(len(content.split()) / 100, 1.0) * 0.3
        
        # Recency factor
        age = (datetime.now() - message['timestamp']).total_seconds()
        recency = 1.0 / (1.0 + age / 3600)  # Decay over hours
        score += recency * 0.3
        
        # Content quality factor
        has_keywords = any(word in content.lower() for word in [
            'definition', 'algorithm', 'theorem', 'formula', 'example'
        ])
        if has_keywords:
            score += 0.4
        
        return score
    
    def _retrieve_relevant_long_term(
        self,
        query: str,
        k: int = 3
    ) -> List[Dict]:
        """
        Retrieve relevant messages from long-term memory
        """
        if not self.long_term:
            return []
        
        from sklearn.metrics.pairwise import cosine_similarity
        
        query_embedding = self.model.encode([query])[0]
        long_term_embeddings = [msg['embedding'] for msg in self.long_term]
        
        similarities = cosine_similarity(
            [query_embedding],
            long_term_embeddings
        )[0]
        
        # Get top k
        top_indices = np.argsort(similarities)[-k:][::-1]
        
        return [self.long_term[i] for i in top_indices if similarities[i] > 0.5]
    
    def _update_semantic_memory(self, message: Dict):
        """
        Extract and store key concepts
        """
        content = message['content'].lower()
        
        # Extract key terms (simple approach)
        # In production, use NER or keyword extraction
        key_terms = self._extract_key_terms(content)
        
        for term in key_terms:
            if term not in self.semantic_memory:
                self.semantic_memory[term] = {
                    'count': 0,
                    'contexts': [],
                    'embedding': self.model.encode([term])[0]
                }
            
            self.semantic_memory[term]['count'] += 1
            
            # Keep last 3 contexts
            contexts = self.semantic_memory[term]['contexts']
            contexts.append(content[:200])
            self.semantic_memory[term]['contexts'] = contexts[-3:]
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """
        Extract key terms from text
        """
        # Simple extraction (can be improved)
        words = text.split()
        
        # Filter stopwords and short words
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'is', 'are'}
        key_terms = [w for w in words if len(w) > 4 and w not in stopwords]
        
        # Get unique terms
        from collections import Counter
        term_counts = Counter(key_terms)
        
        # Return top 5
        return [term for term, count in term_counts.most_common(5)]
    
    def _get_relevant_concepts(self, query: str) -> List[str]:
        """
        Get relevant concepts from semantic memory
        """
        if not self.semantic_memory:
            return []
        
        from sklearn.metrics.pairwise import cosine_similarity
        
        query_embedding = self.model.encode([query])[0]
        
        # Calculate similarity with all concepts
        concept_scores = []
        for term, data in self.semantic_memory.items():
            similarity = cosine_similarity(
                [query_embedding],
                [data['embedding']]
            )[0][0]
            
            # Weight by frequency
            score = similarity * np.log1p(data['count'])
            concept_scores.append((score, term))
        
        # Sort and return top 3
        concept_scores.sort(reverse=True)
        return [term for score, term in concept_scores[:3] if score > 0.5]
    
    def clear(self):
        """Clear all memory"""
        self.short_term.clear()
        self.long_term.clear()
        self.semantic_memory.clear()
    
    def get_summary(self) -> Dict:
        """Get memory summary"""
        return {
            'short_term_count': len(self.short_term),
            'long_term_count': len(self.long_term),
            'semantic_concepts': len(self.semantic_memory),
            'top_concepts': sorted(
                self.semantic_memory.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )[:5]
        }


class FeedbackLearning:
    """
    Learn from user feedback to improve responses
    """
    
    def __init__(self):
        self.feedback_history = []
        self.positive_patterns = []
        self.negative_patterns = []
    
    def add_feedback(
        self,
        query: str,
        answer: str,
        feedback: str,  # 'positive', 'negative', 'neutral'
        details: Optional[str] = None
    ):
        """
        Record user feedback
        """
        feedback_entry = {
            'query': query,
            'answer': answer,
            'feedback': feedback,
            'details': details,
            'timestamp': datetime.now()
        }
        
        self.feedback_history.append(feedback_entry)
        
        # Update patterns
        if feedback == 'positive':
            self._add_positive_pattern(query, answer)
        elif feedback == 'negative':
            self._add_negative_pattern(query, answer, details)
    
    def _add_positive_pattern(self, query: str, answer: str):
        """
        Extract patterns from positive feedback
        """
        pattern = {
            'query_type': self._classify_query(query),
            'answer_length': len(answer.split()),
            'has_examples': 'example' in answer.lower(),
            'has_structure': any(marker in answer for marker in ['1.', '2.', 'First', 'Second']),
            'timestamp': datetime.now()
        }
        
        self.positive_patterns.append(pattern)
    
    def _add_negative_pattern(
        self,
        query: str,
        answer: str,
        details: Optional[str]
    ):
        """
        Extract patterns from negative feedback
        """
        pattern = {
            'query_type': self._classify_query(query),
            'issue': details or 'unspecified',
            'answer_length': len(answer.split()),
            'timestamp': datetime.now()
        }
        
        self.negative_patterns.append(pattern)
    
    def _classify_query(self, query: str) -> str:
        """
        Classify query type
        """
        query_lower = query.lower()
        
        if query_lower.startswith('what'):
            return 'definition'
        elif query_lower.startswith('how'):
            return 'process'
        elif query_lower.startswith('why'):
            return 'explanation'
        elif query_lower.startswith('compare'):
            return 'comparison'
        else:
            return 'general'
    
    def get_recommendations(self, query: str) -> Dict:
        """
        Get recommendations based on feedback history
        """
        query_type = self._classify_query(query)
        
        # Analyze positive patterns for this query type
        relevant_positive = [
            p for p in self.positive_patterns
            if p['query_type'] == query_type
        ]
        
        if not relevant_positive:
            return {}
        
        # Calculate averages
        avg_length = np.mean([p['answer_length'] for p in relevant_positive])
        should_have_examples = np.mean([p['has_examples'] for p in relevant_positive]) > 0.5
        should_have_structure = np.mean([p['has_structure'] for p in relevant_positive]) > 0.5
        
        return {
            'recommended_length': int(avg_length),
            'include_examples': should_have_examples,
            'use_structure': should_have_structure,
            'confidence': len(relevant_positive) / max(len(self.positive_patterns), 1)
        }
    
    def get_feedback_stats(self) -> Dict:
        """
        Get feedback statistics
        """
        if not self.feedback_history:
            return {
                'total': 0,
                'positive': 0,
                'negative': 0,
                'neutral': 0
            }
        
        from collections import Counter
        feedback_counts = Counter(f['feedback'] for f in self.feedback_history)
        
        return {
            'total': len(self.feedback_history),
            'positive': feedback_counts.get('positive', 0),
            'negative': feedback_counts.get('negative', 0),
            'neutral': feedback_counts.get('neutral', 0),
            'positive_rate': feedback_counts.get('positive', 0) / len(self.feedback_history)
        }


# Example usage
if __name__ == "__main__":
    # Initialize memory
    memory = ConversationMemory()
    
    # Add messages
    memory.add_message('user', 'What is clustering?')
    memory.add_message('assistant', 'Clustering is a method to group similar data points together.')
    memory.add_message('user', 'Can you give an example?')
    memory.add_message('assistant', 'Sure! K-means is a popular clustering algorithm that partitions data into K clusters.')
    
    # Get context
    context = memory.get_context('Tell me more about K-means')
    print("Context:")
    print(context)
    
    # Get summary
    summary = memory.get_summary()
    print(f"\nMemory summary: {summary}")
    
    # Test feedback learning
    feedback = FeedbackLearning()
    feedback.add_feedback(
        'What is clustering?',
        'Clustering groups similar objects.',
        'positive'
    )
    
    recommendations = feedback.get_recommendations('What is classification?')
    print(f"\nRecommendations: {recommendations}")
