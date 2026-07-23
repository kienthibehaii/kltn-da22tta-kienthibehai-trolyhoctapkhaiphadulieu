"""
RAG Evaluation Metrics
Comprehensive metrics for evaluating RAG system performance
"""

import numpy as np
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer
from collections import Counter
import re


class RAGEvaluator:
    """
    Comprehensive RAG evaluation system
    """
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        self.model = SentenceTransformer(model_name)
    
    def evaluate_retrieval(
        self,
        query: str,
        retrieved_docs: List[Dict],
        relevant_docs: List[Dict] = None
    ) -> Dict:
        """
        Evaluate retrieval quality
        
        Metrics:
        - Precision@K
        - Recall@K
        - MRR (Mean Reciprocal Rank)
        - NDCG (Normalized Discounted Cumulative Gain)
        - Hit Rate
        """
        metrics = {}
        
        if relevant_docs:
            # Calculate precision and recall
            metrics['precision'] = self._calculate_precision(
                retrieved_docs,
                relevant_docs
            )
            metrics['recall'] = self._calculate_recall(
                retrieved_docs,
                relevant_docs
            )
            metrics['f1'] = self._calculate_f1(
                metrics['precision'],
                metrics['recall']
            )
            metrics['mrr'] = self._calculate_mrr(
                retrieved_docs,
                relevant_docs
            )
            metrics['ndcg'] = self._calculate_ndcg(
                retrieved_docs,
                relevant_docs
            )
        
        # Calculate relevance scores
        metrics['avg_relevance'] = self._calculate_avg_relevance(
            query,
            retrieved_docs
        )
        
        # Calculate diversity
        metrics['diversity'] = self._calculate_diversity(retrieved_docs)
        
        return metrics
    
    def evaluate_generation(
        self,
        query: str,
        answer: str,
        reference_answer: str = None,
        source_docs: List[Dict] = None
    ) -> Dict:
        """
        Evaluate answer generation quality
        
        Metrics:
        - Faithfulness (grounding in sources)
        - Answer Relevance
        - Context Relevance
        - BLEU (if reference available)
        - ROUGE (if reference available)
        - Semantic Similarity
        """
        metrics = {}
        
        # Faithfulness
        if source_docs:
            metrics['faithfulness'] = self._calculate_faithfulness(
                answer,
                source_docs
            )
            metrics['context_relevance'] = self._calculate_context_relevance(
                query,
                source_docs
            )
        
        # Answer relevance
        metrics['answer_relevance'] = self._calculate_answer_relevance(
            query,
            answer
        )
        
        # Comparison with reference
        if reference_answer:
            metrics['bleu'] = self._calculate_bleu(
                answer,
                reference_answer
            )
            metrics['rouge'] = self._calculate_rouge(
                answer,
                reference_answer
            )
            metrics['semantic_similarity'] = self._calculate_semantic_similarity(
                answer,
                reference_answer
            )
        
        # Answer quality
        metrics['completeness'] = self._calculate_completeness(answer)
        metrics['clarity'] = self._calculate_clarity(answer)
        
        return metrics
    
    def evaluate_end_to_end(
        self,
        query: str,
        retrieved_docs: List[Dict],
        answer: str,
        reference_answer: str = None,
        relevant_docs: List[Dict] = None
    ) -> Dict:
        """
        End-to-end RAG evaluation
        """
        retrieval_metrics = self.evaluate_retrieval(
            query,
            retrieved_docs,
            relevant_docs
        )
        
        generation_metrics = self.evaluate_generation(
            query,
            answer,
            reference_answer,
            retrieved_docs
        )
        
        # Combined metrics
        combined = {
            'retrieval': retrieval_metrics,
            'generation': generation_metrics,
            'overall_score': self._calculate_overall_score(
                retrieval_metrics,
                generation_metrics
            )
        }
        
        return combined
    
    # Retrieval Metrics
    
    def _calculate_precision(
        self,
        retrieved: List[Dict],
        relevant: List[Dict]
    ) -> float:
        """Precision@K"""
        if not retrieved:
            return 0.0
        
        retrieved_ids = set(self._get_doc_ids(retrieved))
        relevant_ids = set(self._get_doc_ids(relevant))
        
        true_positives = len(retrieved_ids & relevant_ids)
        
        return true_positives / len(retrieved_ids)
    
    def _calculate_recall(
        self,
        retrieved: List[Dict],
        relevant: List[Dict]
    ) -> float:
        """Recall@K"""
        if not relevant:
            return 0.0
        
        retrieved_ids = set(self._get_doc_ids(retrieved))
        relevant_ids = set(self._get_doc_ids(relevant))
        
        true_positives = len(retrieved_ids & relevant_ids)
        
        return true_positives / len(relevant_ids)
    
    def _calculate_f1(self, precision: float, recall: float) -> float:
        """F1 Score"""
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)
    
    def _calculate_mrr(
        self,
        retrieved: List[Dict],
        relevant: List[Dict]
    ) -> float:
        """Mean Reciprocal Rank"""
        relevant_ids = set(self._get_doc_ids(relevant))
        
        for i, doc in enumerate(retrieved, 1):
            doc_id = self._get_doc_id(doc)
            if doc_id in relevant_ids:
                return 1.0 / i
        
        return 0.0
    
    def _calculate_ndcg(
        self,
        retrieved: List[Dict],
        relevant: List[Dict],
        k: int = None
    ) -> float:
        """Normalized Discounted Cumulative Gain"""
        if k is None:
            k = len(retrieved)
        
        relevant_ids = set(self._get_doc_ids(relevant))
        
        # Calculate DCG
        dcg = 0.0
        for i, doc in enumerate(retrieved[:k], 1):
            doc_id = self._get_doc_id(doc)
            relevance = 1.0 if doc_id in relevant_ids else 0.0
            dcg += relevance / np.log2(i + 1)
        
        # Calculate IDCG (ideal DCG)
        idcg = sum(1.0 / np.log2(i + 1) for i in range(1, min(len(relevant), k) + 1))
        
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    def _calculate_avg_relevance(
        self,
        query: str,
        documents: List[Dict]
    ) -> float:
        """Average relevance score"""
        if not documents:
            return 0.0
        
        query_embedding = self.model.encode([query])[0]
        doc_texts = [doc.get('content', doc.get('text', '')) for doc in documents]
        doc_embeddings = self.model.encode(doc_texts)
        
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity([query_embedding], doc_embeddings)[0]
        
        return float(np.mean(similarities))
    
    def _calculate_diversity(self, documents: List[Dict]) -> float:
        """Calculate diversity of retrieved documents"""
        if len(documents) < 2:
            return 0.0
        
        doc_texts = [doc.get('content', doc.get('text', '')) for doc in documents]
        doc_embeddings = self.model.encode(doc_texts)
        
        from sklearn.metrics.pairwise import cosine_similarity
        similarity_matrix = cosine_similarity(doc_embeddings)
        
        # Average pairwise dissimilarity
        n = len(documents)
        total_dissimilarity = 0.0
        count = 0
        
        for i in range(n):
            for j in range(i + 1, n):
                dissimilarity = 1.0 - similarity_matrix[i][j]
                total_dissimilarity += dissimilarity
                count += 1
        
        return total_dissimilarity / count if count > 0 else 0.0
    
    # Generation Metrics
    
    def _calculate_faithfulness(
        self,
        answer: str,
        source_docs: List[Dict]
    ) -> float:
        """
        Faithfulness: How well answer is grounded in sources
        """
        # Split answer into claims
        claims = self._extract_claims(answer)
        
        if not claims:
            return 0.0
        
        # Check each claim against sources
        supported_count = 0
        
        for claim in claims:
            if self._is_claim_supported(claim, source_docs):
                supported_count += 1
        
        return supported_count / len(claims)
    
    def _calculate_answer_relevance(
        self,
        query: str,
        answer: str
    ) -> float:
        """
        Answer relevance: How relevant answer is to query
        """
        query_embedding = self.model.encode([query])[0]
        answer_embedding = self.model.encode([answer])[0]
        
        from sklearn.metrics.pairwise import cosine_similarity
        similarity = cosine_similarity(
            [query_embedding],
            [answer_embedding]
        )[0][0]
        
        return float(similarity)
    
    def _calculate_context_relevance(
        self,
        query: str,
        source_docs: List[Dict]
    ) -> float:
        """
        Context relevance: How relevant sources are to query
        """
        return self._calculate_avg_relevance(query, source_docs)
    
    def _calculate_bleu(
        self,
        candidate: str,
        reference: str
    ) -> float:
        """
        BLEU score (simplified)
        """
        candidate_tokens = candidate.lower().split()
        reference_tokens = reference.lower().split()
        
        if not candidate_tokens or not reference_tokens:
            return 0.0
        
        # Unigram precision
        candidate_counts = Counter(candidate_tokens)
        reference_counts = Counter(reference_tokens)
        
        overlap = sum((candidate_counts & reference_counts).values())
        precision = overlap / len(candidate_tokens)
        
        # Brevity penalty
        bp = 1.0 if len(candidate_tokens) >= len(reference_tokens) else \
             np.exp(1 - len(reference_tokens) / len(candidate_tokens))
        
        return bp * precision
    
    def _calculate_rouge(
        self,
        candidate: str,
        reference: str
    ) -> Dict:
        """
        ROUGE scores (simplified)
        """
        candidate_tokens = candidate.lower().split()
        reference_tokens = reference.lower().split()
        
        if not candidate_tokens or not reference_tokens:
            return {'rouge-1': 0.0, 'rouge-l': 0.0}
        
        # ROUGE-1 (unigram overlap)
        candidate_set = set(candidate_tokens)
        reference_set = set(reference_tokens)
        
        overlap = len(candidate_set & reference_set)
        rouge_1_precision = overlap / len(candidate_set)
        rouge_1_recall = overlap / len(reference_set)
        
        if rouge_1_precision + rouge_1_recall > 0:
            rouge_1_f1 = 2 * rouge_1_precision * rouge_1_recall / (rouge_1_precision + rouge_1_recall)
        else:
            rouge_1_f1 = 0.0
        
        # ROUGE-L (longest common subsequence)
        lcs_length = self._lcs_length(candidate_tokens, reference_tokens)
        rouge_l_precision = lcs_length / len(candidate_tokens)
        rouge_l_recall = lcs_length / len(reference_tokens)
        
        if rouge_l_precision + rouge_l_recall > 0:
            rouge_l_f1 = 2 * rouge_l_precision * rouge_l_recall / (rouge_l_precision + rouge_l_recall)
        else:
            rouge_l_f1 = 0.0
        
        return {
            'rouge-1': rouge_1_f1,
            'rouge-l': rouge_l_f1
        }
    
    def _calculate_semantic_similarity(
        self,
        text1: str,
        text2: str
    ) -> float:
        """
        Semantic similarity using embeddings
        """
        embeddings = self.model.encode([text1, text2])
        
        from sklearn.metrics.pairwise import cosine_similarity
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        
        return float(similarity)
    
    def _calculate_completeness(self, answer: str) -> float:
        """
        Completeness: How complete the answer is
        """
        # Simple heuristic based on length and structure
        word_count = len(answer.split())
        
        # Check for structure indicators
        has_structure = any(marker in answer for marker in [
            '1.', '2.', 'First', 'Second', 'Finally', '-'
        ])
        
        # Score based on length
        length_score = min(word_count / 100, 1.0)
        
        # Bonus for structure
        structure_bonus = 0.2 if has_structure else 0.0
        
        return min(length_score + structure_bonus, 1.0)
    
    def _calculate_clarity(self, answer: str) -> float:
        """
        Clarity: How clear and well-structured the answer is
        """
        sentences = re.split(r'(?<=[.!?])\s+', answer)
        
        if not sentences:
            return 0.0
        
        # Check average sentence length
        avg_sentence_length = np.mean([len(s.split()) for s in sentences])
        
        # Ideal: 15-25 words per sentence
        if 15 <= avg_sentence_length <= 25:
            length_score = 1.0
        elif avg_sentence_length < 15:
            length_score = avg_sentence_length / 15
        else:
            length_score = max(0.5, 1.0 - (avg_sentence_length - 25) / 50)
        
        # Check for transition words
        transition_words = ['however', 'therefore', 'moreover', 'furthermore', 'additionally']
        has_transitions = any(word in answer.lower() for word in transition_words)
        transition_bonus = 0.2 if has_transitions else 0.0
        
        return min(length_score + transition_bonus, 1.0)
    
    # Helper methods
    
    def _get_doc_ids(self, documents: List[Dict]) -> List[str]:
        """Get document IDs"""
        return [self._get_doc_id(doc) for doc in documents]
    
    def _get_doc_id(self, document: Dict) -> str:
        """Get document ID"""
        return document.get('id', document.get('content', '')[:100])
    
    def _extract_claims(self, text: str) -> List[str]:
        """Extract factual claims from text"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        claims = [s.strip() for s in sentences if s.strip() and '?' not in s]
        return claims
    
    def _is_claim_supported(
        self,
        claim: str,
        source_docs: List[Dict]
    ) -> bool:
        """Check if claim is supported by sources"""
        claim_embedding = self.model.encode([claim])[0]
        
        for doc in source_docs:
            doc_text = doc.get('content', doc.get('text', ''))
            doc_embedding = self.model.encode([doc_text])[0]
            
            from sklearn.metrics.pairwise import cosine_similarity
            similarity = cosine_similarity(
                [claim_embedding],
                [doc_embedding]
            )[0][0]
            
            if similarity > 0.6:
                return True
        
        return False
    
    def _lcs_length(self, seq1: List, seq2: List) -> int:
        """Longest common subsequence length"""
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i-1] == seq2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        return dp[m][n]
    
    def _calculate_overall_score(
        self,
        retrieval_metrics: Dict,
        generation_metrics: Dict
    ) -> float:
        """
        Calculate overall RAG score
        """
        # Weighted average of key metrics
        weights = {
            'retrieval': 0.3,
            'generation': 0.7
        }
        
        # Retrieval score
        retrieval_score = retrieval_metrics.get('avg_relevance', 0.0)
        
        # Generation score
        generation_score = np.mean([
            generation_metrics.get('faithfulness', 0.0),
            generation_metrics.get('answer_relevance', 0.0),
            generation_metrics.get('completeness', 0.0)
        ])
        
        overall = (
            weights['retrieval'] * retrieval_score +
            weights['generation'] * generation_score
        )
        
        return float(overall)


# Example usage
if __name__ == "__main__":
    evaluator = RAGEvaluator()
    
    # Test data
    query = "What is clustering?"
    retrieved_docs = [
        {'id': '1', 'content': 'Clustering groups similar data points together.'},
        {'id': '2', 'content': 'K-means is a clustering algorithm.'}
    ]
    answer = "Clustering is a method to group similar data points. K-means is a popular algorithm."
    reference = "Clustering groups similar objects together using algorithms like K-means."
    
    # Evaluate
    metrics = evaluator.evaluate_end_to_end(
        query,
        retrieved_docs,
        answer,
        reference
    )
    
    print("Evaluation Results:")
    print(f"Overall Score: {metrics['overall_score']:.3f}")
    print(f"Retrieval: {metrics['retrieval']}")
    print(f"Generation: {metrics['generation']}")
