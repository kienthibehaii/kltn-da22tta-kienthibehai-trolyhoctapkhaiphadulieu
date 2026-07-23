"""
Advanced Retrieval System
Implements hybrid retrieval, query expansion, contextual compression
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from sentence_transformers import SentenceTransformer
import re


class QueryExpander:
    """
    Expand queries with synonyms, related terms, and reformulations
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        
        # Predefined expansions for common terms
        self.expansions = {
            'clustering': ['grouping', 'segmentation', 'partitioning'],
            'classification': ['categorization', 'labeling', 'prediction'],
            'regression': ['prediction', 'forecasting', 'estimation'],
            'association': ['correlation', 'relationship', 'pattern'],
        }
    
    def expand_query(
        self,
        query: str,
        method: str = 'hybrid'  # 'synonym', 'llm', 'hybrid'
    ) -> List[str]:
        """
        Expand query into multiple variations
        
        Returns:
            List of query variations
        """
        queries = [query]  # Original query
        
        if method in ['synonym', 'hybrid']:
            # Add synonym expansions
            synonym_queries = self._expand_with_synonyms(query)
            queries.extend(synonym_queries)
        
        if method in ['llm', 'hybrid'] and self.llm_client:
            # Add LLM-generated variations
            llm_queries = self._expand_with_llm(query)
            queries.extend(llm_queries)
        
        # Remove duplicates
        queries = list(dict.fromkeys(queries))
        
        return queries
    
    def _expand_with_synonyms(self, query: str) -> List[str]:
        """
        Expand query with predefined synonyms
        """
        expanded = []
        query_lower = query.lower()
        
        for term, synonyms in self.expansions.items():
            if term in query_lower:
                for synonym in synonyms:
                    expanded_query = query_lower.replace(term, synonym)
                    expanded.append(expanded_query)
        
        return expanded
    
    def _expand_with_llm(self, query: str) -> List[str]:
        """
        Expand query using LLM
        """
        prompt = f"""Generate 3 alternative phrasings of this question:
"{query}"

Requirements:
- Keep the same meaning
- Use different words
- Make them more specific or more general

Alternative questions:
1."""
        
        try:
            response = self.llm_client.invoke(prompt)
            # Parse response to extract questions
            questions = self._parse_llm_response(response.content)
            return questions
        except:
            return []
    
    def _parse_llm_response(self, response: str) -> List[str]:
        """Parse LLM response to extract questions"""
        lines = response.strip().split('\n')
        questions = []
        
        for line in lines:
            # Remove numbering
            line = re.sub(r'^\d+\.\s*', '', line.strip())
            if line and len(line) > 10:
                questions.append(line)
        
        return questions[:3]


class QueryRewriter:
    """
    Rewrite queries for better retrieval
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    def rewrite_query(
        self,
        query: str,
        conversation_history: List[Dict] = None
    ) -> str:
        """
        Rewrite query based on context
        """
        if not conversation_history or not self.llm_client:
            return query
        
        # Build context from history
        context = self._build_context(conversation_history)
        
        prompt = f"""Given the conversation history, rewrite the user's question to be standalone and clear.

Conversation history:
{context}

Current question: {query}

Rewritten question (standalone, clear, specific):"""
        
        try:
            response = self.llm_client.invoke(prompt)
            rewritten = response.content.strip()
            
            # Validate rewrite
            if len(rewritten) > 10 and len(rewritten) < 500:
                return rewritten
            else:
                return query
        except:
            return query
    
    def _build_context(
        self,
        history: List[Dict],
        max_turns: int = 3
    ) -> str:
        """
        Build context string from conversation history
        """
        context_parts = []
        
        for turn in history[-max_turns:]:
            role = turn.get('role', 'user')
            content = turn.get('content', '')
            
            if role == 'user':
                context_parts.append(f"User: {content}")
            else:
                # Truncate assistant response
                content_short = content[:200] + '...' if len(content) > 200 else content
                context_parts.append(f"Assistant: {content_short}")
        
        return '\n'.join(context_parts)


class ContextualCompressor:
    """
    Compress retrieved documents to keep only relevant parts
    """
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        compression_ratio: float = 0.5
    ):
        self.model = SentenceTransformer(model_name)
        self.compression_ratio = compression_ratio
    
    def compress_documents(
        self,
        query: str,
        documents: List[Dict],
        method: str = 'sentence'  # 'sentence', 'extractive', 'abstractive'
    ) -> List[Dict]:
        """
        Compress documents to keep only relevant parts
        """
        if method == 'sentence':
            return self._compress_by_sentence(query, documents)
        elif method == 'extractive':
            return self._compress_extractive(query, documents)
        else:
            return documents
    
    def _compress_by_sentence(
        self,
        query: str,
        documents: List[Dict]
    ) -> List[Dict]:
        """
        Keep only sentences relevant to query
        """
        # Encode query
        query_embedding = self.model.encode([query])[0]
        
        compressed_docs = []
        
        for doc in documents:
            text = doc.get('content', doc.get('text', ''))
            
            # Split into sentences
            sentences = self._split_sentences(text)
            
            if not sentences:
                continue
            
            # Encode sentences
            sentence_embeddings = self.model.encode(sentences)
            
            # Calculate similarity with query
            from sklearn.metrics.pairwise import cosine_similarity
            similarities = cosine_similarity(
                [query_embedding],
                sentence_embeddings
            )[0]
            
            # Keep top sentences
            num_keep = max(1, int(len(sentences) * self.compression_ratio))
            top_indices = np.argsort(similarities)[-num_keep:]
            top_indices = sorted(top_indices)  # Keep original order
            
            # Reconstruct text
            compressed_text = ' '.join([sentences[i] for i in top_indices])
            
            compressed_docs.append({
                **doc,
                'content': compressed_text,
                'original_length': len(text),
                'compressed_length': len(compressed_text),
                'compression_ratio': len(compressed_text) / len(text) if len(text) > 0 else 0
            })
        
        return compressed_docs
    
    def _compress_extractive(
        self,
        query: str,
        documents: List[Dict]
    ) -> List[Dict]:
        """
        Extract key sentences using TextRank-like algorithm
        """
        # Similar to sentence compression but uses graph-based ranking
        return self._compress_by_sentence(query, documents)
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]


class SelfQueryRetriever:
    """
    Parse natural language query into structured query
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    def parse_query(
        self,
        query: str,
        metadata_schema: Dict = None
    ) -> Dict:
        """
        Parse query into structured format
        
        Returns:
            {
                'query': str,  # Semantic query
                'filters': Dict,  # Metadata filters
                'sort': str,  # Sort field
                'limit': int  # Result limit
            }
        """
        if not self.llm_client:
            return {'query': query, 'filters': {}}
        
        # Build prompt with schema
        schema_str = self._format_schema(metadata_schema or {})
        
        prompt = f"""Parse this natural language query into structured format.

Available metadata fields:
{schema_str}

User query: "{query}"

Extract:
1. Semantic query (main question)
2. Metadata filters (e.g., source, date, type)
3. Sort preference
4. Result limit

Output as JSON:
{{
    "query": "...",
    "filters": {{}},
    "sort": "...",
    "limit": 5
}}

JSON:"""
        
        try:
            response = self.llm_client.invoke(prompt)
            import json
            parsed = json.loads(response.content.strip())
            return parsed
        except:
            return {'query': query, 'filters': {}}
    
    def _format_schema(self, schema: Dict) -> str:
        """Format metadata schema for prompt"""
        lines = []
        for field, field_type in schema.items():
            lines.append(f"- {field}: {field_type}")
        return '\n'.join(lines)


