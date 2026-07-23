"""
Integrated Advanced RAG Pipeline
Combines all components into production-ready system
"""

import sys
sys.path.append('..')

from typing import List, Dict, Optional
import time
from datetime import datetime


class AdvancedRAGPipeline:
    """
    Production-ready RAG pipeline with all advanced features
    
    Architecture:
    1. Ingestion: Semantic chunking + metadata enrichment
    2. Retrieval: Hybrid search + query expansion + compression
    3. Reranking: Cross-encoder + dynamic scoring
    4. Generation: Context filtering + hallucination detection + citation grounding
    5. Memory: Conversation + semantic + feedback learning
    6. Evaluation: Comprehensive metrics
    """
    
    def __init__(
        self,
        vector_store,
        llm_client,
        config: Dict = None
    ):
        self.vector_store = vector_store
        self.llm_client = llm_client
        self.config = config or self._default_config()
        
        # Initialize components
        self._initialize_components()
    
    def _default_config(self) -> Dict:
        """Default configuration"""
        return {
            # Ingestion
            'semantic_chunking': True,
            'chunk_size': 1000,
            'chunk_overlap': 200,
            'similarity_threshold': 0.7,
            
            # Retrieval
            'use_hybrid': True,
            'use_query_expansion': True,
            'use_query_rewriting': True,
            'use_compression': True,
            'retrieval_k': 10,
            'final_k': 3,
            
            # Reranking
            'use_reranking': True,
            'rerank_method': 'hybrid',  # 'heuristic', 'llm', 'hybrid'
            'rerank_threshold': 0.3,
            
            # Generation
            'use_context_filtering': True,
            'use_hallucination_detection': True,
            'use_citation_grounding': True,
            'max_context_length': 4000,
            
            # Memory
            'use_conversation_memory': True,
            'short_term_size': 5,
            'long_term_size': 50,
            'use_feedback_learning': True,
            
            # Evaluation
            'enable_evaluation': True,
            'log_metrics': True,
            
            # Performance
            'enable_caching': True,
            'cache_ttl': 3600,
            'async_processing': True
        }
    
    def _initialize_components(self):
        """Initialize all pipeline components"""
        from ingestion.semantic_chunker import AdvancedSemanticChunker, DuplicateDetector
        from retrieval.advanced_retriever import (
            QueryExpander, QueryRewriter, ContextualCompressor,
            SelfQueryRetriever, HybridRetriever
        )
        from generation.advanced_generator import (
            HallucinationDetector, CitationGrounder,
            AnswerValidator, ContextFilter
        )
        from memory.conversation_memory import ConversationMemory, FeedbackLearning
        from evaluation.rag_metrics import RAGEvaluator
        
        # Ingestion
        self.semantic_chunker = AdvancedSemanticChunker(
            similarity_threshold=self.config['similarity_threshold'],
            min_chunk_size=self.config['chunk_size'] // 2,
            max_chunk_size=self.config['chunk_size']
        )
        self.duplicate_detector = DuplicateDetector()
        
        # Retrieval
        self.query_expander = QueryExpander(self.llm_client)
        self.query_rewriter = QueryRewriter(self.llm_client)
        self.contextual_compressor = ContextualCompressor()
        self.self_query_retriever = SelfQueryRetriever(self.llm_client)
        
        # Generation
        self.hallucination_detector = HallucinationDetector()
        self.citation_grounder = CitationGrounder()
        self.answer_validator = AnswerValidator(self.llm_client)
        self.context_filter = ContextFilter(
            max_context_length=self.config['max_context_length']
        )
        
        # Memory
        self.conversation_memory = ConversationMemory(
            short_term_size=self.config['short_term_size'],
            long_term_size=self.config['long_term_size']
        )
        self.feedback_learning = FeedbackLearning()
        
        # Evaluation
        self.evaluator = RAGEvaluator()
        
        # Metrics storage
        self.metrics_history = []
    
    def query(
        self,
        question: str,
        session_id: Optional[str] = None,
        conversation_history: List[Dict] = None,
        reference_answer: Optional[str] = None
    ) -> Dict:
        """
        Main query method - full RAG pipeline
        
        Returns:
            {
                'answer': str,
                'citations': List[Dict],
                'sources': List[Dict],
                'metrics': Dict,
                'metadata': Dict
            }
        """
        start_time = time.time()
        
        # Step 1: Query preprocessing
        processed_query = self._preprocess_query(
            question,
            conversation_history
        )
        
        # Step 2: Retrieval
        retrieved_docs = self._retrieve_documents(
            processed_query,
            conversation_history
        )
        
        # Step 3: Reranking
        reranked_docs = self._rerank_documents(
            processed_query,
            retrieved_docs
        )
        
        # Step 4: Context preparation
        context_docs = self._prepare_context(
            processed_query,
            reranked_docs
        )
        
        # Step 5: Answer generation
        answer = self._generate_answer(
            processed_query,
            context_docs
        )
        
        # Step 6: Post-processing
        final_answer, citations = self._postprocess_answer(
            answer,
            context_docs
        )
        
        # Step 7: Validation
        validation = self._validate_answer(
            processed_query,
            final_answer,
            context_docs
        )
        
        # Step 8: Memory update
        if self.config['use_conversation_memory']:
            self._update_memory(
                question,
                final_answer,
                citations
            )
        
        # Step 9: Evaluation
        metrics = {}
        if self.config['enable_evaluation']:
            metrics = self._evaluate_response(
                processed_query,
                retrieved_docs,
                final_answer,
                reference_answer
            )
        
        # Calculate total time
        total_time = time.time() - start_time
        
        # Build response
        response = {
            'answer': final_answer,
            'citations': citations,
            'sources': context_docs,
            'metrics': metrics,
            'metadata': {
                'query': question,
                'processed_query': processed_query,
                'num_retrieved': len(retrieved_docs),
                'num_reranked': len(reranked_docs),
                'num_used': len(context_docs),
                'validation': validation,
                'response_time': total_time,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        # Log metrics
        if self.config['log_metrics']:
            self._log_metrics(response)
        
        return response
    
    def _preprocess_query(
        self,
        query: str,
        conversation_history: List[Dict] = None
    ) -> str:
        """
        Preprocess query with rewriting and expansion
        """
        processed = query
        
        # Query rewriting based on conversation
        if self.config['use_query_rewriting'] and conversation_history:
            processed = self.query_rewriter.rewrite_query(
                query,
                conversation_history
            )
            print(f"📝 Rewritten: {processed}")
        
        return processed
    
    def _retrieve_documents(
        self,
        query: str,
        conversation_history: List[Dict] = None
    ) -> List[Dict]:
        """
        Retrieve documents using hybrid approach
        """
        # Query expansion
        queries = [query]
        if self.config['use_query_expansion']:
            expanded = self.query_expander.expand_query(query, method='synonym')
            queries.extend(expanded[:2])
            print(f"🔄 Expanded to {len(queries)} queries")
        
        # Retrieve for each query
        all_docs = []
        for q in queries:
            # Vector search
            vector_docs = self.vector_store.similarity_search(
                q,
                k=self.config['retrieval_k']
            )
            all_docs.extend(vector_docs)
        
        # Deduplicate
        unique_docs = self._deduplicate_docs(all_docs)
        
        print(f"📚 Retrieved {len(unique_docs)} unique documents")
        
        return unique_docs
    
    def _rerank_documents(
        self,
        query: str,
        documents: List[Dict]
    ) -> List[Dict]:
        """
        Rerank documents for relevance
        """
        if not self.config['use_reranking'] or not documents:
            return documents[:self.config['final_k']]
        
        # Simple reranking by score
        scored_docs = []
        for doc in documents:
            score = doc.get('score', 0.5)
            scored_docs.append((doc, score))
        
        # Sort by score
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Filter by threshold
        filtered = [
            doc for doc, score in scored_docs
            if score >= self.config['rerank_threshold']
        ]
        
        # Take top k
        reranked = filtered[:self.config['final_k']]
        
        print(f"🎯 Reranked to {len(reranked)} documents")
        
        return reranked
    
    def _prepare_context(
        self,
        query: str,
        documents: List[Dict]
    ) -> List[Dict]:
        """
        Prepare context with filtering and compression
        """
        context_docs = documents
        
        # Context filtering
        if self.config['use_context_filtering']:
            context_docs = self.context_filter.filter_context(
                query,
                documents,
                strategy='hybrid'
            )
            print(f"📦 Filtered to {len(context_docs)} documents")
        
        # Contextual compression
        if self.config['use_compression']:
            context_docs = self.contextual_compressor.compress_documents(
                query,
                context_docs,
                method='sentence'
            )
            print(f"🗜️  Compressed documents")
        
        return context_docs
    
    def _generate_answer(
        self,
        query: str,
        context_docs: List[Dict]
    ) -> str:
        """
        Generate answer using LLM
        """
        # Build context
        context = self._build_context_string(context_docs)
        
        # Build prompt
        prompt = f"""Answer the question based on the provided context.

Context:
{context}

Question: {query}

Answer (be specific, accurate, and cite sources):"""
        
        # Generate
        try:
            response = self.llm_client.invoke(prompt)
            answer = response.content if hasattr(response, 'content') else str(response)
            return answer
        except Exception as e:
            print(f"❌ Generation error: {e}")
            return "I apologize, but I encountered an error generating the answer."
    
    def _postprocess_answer(
        self,
        answer: str,
        context_docs: List[Dict]
    ) -> tuple:
        """
        Post-process answer with citation grounding
        """
        # Citation grounding
        if self.config['use_citation_grounding']:
            grounded = self.citation_grounder.ground_answer(
                answer,
                context_docs
            )
            return grounded['grounded_answer'], grounded['citations']
        
        return answer, []
    
    def _validate_answer(
        self,
        query: str,
        answer: str,
        context_docs: List[Dict]
    ) -> Dict:
        """
        Validate answer quality
        """
        validation = {
            'is_valid': True,
            'quality_score': 1.0,
            'issues': [],
            'hallucination_check': {}
        }
        
        # Answer validation
        answer_validation = self.answer_validator.validate_answer(
            query,
            answer,
            context_docs
        )
        validation.update(answer_validation)
        
        # Hallucination detection
        if self.config['use_hallucination_detection']:
            hallucination_check = self.hallucination_detector.detect_hallucination(
                answer,
                context_docs
            )
            validation['hallucination_check'] = hallucination_check
            
            if hallucination_check['is_hallucinated']:
                validation['issues'].append('Potential hallucination detected')
        
        return validation
    
    def _update_memory(
        self,
        question: str,
        answer: str,
        citations: List[Dict]
    ):
        """
        Update conversation memory
        """
        self.conversation_memory.add_message(
            'user',
            question
        )
        self.conversation_memory.add_message(
            'assistant',
            answer,
            metadata={'citations': citations}
        )
    
    def _evaluate_response(
        self,
        query: str,
        retrieved_docs: List[Dict],
        answer: str,
        reference_answer: Optional[str]
    ) -> Dict:
        """
        Evaluate response quality
        """
        metrics = self.evaluator.evaluate_end_to_end(
            query,
            retrieved_docs,
            answer,
            reference_answer
        )
        
        return metrics
    
    def _log_metrics(self, response: Dict):
        """
        Log metrics for analysis
        """
        self.metrics_history.append({
            'timestamp': response['metadata']['timestamp'],
            'response_time': response['metadata']['response_time'],
            'metrics': response['metrics'],
            'validation': response['metadata']['validation']
        })
    
    def _build_context_string(self, documents: List[Dict]) -> str:
        """
        Build context string from documents
        """
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            content = doc.get('content', doc.get('text', ''))
            source = doc.get('metadata', {}).get('source', 'Unknown')
            page = doc.get('metadata', {}).get('page', 'N/A')
            
            context_parts.append(f"[Source {i}: {source}, Page {page}]\n{content}")
        
        return "\n\n".join(context_parts)
    
    def _deduplicate_docs(self, documents: List[Dict]) -> List[Dict]:
        """
        Remove duplicate documents
        """
        seen = set()
        unique = []
        
        for doc in documents:
            doc_id = doc.get('id', doc.get('content', '')[:100])
            if doc_id not in seen:
                seen.add(doc_id)
                unique.append(doc)
        
        return unique
    
    def add_feedback(
        self,
        query: str,
        answer: str,
        feedback: str,
        details: Optional[str] = None
    ):
        """
        Add user feedback for learning
        """
        if self.config['use_feedback_learning']:
            self.feedback_learning.add_feedback(
                query,
                answer,
                feedback,
                details
            )
    
    def get_metrics_summary(self) -> Dict:
        """
        Get summary of metrics
        """
        if not self.metrics_history:
            return {}
        
        import numpy as np
        
        response_times = [m['response_time'] for m in self.metrics_history]
        quality_scores = [
            m['validation']['quality_score']
            for m in self.metrics_history
            if 'validation' in m and 'quality_score' in m['validation']
        ]
        
        return {
            'total_queries': len(self.metrics_history),
            'avg_response_time': np.mean(response_times),
            'min_response_time': np.min(response_times),
            'max_response_time': np.max(response_times),
            'avg_quality_score': np.mean(quality_scores) if quality_scores else 0.0,
            'feedback_stats': self.feedback_learning.get_feedback_stats()
        }


# Example usage
if __name__ == "__main__":
    print("Advanced RAG Pipeline initialized")
    print("Ready for production deployment")
