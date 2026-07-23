# evaluation/retrieval_eval.py - Retrieval Metrics Evaluation
"""
Retrieval Evaluation Metrics

Metrics:
- Precision@K: Proportion of relevant docs in top-K
- Recall@K: Proportion of relevant docs retrieved
- MRR (Mean Reciprocal Rank): Average of reciprocal ranks
- NDCG (Normalized Discounted Cumulative Gain): Ranking quality
- Hit Rate: Percentage of queries with at least one relevant doc
"""

import numpy as np
from typing import List, Dict, Set, Tuple
from collections import defaultdict


class RetrievalEvaluator:
    """
    Evaluator for retrieval quality metrics.
    """
    
    def __init__(self):
        """Initialize retrieval evaluator"""
        self.results = defaultdict(list)
    
    def precision_at_k(self, 
                       retrieved: List[str], 
                       relevant: Set[str], 
                       k: int) -> float:
        """
        Calculate Precision@K.
        
        Precision@K = (# relevant docs in top-K) / K
        
        Args:
            retrieved: List of retrieved document IDs (ordered by rank)
            relevant: Set of relevant document IDs
            k: Number of top documents to consider
        
        Returns:
            Precision@K score (0.0 to 1.0)
        """
        if k <= 0 or not retrieved:
            return 0.0
        
        top_k = retrieved[:k]
        relevant_in_top_k = sum(1 for doc_id in top_k if doc_id in relevant)
        
        return relevant_in_top_k / k
    
    def recall_at_k(self, 
                    retrieved: List[str], 
                    relevant: Set[str], 
                    k: int) -> float:
        """
        Calculate Recall@K.
        
        Recall@K = (# relevant docs in top-K) / (# total relevant docs)
        
        Args:
            retrieved: List of retrieved document IDs (ordered by rank)
            relevant: Set of relevant document IDs
            k: Number of top documents to consider
        
        Returns:
            Recall@K score (0.0 to 1.0)
        """
        if not relevant or k <= 0 or not retrieved:
            return 0.0
        
        top_k = retrieved[:k]
        relevant_in_top_k = sum(1 for doc_id in top_k if doc_id in relevant)
        
        return relevant_in_top_k / len(relevant)
    
    def mean_reciprocal_rank(self, 
                            retrieved: List[str], 
                            relevant: Set[str]) -> float:
        """
        Calculate Mean Reciprocal Rank (MRR).
        
        MRR = 1 / (rank of first relevant document)
        
        Args:
            retrieved: List of retrieved document IDs (ordered by rank)
            relevant: Set of relevant document IDs
        
        Returns:
            MRR score (0.0 to 1.0)
        """
        if not retrieved or not relevant:
            return 0.0
        
        for rank, doc_id in enumerate(retrieved, start=1):
            if doc_id in relevant:
                return 1.0 / rank
        
        return 0.0
    
    def ndcg_at_k(self, 
                  retrieved: List[str], 
                  relevant: Dict[str, float], 
                  k: int) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain (NDCG@K).
        
        DCG@K = Σ (relevance_i / log2(i + 1)) for i in 1..K
        NDCG@K = DCG@K / IDCG@K
        
        Args:
            retrieved: List of retrieved document IDs (ordered by rank)
            relevant: Dict mapping doc_id to relevance score (0.0 to 1.0)
            k: Number of top documents to consider
        
        Returns:
            NDCG@K score (0.0 to 1.0)
        """
        if k <= 0 or not retrieved or not relevant:
            return 0.0
        
        # Calculate DCG@K
        dcg = 0.0
        for i, doc_id in enumerate(retrieved[:k], start=1):
            relevance = relevant.get(doc_id, 0.0)
            dcg += relevance / np.log2(i + 1)
        
        # Calculate IDCG@K (ideal DCG)
        ideal_relevances = sorted(relevant.values(), reverse=True)[:k]
        idcg = sum(rel / np.log2(i + 1) for i, rel in enumerate(ideal_relevances, start=1))
        
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    def hit_rate_at_k(self, 
                      retrieved: List[str], 
                      relevant: Set[str], 
                      k: int) -> float:
        """
        Calculate Hit Rate@K.
        
        Hit Rate@K = 1 if any relevant doc in top-K, else 0
        
        Args:
            retrieved: List of retrieved document IDs (ordered by rank)
            relevant: Set of relevant document IDs
            k: Number of top documents to consider
        
        Returns:
            Hit rate (0.0 or 1.0)
        """
        if k <= 0 or not retrieved or not relevant:
            return 0.0
        
        top_k = retrieved[:k]
        return 1.0 if any(doc_id in relevant for doc_id in top_k) else 0.0
    
    def evaluate_query(self, 
                      retrieved: List[str], 
                      relevant: Set[str],
                      relevance_scores: Dict[str, float] = None,
                      k_values: List[int] = [1, 3, 5, 10]) -> Dict:
        """
        Evaluate all metrics for a single query.
        
        Args:
            retrieved: List of retrieved document IDs
            relevant: Set of relevant document IDs
            relevance_scores: Optional dict of relevance scores for NDCG
            k_values: List of K values to evaluate
        
        Returns:
            Dict with all metrics
        """
        if relevance_scores is None:
            # Default: binary relevance (1.0 for relevant, 0.0 for irrelevant)
            relevance_scores = {doc_id: 1.0 for doc_id in relevant}
        
        metrics = {}
        
        for k in k_values:
            metrics[f'precision@{k}'] = self.precision_at_k(retrieved, relevant, k)
            metrics[f'recall@{k}'] = self.recall_at_k(retrieved, relevant, k)
            metrics[f'ndcg@{k}'] = self.ndcg_at_k(retrieved, relevance_scores, k)
            metrics[f'hit_rate@{k}'] = self.hit_rate_at_k(retrieved, relevant, k)
        
        metrics['mrr'] = self.mean_reciprocal_rank(retrieved, relevant)
        
        return metrics
    
    def evaluate_batch(self, 
                      queries: List[Dict]) -> Dict:
        """
        Evaluate metrics for multiple queries.
        
        Args:
            queries: List of dicts with 'retrieved', 'relevant', 'relevance_scores'
        
        Returns:
            Dict with averaged metrics
        """
        all_metrics = defaultdict(list)
        
        for query_data in queries:
            retrieved = query_data['retrieved']
            relevant = query_data['relevant']
            relevance_scores = query_data.get('relevance_scores', None)
            k_values = query_data.get('k_values', [1, 3, 5, 10])
            
            metrics = self.evaluate_query(retrieved, relevant, relevance_scores, k_values)
            
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
        print(f"📊 RETRIEVAL EVALUATION METRICS")
        print(f"{'='*60}")
        
        # Group by metric type
        precision_metrics = {k: v for k, v in metrics.items() if 'precision' in k and 'std' not in k}
        recall_metrics = {k: v for k, v in metrics.items() if 'recall' in k and 'std' not in k}
        ndcg_metrics = {k: v for k, v in metrics.items() if 'ndcg' in k and 'std' not in k}
        hit_rate_metrics = {k: v for k, v in metrics.items() if 'hit_rate' in k and 'std' not in k}
        mrr = metrics.get('mrr', 0.0)
        
        if precision_metrics:
            print(f"\n📍 Precision@K:")
            for k, v in sorted(precision_metrics.items()):
                std = metrics.get(f'{k}_std', 0.0)
                print(f"   {k}: {v:.4f} (±{std:.4f})")
        
        if recall_metrics:
            print(f"\n🎯 Recall@K:")
            for k, v in sorted(recall_metrics.items()):
                std = metrics.get(f'{k}_std', 0.0)
                print(f"   {k}: {v:.4f} (±{std:.4f})")
        
        if ndcg_metrics:
            print(f"\n📈 NDCG@K:")
            for k, v in sorted(ndcg_metrics.items()):
                std = metrics.get(f'{k}_std', 0.0)
                print(f"   {k}: {v:.4f} (±{std:.4f})")
        
        if hit_rate_metrics:
            print(f"\n✅ Hit Rate@K:")
            for k, v in sorted(hit_rate_metrics.items()):
                std = metrics.get(f'{k}_std', 0.0)
                print(f"   {k}: {v:.4f} (±{std:.4f})")
        
        if mrr > 0:
            mrr_std = metrics.get('mrr_std', 0.0)
            print(f"\n🏆 Mean Reciprocal Rank:")
            print(f"   MRR: {mrr:.4f} (±{mrr_std:.4f})")
        
        print(f"{'='*60}\n")


# Test code
if __name__ == "__main__":
    print("="*60)
    print("TESTING RETRIEVAL EVALUATOR")
    print("="*60)
    
    evaluator = RetrievalEvaluator()
    
    # Example 1: Single query
    print("\n# Example 1: Single Query")
    retrieved = ['doc1', 'doc2', 'doc3', 'doc4', 'doc5']
    relevant = {'doc1', 'doc3', 'doc6'}
    relevance_scores = {'doc1': 1.0, 'doc3': 0.8, 'doc6': 0.6}
    
    metrics = evaluator.evaluate_query(retrieved, relevant, relevance_scores, k_values=[1, 3, 5])
    evaluator.print_metrics(metrics)
    
    # Example 2: Batch evaluation
    print("\n# Example 2: Batch Evaluation")
    queries = [
        {
            'retrieved': ['doc1', 'doc2', 'doc3'],
            'relevant': {'doc1', 'doc3'},
            'relevance_scores': {'doc1': 1.0, 'doc3': 0.8}
        },
        {
            'retrieved': ['doc4', 'doc5', 'doc6'],
            'relevant': {'doc5', 'doc7'},
            'relevance_scores': {'doc5': 1.0, 'doc7': 0.9}
        },
        {
            'retrieved': ['doc8', 'doc9', 'doc10'],
            'relevant': {'doc8', 'doc9', 'doc10'},
            'relevance_scores': {'doc8': 1.0, 'doc9': 0.9, 'doc10': 0.8}
        }
    ]
    
    batch_metrics = evaluator.evaluate_batch(queries)
    evaluator.print_metrics(batch_metrics)
