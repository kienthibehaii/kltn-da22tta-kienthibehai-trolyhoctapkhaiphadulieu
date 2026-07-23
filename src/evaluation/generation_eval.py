# evaluation/generation_eval.py - Generation Metrics Evaluation
"""
Generation Evaluation Metrics

Metrics:
- BLEU: N-gram overlap (machine translation quality)
- ROUGE: Recall-oriented n-gram overlap (summarization quality)
- BERTScore: Semantic similarity using BERT embeddings
- Semantic Similarity: Cosine similarity of embeddings
"""

import numpy as np
from typing import List, Dict
from collections import Counter, defaultdict
import re


class GenerationEvaluator:
    """
    Evaluator for generation quality metrics.
    """
    
    def __init__(self):
        """Initialize generation evaluator"""
        self.embeddings_model = None
        self.bertscore_model = None
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        # Lowercase and split on whitespace/punctuation
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return tokens
    
    def _get_ngrams(self, tokens: List[str], n: int) -> Counter:
        """Get n-grams from tokens"""
        ngrams = []
        for i in range(len(tokens) - n + 1):
            ngram = tuple(tokens[i:i+n])
            ngrams.append(ngram)
        return Counter(ngrams)
    
    def bleu_score(self, 
                   generated: str, 
                   reference: str, 
                   max_n: int = 4) -> Dict[str, float]:
        """
        Calculate BLEU score.
        
        BLEU = BP * exp(Σ w_n * log(p_n))
        where p_n is n-gram precision
        
        Args:
            generated: Generated text
            reference: Reference text
            max_n: Maximum n-gram size (default: 4)
        
        Returns:
            Dict with BLEU scores for each n-gram size
        """
        gen_tokens = self._tokenize(generated)
        ref_tokens = self._tokenize(reference)
        
        if not gen_tokens or not ref_tokens:
            return {f'bleu-{n}': 0.0 for n in range(1, max_n + 1)}
        
        scores = {}
        
        for n in range(1, max_n + 1):
            gen_ngrams = self._get_ngrams(gen_tokens, n)
            ref_ngrams = self._get_ngrams(ref_tokens, n)
            
            if not gen_ngrams:
                scores[f'bleu-{n}'] = 0.0
                continue
            
            # Calculate precision
            matches = sum((gen_ngrams & ref_ngrams).values())
            total = sum(gen_ngrams.values())
            
            precision = matches / total if total > 0 else 0.0
            scores[f'bleu-{n}'] = precision
        
        # Calculate brevity penalty
        gen_len = len(gen_tokens)
        ref_len = len(ref_tokens)
        
        if gen_len >= ref_len:
            bp = 1.0
        else:
            bp = np.exp(1 - ref_len / gen_len) if gen_len > 0 else 0.0
        
        # Calculate geometric mean of precisions
        precisions = [scores[f'bleu-{n}'] for n in range(1, max_n + 1)]
        if all(p > 0 for p in precisions):
            geo_mean = np.exp(np.mean([np.log(p) for p in precisions]))
            scores['bleu'] = bp * geo_mean
        else:
            scores['bleu'] = 0.0
        
        scores['brevity_penalty'] = bp
        
        return scores
    
    def rouge_score(self, 
                   generated: str, 
                   reference: str) -> Dict[str, float]:
        """
        Calculate ROUGE scores (ROUGE-1, ROUGE-2, ROUGE-L).
        
        ROUGE-N = (# overlapping n-grams) / (# n-grams in reference)
        
        Args:
            generated: Generated text
            reference: Reference text
        
        Returns:
            Dict with ROUGE scores
        """
        gen_tokens = self._tokenize(generated)
        ref_tokens = self._tokenize(reference)
        
        if not gen_tokens or not ref_tokens:
            return {'rouge-1': 0.0, 'rouge-2': 0.0, 'rouge-l': 0.0}
        
        scores = {}
        
        # ROUGE-1 (unigram overlap)
        gen_unigrams = Counter(gen_tokens)
        ref_unigrams = Counter(ref_tokens)
        
        overlap_1 = sum((gen_unigrams & ref_unigrams).values())
        recall_1 = overlap_1 / len(ref_tokens) if ref_tokens else 0.0
        precision_1 = overlap_1 / len(gen_tokens) if gen_tokens else 0.0
        
        if recall_1 + precision_1 > 0:
            f1_1 = 2 * (precision_1 * recall_1) / (precision_1 + recall_1)
        else:
            f1_1 = 0.0
        
        scores['rouge-1'] = f1_1
        scores['rouge-1-recall'] = recall_1
        scores['rouge-1-precision'] = precision_1
        
        # ROUGE-2 (bigram overlap)
        gen_bigrams = self._get_ngrams(gen_tokens, 2)
        ref_bigrams = self._get_ngrams(ref_tokens, 2)
        
        overlap_2 = sum((gen_bigrams & ref_bigrams).values())
        total_ref_2 = sum(ref_bigrams.values())
        total_gen_2 = sum(gen_bigrams.values())
        
        recall_2 = overlap_2 / total_ref_2 if total_ref_2 > 0 else 0.0
        precision_2 = overlap_2 / total_gen_2 if total_gen_2 > 0 else 0.0
        
        if recall_2 + precision_2 > 0:
            f1_2 = 2 * (precision_2 * recall_2) / (precision_2 + recall_2)
        else:
            f1_2 = 0.0
        
        scores['rouge-2'] = f1_2
        scores['rouge-2-recall'] = recall_2
        scores['rouge-2-precision'] = precision_2
        
        # ROUGE-L (longest common subsequence)
        lcs_length = self._lcs_length(gen_tokens, ref_tokens)
        
        recall_l = lcs_length / len(ref_tokens) if ref_tokens else 0.0
        precision_l = lcs_length / len(gen_tokens) if gen_tokens else 0.0
        
        if recall_l + precision_l > 0:
            f1_l = 2 * (precision_l * recall_l) / (precision_l + recall_l)
        else:
            f1_l = 0.0
        
        scores['rouge-l'] = f1_l
        scores['rouge-l-recall'] = recall_l
        scores['rouge-l-precision'] = precision_l
        
        return scores
    
    def _lcs_length(self, seq1: List[str], seq2: List[str]) -> int:
        """Calculate longest common subsequence length"""
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i-1] == seq2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        return dp[m][n]
    
    def bert_score(self, 
                  generated: str, 
                  reference: str) -> Dict[str, float]:
        """
        Calculate BERTScore using sentence-transformers.
        
        Args:
            generated: Generated text
            reference: Reference text
        
        Returns:
            Dict with BERTScore (precision, recall, F1)
        """
        try:
            if self.bertscore_model is None:
                from sentence_transformers import SentenceTransformer
                self.bertscore_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Get embeddings
            gen_embedding = self.bertscore_model.encode(generated, convert_to_tensor=True)
            ref_embedding = self.bertscore_model.encode(reference, convert_to_tensor=True)
            
            # Calculate cosine similarity
            import torch
            similarity = torch.nn.functional.cosine_similarity(
                gen_embedding.unsqueeze(0), 
                ref_embedding.unsqueeze(0)
            ).item()
            
            # BERTScore uses similarity as both precision and recall for sentence-level
            return {
                'bertscore-precision': similarity,
                'bertscore-recall': similarity,
                'bertscore-f1': similarity
            }
        
        except ImportError:
            print("⚠️  sentence-transformers not installed. Skipping BERTScore.")
            return {
                'bertscore-precision': 0.0,
                'bertscore-recall': 0.0,
                'bertscore-f1': 0.0
            }
    
    def semantic_similarity(self, 
                          generated: str, 
                          reference: str) -> float:
        """
        Calculate semantic similarity using embeddings.
        
        Args:
            generated: Generated text
            reference: Reference text
        
        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        try:
            if self.embeddings_model is None:
                from sentence_transformers import SentenceTransformer
                self.embeddings_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Get embeddings
            embeddings = self.embeddings_model.encode([generated, reference])
            
            # Calculate cosine similarity
            from sklearn.metrics.pairwise import cosine_similarity
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            
            return float(similarity)
        
        except ImportError:
            print("⚠️  sentence-transformers not installed. Using fallback.")
            # Fallback: simple token overlap
            gen_tokens = set(self._tokenize(generated))
            ref_tokens = set(self._tokenize(reference))
            
            if not gen_tokens or not ref_tokens:
                return 0.0
            
            overlap = len(gen_tokens & ref_tokens)
            union = len(gen_tokens | ref_tokens)
            
            return overlap / union if union > 0 else 0.0
    
    def evaluate_generation(self, 
                          generated: str, 
                          reference: str) -> Dict[str, float]:
        """
        Evaluate all generation metrics.
        
        Args:
            generated: Generated text
            reference: Reference text
        
        Returns:
            Dict with all metrics
        """
        metrics = {}
        
        # BLEU
        bleu_scores = self.bleu_score(generated, reference)
        metrics.update(bleu_scores)
        
        # ROUGE
        rouge_scores = self.rouge_score(generated, reference)
        metrics.update(rouge_scores)
        
        # BERTScore
        bert_scores = self.bert_score(generated, reference)
        metrics.update(bert_scores)
        
        # Semantic Similarity
        metrics['semantic_similarity'] = self.semantic_similarity(generated, reference)
        
        return metrics
    
    def evaluate_batch(self, 
                      generations: List[Dict]) -> Dict[str, float]:
        """
        Evaluate metrics for multiple generations.
        
        Args:
            generations: List of dicts with 'generated' and 'reference'
        
        Returns:
            Dict with averaged metrics
        """
        all_metrics = defaultdict(list)
        
        for gen_data in generations:
            generated = gen_data['generated']
            reference = gen_data['reference']
            
            metrics = self.evaluate_generation(generated, reference)
            
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
        print(f"📝 GENERATION EVALUATION METRICS")
        print(f"{'='*60}")
        
        # BLEU scores
        bleu_metrics = {k: v for k, v in metrics.items() if 'bleu' in k and 'std' not in k}
        if bleu_metrics:
            print(f"\n📊 BLEU Scores:")
            for k, v in sorted(bleu_metrics.items()):
                std = metrics.get(f'{k}_std', 0.0)
                print(f"   {k}: {v:.4f} (±{std:.4f})")
        
        # ROUGE scores
        rouge_metrics = {k: v for k, v in metrics.items() if 'rouge' in k and 'std' not in k}
        if rouge_metrics:
            print(f"\n🎯 ROUGE Scores:")
            for k, v in sorted(rouge_metrics.items()):
                std = metrics.get(f'{k}_std', 0.0)
                print(f"   {k}: {v:.4f} (±{std:.4f})")
        
        # BERTScore
        bert_metrics = {k: v for k, v in metrics.items() if 'bertscore' in k and 'std' not in k}
        if bert_metrics:
            print(f"\n🤖 BERTScore:")
            for k, v in sorted(bert_metrics.items()):
                std = metrics.get(f'{k}_std', 0.0)
                print(f"   {k}: {v:.4f} (±{std:.4f})")
        
        # Semantic Similarity
        if 'semantic_similarity' in metrics:
            sem_sim = metrics['semantic_similarity']
            sem_sim_std = metrics.get('semantic_similarity_std', 0.0)
            print(f"\n🔗 Semantic Similarity:")
            print(f"   similarity: {sem_sim:.4f} (±{sem_sim_std:.4f})")
        
        print(f"{'='*60}\n")


# Test code
if __name__ == "__main__":
    print("="*60)
    print("TESTING GENERATION EVALUATOR")
    print("="*60)
    
    evaluator = GenerationEvaluator()
    
    # Example 1: Single generation
    print("\n# Example 1: Single Generation")
    generated = "Data mining is the process of discovering patterns in large datasets."
    reference = "Data mining discovers patterns in large data sets using machine learning."
    
    metrics = evaluator.evaluate_generation(generated, reference)
    evaluator.print_metrics(metrics)
    
    # Example 2: Batch evaluation
    print("\n# Example 2: Batch Evaluation")
    generations = [
        {
            'generated': "Classification predicts categories for data points.",
            'reference': "Classification is a supervised learning task that predicts categories."
        },
        {
            'generated': "Clustering groups similar items together.",
            'reference': "Clustering algorithms group similar data points without labels."
        },
        {
            'generated': "Association rules find patterns in transactions.",
            'reference': "Association rule mining discovers relationships in transaction data."
        }
    ]
    
    batch_metrics = evaluator.evaluate_batch(generations)
    evaluator.print_metrics(batch_metrics)
