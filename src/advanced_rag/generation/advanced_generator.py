"""
Advanced Answer Generation
Includes hallucination reduction, citation grounding, answer validation
"""

from typing import List, Dict, Optional, Tuple
import re
import numpy as np
from sentence_transformers import SentenceTransformer


class HallucinationDetector:
    """
    Detect and reduce hallucinations in generated answers
    """
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        threshold: float = 0.5
    ):
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold
    
    def detect_hallucination(
        self,
        answer: str,
        source_documents: List[Dict]
    ) -> Dict:
        """
        Detect if answer contains hallucinated information
        
        Returns:
            {
                'is_hallucinated': bool,
                'confidence': float,
                'unsupported_claims': List[str],
                'supported_claims': List[str]
            }
        """
        # Split answer into claims
        claims = self._extract_claims(answer)
        
        # Check each claim against sources
        supported = []
        unsupported = []
        
        for claim in claims:
            is_supported, confidence = self._verify_claim(
                claim,
                source_documents
            )
            
            if is_supported:
                supported.append(claim)
            else:
                unsupported.append(claim)
        
        # Calculate overall confidence
        total_claims = len(claims)
        if total_claims == 0:
            return {
                'is_hallucinated': False,
                'confidence': 1.0,
                'unsupported_claims': [],
                'supported_claims': []
            }
        
        support_ratio = len(supported) / total_claims
        is_hallucinated = support_ratio < self.threshold
        
        return {
            'is_hallucinated': is_hallucinated,
            'confidence': support_ratio,
            'unsupported_claims': unsupported,
            'supported_claims': supported
        }
    
    def _extract_claims(self, text: str) -> List[str]:
        """
        Extract factual claims from text
        """
        # Split by sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Filter out questions and non-factual statements
        claims = []
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Skip questions
            if '?' in sentence:
                continue
            
            # Skip very short sentences
            if len(sentence.split()) < 5:
                continue
            
            claims.append(sentence)
        
        return claims
    
    def _verify_claim(
        self,
        claim: str,
        source_documents: List[Dict]
    ) -> Tuple[bool, float]:
        """
        Verify if claim is supported by source documents
        
        Returns:
            (is_supported, confidence)
        """
        # Encode claim
        claim_embedding = self.model.encode([claim])[0]
        
        # Encode source texts
        source_texts = [
            doc.get('content', doc.get('text', ''))
            for doc in source_documents
        ]
        
        if not source_texts:
            return False, 0.0
        
        source_embeddings = self.model.encode(source_texts)
        
        # Calculate similarity
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(
            [claim_embedding],
            source_embeddings
        )[0]
        
        # Get max similarity
        max_similarity = np.max(similarities)
        
        # Check if supported
        is_supported = max_similarity >= self.threshold
        
        return is_supported, float(max_similarity)


class CitationGrounder:
    """
    Ground answer with specific citations from source documents
    """
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        self.model = SentenceTransformer(model_name)
    
    def ground_answer(
        self,
        answer: str,
        source_documents: List[Dict]
    ) -> Dict:
        """
        Add citations to answer
        
        Returns:
            {
                'grounded_answer': str,
                'citations': List[Dict],
                'citation_map': Dict[str, List[int]]
            }
        """
        # Split answer into sentences
        sentences = self._split_sentences(answer)
        
        # Find citation for each sentence
        grounded_sentences = []
        citations = []
        citation_map = {}
        
        for i, sentence in enumerate(sentences):
            # Find best matching source
            best_source, similarity = self._find_best_source(
                sentence,
                source_documents
            )
            
            if best_source and similarity > 0.5:
                # Add citation
                citation_id = len(citations) + 1
                citations.append({
                    'id': citation_id,
                    'source': best_source.get('metadata', {}).get('source', 'Unknown'),
                    'page': best_source.get('metadata', {}).get('page', 'N/A'),
                    'text': best_source.get('content', '')[:200],
                    'similarity': float(similarity)
                })
                
                # Add citation marker to sentence
                grounded_sentence = f"{sentence} [{citation_id}]"
                grounded_sentences.append(grounded_sentence)
                
                # Map sentence to citation
                citation_map[sentence] = [citation_id]
            else:
                # No good citation found
                grounded_sentences.append(sentence)
        
        grounded_answer = ' '.join(grounded_sentences)
        
        return {
            'grounded_answer': grounded_answer,
            'citations': citations,
            'citation_map': citation_map
        }
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _find_best_source(
        self,
        sentence: str,
        source_documents: List[Dict]
    ) -> Tuple[Optional[Dict], float]:
        """
        Find best matching source document for sentence
        """
        if not source_documents:
            return None, 0.0
        
        # Encode sentence
        sentence_embedding = self.model.encode([sentence])[0]
        
        # Encode sources
        source_texts = [
            doc.get('content', doc.get('text', ''))
            for doc in source_documents
        ]
        source_embeddings = self.model.encode(source_texts)
        
        # Calculate similarity
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(
            [sentence_embedding],
            source_embeddings
        )[0]
        
        # Get best match
        best_idx = np.argmax(similarities)
        best_similarity = similarities[best_idx]
        
        return source_documents[best_idx], float(best_similarity)


