# multi_document/__init__.py - Multi-Document RAG System
"""
Multi-Document Intelligent RAG System

Modules:
- document_manager: Multi-document management and upload
- metadata_retriever: Metadata-based filtering and retrieval
- document_router: Intelligent document routing
- cross_document: Cross-document retrieval and comparison
- file_processor: Multi-format file processing (PDF, DOCX, PPTX, TXT, CSV)
"""

from .document_manager import MultiDocumentManager, create_document_manager
from .metadata_retriever import MetadataRetriever, create_metadata_retriever
from .document_router import DocumentRouter, create_document_router
from .cross_document import CrossDocumentRetriever, create_cross_document_retriever
from .file_processor import FileProcessor, create_file_processor, process_file

__all__ = [
    'MultiDocumentManager',
    'MetadataRetriever',
    'DocumentRouter',
    'CrossDocumentRetriever',
    'FileProcessor',
    'create_document_manager',
    'create_metadata_retriever',
    'create_document_router',
    'create_cross_document_retriever',
    'create_file_processor',
    'process_file'
]

__version__ = '1.0.0'
