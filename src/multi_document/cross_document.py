# multi_document/cross_document.py - Cross-Document Retrieval
"""
Cross-Document Retriever for Multi-Document RAG System

Features:
- Retrieve across multiple documents
- Compare content between documents
- Aggregate results
- Group citations by document
- Synthesize information from multiple sources
"""

from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class RetrievalResult:
    """Single retrieval result"""
    document_id: str
    filename: str
    content: str
    metadata: Dict
    score: float
    page: Optional[int] = None
    slide: Optional[int] = None


@dataclass
class AggregatedResult:
    """Aggregated result from multiple documents"""
    query: str
    results: List[RetrievalResult]
    grouped_by_document: Dict[str, List[RetrievalResult]]
    total_documents: int
    total_results: int
    synthesis: Optional[str] = None


@dataclass
class ComparisonResult:
    """Comparison result between documents"""
    query: str
    document_results: Dict[str, Dict[str, Any]]
    similarities: List[str]
    differences: List[str]
    summary: str


class CrossDocumentRetriever:
    """
    Retrieves and compares information across multiple documents
    """
    
    def __init__(self, retriever, document_manager):
        """
        Initialize cross-document retriever
        
        Args:
            retriever: Base retriever (HybridRetriever or similar)
            document_manager: Document manager instance
        """
        self.retriever = retriever
        self.doc_manager = document_manager
    
    def retrieve_across_documents(
        self,
        query: str,
        document_ids: List[str],
        k: int = 3
    ) -> AggregatedResult:
        """
        Retrieve relevant content across multiple documents
        
        Args:
            query: Search query
            document_ids: List of document IDs to search
            k: Number of results per document
            
        Returns:
            AggregatedResult object
        """
        all_results = []
        
        # Retrieve from each document
        for doc_id in document_ids:
            # Get document info
            doc_info = self.doc_manager.get_document(doc_id)
            if not doc_info:
                continue
            
            # Get vector collection for this document
            collection_name = doc_info.get('vector_collection')
            
            # Retrieve from this document's collection
            # Note: This requires filtering by document_id in metadata
            try:
                docs = self.retriever.get_relevant_documents(query)
                
                # Filter by document
                doc_results = []
                for doc in docs[:k]:
                    # Check if this result belongs to current document
                    doc_source = doc.metadata.get('source', '')
                    doc_filename = doc_info.get('filename', '')
                    
                    if doc_filename in doc_source or doc_source in doc_info.get('file_path', ''):
                        result = RetrievalResult(
                            document_id=doc_id,
                            filename=doc_info['filename'],
                            content=doc.page_content,
                            metadata=doc.metadata,
                            score=doc.metadata.get('relevance_score', 0.0),
                            page=doc.metadata.get('page'),
                            slide=doc.metadata.get('slide')
                        )
                        doc_results.append(result)
                
                all_results.extend(doc_results)
                
            except Exception as e:
                print(f"⚠️  Error retrieving from {doc_id}: {e}")
                continue
        
        # Group by document
        grouped = defaultdict(list)
        for result in all_results:
            grouped[result.document_id].append(result)
        
        return AggregatedResult(
            query=query,
            results=all_results,
            grouped_by_document=dict(grouped),
            total_documents=len(grouped),
            total_results=len(all_results)
        )
    
    def compare_documents(
        self,
        query: str,
        document_ids: List[str],
        k: int = 3
    ) -> ComparisonResult:
        """
        Compare content across documents for a query
        
        Args:
            query: Comparison query
            document_ids: List of document IDs to compare
            k: Number of results per document
            
        Returns:
            ComparisonResult object
        """
        # Retrieve from each document
        aggregated = self.retrieve_across_documents(query, document_ids, k)
        
        # Organize results by document
        document_results = {}
        for doc_id, results in aggregated.grouped_by_document.items():
            # Get best result for this document
            best_result = max(results, key=lambda r: r.score) if results else None
            
            if best_result:
                document_results[doc_id] = {
                    'filename': best_result.filename,
                    'content': best_result.content,
                    'score': best_result.score,
                    'metadata': best_result.metadata,
                    'all_results': results
                }
        
        # Analyze similarities and differences
        similarities, differences = self._analyze_comparison(document_results)
        
        # Generate summary
        summary = self._generate_comparison_summary(query, document_results, similarities, differences)
        
        return ComparisonResult(
            query=query,
            document_results=document_results,
            similarities=similarities,
            differences=differences,
            summary=summary
        )
    
    def _analyze_comparison(
        self,
        document_results: Dict[str, Dict]
    ) -> Tuple[List[str], List[str]]:
        """
        Analyze similarities and differences between documents
        
        Args:
            document_results: Results by document
            
        Returns:
            Tuple of (similarities, differences)
        """
        similarities = []
        differences = []
        
        if len(document_results) < 2:
            return similarities, differences
        
        # Extract key terms from each document
        doc_terms = {}
        for doc_id, result in document_results.items():
            content = result['content'].lower()
            # Simple term extraction (can be improved with NLP)
            terms = set(word.strip() for word in content.split() if len(word.strip()) > 4)
            doc_terms[doc_id] = terms
        
        # Find common terms (similarities)
        if len(doc_terms) >= 2:
            doc_ids = list(doc_terms.keys())
            common_terms = doc_terms[doc_ids[0]]
            for doc_id in doc_ids[1:]:
                common_terms = common_terms.intersection(doc_terms[doc_id])
            
            if common_terms:
                similarities.append(f"Common concepts: {', '.join(list(common_terms)[:5])}")
        
        # Find unique terms (differences)
        for doc_id, terms in doc_terms.items():
            other_terms = set()
            for other_id, other_doc_terms in doc_terms.items():
                if other_id != doc_id:
                    other_terms.update(other_doc_terms)
            
            unique_terms = terms - other_terms
            if unique_terms:
                filename = document_results[doc_id]['filename']
                differences.append(f"{filename}: {', '.join(list(unique_terms)[:3])}")
        
        return similarities, differences
    
    def _generate_comparison_summary(
        self,
        query: str,
        document_results: Dict[str, Dict],
        similarities: List[str],
        differences: List[str]
    ) -> str:
        """Generate comparison summary"""
        summary_parts = []
        
        summary_parts.append(f"Comparison for: '{query}'")
        summary_parts.append(f"Compared {len(document_results)} documents")
        
        if similarities:
            summary_parts.append("\nSimilarities:")
            for sim in similarities:
                summary_parts.append(f"  - {sim}")
        
        if differences:
            summary_parts.append("\nDifferences:")
            for diff in differences:
                summary_parts.append(f"  - {diff}")
        
        return "\n".join(summary_parts)
    
    def aggregate_results(
        self,
        results: List[RetrievalResult],
        strategy: str = 'top_k',
        k: int = 5
    ) -> List[RetrievalResult]:
        """
        Aggregate results using different strategies
        
        Args:
            results: List of retrieval results
            strategy: Aggregation strategy (top_k, diverse, balanced)
            k: Number of results to return
            
        Returns:
            Aggregated results
        """
        if strategy == 'top_k':
            # Simply take top K by score
            sorted_results = sorted(results, key=lambda r: r.score, reverse=True)
            return sorted_results[:k]
        
        elif strategy == 'diverse':
            # Ensure diversity across documents
            selected = []
            used_docs = set()
            
            # Sort by score
            sorted_results = sorted(results, key=lambda r: r.score, reverse=True)
            
            # Select one from each document first
            for result in sorted_results:
                if result.document_id not in used_docs:
                    selected.append(result)
                    used_docs.add(result.document_id)
                    if len(selected) >= k:
                        break
            
            # Fill remaining slots with highest scores
            if len(selected) < k:
                for result in sorted_results:
                    if result not in selected:
                        selected.append(result)
                        if len(selected) >= k:
                            break
            
            return selected
        
        elif strategy == 'balanced':
            # Balance between documents
            grouped = defaultdict(list)
            for result in results:
                grouped[result.document_id].append(result)
            
            # Sort each group by score
            for doc_id in grouped:
                grouped[doc_id].sort(key=lambda r: r.score, reverse=True)
            
            # Round-robin selection
            selected = []
            doc_ids = list(grouped.keys())
            idx = 0
            
            while len(selected) < k and any(grouped.values()):
                doc_id = doc_ids[idx % len(doc_ids)]
                if grouped[doc_id]:
                    selected.append(grouped[doc_id].pop(0))
                idx += 1
            
            return selected
        
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    
    def group_citations_by_document(
        self,
        results: List[RetrievalResult]
    ) -> Dict[str, List[Dict]]:
        """
        Group citations by document
        
        Args:
            results: List of retrieval results
            
        Returns:
            Dict mapping document_id to list of citations
        """
        grouped = defaultdict(list)
        
        for result in results:
            citation = {
                'filename': result.filename,
                'content': result.content,
                'score': result.score,
                'page': result.page,
                'slide': result.slide,
                'metadata': result.metadata
            }
            grouped[result.document_id].append(citation)
        
        return dict(grouped)
    
    def synthesize_information(
        self,
        query: str,
        results: List[RetrievalResult],
        llm_chain
    ) -> str:
        """
        Synthesize information from multiple sources
        
        Args:
            query: Original query
            results: Retrieval results
            llm_chain: LLM chain for synthesis
            
        Returns:
            Synthesized answer
        """
        # Group by document
        grouped = self.group_citations_by_document(results)
        
        # Build context from multiple sources
        context_parts = []
        for doc_id, citations in grouped.items():
            doc_name = citations[0]['filename']
            context_parts.append(f"\n=== From {doc_name} ===")
            for i, citation in enumerate(citations, 1):
                context_parts.append(f"\n[{i}] {citation['content']}")
        
        context = "\n".join(context_parts)
        
        # Create synthesis prompt
        synthesis_prompt = f"""Based on information from multiple documents, answer the following question.
Synthesize the information and provide a comprehensive answer.

Question: {query}

Context from multiple sources:
{context}

Provide a synthesized answer that:
1. Combines information from all sources
2. Removes redundancy
3. Highlights key points
4. Cites sources using [Document Name]

Answer:"""
        
        # Generate synthesis
        try:
            response = llm_chain.invoke({"question": synthesis_prompt})
            if isinstance(response, dict):
                return response.get('answer', response.get('result', str(response)))
            return str(response)
        except Exception as e:
            print(f"⚠️  Synthesis error: {e}")
            # Fallback: concatenate results
            return "\n\n".join([r.content for r in results[:3]])


# Convenience functions
def create_cross_document_retriever(retriever, document_manager) -> CrossDocumentRetriever:
    """Create cross-document retriever instance"""
    return CrossDocumentRetriever(retriever, document_manager)


if __name__ == "__main__":
    print("✅ Cross-Document Retriever module loaded")
