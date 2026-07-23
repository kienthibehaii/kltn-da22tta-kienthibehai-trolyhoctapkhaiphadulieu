# multi_document/document_router.py - Intelligent Document Routing
"""
Document Router for Multi-Document RAG System

Features:
- Query analysis
- Document selection based on relevance
- Routing strategies
- Intelligent document filtering
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from .document_manager import MultiDocumentManager
from .metadata_retriever import MetadataRetriever


@dataclass
class QueryIntent:
    """Query intent analysis result"""
    query: str
    keywords: List[str]
    subject_hints: List[str]
    chapter_hints: List[str]
    file_type_hints: List[str]
    is_comparison: bool
    is_multi_doc: bool


class DocumentRouter:
    """
    Routes queries to relevant documents
    """
    
    # Keywords for different subjects
    SUBJECT_KEYWORDS = {
        'Data Mining': ['data mining', 'khai phá dữ liệu', 'mining', 'kdd'],
        'Clustering': ['clustering', 'phân cụm', 'cluster', 'k-means', 'dbscan', 'hierarchical'],
        'Classification': ['classification', 'phân loại', 'classifier', 'decision tree', 'naive bayes', 'svm'],
        'Association Rules': ['association', 'kết hợp', 'apriori', 'fp-growth', 'frequent itemset'],
        'Preprocessing': ['preprocessing', 'tiền xử lý', 'cleaning', 'normalization', 'transformation']
    }
    
    # Keywords for file types
    FILE_TYPE_KEYWORDS = {
        'pdf': ['pdf', 'textbook', 'book', 'giáo trình'],
        'pptx': ['slide', 'presentation', 'bài giảng'],
        'docx': ['document', 'word', 'tài liệu'],
        'txt': ['note', 'ghi chú', 'text'],
        'csv': ['data', 'table', 'bảng']
    }
    
    # Comparison keywords
    COMPARISON_KEYWORDS = ['so sánh', 'compare', 'khác nhau', 'difference', 'giống nhau', 'similarity', 'vs', 'versus']
    
    def __init__(
        self,
        document_manager: MultiDocumentManager,
        metadata_retriever: MetadataRetriever
    ):
        """
        Initialize document router
        
        Args:
            document_manager: Document manager instance
            metadata_retriever: Metadata retriever instance
        """
        self.doc_manager = document_manager
        self.metadata_retriever = metadata_retriever
    
    def analyze_query(self, query: str) -> QueryIntent:
        """
        Analyze query to extract intent
        
        Args:
            query: User query
            
        Returns:
            QueryIntent object
        """
        query_lower = query.lower()
        
        # Extract keywords (simple tokenization)
        keywords = [word.strip() for word in query_lower.split() if len(word.strip()) > 2]
        
        # Detect subject hints
        subject_hints = []
        for subject, subject_keywords in self.SUBJECT_KEYWORDS.items():
            if any(kw in query_lower for kw in subject_keywords):
                subject_hints.append(subject)
        
        # Detect chapter hints
        chapter_hints = []
        if 'chapter' in query_lower or 'chương' in query_lower:
            # Extract chapter numbers
            import re
            chapter_matches = re.findall(r'chapter\s+(\d+)|chương\s+(\d+)', query_lower)
            for match in chapter_matches:
                chapter_num = match[0] or match[1]
                chapter_hints.append(f"Chapter {chapter_num}")
        
        # Detect file type hints
        file_type_hints = []
        for file_type, type_keywords in self.FILE_TYPE_KEYWORDS.items():
            if any(kw in query_lower for kw in type_keywords):
                file_type_hints.append(file_type)
        
        # Detect comparison intent
        is_comparison = any(kw in query_lower for kw in self.COMPARISON_KEYWORDS)
        
        # Detect multi-document intent
        is_multi_doc = is_comparison or len(file_type_hints) > 1 or len(subject_hints) > 1
        
        return QueryIntent(
            query=query,
            keywords=keywords,
            subject_hints=subject_hints,
            chapter_hints=chapter_hints,
            file_type_hints=file_type_hints,
            is_comparison=is_comparison,
            is_multi_doc=is_multi_doc
        )
    
    def select_documents(
        self,
        query: str,
        strategy: str = 'hybrid',
        max_documents: Optional[int] = None
    ) -> List[str]:
        """
        Select relevant documents for query
        
        Args:
            query: User query
            strategy: Selection strategy (all, metadata, relevance, hybrid)
            max_documents: Maximum number of documents to select
            
        Returns:
            List of document IDs
        """
        # Analyze query
        intent = self.analyze_query(query)
        
        if strategy == 'all':
            # Select all documents
            return self._select_all_documents(max_documents)
        
        elif strategy == 'metadata':
            # Select based on metadata only
            return self._select_by_metadata(intent, max_documents)
        
        elif strategy == 'relevance':
            # Select based on relevance scoring
            return self._select_by_relevance(intent, max_documents)
        
        elif strategy == 'hybrid':
            # Combine metadata and relevance
            return self._select_hybrid(intent, max_documents)
        
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    
    def _select_all_documents(self, max_documents: Optional[int]) -> List[str]:
        """Select all documents"""
        docs = self.doc_manager.list_documents(
            filters={'status': 'processed'},
            limit=max_documents
        )
        return [doc['document_id'] for doc in docs]
    
    def _select_by_metadata(
        self,
        intent: QueryIntent,
        max_documents: Optional[int]
    ) -> List[str]:
        """Select documents based on metadata"""
        filters = {}
        
        # Add subject filter
        if intent.subject_hints:
            filters['subject'] = intent.subject_hints[0]
        
        # Add chapter filter
        if intent.chapter_hints:
            filters['chapter'] = intent.chapter_hints[0]
        
        # Add file type filter
        if intent.file_type_hints:
            filters['file_type'] = intent.file_type_hints[0]
        
        # Get documents
        if filters:
            docs = self.metadata_retriever.filter_by_metadata(filters)
        else:
            docs = self.doc_manager.list_documents(filters={'status': 'processed'})
        
        # Limit results
        if max_documents:
            docs = docs[:max_documents]
        
        return [doc['document_id'] for doc in docs]
    
    def _select_by_relevance(
        self,
        intent: QueryIntent,
        max_documents: Optional[int]
    ) -> List[str]:
        """Select documents based on relevance scoring"""
        # Get all processed documents
        all_docs = self.doc_manager.list_documents(filters={'status': 'processed'})
        
        # Score each document
        scored_docs = []
        for doc in all_docs:
            score = self.score_relevance(intent, doc)
            scored_docs.append((doc['document_id'], score))
        
        # Sort by score
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Limit results
        if max_documents:
            scored_docs = scored_docs[:max_documents]
        
        return [doc_id for doc_id, score in scored_docs if score > 0]
    
    def _select_hybrid(
        self,
        intent: QueryIntent,
        max_documents: Optional[int]
    ) -> List[str]:
        """Select documents using hybrid approach"""
        # First, filter by metadata if hints exist
        if intent.subject_hints or intent.chapter_hints or intent.file_type_hints:
            candidate_ids = self._select_by_metadata(intent, max_documents=None)
            candidates = self.metadata_retriever.get_documents_by_ids(candidate_ids)
        else:
            candidates = self.doc_manager.list_documents(filters={'status': 'processed'})
        
        # Then, score remaining candidates
        scored_docs = []
        for doc in candidates:
            score = self.score_relevance(intent, doc)
            scored_docs.append((doc['document_id'], score))
        
        # Sort by score
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Limit results
        if max_documents:
            scored_docs = scored_docs[:max_documents]
        
        return [doc_id for doc_id, score in scored_docs]
    
    def score_relevance(self, intent: QueryIntent, document: Dict) -> float:
        """
        Score document relevance to query intent
        
        Args:
            intent: Query intent
            document: Document dict
            
        Returns:
            Relevance score (0-1)
        """
        score = 0.0
        
        # Subject match (weight: 0.4)
        if intent.subject_hints:
            doc_subject = document.get('metadata', {}).get('subject', '')
            if any(hint.lower() in doc_subject.lower() for hint in intent.subject_hints):
                score += 0.4
        
        # Chapter match (weight: 0.3)
        if intent.chapter_hints:
            doc_chapter = document.get('metadata', {}).get('chapter', '')
            if any(hint.lower() in doc_chapter.lower() for hint in intent.chapter_hints):
                score += 0.3
        
        # File type match (weight: 0.2)
        if intent.file_type_hints:
            doc_type = document.get('file_type', '')
            if doc_type in intent.file_type_hints:
                score += 0.2
        
        # Filename match (weight: 0.1)
        filename = document.get('filename', '').lower()
        keyword_matches = sum(1 for kw in intent.keywords if kw in filename)
        if keyword_matches > 0:
            score += 0.1 * min(keyword_matches / len(intent.keywords), 1.0)
        
        return min(score, 1.0)
    
    def route_query(
        self,
        query: str,
        strategy: str = 'hybrid',
        max_documents: Optional[int] = 5
    ) -> Tuple[List[str], QueryIntent]:
        """
        Route query to relevant documents
        
        Args:
            query: User query
            strategy: Selection strategy
            max_documents: Maximum documents to select
            
        Returns:
            Tuple of (document_ids, query_intent)
        """
        # Analyze query
        intent = self.analyze_query(query)
        
        # Select documents
        document_ids = self.select_documents(query, strategy, max_documents)
        
        return document_ids, intent
    
    def get_routing_explanation(
        self,
        query: str,
        document_ids: List[str],
        intent: QueryIntent
    ) -> str:
        """
        Generate explanation for routing decision
        
        Args:
            query: User query
            document_ids: Selected document IDs
            intent: Query intent
            
        Returns:
            Explanation string
        """
        explanation_parts = []
        
        explanation_parts.append(f"Query: '{query}'")
        explanation_parts.append(f"Selected {len(document_ids)} documents")
        
        if intent.subject_hints:
            explanation_parts.append(f"Subject hints: {', '.join(intent.subject_hints)}")
        
        if intent.chapter_hints:
            explanation_parts.append(f"Chapter hints: {', '.join(intent.chapter_hints)}")
        
        if intent.file_type_hints:
            explanation_parts.append(f"File type hints: {', '.join(intent.file_type_hints)}")
        
        if intent.is_comparison:
            explanation_parts.append("Detected comparison query")
        
        if intent.is_multi_doc:
            explanation_parts.append("Multi-document query detected")
        
        return "\n".join(explanation_parts)


# Convenience functions
def create_document_router(
    document_manager: MultiDocumentManager,
    metadata_retriever: MetadataRetriever
) -> DocumentRouter:
    """Create document router instance"""
    return DocumentRouter(document_manager, metadata_retriever)


if __name__ == "__main__":
    # Test document router
    from .document_manager import create_document_manager
    from .metadata_retriever import create_metadata_retriever
    
    manager = create_document_manager()
    retriever = create_metadata_retriever(manager)
    router = create_document_router(manager, retriever)
    
    # Test queries
    test_queries = [
        "What is clustering?",
        "So sánh Apriori trong slide và giáo trình",
        "Các bước preprocessing trong Chapter 3"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        doc_ids, intent = router.route_query(query)
        print(f"Selected documents: {len(doc_ids)}")
        print(f"Intent: {intent}")
    
    manager.close()