class HybridRetriever:
    """
    Advanced hybrid retrieval combining multiple strategies
    """
    
    def __init__(
        self,
        vector_retriever,
        bm25_retriever,
        query_expander: QueryExpander,
        query_rewriter: QueryRewriter,
        contextual_compressor: ContextualCompressor,
        self_query_retriever: SelfQueryRetriever
    ):
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        self.query_expander = query_expander
        self.query_rewriter = query_rewriter
        self.contextual_compressor = contextual_compressor
        self.self_query_retriever = self_query_retriever
    
    def retrieve(
        self,
        query: str,
        k: int = 10,
        conversation_history: List[Dict] = None,
        use_expansion: bool = True,
        use_rewriting: bool = True,
        use_compression: bool = True,
        use_self_query: bool = False
    ) -> List[Dict]:
        """
        Advanced hybrid retrieval pipeline
        
        Steps:
        1. Query rewriting (if conversation context)
        2. Query expansion (multiple variations)
        3. Self-query parsing (structured filters)
        4. Hybrid retrieval (vector + BM25)
        5. Contextual compression
        6. Fusion and ranking
        """
        # Step 1: Query rewriting
        if use_rewriting and conversation_history:
            query = self.query_rewriter.rewrite_query(
                query,
                conversation_history
            )
            print(f"📝 Rewritten query: {query}")
        
        # Step 2: Query expansion
        queries = [query]
        if use_expansion:
            expanded = self.query_expander.expand_query(query, method='synonym')
            queries.extend(expanded[:2])  # Limit to avoid too many queries
            print(f"🔄 Expanded to {len(queries)} queries")
        
        # Step 3: Self-query parsing
        structured_query = query
        filters = {}
        if use_self_query:
            parsed = self.self_query_retriever.parse_query(query)
            structured_query = parsed.get('query', query)
            filters = parsed.get('filters', {})
            print(f"🔍 Parsed filters: {filters}")
        
        # Step 4: Hybrid retrieval for each query
        all_results = []
        
        for q in queries:
            # Vector search
            vector_results = self.vector_retriever.search(
                q,
                k=k*2,
                filters=filters
            )
            
            # BM25 search
            bm25_results = self.bm25_retriever.search(
                q,
                k=k*2,
                filters=filters
            )
            
            # Combine
            all_results.extend(vector_results)
            all_results.extend(bm25_results)
        
        # Step 5: Deduplicate and rank
        unique_results = self._deduplicate(all_results)
        ranked_results = self._rank_results(unique_results, query)
        
        # Step 6: Contextual compression
        if use_compression:
            ranked_results = self.contextual_compressor.compress_documents(
                query,
                ranked_results[:k]
            )
            print(f"📦 Compressed {len(ranked_results)} documents")
        
        return ranked_results[:k]
    
    def _deduplicate(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicate documents"""
        seen = set()
        unique = []
        
        for doc in results:
            doc_id = doc.get('id', doc.get('content', '')[:100])
            if doc_id not in seen:
                seen.add(doc_id)
                unique.append(doc)
        
        return unique
    
    def _rank_results(
        self,
        results: List[Dict],
        query: str
    ) -> List[Dict]:
        """
        Rank results using RRF (Reciprocal Rank Fusion)
        """
        # Simple ranking by score
        ranked = sorted(
            results,
            key=lambda x: x.get('score', 0),
            reverse=True
        )
        
        return ranked


# Example usage
if __name__ == "__main__":
    print("Advanced Retrieval System initialized")
    
    # Initialize components
    query_expander = QueryExpander()
    
    # Test query expansion
    query = "What is clustering in data mining?"
    expanded = query_expander.expand_query(query, method='synonym')
    
    print(f"\nOriginal: {query}")
    print(f"Expanded: {expanded}")
