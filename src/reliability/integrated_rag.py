# reliability/integrated_rag.py - Production RAG with Full Reliability
"""
Production-ready RAG với tất cả reliability features:
- Rate limiting
- Retry with backoff
- Caching
- API key rotation
- Graceful degradation
- Monitoring
"""

import asyncio
from typing import Optional, Dict, List
import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.documents import Document

from .rate_limiter import with_rate_limit, rate_limiter
from .retry_strategy import retry_with_backoff, RetryConfig
from .cache_manager import cached, TranslationCache, ResponseCache
from .api_key_manager import get_model_and_key, api_key_manager
from .graceful_degradation import (
    with_graceful_degradation,
    FallbackResponse,
    TimeoutHandler
)
from .monitoring import trace_request, monitoring

logger = logging.getLogger(__name__)


class ReliableRAG:
    """Production RAG with full reliability"""
    
    def __init__(self, cache_manager, retriever, qa_chain):
        self.translation_cache = TranslationCache(cache_manager)
        self.response_cache = ResponseCache(cache_manager)
        self.retriever = retriever
        self.qa_chain = qa_chain
    
    @trace_request("/api/translate", "translation")
    @retry_with_backoff(RetryConfig(max_attempts=3, initial_delay=1.0))
    @with_rate_limit("translation")
    async def translate_text(
        self,
        text: str,
        target_language: str = "English"
    ) -> str:
        """
        Translate text with full reliability
        """
        # Check cache first
        cached_translation = self.translation_cache.get(text, target_language)
        if cached_translation:
            logger.info("Translation cache HIT")
            return cached_translation
        
        # Get model and API key
        model_name, api_key = get_model_and_key("translation")
        if not model_name or not api_key:
            raise Exception("No available API key for translation")
        
        # Create LLM
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.3,
            timeout=30
        )
        
        prompt = f"""Translate the following text to {target_language}. 
Only provide the translation, nothing else.

Text: {text}

Translation:"""
        
        try:
            # Call with timeout
            response = await TimeoutHandler.with_timeout(
                llm.ainvoke(prompt),
                timeout=30.0
            )
            
            # Extract text
            if hasattr(response, 'content'):
                translation = response.content
            else:
                translation = str(response)
            
            # Cache result
            self.translation_cache.set(text, target_language, translation)
            
            # Record success
            key_info = api_key_manager.get_available_key()
            if key_info:
                api_key_manager.record_request(key_info, success=True)
            
            return translation
        
        except Exception as e:
            # Record failure
            key_info = api_key_manager.get_available_key()
            if key_info:
                api_key_manager.record_request(key_info, success=False)
            raise e
    
    @trace_request("/api/retrieve", "retrieval")
    async def retrieve_documents(
        self,
        query: str,
        k: int = 10
    ) -> List[Document]:
        """
        Retrieve documents with reliability
        """
        try:
            # Use retriever with timeout
            if hasattr(self.retriever, 'ainvoke'):
                docs = await TimeoutHandler.with_timeout(
                    self.retriever.ainvoke(query, k=k),
                    timeout=10.0,
                    fallback_value=[]
                )
            else:
                # Sync retriever
                docs = self.retriever.invoke(query, k=k)
            
            return docs
        
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return []
    
    @trace_request("/api/generate", "generation")
    @retry_with_backoff(RetryConfig(max_attempts=2, initial_delay=2.0))
    @with_rate_limit("gemini_flash")
    async def generate_answer(
        self,
        question: str,
        documents: List[Document]
    ) -> Dict:
        """
        Generate answer with full reliability
        """
        # Get model and API key
        model_name, api_key = get_model_and_key("fast")
        if not model_name or not api_key:
            raise Exception("No available API key for generation")
        
        # Create context from documents
        context = "\n\n".join([
            f"Document {i+1}:\n{doc.page_content}"
            for i, doc in enumerate(documents[:3])
        ])
        
        # Create LLM
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.3,
            timeout=60
        )
        
        prompt = f"""Based on the following documents, answer the question.

Documents:
{context}

Question: {question}

Answer:"""
        
        try:
            # Call with timeout
            response = await TimeoutHandler.with_timeout(
                llm.ainvoke(prompt),
                timeout=60.0
            )
            
            # Extract answer
            if hasattr(response, 'content'):
                answer = response.content
            else:
                answer = str(response)
            
            # Record success
            key_info = api_key_manager.get_available_key()
            if key_info:
                api_key_manager.record_request(key_info, success=True)
            
            return {
                "answer": answer,
                "sources": documents,
                "model": model_name,
                "mode": "full"
            }
        
        except Exception as e:
            # Record failure
            key_info = api_key_manager.get_available_key()
            if key_info:
                api_key_manager.record_request(key_info, success=False)
            raise e
    
    @trace_request("/api/question", "rag")
    async def ask_question(
        self,
        question: str,
        use_cache: bool = True
    ) -> Dict:
        """
        Complete RAG pipeline with full reliability
        """
        # Check response cache
        if use_cache:
            cached_response = self.response_cache.get(question, "default")
            if cached_response:
                logger.info("Response cache HIT")
                return cached_response
        
        # Define primary function
        async def primary_rag():
            # Step 1: Translate if needed
            question_en = question
            if self._is_vietnamese(question):
                question_en = await self.translate_text(question, "English")
            
            # Step 2: Retrieve documents
            documents = await self.retrieve_documents(question_en, k=10)
            
            if not documents:
                return FallbackResponse.simple_answer(question)
            
            # Step 3: Generate answer
            result = await self.generate_answer(question_en, documents)
            
            # Step 4: Translate answer back if needed
            if self._is_vietnamese(question):
                result["answer"] = await self.translate_text(
                    result["answer"],
                    "Vietnamese"
                )
            
            return result
        
        # Define fallback function
        async def fallback_rag():
            # Try search-only mode
            try:
                documents = await self.retrieve_documents(question, k=5)
                return FallbackResponse.search_only_answer(question, documents)
            except:
                return FallbackResponse.simple_answer(question)
        
        # Execute with graceful degradation
        try:
            result = await with_graceful_degradation(
                "rag_pipeline",
                primary_rag,
                fallback_rag
            )
            
            # Cache result
            if use_cache and result.get("mode") == "full":
                self.response_cache.set(question, "default", result)
            
            return result
        
        except Exception as e:
            logger.error(f"RAG pipeline failed completely: {e}")
            return FallbackResponse.simple_answer(question)
    
    def _is_vietnamese(self, text: str) -> bool:
        """Check if text is Vietnamese"""
        vietnamese_chars = "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
        return any(char in text.lower() for char in vietnamese_chars)


# Helper function to create reliable RAG
def create_reliable_rag(cache_manager, retriever, qa_chain) -> ReliableRAG:
    """Create production RAG instance"""
    return ReliableRAG(cache_manager, retriever, qa_chain)
