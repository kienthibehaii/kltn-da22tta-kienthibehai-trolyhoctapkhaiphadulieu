# evaluation/benchmark.py - RAG Benchmark System
"""
RAG Benchmark System

Features:
- Automatic benchmarking
- Evaluation pipeline
- Experiment tracking
- Performance reports
- Visualization
- Export (CSV, JSON, PDF)
"""

import json
import time
import os
from datetime import datetime
from typing import List, Dict, Optional, Callable
from pathlib import Path
import numpy as np

from .retrieval_eval import RetrievalEvaluator
from .generation_eval import GenerationEvaluator
from .citation_eval import CitationEvaluator


class RAGBenchmark:
    """
    Complete RAG benchmarking system.
    """
    
    def __init__(self, 
                 dataset_path: str = "evaluation/dataset.json",
                 output_dir: str = "evaluation/results"):
        """
        Initialize RAG Benchmark.
        
        Args:
            dataset_path: Path to test dataset JSON
            output_dir: Directory for results
        """
        self.dataset_path = dataset_path
        self.output_dir = output_dir
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize evaluators
        self.retrieval_eval = RetrievalEvaluator()
        self.generation_eval = GenerationEvaluator()
        self.citation_eval = CitationEvaluator()
        
        # Load dataset
        self.dataset = self._load_dataset()
        
        # Experiment tracking
        self.experiments = []
        
        print(f"✅ RAG Benchmark initialized")
        print(f"   Dataset: {len(self.dataset)} queries")
        print(f"   Output: {output_dir}")
    
    def _load_dataset(self) -> List[Dict]:
        """Load test dataset from JSON"""
        try:
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                dataset = json.load(f)
            return dataset
        except FileNotFoundError:
            print(f"⚠️  Dataset not found: {self.dataset_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"⚠️  Invalid JSON in dataset: {e}")
            return []
    
    def run_benchmark(self,
                     rag_system: Callable,
                     experiment_name: str = "default",
                     k_values: List[int] = [1, 3, 5],
                     verbose: bool = True) -> Dict:
        """
        Run complete benchmark on RAG system.
        
        Args:
            rag_system: Function that takes query and returns (answer, retrieved_docs, sources)
            experiment_name: Name for this experiment
            k_values: K values for retrieval metrics
            verbose: Print progress
        
        Returns:
            Dict with all metrics
        """
        if verbose:
            print(f"\n{'='*60}")
            print(f"🚀 RUNNING RAG BENCHMARK: {experiment_name}")
            print(f"{'='*60}")
            print(f"Dataset: {len(self.dataset)} queries")
            print(f"K values: {k_values}")
        
        start_time = time.time()
        
        # Collect results
        retrieval_queries = []
        generation_pairs = []
        citation_evals = []
        
        for i, test_case in enumerate(self.dataset, 1):
            if verbose:
                print(f"\n[{i}/{len(self.dataset)}] Processing: {test_case['query'][:50]}...")
            
            query = test_case['query']
            reference_answer = test_case['reference_answer']
            relevant_docs = set(test_case['relevant_docs'])
            relevance_scores = test_case['relevance_scores']
            sources = test_case['sources']
            
            try:
                # Run RAG system
                answer, retrieved_docs, retrieved_sources = rag_system(query)
                
                # Retrieval evaluation
                retrieval_queries.append({
                    'retrieved': retrieved_docs,
                    'relevant': relevant_docs,
                    'relevance_scores': relevance_scores,
                    'k_values': k_values
                })
                
                # Generation evaluation
                generation_pairs.append({
                    'generated': answer,
                    'reference': reference_answer
                })
                
                # Citation evaluation
                # Extract citations from answer
                citations = self._extract_citations_from_answer(answer, retrieved_sources)
                
                citation_evals.append({
                    'answer': answer,
                    'query': query,
                    'citations': citations,
                    'sources': retrieved_sources
                })
                
            except Exception as e:
                if verbose:
                    print(f"   ⚠️  Error: {e}")
                continue
        
        # Evaluate all metrics
        if verbose:
            print(f"\n{'='*60}")
            print(f"📊 EVALUATING METRICS")
            print(f"{'='*60}")
        
        retrieval_metrics = self.retrieval_eval.evaluate_batch(retrieval_queries)
        generation_metrics = self.generation_eval.evaluate_batch(generation_pairs)
        citation_metrics = self.citation_eval.evaluate_batch(citation_evals)
        
        # Combine metrics
        all_metrics = {
            'experiment_name': experiment_name,
            'timestamp': datetime.now().isoformat(),
            'dataset_size': len(self.dataset),
            'execution_time': time.time() - start_time,
            'retrieval': retrieval_metrics,
            'generation': generation_metrics,
            'citation': citation_metrics
        }
        
        # Save experiment
        self.experiments.append(all_metrics)
        
        # Print results
        if verbose:
            self._print_results(all_metrics)
        
        # Save results
        self._save_results(all_metrics, experiment_name)
        
        return all_metrics
    
    def _extract_citations_from_answer(self, 
                                      answer: str, 
                                      sources: Dict[str, str]) -> List[Dict]:
        """Extract citations from answer"""
        citations = []
        
        # Simple extraction: look for [doc_id] patterns
        import re
        pattern = r'\[([^\]]+)\]'
        matches = re.findall(pattern, answer)
        
        for match in matches:
            if match in sources:
                # Find the sentence containing this citation
                sentences = answer.split('.')
                for sentence in sentences:
                    if f'[{match}]' in sentence:
                        citations.append({
                            'id': match,
                            'claim': sentence.strip()
                        })
                        break
        
        return citations
    
    def _print_results(self, metrics: Dict):
        """Print benchmark results"""
        print(f"\n{'='*60}")
        print(f"📊 BENCHMARK RESULTS: {metrics['experiment_name']}")
        print(f"{'='*60}")
        print(f"Execution time: {metrics['execution_time']:.2f}s")
        print(f"Dataset size: {metrics['dataset_size']}")
        
        # Retrieval metrics
        print(f"\n📚 RETRIEVAL METRICS:")
        retrieval = metrics['retrieval']
        for k in [1, 3, 5]:
            if f'precision@{k}' in retrieval:
                print(f"   Precision@{k}: {retrieval[f'precision@{k}']:.4f}")
                print(f"   Recall@{k}: {retrieval[f'recall@{k}']:.4f}")
                print(f"   NDCG@{k}: {retrieval[f'ndcg@{k}']:.4f}")
        if 'mrr' in retrieval:
            print(f"   MRR: {retrieval['mrr']:.4f}")
        
        # Generation metrics
        print(f"\n📝 GENERATION METRICS:")
        generation = metrics['generation']
        if 'bleu' in generation:
            print(f"   BLEU: {generation['bleu']:.4f}")
        if 'rouge-1' in generation:
            print(f"   ROUGE-1: {generation['rouge-1']:.4f}")
            print(f"   ROUGE-2: {generation['rouge-2']:.4f}")
            print(f"   ROUGE-L: {generation['rouge-l']:.4f}")
        if 'semantic_similarity' in generation:
            print(f"   Semantic Similarity: {generation['semantic_similarity']:.4f}")
        
        # Citation metrics
        print(f"\n📚 CITATION METRICS:")
        citation = metrics['citation']
        if 'citation_accuracy' in citation:
            print(f"   Citation Accuracy: {citation['citation_accuracy']:.4f}")
        if 'avg_relevance' in citation:
            print(f"   Source Relevance: {citation['avg_relevance']:.4f}")
        if 'hallucination_rate' in citation:
            print(f"   Hallucination Rate: {citation['hallucination_rate']:.4f}")
        if 'citation_coverage' in citation:
            print(f"   Citation Coverage: {citation['citation_coverage']:.4f}")
        
        print(f"{'='*60}\n")
    
    def _save_results(self, metrics: Dict, experiment_name: str):
        """Save results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{experiment_name}_{timestamp}"
        
        # Save JSON
        json_path = os.path.join(self.output_dir, f"{base_name}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved:")
        print(f"   JSON: {json_path}")
        
        # Save CSV
        csv_path = os.path.join(self.output_dir, f"{base_name}.csv")
        self._save_csv(metrics, csv_path)
        print(f"   CSV: {csv_path}")
    
    def _save_csv(self, metrics: Dict, csv_path: str):
        """Save metrics to CSV"""
        import csv
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow(['Metric Category', 'Metric Name', 'Value', 'Std Dev'])
            
            # Retrieval metrics
            for key, value in metrics['retrieval'].items():
                if '_std' not in key:
                    std = metrics['retrieval'].get(f'{key}_std', 0.0)
                    writer.writerow(['Retrieval', key, f'{value:.4f}', f'{std:.4f}'])
            
            # Generation metrics
            for key, value in metrics['generation'].items():
                if '_std' not in key:
                    std = metrics['generation'].get(f'{key}_std', 0.0)
                    writer.writerow(['Generation', key, f'{value:.4f}', f'{std:.4f}'])
            
            # Citation metrics
            for key, value in metrics['citation'].items():
                if '_std' not in key:
                    std = metrics['citation'].get(f'{key}_std', 0.0)
                    writer.writerow(['Citation', key, f'{value:.4f}', f'{std:.4f}'])
    
    def compare_experiments(self, 
                          experiment_names: List[str] = None) -> Dict:
        """
        Compare multiple experiments.
        
        Args:
            experiment_names: List of experiment names to compare (None = all)
        
        Returns:
            Dict with comparison data
        """
        if not self.experiments:
            print("⚠️  No experiments to compare")
            return {}
        
        if experiment_names is None:
            experiments = self.experiments
        else:
            experiments = [e for e in self.experiments if e['experiment_name'] in experiment_names]
        
        if not experiments:
            print("⚠️  No matching experiments found")
            return {}
        
        print(f"\n{'='*60}")
        print(f"📊 COMPARING {len(experiments)} EXPERIMENTS")
        print(f"{'='*60}")
        
        # Compare key metrics
        comparison = {}
        
        for exp in experiments:
            name = exp['experiment_name']
            comparison[name] = {
                'retrieval': {
                    'precision@3': exp['retrieval'].get('precision@3', 0.0),
                    'recall@3': exp['retrieval'].get('recall@3', 0.0),
                    'ndcg@3': exp['retrieval'].get('ndcg@3', 0.0),
                    'mrr': exp['retrieval'].get('mrr', 0.0)
                },
                'generation': {
                    'bleu': exp['generation'].get('bleu', 0.0),
                    'rouge-1': exp['generation'].get('rouge-1', 0.0),
                    'semantic_similarity': exp['generation'].get('semantic_similarity', 0.0)
                },
                'citation': {
                    'citation_accuracy': exp['citation'].get('citation_accuracy', 0.0),
                    'hallucination_rate': exp['citation'].get('hallucination_rate', 0.0)
                }
            }
        
        # Print comparison
        print(f"\n📊 Comparison Table:")
        print(f"\n{'Experiment':<20} {'P@3':<8} {'R@3':<8} {'NDCG@3':<8} {'MRR':<8} {'BLEU':<8} {'ROUGE-1':<8}")
        print(f"{'-'*80}")
        
        for name, metrics in comparison.items():
            print(f"{name:<20} "
                  f"{metrics['retrieval']['precision@3']:<8.4f} "
                  f"{metrics['retrieval']['recall@3']:<8.4f} "
                  f"{metrics['retrieval']['ndcg@3']:<8.4f} "
                  f"{metrics['retrieval']['mrr']:<8.4f} "
                  f"{metrics['generation']['bleu']:<8.4f} "
                  f"{metrics['generation']['rouge-1']:<8.4f}")
        
        return comparison
    
    def visualize_results(self, 
                         metrics: Dict,
                         save_path: Optional[str] = None):
        """
        Visualize benchmark results.
        
        Args:
            metrics: Metrics dict from run_benchmark
            save_path: Path to save figure (None = show only)
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            
            fig, axes = plt.subplots(2, 2, figsize=(14, 10))
            fig.suptitle(f"RAG Benchmark Results: {metrics['experiment_name']}", 
                        fontsize=16, fontweight='bold')
            
            # 1. Retrieval Metrics
            ax1 = axes[0, 0]
            retrieval = metrics['retrieval']
            k_values = [1, 3, 5]
            
            precision = [retrieval.get(f'precision@{k}', 0) for k in k_values]
            recall = [retrieval.get(f'recall@{k}', 0) for k in k_values]
            ndcg = [retrieval.get(f'ndcg@{k}', 0) for k in k_values]
            
            x = np.arange(len(k_values))
            width = 0.25
            
            ax1.bar(x - width, precision, width, label='Precision', color='#3498db')
            ax1.bar(x, recall, width, label='Recall', color='#2ecc71')
            ax1.bar(x + width, ndcg, width, label='NDCG', color='#e74c3c')
            
            ax1.set_xlabel('K')
            ax1.set_ylabel('Score')
            ax1.set_title('Retrieval Metrics @K')
            ax1.set_xticks(x)
            ax1.set_xticklabels(k_values)
            ax1.legend()
            ax1.grid(axis='y', alpha=0.3)
            
            # 2. Generation Metrics
            ax2 = axes[0, 1]
            generation = metrics['generation']
            
            gen_metrics = {
                'BLEU': generation.get('bleu', 0),
                'ROUGE-1': generation.get('rouge-1', 0),
                'ROUGE-2': generation.get('rouge-2', 0),
                'ROUGE-L': generation.get('rouge-l', 0),
                'Semantic\nSimilarity': generation.get('semantic_similarity', 0)
            }
            
            ax2.bar(gen_metrics.keys(), gen_metrics.values(), color='#9b59b6')
            ax2.set_ylabel('Score')
            ax2.set_title('Generation Metrics')
            ax2.set_ylim([0, 1])
            ax2.grid(axis='y', alpha=0.3)
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # 3. Citation Metrics
            ax3 = axes[1, 0]
            citation = metrics['citation']
            
            cite_metrics = {
                'Citation\nAccuracy': citation.get('citation_accuracy', 0),
                'Source\nRelevance': citation.get('avg_relevance', 0),
                'Support\nRate': citation.get('support_rate', 0),
                'Citation\nCoverage': citation.get('citation_coverage', 0)
            }
            
            colors = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c']
            ax3.bar(cite_metrics.keys(), cite_metrics.values(), color=colors)
            ax3.set_ylabel('Score')
            ax3.set_title('Citation Metrics')
            ax3.set_ylim([0, 1])
            ax3.grid(axis='y', alpha=0.3)
            plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # 4. Overall Summary
            ax4 = axes[1, 1]
            ax4.axis('off')
            
            summary_text = f"""
            BENCHMARK SUMMARY
            
            Experiment: {metrics['experiment_name']}
            Dataset Size: {metrics['dataset_size']}
            Execution Time: {metrics['execution_time']:.2f}s
            
            TOP METRICS:
            • Precision@3: {retrieval.get('precision@3', 0):.4f}
            • Recall@3: {retrieval.get('recall@3', 0):.4f}
            • MRR: {retrieval.get('mrr', 0):.4f}
            • BLEU: {generation.get('bleu', 0):.4f}
            • ROUGE-1: {generation.get('rouge-1', 0):.4f}
            • Citation Accuracy: {citation.get('citation_accuracy', 0):.4f}
            • Hallucination Rate: {citation.get('hallucination_rate', 0):.4f}
            """
            
            ax4.text(0.1, 0.5, summary_text, fontsize=11, 
                    verticalalignment='center', fontfamily='monospace')
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"📊 Visualization saved: {save_path}")
            else:
                plt.savefig(os.path.join(self.output_dir, 
                           f"{metrics['experiment_name']}_visualization.png"),
                           dpi=300, bbox_inches='tight')
                print(f"📊 Visualization saved to: {self.output_dir}")
            
            plt.close()
            
        except ImportError:
            print("⚠️  matplotlib not installed. Skipping visualization.")
        except Exception as e:
            print(f"⚠️  Visualization error: {e}")


# Test code
if __name__ == "__main__":
    print("="*60)
    print("TESTING RAG BENCHMARK")
    print("="*60)
    
    # Mock RAG system for testing
    def mock_rag_system(query: str):
        """Mock RAG system that returns dummy results"""
        answer = f"This is a generated answer for: {query}"
        retrieved_docs = ['doc1', 'doc2', 'doc3']
        sources = {
            'doc1': 'Source text for doc1',
            'doc2': 'Source text for doc2',
            'doc3': 'Source text for doc3'
        }
        return answer, retrieved_docs, sources
    
    # Create benchmark
    benchmark = RAGBenchmark(
        dataset_path="evaluation/dataset.json",
        output_dir="evaluation/results"
    )
    
    # Run benchmark
    if benchmark.dataset:
        metrics = benchmark.run_benchmark(
            rag_system=mock_rag_system,
            experiment_name="test_experiment",
            verbose=True
        )
        
        # Visualize
        benchmark.visualize_results(metrics)
    else:
        print("⚠️  No dataset loaded. Skipping benchmark.")
