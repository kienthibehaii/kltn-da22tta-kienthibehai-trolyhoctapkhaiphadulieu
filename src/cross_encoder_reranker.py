# cross_encoder_reranker.py - Cross-Encoder Reranking for RAG
"""
Cross-Encoder Reranking Module

Pipeline:
Query → Hybrid Retrieval → Top 20 docs → Cross-Encoder Rerank → Top 3 docs → LLM

Features:
- Cross-encoder/ms-marco-MiniLM-L-6-v2 model
- Accurate relevance scoring
- Threshold filtering
- GPU/CPU optimization
- Performance metrics
- Debug logging
"""

import time
from typing import List, Tuple, Dict, Optional
from langchain_core.documents import Document
import numpy as np
import torch


class CrossEncoderReranker:
    """
    Cross-Encoder based reranker for accurate relevance scoring.
    
    Uses ms-marco-MiniLM-L-6-v2 trained on MS MARCO dataset.
    """
    
    def __init__(self, 
                 model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
                 device: Optional[str] = None,
                 batch_size: int = 16):
        """
        Initialize Cross-Encoder Reranker.
        
        Args:
            model_name: HuggingFace model name
            device: 'cuda', 'cpu', or None (auto-detect)
            batch_size: Batch size for inference
        """
        print(f"🔄 Initializing Cross-Encoder Reranker...")
        print(f"   Model: {model_name}")
        
        # Auto-detect device
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.device = device
        print(f"   Device: {device.upper()}")
        
        # Load model
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(model_name, device=device)
            self.batch_size = batch_size
            print(f"✅ Cross-Encoder loaded successfully")
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load Cross-Encoder: {e}")
        
        # Metrics tracking
        self.metrics = {
            'total_reranks': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
            'total_docs_processed': 0
        }
    
    def rerank(self, 
               query: str, 
               documents: List[Document],
               top_k: int = 3,
               threshold: Optional[float] = None,
               return_scores: bool = True,
               debug: bool = False) -> List[Tuple[Document, float]]:
        """
        Rerank documents using Cross-Encoder.
        
        Args:
            query: Search query
            documents: List of documents to rerank
            top_k: Number of top documents to return
            threshold: Minimum relevance score (None = no filtering)
            return_scores: Whether to return scores
            debug: Enable debug logging
        
        Returns:
            List of (document, score) tuples sorted by relevance
        """
        if not documents:
            return []
        
        start_time = time.time()
        
        if debug:
            print(f"\n{'='*60}")
            print(f"🔍 CROSS-ENCODER RERANKING")
            print(f"{'='*60}")
            print(f"Query: {query}")
            print(f"Documents to rerank: {len(documents)}")
            print(f"Top K: {top_k}")
            print(f"Threshold: {threshold}")
        
        # Prepare query-document pairs
        pairs = [(query, doc.page_content) for doc in documents]
        
        # Predict relevance scores
        if debug:
            print(f"\n🤖 Computing relevance scores...")
        
        scores = self.model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=debug
        )
        
        # Convert to list if numpy array
        if isinstance(scores, np.ndarray):
            scores = scores.tolist()
        
        # Combine documents with scores
        scored_docs = list(zip(documents, scores))
        
        # Sort by score (descending)
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Apply threshold filtering
        if threshold is not None:
            original_count = len(scored_docs)
            scored_docs = [(doc, score) for doc, score in scored_docs if score >= threshold]
            filtered_count = original_count - len(scored_docs)
            
            if debug and filtered_count > 0:
                print(f"🗑️  Filtered out {filtered_count} docs below threshold {threshold}")
        
        # Take top K
        top_docs = scored_docs[:top_k]
        
        # Update metrics
        elapsed_time = time.time() - start_time
        self._update_metrics(len(documents), elapsed_time)
        
        # Debug output
        if debug:
            print(f"\n📊 Reranking Results:")
            print(f"{'='*60}")
            for i, (doc, score) in enumerate(top_docs, 1):
                print(f"\n{i}. Score: {score:.4f}")
                print(f"   Content: {doc.page_content[:100]}...")
                if 'source' in doc.metadata:
                    print(f"   Source: {doc.metadata['source']}")
                if 'page' in doc.metadata:
                    print(f"   Page: {doc.metadata['page']}")
            
            print(f"\n⏱️  Time: {elapsed_time:.3f}s")
            print(f"{'='*60}\n")
        
        if return_scores:
            return top_docs
        else:
            return [doc for doc, _ in top_docs]
    
    def rerank_with_details(self,
                           query: str,
                           documents: List[Document],
                           top_k: int = 3,
                           threshold: Optional[float] = None) -> Dict:
        """
        Rerank with detailed metrics and analysis.
        
        Returns:
            Dict with reranked_docs, scores, metrics, and analysis
        """
        start_time = time.time()
        
        # Prepare pairs
        pairs = [(query, doc.page_content) for doc in documents]
        
        # Predict scores
        scores = self.model.predict(pairs, batch_size=self.batch_size)
        if isinstance(scores, np.ndarray):
            scores = scores.tolist()
        
        # Combine and sort
        scored_docs = list(zip(documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Apply threshold
        if threshold is not None:
            scored_docs = [(doc, score) for doc, score in scored_docs if score >= threshold]
        
        # Take top K
        top_docs = scored_docs[:top_k]
        
        # Calculate metrics
        elapsed_time = time.time() - start_time
        
        # Score analysis
        all_scores = [score for _, score in scored_docs]
        score_stats = {
            'mean': np.mean(all_scores) if all_scores else 0,
            'std': np.std(all_scores) if all_scores else 0,
            'min': np.min(all_scores) if all_scores else 0,
            'max': np.max(all_scores) if all_scores else 0,
            'median': np.median(all_scores) if all_scores else 0
        }
        
        return {
            'reranked_docs': top_docs,
            'all_scored_docs': scored_docs,
            'score_stats': score_stats,
            'metrics': {
                'num_input_docs': len(documents),
                'num_output_docs': len(top_docs),
                'num_filtered': len(documents) - len(scored_docs) if threshold else 0,
                'time_seconds': elapsed_time,
                'docs_per_second': len(documents) / elapsed_time if elapsed_time > 0 else 0
            }
        }
    
    def batch_rerank(self,
                    queries: List[str],
                    documents_list: List[List[Document]],
                    top_k: int = 3,
                    threshold: Optional[float] = None) -> List[List[Tuple[Document, float]]]:
        """
        Rerank multiple queries in batch.
        
        Args:
            queries: List of queries
            documents_list: List of document lists (one per query)
            top_k: Number of top documents per query
            threshold: Minimum relevance score
        
        Returns:
            List of reranked document lists
        """
        results = []
        
        for query, documents in zip(queries, documents_list):
            reranked = self.rerank(
                query=query,
                documents=documents,
                top_k=top_k,
                threshold=threshold,
                return_scores=True,
                debug=False
            )
            results.append(reranked)
        
        return results
    
    def _update_metrics(self, num_docs: int, elapsed_time: float):
        """Update internal metrics"""
        self.metrics['total_reranks'] += 1
        self.metrics['total_time'] += elapsed_time
        self.metrics['total_docs_processed'] += num_docs
        self.metrics['avg_time'] = self.metrics['total_time'] / self.metrics['total_reranks']
    
    def get_metrics(self) -> Dict:
        """Get performance metrics"""
        return self.metrics.copy()
    
    def reset_metrics(self):
        """Reset performance metrics"""
        self.metrics = {
            'total_reranks': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
            'total_docs_processed': 0
        }
    
    def print_metrics(self):
        """Print performance metrics"""
        print(f"\n{'='*60}")
        print(f"📊 CROSS-ENCODER RERANKER METRICS")
        print(f"{'='*60}")
        print(f"Total reranks: {self.metrics['total_reranks']}")
        print(f"Total documents processed: {self.metrics['total_docs_processed']}")
        print(f"Total time: {self.metrics['total_time']:.3f}s")
        print(f"Average time per rerank: {self.metrics['avg_time']:.3f}s")
        if self.metrics['total_reranks'] > 0:
            avg_docs = self.metrics['total_docs_processed'] / self.metrics['total_reranks']
            print(f"Average documents per rerank: {avg_docs:.1f}")
        print(f"{'='*60}\n")


def create_cross_encoder_reranker(
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    device: Optional[str] = None,
    batch_size: int = 16
) -> CrossEncoderReranker:
    """
    Factory function to create Cross-Encoder Reranker.
    
    Args:
        model_name: HuggingFace model name
        device: 'cuda', 'cpu', or None (auto-detect)
        batch_size: Batch size for inference
    
    Returns:
        CrossEncoderReranker instance
    """
    return CrossEncoderReranker(
        model_name=model_name,
        device=device,
        batch_size=batch_size
    )


# Test code
if __name__ == "__main__":
    print("="*60)
    print("TESTING CROSS-ENCODER RERANKER")
    print("="*60)
    
    # Sample documents
    docs = [
        Document(
            page_content="Data mining is the process of discovering patterns in large datasets.",
            metadata={'source': 'test.pdf', 'page': 1}
        ),
        Document(
            page_content="Machine learning algorithms can be supervised or unsupervised.",
            metadata={'source': 'test.pdf', 'page': 2}
        ),
        Document(
            page_content="Classification is a supervised learning task that predicts categories.",
            metadata={'source': 'test.pdf', 'page': 3}
        ),
        Document(
            page_content="The weather today is sunny and warm.",
            metadata={'source': 'test.pdf', 'page': 4}
        ),
        Document(
            page_content="Clustering groups similar data points together without labels.",
            metadata={'source': 'test.pdf', 'page': 5}
        )
    ]
    
    # Create reranker
    print("\n# Create reranker")
    reranker = create_cross_encoder_reranker()
    
    # Test query
    query = "What is data mining?"
    
    # Rerank
    print(f"\n# Rerank documents for query: '{query}'")
    results = reranker.rerank(
        query=query,
        documents=docs,
        top_k=3,
        threshold=0.0,
        debug=True
    )
    
    # Print metrics
    reranker.print_metrics()
    
    # Test with details
    print("\n# Rerank with details")
    details = reranker.rerank_with_details(
        query=query,
        documents=docs,
        top_k=3,
        threshold=0.5
    )
    
    print(f"\n📊 Score Statistics:")
    for key, value in details['score_stats'].items():
        print(f"   {key}: {value:.4f}")
    
    print(f"\n📈 Metrics:")
    for key, value in details['metrics'].items():
        print(f"   {key}: {value}")
