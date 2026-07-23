# multi_document/document_manager.py - Multi-Document Management System
"""
Document Manager for Multi-Document RAG System

Features:
- Document registration and tracking
- Metadata management
- File upload handling
- Document CRUD operations
- MongoDB storage
"""

import os
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError


class MultiDocumentManager:
    """
    Manages multiple documents in RAG system
    """
    
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/", db_name: str = "rag_system"):
        """
        Initialize document manager
        
        Args:
            mongo_uri: MongoDB connection URI
            db_name: Database name
        """
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection = self.db['documents']
        
        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for performance"""
        # Unique index on document_id
        self.collection.create_index([("document_id", ASCENDING)], unique=True)
        
        # Indexes for common queries
        self.collection.create_index([("metadata.subject", ASCENDING)])
        self.collection.create_index([("metadata.file_type", ASCENDING)])
        self.collection.create_index([("metadata.upload_date", DESCENDING)])
        self.collection.create_index([("status", ASCENDING)])
        
        # Text index for filename search
        self.collection.create_index([("filename", "text")])
    
    def upload_document(
        self,
        file_path: str,
        metadata: Optional[Dict] = None,
        vector_collection: Optional[str] = None
    ) -> str:
        """
        Upload and register a document
        
        Args:
            file_path: Path to document file
            metadata: Document metadata
            vector_collection: ChromaDB collection name
            
        Returns:
            document_id
        """
        # Generate document ID
        document_id = f"doc_{uuid.uuid4().hex[:12]}"
        
        # Get file info
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_type = os.path.splitext(filename)[1].lstrip('.').lower()
        
        # Prepare metadata
        doc_metadata = metadata or {}
        doc_metadata.update({
            'filename': filename,
            'file_type': file_type,
            'file_size': file_size,
            'upload_date': datetime.now(timezone.utc)
        })
        
        # Create document record
        document = {
            'document_id': document_id,
            'filename': filename,
            'file_path': file_path,
            'file_type': file_type,
            'metadata': doc_metadata,
            'status': 'uploaded',
            'chunks_count': 0,
            'vector_collection': vector_collection or f"{document_id}_vectors",
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        
        # Insert into database
        try:
            self.collection.insert_one(document)
            print(f"✅ Uploaded document: {document_id} ({filename})")
            return document_id
        except DuplicateKeyError:
            raise ValueError(f"Document ID already exists: {document_id}")
    
    def get_document(self, document_id: str) -> Optional[Dict]:
        """
        Get document by ID
        
        Args:
            document_id: Document ID
            
        Returns:
            Document dict or None
        """
        doc = self.collection.find_one({'document_id': document_id}, {'_id': 0})
        return doc
    
    def list_documents(
        self,
        filters: Optional[Dict] = None,
        sort_by: str = 'upload_date',
        sort_order: int = DESCENDING,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        List documents with optional filtering
        
        Args:
            filters: MongoDB query filters
            sort_by: Field to sort by
            sort_order: ASCENDING or DESCENDING
            limit: Maximum number of results
            
        Returns:
            List of documents
        """
        query = filters or {}
        
        # Build sort key
        if sort_by.startswith('metadata.'):
            sort_key = sort_by
        else:
            sort_key = f"metadata.{sort_by}" if sort_by not in ['document_id', 'filename', 'status', 'created_at'] else sort_by
        
        cursor = self.collection.find(query, {'_id': 0}).sort(sort_key, sort_order)
        
        if limit:
            cursor = cursor.limit(limit)
        
        return list(cursor)
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete document
        
        Args:
            document_id: Document ID
            
        Returns:
            True if deleted, False otherwise
        """
        result = self.collection.delete_one({'document_id': document_id})
        
        if result.deleted_count > 0:
            print(f"✅ Deleted document: {document_id}")
            return True
        else:
            print(f"⚠️  Document not found: {document_id}")
            return False
    
    def update_metadata(self, document_id: str, metadata: Dict) -> bool:
        """
        Update document metadata
        
        Args:
            document_id: Document ID
            metadata: New metadata fields
            
        Returns:
            True if updated, False otherwise
        """
        update_data = {
            '$set': {
                f'metadata.{key}': value for key, value in metadata.items()
            }
        }
        update_data['$set']['updated_at'] = datetime.now(timezone.utc)
        
        result = self.collection.update_one(
            {'document_id': document_id},
            update_data
        )
        
        if result.modified_count > 0:
            print(f"✅ Updated metadata for: {document_id}")
            return True
        else:
            print(f"⚠️  Document not found or no changes: {document_id}")
            return False
    
    def update_status(self, document_id: str, status: str, chunks_count: Optional[int] = None) -> bool:
        """
        Update document processing status
        
        Args:
            document_id: Document ID
            status: New status (uploaded, processing, processed, error)
            chunks_count: Number of chunks (optional)
            
        Returns:
            True if updated, False otherwise
        """
        update_data = {
            '$set': {
                'status': status,
                'updated_at': datetime.now(timezone.utc)
            }
        }
        
        if chunks_count is not None:
            update_data['$set']['chunks_count'] = chunks_count
        
        result = self.collection.update_one(
            {'document_id': document_id},
            update_data
        )
        
        return result.modified_count > 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get system statistics
        
        Returns:
            Statistics dict
        """
        total_docs = self.collection.count_documents({})
        
        # Count by status
        status_counts = {}
        for status in ['uploaded', 'processing', 'processed', 'error']:
            count = self.collection.count_documents({'status': status})
            status_counts[status] = count
        
        # Count by file type
        pipeline = [
            {'$group': {'_id': '$file_type', 'count': {'$sum': 1}}}
        ]
        type_counts = {doc['_id']: doc['count'] for doc in self.collection.aggregate(pipeline)}
        
        # Total chunks
        pipeline = [
            {'$group': {'_id': None, 'total_chunks': {'$sum': '$chunks_count'}}}
        ]
        result = list(self.collection.aggregate(pipeline))
        total_chunks = result[0]['total_chunks'] if result else 0
        
        # Total file size
        pipeline = [
            {'$group': {'_id': None, 'total_size': {'$sum': '$metadata.file_size'}}}
        ]
        result = list(self.collection.aggregate(pipeline))
        total_size = result[0]['total_size'] if result else 0
        
        return {
            'total_documents': total_docs,
            'status_counts': status_counts,
            'type_counts': type_counts,
            'total_chunks': total_chunks,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2)
        }
    
    def search_by_filename(self, query: str) -> List[Dict]:
        """
        Search documents by filename
        
        Args:
            query: Search query
            
        Returns:
            List of matching documents
        """
        results = self.collection.find(
            {'$text': {'$search': query}},
            {'_id': 0, 'score': {'$meta': 'textScore'}}
        ).sort([('score', {'$meta': 'textScore'})])
        
        return list(results)
    
    def filter_by_metadata(
        self,
        subject: Optional[str] = None,
        chapter: Optional[str] = None,
        source: Optional[str] = None,
        file_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Filter documents by metadata
        
        Args:
            subject: Subject filter
            chapter: Chapter filter
            source: Source filter
            file_type: File type filter
            date_from: Start date
            date_to: End date
            
        Returns:
            List of matching documents
        """
        query = {}
        
        if subject:
            query['metadata.subject'] = subject
        
        if chapter:
            query['metadata.chapter'] = chapter
        
        if source:
            query['metadata.source'] = source
        
        if file_type:
            query['file_type'] = file_type
        
        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query['$gte'] = date_from
            if date_to:
                date_query['$lte'] = date_to
            query['metadata.upload_date'] = date_query
        
        return self.list_documents(filters=query)
    
    def get_available_filters(self) -> Dict[str, List[str]]:
        """
        Get available filter values
        
        Returns:
            Dict of filter options
        """
        # Get unique subjects
        subjects = self.collection.distinct('metadata.subject')
        
        # Get unique chapters
        chapters = self.collection.distinct('metadata.chapter')
        
        # Get unique sources
        sources = self.collection.distinct('metadata.source')
        
        # Get unique file types
        file_types = self.collection.distinct('file_type')
        
        return {
            'subjects': [s for s in subjects if s],
            'chapters': [c for c in chapters if c],
            'sources': [s for s in sources if s],
            'file_types': [f for f in file_types if f]
        }
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()


# Convenience functions
def create_document_manager(mongo_uri: str = "mongodb://localhost:27017/") -> MultiDocumentManager:
    """Create document manager instance"""
    return MultiDocumentManager(mongo_uri)


if __name__ == "__main__":
    # Test document manager
    manager = create_document_manager()
    
    print("📊 System Statistics:")
    stats = manager.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n🔍 Available Filters:")
    filters = manager.get_available_filters()
    for key, values in filters.items():
        print(f"  {key}: {values}")
    
    manager.close()
