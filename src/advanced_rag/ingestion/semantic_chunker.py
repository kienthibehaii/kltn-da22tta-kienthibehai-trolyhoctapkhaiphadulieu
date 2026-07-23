"""
Advanced Semantic Chunker
Chunks documents based on semantic similarity instead of fixed size
"""

import numpy as np
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import re

class AdvancedSemanticChunker:
    """
    Semantic chunking with:
    - Sentence-level splitting
    - Similarity-based grouping
    - Metadata enrichment
    - Document hierarchy preservation
    """
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        similarity_threshold: float = 0.7,
        min_chunk_size: int = 100,
        max_chunk_size: int = 1000,
        overlap_sentences: int = 2
    ):
        self.model = SentenceTransformer(model_name)
        self.similarity_threshold = similarity_threshold
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_sentences = overlap_sentences
    
    def chunk_document(
        self,
        text: str,
        metadata: Dict = None
    ) -> List[Dict]:
        """
        Chunk document semantically
        
        Returns:
            List of chunks with metadata
        """
        # Step 1: Split into sentences
        sentences = self._split_sentences(text)
        
        if not sentences:
            return []
        
        # Step 2: Generate embeddings
        embeddings = self.model.encode(sentences)
        
        # Step 3: Calculate similarity matrix
        similarity_matrix = cosine_similarity(embeddings)
        
        # Step 4: Group sentences by similarity
        chunks = self._group_sentences(
            sentences,
            similarity_matrix,
            embeddings
        )
        
        # Step 5: Add metadata
        enriched_chunks = self._enrich_metadata(
            chunks,
            metadata or {}
        )
        
        return enriched_chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences intelligently
        """
        # Handle common abbreviations
        text = re.sub(r'\b(Dr|Mr|Mrs|Ms|Prof|Sr|Jr)\.\s', r'\1<PERIOD> ', text)
        text = re.sub(r'\b([A-Z])\.\s', r'\1<PERIOD> ', text)
        
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Restore periods
        sentences = [s.replace('<PERIOD>', '.') for s in sentences]
        
        # Filter empty
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _group_sentences(
        self,
        sentences: List[str],
        similarity_matrix: np.ndarray,
        embeddings: np.ndarray
    ) -> List[Dict]:
        """
        Group sentences into semantic chunks
        """
        chunks = []
        current_chunk = []
        current_size = 0
        
        for i, sentence in enumerate(sentences):
            sentence_len = len(sentence)
            
            # Check if adding this sentence exceeds max size
            if current_size + sentence_len > self.max_chunk_size and current_chunk:
                # Save current chunk
                chunks.append({
                    'text': ' '.join(current_chunk),
                    'sentences': current_chunk.copy(),
                    'embedding': np.mean([embeddings[j] for j in range(i - len(current_chunk), i)], axis=0)
                })
                
                # Start new chunk with overlap
                overlap_start = max(0, len(current_chunk) - self.overlap_sentences)
                current_chunk = current_chunk[overlap_start:]
                current_size = sum(len(s) for s in current_chunk)
            
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_size += sentence_len
            
            # Check semantic boundary
            if i > 0 and current_size >= self.min_chunk_size:
                # Calculate similarity with previous sentence
                similarity = similarity_matrix[i][i-1]
                
                # If similarity drops below threshold, create new chunk
                if similarity < self.similarity_threshold:
                    chunks.append({
                        'text': ' '.join(current_chunk),
                        'sentences': current_chunk.copy(),
                        'embedding': np.mean([embeddings[j] for j in range(i - len(current_chunk) + 1, i + 1)], axis=0)
                    })
                    
                    # Start new chunk with overlap
                    overlap_start = max(0, len(current_chunk) - self.overlap_sentences)
                    current_chunk = current_chunk[overlap_start:]
                    current_size = sum(len(s) for s in current_chunk)
        
        # Add final chunk
        if current_chunk:
            chunks.append({
                'text': ' '.join(current_chunk),
                'sentences': current_chunk,
                'embedding': np.mean([embeddings[len(sentences) - len(current_chunk):]], axis=0)
            })
        
        return chunks
    
    def _enrich_metadata(
        self,
        chunks: List[Dict],
        base_metadata: Dict
    ) -> List[Dict]:
        """
        Enrich chunks with metadata
        """
        enriched = []
        
        for i, chunk in enumerate(chunks):
            # Extract key phrases
            key_phrases = self._extract_key_phrases(chunk['text'])
            
            # Detect section type
            section_type = self._detect_section_type(chunk['text'])
            
            # Calculate statistics
            stats = {
                'char_count': len(chunk['text']),
                'word_count': len(chunk['text'].split()),
                'sentence_count': len(chunk['sentences']),
                'avg_sentence_length': len(chunk['text']) / len(chunk['sentences']) if chunk['sentences'] else 0
            }
            
            enriched.append({
                'text': chunk['text'],
                'chunk_id': i,
                'metadata': {
                    **base_metadata,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'key_phrases': key_phrases,
                    'section_type': section_type,
                    'statistics': stats,
                    'has_code': self._has_code(chunk['text']),
                    'has_math': self._has_math(chunk['text']),
                    'has_table': self._has_table(chunk['text'])
                },
                'embedding': chunk['embedding']
            })
        
        return enriched
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """
        Extract key phrases from text
        """
        # Simple keyword extraction (can be improved with RAKE, YAKE, etc.)
        words = text.lower().split()
        
        # Filter stopwords and short words
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        keywords = [w for w in words if len(w) > 3 and w not in stopwords]
        
        # Get top 5 most frequent
        from collections import Counter
        top_keywords = [word for word, count in Counter(keywords).most_common(5)]
        
        return top_keywords
    
    def _detect_section_type(self, text: str) -> str:
        """
        Detect section type (definition, example, algorithm, etc.)
        """
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['definition:', 'is defined as', 'refers to']):
            return 'definition'
        elif any(word in text_lower for word in ['example:', 'for example', 'for instance']):
            return 'example'
        elif any(word in text_lower for word in ['algorithm:', 'procedure:', 'steps:']):
            return 'algorithm'
        elif any(word in text_lower for word in ['theorem:', 'proof:', 'lemma:']):
            return 'theorem'
        elif '?' in text:
            return 'question'
        else:
            return 'general'
    
    def _has_code(self, text: str) -> bool:
        """Check if text contains code"""
        code_indicators = ['def ', 'class ', 'import ', 'function', '```', 'for (', 'while (']
        return any(indicator in text for indicator in code_indicators)
    
    def _has_math(self, text: str) -> bool:
        """Check if text contains mathematical notation"""
        math_indicators = ['∑', '∫', '∂', '√', '≤', '≥', '∈', '∀', '∃', r'\[', r'\(']
        return any(indicator in text for indicator in math_indicators)
    
    def _has_table(self, text: str) -> bool:
        """Check if text contains table"""
        return '|' in text or '\t' in text


class HierarchicalChunker:
    """
    Preserve document hierarchy during chunking
    """
    
    def __init__(self, semantic_chunker: AdvancedSemanticChunker):
        self.semantic_chunker = semantic_chunker
    
    def chunk_with_hierarchy(
        self,
        document: Dict
    ) -> List[Dict]:
        """
        Chunk document while preserving hierarchy
        
        Args:
            document: {
                'title': str,
                'sections': [
                    {
                        'heading': str,
                        'level': int,
                        'content': str,
                        'subsections': [...]
                    }
                ]
            }
        
        Returns:
            List of chunks with hierarchy metadata
        """
        chunks = []
        
        # Process title
        if document.get('title'):
            title_chunk = {
                'text': document['title'],
                'metadata': {
                    'type': 'title',
                    'level': 0,
                    'hierarchy': [document['title']]
                }
            }
            chunks.append(title_chunk)
        
        # Process sections recursively
        for section in document.get('sections', []):
            section_chunks = self._process_section(
                section,
                hierarchy=[document.get('title', 'Document')]
            )
            chunks.extend(section_chunks)
        
        return chunks
    
    def _process_section(
        self,
        section: Dict,
        hierarchy: List[str]
    ) -> List[Dict]:
        """
        Process section recursively
        """
        chunks = []
        current_hierarchy = hierarchy + [section['heading']]
        
        # Chunk section content
        if section.get('content'):
            content_chunks = self.semantic_chunker.chunk_document(
                section['content'],
                metadata={
                    'section_heading': section['heading'],
                    'section_level': section['level'],
                    'hierarchy': current_hierarchy
                }
            )
            chunks.extend(content_chunks)
        
        # Process subsections
        for subsection in section.get('subsections', []):
            subsection_chunks = self._process_section(
                subsection,
                current_hierarchy
            )
            chunks.extend(subsection_chunks)
        
        return chunks


class DuplicateDetector:
    """
    Detect and remove duplicate chunks
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.95,
        min_length: int = 50
    ):
        self.similarity_threshold = similarity_threshold
        self.min_length = min_length
    
    def detect_duplicates(
        self,
        chunks: List[Dict]
    ) -> Tuple[List[Dict], List[Tuple[int, int]]]:
        """
        Detect duplicate chunks
        
        Returns:
            (unique_chunks, duplicate_pairs)
        """
        if not chunks:
            return [], []
        
        # Extract embeddings
        embeddings = np.array([chunk['embedding'] for chunk in chunks])
        
        # Calculate similarity matrix
        similarity_matrix = cosine_similarity(embeddings)
        
        # Find duplicates
        duplicates = []
        seen = set()
        
        for i in range(len(chunks)):
            if i in seen:
                continue
            
            for j in range(i + 1, len(chunks)):
                if j in seen:
                    continue
                
                # Check similarity
                if similarity_matrix[i][j] >= self.similarity_threshold:
                    # Check text length
                    if len(chunks[i]['text']) >= self.min_length:
                        duplicates.append((i, j))
                        seen.add(j)
        
        # Keep unique chunks
        unique_chunks = [
            chunk for i, chunk in enumerate(chunks)
            if i not in seen
        ]
        
        return unique_chunks, duplicates
    
    def merge_duplicates(
        self,
        chunks: List[Dict],
        duplicates: List[Tuple[int, int]]
    ) -> List[Dict]:
        """
        Merge duplicate chunks by combining metadata
        """
        # Create mapping
        merge_map = {}
        for i, j in duplicates:
            if i not in merge_map:
                merge_map[i] = [j]
            else:
                merge_map[i].append(j)
        
        # Merge metadata
        merged_chunks = []
        processed = set()
        
        for i, chunk in enumerate(chunks):
            if i in processed:
                continue
            
            if i in merge_map:
                # Merge with duplicates
                duplicate_indices = merge_map[i]
                merged_metadata = self._merge_metadata(
                    [chunk] + [chunks[j] for j in duplicate_indices]
                )
                
                chunk['metadata'] = merged_metadata
                processed.update(duplicate_indices)
            
            merged_chunks.append(chunk)
        
        return merged_chunks
    
    def _merge_metadata(self, chunks: List[Dict]) -> Dict:
        """
        Merge metadata from duplicate chunks
        """
        merged = chunks[0]['metadata'].copy()
        
        # Collect all sources
        sources = [chunks[0]['metadata'].get('source', '')]
        for chunk in chunks[1:]:
            source = chunk['metadata'].get('source', '')
            if source and source not in sources:
                sources.append(source)
        
        merged['sources'] = sources
        merged['duplicate_count'] = len(chunks)
        
        return merged


# Example usage
if __name__ == "__main__":
    # Initialize chunker
    chunker = AdvancedSemanticChunker(
        similarity_threshold=0.7,
        min_chunk_size=100,
        max_chunk_size=1000
    )
    
    # Sample text
    text = """
    Data mining is the process of discovering patterns in large data sets.
    It involves methods at the intersection of machine learning, statistics, and database systems.
    
    Classification is a supervised learning task. The goal is to predict the class label of new instances.
    Common algorithms include decision trees, random forests, and neural networks.
    
    Clustering is an unsupervised learning task. It groups similar objects together.
    Popular algorithms are K-means, DBSCAN, and hierarchical clustering.
    """
    
    # Chunk document
    chunks = chunker.chunk_document(
        text,
        metadata={'source': 'textbook.pdf', 'page': 1}
    )
    
    # Print results
    for i, chunk in enumerate(chunks):
        print(f"\n=== Chunk {i} ===")
        print(f"Text: {chunk['text'][:100]}...")
        print(f"Metadata: {chunk['metadata']}")