class AnswerValidator:
    """
    Validate generated answers for quality and correctness
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    def validate_answer(
        self,
        question: str,
        answer: str,
        source_documents: List[Dict]
    ) -> Dict:
        """
        Validate answer quality
        
        Returns:
            {
                'is_valid': bool,
                'quality_score': float,
                'issues': List[str],
                'suggestions': List[str]
            }
        """
        issues = []
        suggestions = []
        
        # Check 1: Answer length
        if len(answer.split()) < 10:
            issues.append("Answer too short")
            suggestions.append("Provide more detailed explanation")
        
        # Check 2: Answer relevance
        if not self._is_relevant(question, answer):
            issues.append("Answer not relevant to question")
            suggestions.append("Focus on answering the specific question")
        
        # Check 3: Source grounding
        if not self._is_grounded(answer, source_documents):
            issues.append("Answer not well-grounded in sources")
            suggestions.append("Use more information from source documents")
        
        # Check 4: Completeness
        if not self._is_complete(question, answer):
            issues.append("Answer incomplete")
            suggestions.append("Address all parts of the question")
        
        # Check 5: Clarity
        if not self._is_clear(answer):
            issues.append("Answer unclear or confusing")
            suggestions.append("Use simpler language and better structure")
        
        # Calculate quality score
        max_checks = 5
        passed_checks = max_checks - len(issues)
        quality_score = passed_checks / max_checks
        
        is_valid = quality_score >= 0.6
        
        return {
            'is_valid': is_valid,
            'quality_score': quality_score,
            'issues': issues,
            'suggestions': suggestions
        }
    
    def _is_relevant(self, question: str, answer: str) -> bool:
        """Check if answer is relevant to question"""
        # Simple keyword overlap check
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        
        # Remove stopwords
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'is', 'are'}
        question_words -= stopwords
        answer_words -= stopwords
        
        # Calculate overlap
        overlap = len(question_words & answer_words)
        overlap_ratio = overlap / len(question_words) if question_words else 0
        
        return overlap_ratio >= 0.3
    
    def _is_grounded(self, answer: str, source_documents: List[Dict]) -> bool:
        """Check if answer is grounded in sources"""
        if not source_documents:
            return False
        
        # Check if answer contains information from sources
        answer_lower = answer.lower()
        
        for doc in source_documents:
            source_text = doc.get('content', doc.get('text', '')).lower()
            
            # Check for common phrases
            source_words = set(source_text.split())
            answer_words = set(answer_lower.split())
            
            overlap = len(source_words & answer_words)
            if overlap > 10:  # At least 10 common words
                return True
        
        return False
    
    def _is_complete(self, question: str, answer: str) -> bool:
        """Check if answer is complete"""
        # Check if answer addresses the question type
        question_lower = question.lower()
        
        # What questions should have definitions
        if question_lower.startswith('what'):
            return len(answer.split()) >= 20
        
        # How questions should have steps/process
        if question_lower.startswith('how'):
            return len(answer.split()) >= 30
        
        # Why questions should have explanations
        if question_lower.startswith('why'):
            return len(answer.split()) >= 25
        
        # Default: reasonable length
        return len(answer.split()) >= 15
    
    def _is_clear(self, answer: str) -> bool:
        """Check if answer is clear"""
        # Check for overly long sentences
        sentences = re.split(r'(?<=[.!?])\s+', answer)
        
        for sentence in sentences:
            words = sentence.split()
            if len(words) > 40:  # Very long sentence
                return False
        
        # Check for structure
        has_structure = any(marker in answer for marker in ['First', 'Second', 'Finally', '1.', '2.', '-'])
        
        return True  # Default to true if no major issues


class ContextFilter:
    """
    Filter and prioritize context before generation
    """
    
    def __init__(
        self,
        max_context_length: int = 4000,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        self.max_context_length = max_context_length
        self.model = SentenceTransformer(model_name)
    
    def filter_context(
        self,
        query: str,
        documents: List[Dict],
        strategy: str = 'relevance'  # 'relevance', 'diversity', 'hybrid'
    ) -> List[Dict]:
        """
        Filter and prioritize documents for context
        """
        if strategy == 'relevance':
            return self._filter_by_relevance(query, documents)
        elif strategy == 'diversity':
            return self._filter_by_diversity(query, documents)
        elif strategy == 'hybrid':
            return self._filter_hybrid(query, documents)
        else:
            return documents
    
    def _filter_by_relevance(
        self,
        query: str,
        documents: List[Dict]
    ) -> List[Dict]:
        """
        Keep most relevant documents within token limit
        """
        # Sort by relevance score
        sorted_docs = sorted(
            documents,
            key=lambda x: x.get('score', 0),
            reverse=True
        )
        
        # Add documents until token limit
        filtered = []
        current_length = 0
        
        for doc in sorted_docs:
            doc_text = doc.get('content', doc.get('text', ''))
            doc_length = len(doc_text)
            
            if current_length + doc_length <= self.max_context_length:
                filtered.append(doc)
                current_length += doc_length
            else:
                break
        
        return filtered
    
    def _filter_by_diversity(
        self,
        query: str,
        documents: List[Dict]
    ) -> List[Dict]:
        """
        Select diverse documents using MMR (Maximal Marginal Relevance)
        """
        if not documents:
            return []
        
        # Encode query and documents
        query_embedding = self.model.encode([query])[0]
        doc_texts = [doc.get('content', doc.get('text', '')) for doc in documents]
        doc_embeddings = self.model.encode(doc_texts)
        
        # Calculate similarities
        from sklearn.metrics.pairwise import cosine_similarity
        query_similarities = cosine_similarity([query_embedding], doc_embeddings)[0]
        
        # MMR selection
        selected = []
        selected_embeddings = []
        remaining_indices = list(range(len(documents)))
        current_length = 0
        
        lambda_param = 0.5  # Balance between relevance and diversity
        
        while remaining_indices and current_length < self.max_context_length:
            if not selected:
                # Select most relevant first
                best_idx = remaining_indices[np.argmax(query_similarities[remaining_indices])]
            else:
                # Calculate MMR scores
                mmr_scores = []
                for idx in remaining_indices:
                    relevance = query_similarities[idx]
                    
                    # Calculate max similarity to selected docs
                    similarities_to_selected = cosine_similarity(
                        [doc_embeddings[idx]],
                        selected_embeddings
                    )[0]
                    max_similarity = np.max(similarities_to_selected)
                    
                    # MMR score
                    mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity
                    mmr_scores.append(mmr_score)
                
                # Select best MMR score
                best_idx = remaining_indices[np.argmax(mmr_scores)]
            
            # Add to selected
            doc = documents[best_idx]
            doc_length = len(doc.get('content', doc.get('text', '')))
            
            if current_length + doc_length <= self.max_context_length:
                selected.append(doc)
                selected_embeddings.append(doc_embeddings[best_idx])
                current_length += doc_length
            
            remaining_indices.remove(best_idx)
        
        return selected
    
    def _filter_hybrid(
        self,
        query: str,
        documents: List[Dict]
    ) -> List[Dict]:
        """
        Combine relevance and diversity
        """
        # Get top relevant docs
        relevant_docs = self._filter_by_relevance(query, documents)
        
        # Apply diversity within relevant docs
        diverse_docs = self._filter_by_diversity(query, relevant_docs)
        
        return diverse_docs


# Example usage
if __name__ == "__main__":
    # Test hallucination detection
    detector = HallucinationDetector()
    
    answer = "Clustering is a method to group similar data points. K-means is the most popular algorithm."
    sources = [
        {'content': 'Clustering groups similar objects together. Common algorithms include K-means and DBSCAN.'}
    ]
    
    result = detector.detect_hallucination(answer, sources)
    print(f"Hallucination detection: {result}")
    
    # Test citation grounding
    grounder = CitationGrounder()
    grounded = grounder.ground_answer(answer, sources)
    print(f"\nGrounded answer: {grounded['grounded_answer']}")
    print(f"Citations: {grounded['citations']}")
