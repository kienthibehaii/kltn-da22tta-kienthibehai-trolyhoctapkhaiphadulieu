# hybrid_rerank_pipeline.py - Integrated Hybrid Retrieval + Cross-Encoder Reranking
"""
Complete RAG Pipeline with Reranking

Pipeline Flow:
1. Query → Hybrid Retrieval (Vector + BM25 + RRF) → Top 20 docs
2. Top 20 docs → Cross-Encoder Rerank → Top 3 docs
3. Top 3 docs → LLM → Answer

Features:
- Hybrid retrieval (vector + BM25)
- Reciprocal Rank Fusion
- Cross-Encoder reranking
- Threshold filtering
- Performance metrics
- Debug visualization
"""

import time
from typing import List, Tuple, Dict, Optional
from langchain_core.documents import Document
from cross_encoder_reranker import CrossEncoderReranker


class HybridRerankPipeline:
    """
    Complete pipeline: Hybrid Retrieval → Cross-Encoder Reranking
    """
    
    def __init__(self,
                 hybrid_retriever,
                 reranker: Optional[CrossEncoderReranker] = None,
                 initial_k: int = 20,
                 final_k: int = 3,
                 rerank_threshold: float = 0.0,
                 enable_reranking: bool = True):
        """
        Initialize Hybrid Rerank Pipeline.
        
        Args:
            hybrid_retriever: HybridRetriever instance
            reranker: CrossEncoderReranker instance (None = create new)
            initial_k: Number of docs from hybrid retrieval
            final_k: Number of docs after reranking
            rerank_threshold: Minimum relevance score
            enable_reranking: Enable/disable reranking
        """
        self.hybrid_retriever = hybrid_retriever
        
        # Create reranker if not provided
        if reranker is None and enable_reranking:
            from cross_encoder_reranker import create_cross_encoder_reranker
            self.reranker = create_cross_encoder_reranker()
        else:
            self.reranker = reranker
        
        self.initial_k = initial_k
        self.final_k = final_k
        self.rerank_threshold = rerank_threshold
        self.enable_reranking = enable_reranking
        
        # Metrics
        self.metrics = {
            'total_queries': 0,
            'total_time': 0.0,
            'retrieval_time': 0.0,
            'rerank_time': 0.0,
            'avg_total_time': 0.0,
            'avg_retrieval_time': 0.0,
            'avg_rerank_time': 0.0
        }
        
        print(f"✅ Hybrid Rerank Pipeline initialized")
        print(f"   Initial K: {initial_k}")
        print(f"   Final K: {final_k}")
        print(f"   Reranking: {'Enabled' if enable_reranking else 'Disabled'}")
        print(f"   Threshold: {rerank_threshold}")
    
    def retrieve_and_rerank(self,
                           query: str,
                           debug: bool = False) -> List[Tuple[Document, float]]:
        """
        Complete pipeline: retrieve → rerank.
        
        Args:
            query: Search query
            debug: Enable debug logging
        
        Returns:
            List of (document, score) tuples
        """
        total_start = time.time()
        
        if debug:
            print(f"\n{'='*60}")
            print(f"🔍 HYBRID RERANK PIPELINE")
            print(f"{'='*60}")
            print(f"Query: {query}")
        
        # Step 1: Hybrid Retrieval
        if debug:
            print(f"\n📚 Step 1: Hybrid Retrieval (Top {self.initial_k})")
        
        retrieval_start = time.time()
        retrieved_docs = self.hybrid_retriever.invoke(query)
        
        # Limit to initial_k
        if len(retrieved_docs) > self.initial_k:
            retrieved_docs = retrieved_docs[:self.initial_k]
        
        retrieval_time = time.time() - retrieval_start
        
        if debug:
            print(f"   ✅ Retrieved {len(retrieved_docs)} documents")
            print(f"   ⏱️  Time: {retrieval_time:.3f}s")
        
        # Step 2: Cross-Encoder Reranking
        if self.enable_reranking and self.reranker is not None:
            if debug:
                print(f"\n🎯 Step 2: Cross-Encoder Reranking (Top {self.final_k})")
            
            rerank_start = time.time()
            reranked_docs = self.reranker.rerank(
                query=query,
                documents=retrieved_docs,
                top_k=self.final_k,
                threshold=self.rerank_threshold,
                return_scores=True,
                debug=debug
            )
            rerank_time = time.time() - rerank_start
            
            if debug:
                print(f"   ✅ Reranked to {len(reranked_docs)} documents")
                print(f"   ⏱️  Time: {rerank_time:.3f}s")
        else:
            # No reranking - just take top final_k
            reranked_docs = [(doc, 1.0) for doc in retrieved_docs[:self.final_k]]
            rerank_time = 0.0
            
            if debug:
                print(f"\n⚠️  Reranking disabled - using top {self.final_k} from retrieval")
        
        # Update metrics
        total_time = time.time() - total_start
        self._update_metrics(retrieval_time, rerank_time, total_time)
        
        if debug:
            print(f"\n⏱️  Total Time: {total_time:.3f}s")
            print(f"   - Retrieval: {retrieval_time:.3f}s ({retrieval_time/total_time*100:.1f}%)")
            print(f"   - Reranking: {rerank_time:.3f}s ({rerank_time/total_time*100:.1f}%)")
            print(f"{'='*60}\n")
        
        return reranked_docs
    
    def retrieve_with_details(self, query: str) -> Dict:
        """
        Retrieve with detailed metrics and analysis.
        
        Returns:
            Dict with documents, scores, metrics, and analysis
        """
        total_start = time.time()
        
        # Retrieval
        retrieval_start = time.time()
        retrieved_docs = self.hybrid_retriever.invoke(query)
        if len(retrieved_docs) > self.initial_k:
            retrieved_docs = retrieved_docs[:self.initial_k]
        retrieval_time = time.time() - retrieval_start
        
        # Reranking
        if self.enable_reranking and self.reranker is not None:
            rerank_start = time.time()
            rerank_details = self.reranker.rerank_with_details(
                query=query,
                documents=retrieved_docs,
                top_k=self.final_k,
                threshold=self.rerank_threshold
            )
            rerank_time = time.time() - rerank_start
            
            final_docs = rerank_details['reranked_docs']
            score_stats = rerank_details['score_stats']
        else:
            final_docs = [(doc, 1.0) for doc in retrieved_docs[:self.final_k]]
            rerank_time = 0.0
            score_stats = {}
        
        total_time = time.time() - total_start
        
        return {
            'query': query,
            'retrieved_docs': retrieved_docs,
            'final_docs': final_docs,
            'score_stats': score_stats,
            'metrics': {
                'num_retrieved': len(retrieved_docs),
                'num_final': len(final_docs),
                'retrieval_time': retrieval_time,
                'rerank_time': rerank_time,
                'total_time': total_time,
                'reranking_enabled': self.enable_reranking
            }
        }
    
    def compare_with_without_reranking(self, query: str) -> Dict:
        """
        Compare results with and without reranking.
        
        Returns:
            Dict with comparison data
        """
        print(f"\n{'='*60}")
        print(f"📊 COMPARING WITH/WITHOUT RERANKING")
        print(f"{'='*60}")
        print(f"Query: {query}\n")
        
        # Get retrieved docs
        retrieved_docs = self.hybrid_retriever.invoke(query)
        if len(retrieved_docs) > self.initial_k:
            retrieved_docs = retrieved_docs[:self.initial_k]
        
        # Without reranking
        print(f"📚 Without Reranking (Top {self.final_k} from retrieval):")
        without_rerank = retrieved_docs[:self.final_k]
        for i, doc in enumerate(without_rerank, 1):
            print(f"   {i}. {doc.page_content[:80]}...")
        
        # With reranking
        if self.enable_reranking and self.reranker is not None:
            print(f"\n🎯 With Cross-Encoder Reranking (Top {self.final_k}):")
            with_rerank = self.reranker.rerank(
                query=query,
                documents=retrieved_docs,
                top_k=self.final_k,
                threshold=self.rerank_threshold,
                return_scores=True,
                debug=False
            )
            
            for i, (doc, score) in enumerate(with_rerank, 1):
                print(f"   {i}. Score: {score:.4f} - {doc.page_content[:80]}...")
            
            # Calculate overlap
            without_ids = [id(doc) for doc in without_rerank]
            with_ids = [id(doc) for doc, _ in with_rerank]
            overlap = len(set(without_ids) & set(with_ids))
            overlap_pct = (overlap / self.final_k) * 100
            
            print(f"\n📈 Overlap: {overlap}/{self.final_k} ({overlap_pct:.1f}%)")
            print(f"   Changed: {self.final_k - overlap} documents")
        else:
            print(f"\n⚠️  Reranking disabled")
            with_rerank = [(doc, 1.0) for doc in without_rerank]
            overlap = self.final_k
            overlap_pct = 100.0
        
        print(f"{'='*60}\n")
        
        return {
            'query': query,
            'without_rerank': without_rerank,
            'with_rerank': with_rerank,
            'overlap': overlap,
            'overlap_percentage': overlap_pct,
            'changed': self.final_k - overlap
        }
    
    def _update_metrics(self, retrieval_time: float, rerank_time: float, total_time: float):
        """Update internal metrics"""
        self.metrics['total_queries'] += 1
        self.metrics['retrieval_time'] += retrieval_time
        self.metrics['rerank_time'] += rerank_time
        self.metrics['total_time'] += total_time
        
        n = self.metrics['total_queries']
        self.metrics['avg_retrieval_time'] = self.metrics['retrieval_time'] / n
        self.metrics['avg_rerank_time'] = self.metrics['rerank_time'] / n
        self.metrics['avg_total_time'] = self.metrics['total_time'] / n
    
    def get_metrics(self) -> Dict:
        """Get performance metrics"""
        return self.metrics.copy()
    
    def print_metrics(self):
        """Print performance metrics"""
        print(f"\n{'='*60}")
        print(f"📊 HYBRID RERANK PIPELINE METRICS")
        print(f"{'='*60}")
        print(f"Total queries: {self.metrics['total_queries']}")
        print(f"Total time: {self.metrics['total_time']:.3f}s")
        print(f"  - Retrieval: {self.metrics['retrieval_time']:.3f}s")
        print(f"  - Reranking: {self.metrics['rerank_time']:.3f}s")
        print(f"\nAverage per query:")
        print(f"  - Total: {self.metrics['avg_total_time']:.3f}s")
        print(f"  - Retrieval: {self.metrics['avg_retrieval_time']:.3f}s")
        print(f"  - Reranking: {self.metrics['avg_rerank_time']:.3f}s")
        
        if self.metrics['avg_total_time'] > 0:
            retrieval_pct = (self.metrics['avg_retrieval_time'] / self.metrics['avg_total_time']) * 100
            rerank_pct = (self.metrics['avg_rerank_time'] / self.metrics['avg_total_time']) * 100
            print(f"\nTime breakdown:")
            print(f"  - Retrieval: {retrieval_pct:.1f}%")
            print(f"  - Reranking: {rerank_pct:.1f}%")
        
        print(f"{'='*60}\n")
    
    def reset_metrics(self):
        """Reset performance metrics"""
        self.metrics = {
            'total_queries': 0,
            'total_time': 0.0,
            'retrieval_time': 0.0,
            'rerank_time': 0.0,
            'avg_total_time': 0.0,
            'avg_retrieval_time': 0.0,
            'avg_rerank_time': 0.0
        }


def create_hybrid_rerank_pipeline(
    hybrid_retriever,
    reranker: Optional[CrossEncoderReranker] = None,
    initial_k: int = 20,
    final_k: int = 3,
    rerank_threshold: float = 0.0,
    enable_reranking: bool = True
) -> HybridRerankPipeline:
    """
    Factory function to create Hybrid Rerank Pipeline.
    
    Args:
        hybrid_retriever: HybridRetriever instance
        reranker: CrossEncoderReranker instance (None = create new)
        initial_k: Number of docs from hybrid retrieval
        final_k: Number of docs after reranking
        rerank_threshold: Minimum relevance score
        enable_reranking: Enable/disable reranking
    
    Returns:
        HybridRerankPipeline instance
    """
    return HybridRerankPipeline(
        hybrid_retriever=hybrid_retriever,
        reranker=reranker,
        initial_k=initial_k,
        final_k=final_k,
        rerank_threshold=rerank_threshold,
        enable_reranking=enable_reranking
    )
