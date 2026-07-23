# multi_document/metadata_retriever.py - Metadata-Based Retrieval
"""
Metadata Retriever for Multi-Document RAG System

Features:
- Metadata-based filtering
- Advanced search
- Faceted search
- Document selection based on metadata
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from .document_manager import MultiDocumentManager


class MetadataRetriever:
    """
    Retrieves documents based on metadata
    """
    
    def __init__(self, document_manager: MultiDocumentManager):
        """
        Initialize metadata retriever
        
        Args:
            document_manager: Document manager instance
        """
        self.doc_manager = document_manager
    
    def filter_by_metadata(self, filters: Dict[str, Any]) -> List[Dict]:
        """
        Filter documents by metadata
        
        Args:
            filters: Metadata filters
                - subject: str
                - chapter: str
                - source: str
                - file_type: str
                - date_from: datetime
                - date_to: datetime
                
        Returns:
            List of matching documents
        """
        return self.doc_manager.filter_by_metadata(**filters)
    
    def search_by_subject(self, subject: str) -> List[Dict]:
        """
        Search documents by subject
        
        Args:
            subject: Subject name
            
        Returns:
            List of matching documents
        """
        return self.doc_manager.filter_by_metadata(subject=subject)
    
    def search_by_chapter(self, chapter: str) -> List[Dict]:
        """
        Search documents by chapter
        
        Args:
            chapter: Chapter name
            
        Returns:
            List of matching documents
        """
        return self.doc_manager.filter_by_metadata(chapter=chapter)
    
    def search_by_source(self, source: str) -> List[Dict]:
        """
        Search documents by source
        
        Args:
            source: Source name
            
        Returns:
            List of matching documents
        """
        return self.doc_manager.filter_by_metadata(source=source)
    
    def search_by_file_type(self, file_type: str) -> List[Dict]:
        """
        Search documents by file type
        
        Args:
            file_type: File type (pdf, docx, pptx, txt, csv)
            
        Returns:
            List of matching documents
        """
        return self.doc_manager.filter_by_metadata(file_type=file_type)
    
    def search_by_date_range(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Search documents by upload date range
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of matching documents
        """
        return self.doc_manager.filter_by_metadata(
            date_from=start_date,
            date_to=end_date
        )
    
    def get_available_filters(self) -> Dict[str, List[str]]:
        """
        Get available filter values
        
        Returns:
            Dict of filter options
        """
        return self.doc_manager.get_available_filters()
    
    def search_by_query(self, query: str) -> List[Dict]:
        """
        Search documents by query string
        Analyzes query to extract metadata hints
        
        Args:
            query: Search query
            
        Returns:
            List of matching documents
        """
        query_lower = query.lower()
        
        # Extract metadata hints from query
        filters = {}
        
        # Check for subject hints
        available_filters = self.get_available_filters()
        
        for subject in available_filters.get('subjects', []):
            if subject and subject.lower() in query_lower:
                filters['subject'] = subject
                break
        
        # Check for chapter hints
        for chapter in available_filters.get('chapters', []):
            if chapter and chapter.lower() in query_lower:
                filters['chapter'] = chapter
                break
        
        # Check for file type hints
        file_type_keywords = {
            'pdf': ['pdf', 'document', 'textbook', 'book'],
            'pptx': ['slide', 'presentation', 'ppt', 'powerpoint'],
            'docx': ['word', 'doc', 'document'],
            'txt': ['text', 'note', 'txt'],
            'csv': ['csv', 'data', 'table', 'spreadsheet']
        }
        
        for file_type, keywords in file_type_keywords.items():
            if any(kw in query_lower for kw in keywords):
                filters['file_type'] = file_type
                break
        
        # Apply filters if found
        if filters:
            return self.filter_by_metadata(filters)
        
        # Otherwise, search by filename
        return self.doc_manager.search_by_filename(query)
    
    def get_document_ids(self, filters: Optional[Dict] = None) -> List[str]:
        """
        Get document IDs matching filters
        
        Args:
            filters: Metadata filters
            
        Returns:
            List of document IDs
        """
        if filters:
            documents = self.filter_by_metadata(filters)
        else:
            documents = self.doc_manager.list_documents()
        
        return [doc['document_id'] for doc in documents]
    
    def get_documents_by_ids(self, document_ids: List[str]) -> List[Dict]:
        """
        Get documents by IDs
        
        Args:
            document_ids: List of document IDs
            
        Returns:
            List of documents
        """
        documents = []
        for doc_id in document_ids:
            doc = self.doc_manager.get_document(doc_id)
            if doc:
                documents.append(doc)
        return documents
    
    def faceted_search(
        self,
        query: str,
        facets: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Perform faceted search
        
        Args:
            query: Search query
            facets: List of facets to return (subject, chapter, source, file_type)
            
        Returns:
            Dict with results and facet counts
        """
        # Get matching documents
        results = self.search_by_query(query)
        
        # Calculate facets
        facet_counts = {}
        
        if not facets:
            facets = ['subject', 'chapter', 'source', 'file_type']
        
        for facet in facets:
            counts = {}
            for doc in results:
                if facet == 'file_type':
                    value = doc.get('file_type')
                else:
                    value = doc.get('metadata', {}).get(facet)
                
                if value:
                    counts[value] = counts.get(value, 0) + 1
            
            facet_counts[facet] = counts
        
        return {
            'results': results,
            'facets': facet_counts,
            'total': len(results)
        }
    
    def get_related_documents(
        self,
        document_id: str,
        relation_type: str = 'subject'
    ) -> List[Dict]:
        """
        Get documents related to a given document
        
        Args:
            document_id: Source document ID
            relation_type: Type of relation (subject, chapter, source)
            
        Returns:
            List of related documents
        """
        # Get source document
        source_doc = self.doc_manager.get_document(document_id)
        if not source_doc:
            return []
        
        # Get relation value
        if relation_type == 'file_type':
            relation_value = source_doc.get('file_type')
        else:
            relation_value = source_doc.get('metadata', {}).get(relation_type)
        
        if not relation_value:
            return []
        
        # Find related documents
        filters = {relation_type: relation_value}
        related = self.filter_by_metadata(filters)
        
        # Exclude source document
        related = [doc for doc in related if doc['document_id'] != document_id]
        
        return related


# Convenience functions
def create_metadata_retriever(document_manager: MultiDocumentManager) -> MetadataRetriever:
    """Create metadata retriever instance"""
    return MetadataRetriever(document_manager)


if __name__ == "__main__":
    # Test metadata retriever
    from .document_manager import create_document_manager
    
    manager = create_document_manager()
    retriever = create_metadata_retriever(manager)
    
    print("🔍 Available Filters:")
    filters = retriever.get_available_filters()
    for key, values in filters.items():
        print(f"  {key}: {values}")
    
    print("\n📚 All Documents:")
    docs = retriever.get_document_ids()
    print(f"  Total: {len(docs)}")
    
    manager.close()
