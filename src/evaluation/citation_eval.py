# evaluation/citation_eval.py - Citation Metrics Evaluation
"""
Citation Evaluation Metrics

Metrics:
- Citation Accuracy: Correctness of citations
- Source Relevance: Relevance of cited sources
- Hallucination Detection: Detection of unsupported claims
- Citation Coverage: Percentage of answer covered by citations
"""

import re
from typing import List, Dict, Set, Tuple
from collections import defaultdict
import numpy as np


class CitationEvaluator:
    """
    Evaluator for citation quality metrics.
    """
    
    def __init__(self):
        """Initialize citation evaluator"""
        self.embeddings_model = None
    
    def _extract_citations(self, text: str) -> List[str]:
        """
        Extract citation markers from text.
        
        Supports formats: [1], [doc1], (Smith, 2020), etc.
        """
        # Pattern for [number] or [doc_id]
        pattern1 = r'\[([^\]]+)\]'
        # Pattern for (Author, Year)
        pattern2 = r'\(([^)]+,\s*\d{4})\)'
        
        citations = []
        citations.extend(re.findall(pattern1, text))
        citations.extend(re.findall(pattern2, text))
        
        return citations
    
    def _tokenize(self, text: str) -> Set[str]:
        """Simple tokenization"""
        text = text.lower()
        tokens = set(re.findall(r'\b\w+\b', text))
        return tokens
    
    def citation_accuracy(self, 
                         answer: str,
                         citations: List[Dict],
                         sources: Dict[str, str]) -> Dict[str, float]:
        """
        Calculate citation accuracy.
        
        Checks if cited sources actually support the claims.
        
        Args:
            answer: Generated answer with citations
            citations: List of citation dicts with 'id' and 'claim'
            sources: Dict mapping source_id to source_text
        
        Returns:
            Dict with accuracy metrics
        """
        if not citations:
            return {
                'citation_accuracy': 0.0,
                'correct_citations': 0,
                'total_citations': 0
            }
        
        correct = 0
        total = len(citations)
        
        for citation in citations:
            cite_id = citation['id']
            claim = citation['claim']
            
            if cite_id not in sources:
                continue
            
            source_text = sources[cite_id]
            
            # Check if claim is supported by source
            if self._is_claim_supported(claim, source_text):
                correct += 1
        
        accuracy = correct / total if total > 0 else 0.0
        
        return {
            'citation_accuracy': accuracy,
            'correct_citations': correct,
            'total_citations': total
        }
    
    def _is_claim_supported(self, claim: str, source: str, threshold: float = 0.5) -> bool:
        """
        Check if claim is supported by source.
        
        Uses token overlap as a simple heuristic.
        """
        claim_tokens = self._tokenize(claim)
        source_tokens = self._tokenize(source)
        
        if not claim_tokens:
            return False
        
        overlap = len(claim_tokens & source_tokens)
        overlap_ratio = overlap / len(claim_tokens)
        
        return overlap_ratio >= threshold
    
    def source_relevance(self, 
                        query: str,
                        sources: List[str]) -> Dict[str, float]:
        """
        Calculate source relevance to query.
        
        Args:
            query: Original query
            sources: List of source texts
        
        Returns:
            Dict with relevance metrics
        """
        if not sources:
            return {
                'avg_relevance': 0.0,
                'min_relevance': 0.0,
                'max_relevance': 0.0
            }
        
        relevances = []
        
        for source in sources:
            relevance = self._calculate_relevance(query, source)
            relevances.append(relevance)
        
        return {
            'avg_relevance': np.mean(relevances),
            'min_relevance': np.min(relevances),
            'max_relevance': np.max(relevances),
            'std_relevance': np.std(relevances)
        }
    
    def _calculate_relevance(self, query: str, source: str) -> float:
        """
        Calculate relevance score between query and source.
        
        Uses token overlap as a simple heuristic.
        """
        query_tokens = self._tokenize(query)
        source_tokens = self._tokenize(source)
        
        if not query_tokens or not source_tokens:
            return 0.0
        
        overlap = len(query_tokens & source_tokens)
        
        # Jaccard similarity
        union = len(query_tokens | source_tokens)
        relevance = overlap / union if union > 0 else 0.0
        
        return relevance
    
    def hallucination_detection(self, 
                               answer: str,
                               sources: List[str],
                               threshold: float = 0.3) -> Dict[str, float]:
        """
        Detect potential hallucinations in answer.
        
        Hallucination = claims not supported by sources.
        
        Args:
            answer: Generated answer
            sources: List of source texts
            threshold: Minimum support threshold
        
        Returns:
            Dict with hallucination metrics
        """
        # Split answer into sentences
        sentences = self._split_sentences(answer)
        
        if not sentences:
            return {
                'hallucination_rate': 0.0,
                'supported_sentences': 0,
                'total_sentences': 0,
                'unsupported_sentences': 0
            }
        
        supported = 0
        unsupported = 0
        
        for sentence in sentences:
            is_supported = False
            
            for source in sources:
                if self._is_claim_supported(sentence, source, threshold):
                    is_supported = True
                    break
            
            if is_supported:
                supported += 1
            else:
                unsupported += 1
        
        total = len(sentences)
        hallucination_rate = unsupported / total if total > 0 else 0.0
        
        return {
            'hallucination_rate': hallucination_rate,
            'supported_sentences': supported,
            'unsupported_sentences': unsupported,
            'total_sentences': total,
            'support_rate': supported / total if total > 0 else 0.0
        }
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    
    def citation_coverage(self, 
                         answer: str,
                         citations: List[str]) -> Dict[str, float]:
        """
        Calculate citation coverage.
        
        Percentage of answer that has citations.
        
        Args:
            answer: Generated answer with citations
            citations: List of citation markers found
        
        Returns:
            Dict with coverage metrics
        """
        sentences = self._split_sentences(answer)
        
        if not sentences:
            return {
                'citation_coverage': 0.0,
                'cited_sentences': 0,
                'total_sentences': 0
            }
        
        cited = 0
        
        for sentence in sentences:
            # Check if sentence contains any citation
            if any(f'[{cite}]' in sentence or f'({cite})' in sentence for cite in citations):
                cited += 1
        
        total = len(sentences)
        coverage = cited / total if total > 0 else 0.0
        
        return {
            'citation_coverage': coverage,
            'cited_sentences': cited,
            'uncited_sentences': total - cited,
            'total_sentences': total
        }
    
    def evaluate_citations(self, 
                          answer: str,
                          query: str,
                          citations: List[Dict],
                          sources: Dict[str, str]) -> Dict[str, float]:
        """
        Evaluate all citation metrics.
        
        Args:
            answer: Generated answer with citations
            query: Original query
            citations: List of citation dicts
            sources: Dict mapping source_id to source_text
        
        Returns:
            Dict with all metrics
        """
        metrics = {}
        
        # Citation accuracy
        accuracy_metrics = self.citation_accuracy(answer, citations, sources)
        metrics.update(accuracy_metrics)
        
        # Source relevance
        source_texts = list(sources.values())
        relevance_metrics = self.source_relevance(query, source_texts)
        metrics.update(relevance_metrics)
        
        # Hallucination detection
        hallucination_metrics = self.hallucination_detection(answer, source_texts)
        metrics.update(hallucination_metrics)
        
        # Citation coverage
        citation_ids = [c['id'] for c in citations]
        coverage_metrics = self.citation_coverage(answer, citation_ids)
        metrics.update(coverage_metrics)
        
        return metrics
    
    def evaluate_batch(self, 
                      evaluations: List[Dict]) -> Dict[str, float]:
        """
        Evaluate metrics for multiple answers.
        
        Args:
            evaluations: List of dicts with answer, query, citations, sources
        
        Returns:
            Dict with averaged metrics
        """
        all_metrics = defaultdict(list)
        
        for eval_data in evaluations:
            answer = eval_data['answer']
            query = eval_data['query']
            citations = eval_data['citations']
            sources = eval_data['sources']
            
            metrics = self.evaluate_citations(answer, query, citations, sources)
            
            for metric_name, value in metrics.items():
                all_metrics[metric_name].append(value)
        
        # Calculate averages
        avg_metrics = {}
        for metric_name, values in all_metrics.items():
            avg_metrics[metric_name] = np.mean(values)
            avg_metrics[f'{metric_name}_std'] = np.std(values)
        
        return avg_metrics
    
    def print_metrics(self, metrics: Dict):
        """Print metrics in a formatted way"""
        print(f"\n{'='*60}")
        print(f"📚 CITATION EVALUATION METRICS")
        print(f"{'='*60}")
        
        # Citation accuracy
        if 'citation_accuracy' in metrics:
            acc = metrics['citation_accuracy']
            acc_std = metrics.get('citation_accuracy_std', 0.0)
            correct = metrics.get('correct_citations', 0)
            total = metrics.get('total_citations', 0)
            
            print(f"\n✅ Citation Accuracy:")
            print(f"   Accuracy: {acc:.4f} (±{acc_std:.4f})")
            print(f"   Correct: {correct}/{total}")
        
        # Source relevance
        if 'avg_relevance' in metrics:
            avg_rel = metrics['avg_relevance']
            avg_rel_std = metrics.get('avg_relevance_std', 0.0)
            min_rel = metrics.get('min_relevance', 0.0)
            max_rel = metrics.get('max_relevance', 0.0)
            
            print(f"\n🎯 Source Relevance:")
            print(f"   Average: {avg_rel:.4f} (±{avg_rel_std:.4f})")
            print(f"   Range: {min_rel:.4f} - {max_rel:.4f}")
        
        # Hallucination detection
        if 'hallucination_rate' in metrics:
            hall_rate = metrics['hallucination_rate']
            hall_rate_std = metrics.get('hallucination_rate_std', 0.0)
            support_rate = metrics.get('support_rate', 0.0)
            supported = metrics.get('supported_sentences', 0)
            unsupported = metrics.get('unsupported_sentences', 0)
            
            print(f"\n🚨 Hallucination Detection:")
            print(f"   Hallucination Rate: {hall_rate:.4f} (±{hall_rate_std:.4f})")
            print(f"   Support Rate: {support_rate:.4f}")
            print(f"   Supported: {supported}, Unsupported: {unsupported}")
        
        # Citation coverage
        if 'citation_coverage' in metrics:
            coverage = metrics['citation_coverage']
            coverage_std = metrics.get('citation_coverage_std', 0.0)
            cited = metrics.get('cited_sentences', 0)
            uncited = metrics.get('uncited_sentences', 0)
            
            print(f"\n📊 Citation Coverage:")
            print(f"   Coverage: {coverage:.4f} (±{coverage_std:.4f})")
            print(f"   Cited: {cited}, Uncited: {uncited}")
        
        print(f"{'='*60}\n")


# Test code
if __name__ == "__main__":
    print("="*60)
    print("TESTING CITATION EVALUATOR")
    print("="*60)
    
    evaluator = CitationEvaluator()
    
    # Example
    print("\n# Example: Citation Evaluation")
    
    answer = "Data mining discovers patterns in large datasets [1]. It uses machine learning algorithms [2]. Classification predicts categories."
    query = "What is data mining?"
    citations = [
        {'id': '1', 'claim': 'Data mining discovers patterns in large datasets'},
        {'id': '2', 'claim': 'It uses machine learning algorithms'}
    ]
    sources = {
        '1': 'Data mining is the process of discovering patterns in large datasets using various techniques.',
        '2': 'Machine learning algorithms are commonly used in data mining applications.'
    }
    
    metrics = evaluator.evaluate_citations(answer, query, citations, sources)
    evaluator.print_metrics(metrics)
