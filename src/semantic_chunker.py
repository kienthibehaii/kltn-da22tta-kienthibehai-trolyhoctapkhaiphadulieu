# semantic_chunker.py - Advanced Semantic Chunking for RAG
"""
Semantic Chunking Strategy optimized for academic PDFs and lecture slides.

Features:
- Sentence boundary detection
- Semantic similarity-based splitting
- Preserves tables, formulas, code blocks, headings
- Optimized for Data Mining educational content
"""

import re
from typing import List, Dict, Tuple
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_experimental.text_splitter import SemanticChunker
import numpy as np


class AcademicSemanticChunker:
    """
    Advanced semantic chunker optimized for academic content.
    
    Preserves:
    - Tables
    - Mathematical formulas
    - Code blocks
    - Headings and sections
    - Figure captions
    """
    
    def __init__(self, 
                 min_chunk_size: int = 200,
                 max_chunk_size: int = 800,
                 breakpoint_threshold_type: str = "percentile",
                 breakpoint_threshold_amount: float = 95):
        """
        Initialize semantic chunker.
        
        Args:
            min_chunk_size: Minimum characters per chunk
            max_chunk_size: Maximum characters per chunk
            breakpoint_threshold_type: "percentile", "standard_deviation", or "interquartile"
            breakpoint_threshold_amount: Threshold value (95 for percentile)
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.breakpoint_threshold_type = breakpoint_threshold_type
        self.breakpoint_threshold_amount = breakpoint_threshold_amount
        
        # Initialize embeddings
        print("🔄 Initializing embeddings for semantic chunking...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # Initialize LangChain SemanticChunker
        self.semantic_splitter = SemanticChunker(
            self.embeddings,
            breakpoint_threshold_type=breakpoint_threshold_type,
            breakpoint_threshold_amount=breakpoint_threshold_amount
        )
        
        print("✅ Semantic chunker initialized")
    
    def _detect_special_blocks(self, text: str) -> List[Dict]:
        """
        Detect special blocks that should not be split.
        
        Returns list of {type, start, end, content}
        """
        special_blocks = []
        
        # 1. Detect tables (simple heuristic)
        table_pattern = r'(\|[^\n]+\|[\s\S]*?\|[^\n]+\|)'
        for match in re.finditer(table_pattern, text):
            special_blocks.append({
                'type': 'table',
                'start': match.start(),
                'end': match.end(),
                'content': match.group(0)
            })
        
        # 2. Detect code blocks
        code_pattern = r'```[\s\S]*?```|`[^`]+`'
        for match in re.finditer(code_pattern, text):
            special_blocks.append({
                'type': 'code',
                'start': match.start(),
                'end': match.end(),
                'content': match.group(0)
            })
        
        # 3. Detect mathematical formulas
        # LaTeX inline: $...$
        # LaTeX display: $$...$$
        formula_pattern = r'\$\$[\s\S]*?\$\$|\$[^\$]+\$'
        for match in re.finditer(formula_pattern, text):
            special_blocks.append({
                'type': 'formula',
                'start': match.start(),
                'end': match.end(),
                'content': match.group(0)
            })
        
        # 4. Detect headings (markdown style)
        heading_pattern = r'^#{1,6}\s+.+$'
        for match in re.finditer(heading_pattern, text, re.MULTILINE):
            special_blocks.append({
                'type': 'heading',
                'start': match.start(),
                'end': match.end(),
                'content': match.group(0)
            })
        
        # 5. Detect figure captions
        caption_pattern = r'(Figure|Fig\.|Table)\s+\d+[:\.].*?(?=\n\n|\n[A-Z]|$)'
        for match in re.finditer(caption_pattern, text, re.IGNORECASE):
            special_blocks.append({
                'type': 'caption',
                'start': match.start(),
                'end': match.end(),
                'content': match.group(0)
            })
        
        # Sort by start position
        special_blocks.sort(key=lambda x: x['start'])
        
        return special_blocks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences with academic-aware rules.
        """
        # Handle abbreviations common in academic text
        text = re.sub(r'Dr\.', 'Dr<DOT>', text)
        text = re.sub(r'Prof\.', 'Prof<DOT>', text)
        text = re.sub(r'Fig\.', 'Fig<DOT>', text)
        text = re.sub(r'et al\.', 'et al<DOT>', text)
        text = re.sub(r'i\.e\.', 'i<DOT>e<DOT>', text)
        text = re.sub(r'e\.g\.', 'e<DOT>g<DOT>', text)
        
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        
        # Restore abbreviations
        sentences = [s.replace('<DOT>', '.') for s in sentences]
        
        return [s.strip() for s in sentences if s.strip()]
    
    def _merge_small_chunks(self, chunks: List[str]) -> List[str]:
        """
        Merge chunks that are too small.
        """
        merged = []
        current = ""
        
        for chunk in chunks:
            if len(current) + len(chunk) < self.min_chunk_size:
                current += " " + chunk if current else chunk
            else:
                if current:
                    merged.append(current)
                current = chunk
        
        if current:
            merged.append(current)
        
        return merged
    
    def _split_large_chunks(self, chunks: List[str]) -> List[str]:
        """
        Split chunks that are too large.
        """
        result = []
        
        for chunk in chunks:
            if len(chunk) <= self.max_chunk_size:
                result.append(chunk)
            else:
                # Split by paragraphs first
                paragraphs = chunk.split('\n\n')
                current = ""
                
                for para in paragraphs:
                    if len(current) + len(para) <= self.max_chunk_size:
                        current += "\n\n" + para if current else para
                    else:
                        if current:
                            result.append(current)
                        
                        # If single paragraph is too large, split by sentences
                        if len(para) > self.max_chunk_size:
                            sentences = self._split_into_sentences(para)
                            temp = ""
                            for sent in sentences:
                                if len(temp) + len(sent) <= self.max_chunk_size:
                                    temp += " " + sent if temp else sent
                                else:
                                    if temp:
                                        result.append(temp)
                                    temp = sent
                            if temp:
                                result.append(temp)
                        else:
                            current = para
                
                if current:
                    result.append(current)
        
        return result
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Chunk text using semantic similarity with special block preservation.
        
        Args:
            text: Input text
            
        Returns:
            List of text chunks
        """
        # 1. Detect special blocks
        special_blocks = self._detect_special_blocks(text)
        
        # 2. Split text around special blocks
        chunks = []
        last_end = 0
        
        for block in special_blocks:
            # Add text before special block
            if block['start'] > last_end:
                before_text = text[last_end:block['start']].strip()
                if before_text:
                    # Use semantic chunking for regular text
                    try:
                        semantic_chunks = self.semantic_splitter.split_text(before_text)
                        chunks.extend(semantic_chunks)
                    except:
                        # Fallback to sentence splitting
                        sentences = self._split_into_sentences(before_text)
                        chunks.extend(sentences)
            
            # Add special block as single chunk
            chunks.append(block['content'])
            last_end = block['end']
        
        # Add remaining text
        if last_end < len(text):
            remaining_text = text[last_end:].strip()
            if remaining_text:
                try:
                    semantic_chunks = self.semantic_splitter.split_text(remaining_text)
                    chunks.extend(semantic_chunks)
                except:
                    sentences = self._split_into_sentences(remaining_text)
                    chunks.extend(sentences)
        
        # 3. Post-process: merge small and split large chunks
        chunks = self._merge_small_chunks(chunks)
        chunks = self._split_large_chunks(chunks)
        
        return chunks
    
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Chunk a list of documents.
        
        Args:
            documents: List of LangChain Documents
            
        Returns:
            List of chunked Documents with preserved metadata
        """
        chunked_docs = []
        
        for doc in documents:
            text = doc.page_content
            metadata = doc.metadata.copy()
            
            # Chunk the text
            chunks = self.chunk_text(text)
            
            # Create new documents for each chunk
            for i, chunk in enumerate(chunks):
                chunk_metadata = metadata.copy()
                chunk_metadata['chunk_index'] = i
                chunk_metadata['total_chunks'] = len(chunks)
                chunk_metadata['chunk_method'] = 'semantic'
                
                chunked_docs.append(Document(
                    page_content=chunk,
                    metadata=chunk_metadata
                ))
        
        return chunked_docs
    
    def get_chunk_statistics(self, chunks: List[Document]) -> Dict:
        """
        Get statistics about chunks.
        
        Returns:
            Dictionary with statistics
        """
        lengths = [len(chunk.page_content) for chunk in chunks]
        
        stats = {
            'total_chunks': len(chunks),
            'avg_length': np.mean(lengths) if lengths else 0,
            'min_length': np.min(lengths) if lengths else 0,
            'max_length': np.max(lengths) if lengths else 0,
            'std_length': np.std(lengths) if lengths else 0,
            'median_length': np.median(lengths) if lengths else 0,
            'chunks_below_min': sum(1 for l in lengths if l < self.min_chunk_size),
            'chunks_above_max': sum(1 for l in lengths if l > self.max_chunk_size),
        }
        
        return stats


def create_semantic_chunker(min_chunk_size: int = 200,
                            max_chunk_size: int = 800,
                            breakpoint_threshold_type: str = "percentile",
                            breakpoint_threshold_amount: float = 95) -> AcademicSemanticChunker:
    """
    Factory function to create semantic chunker.
    
    Args:
        min_chunk_size: Minimum characters per chunk
        max_chunk_size: Maximum characters per chunk
        breakpoint_threshold_type: Type of threshold
        breakpoint_threshold_amount: Threshold value
        
    Returns:
        AcademicSemanticChunker instance
    """
    return AcademicSemanticChunker(
        min_chunk_size=min_chunk_size,
        max_chunk_size=max_chunk_size,
        breakpoint_threshold_type=breakpoint_threshold_type,
        breakpoint_threshold_amount=breakpoint_threshold_amount
    )


# Test code
if __name__ == "__main__":
    print("=" * 60)
    print("TESTING SEMANTIC CHUNKER")
    print("=" * 60)
    
    # Sample academic text
    sample_text = """
    # Chapter 1: Introduction to Data Mining
    
    Data mining is the process of discovering patterns in large data sets. 
    It involves methods at the intersection of machine learning, statistics, 
    and database systems.
    
    ## 1.1 What is Data Mining?
    
    Data mining, also known as knowledge discovery in databases (KDD), 
    is the process of extracting useful information from data. The main 
    goal is to find patterns that are:
    
    - Valid: hold on new data
    - Novel: non-obvious to the system
    - Useful: actionable
    - Understandable: humans can interpret
    
    Table 1.1: Data Mining Tasks
    |------|-------------|---------|
    | Task | Description | Example |
    | Classification | Predict category | Spam detection |
    | Clustering | Group similar items | Customer segmentation |
    
    The formula for entropy is: $H(X) = -\\sum p(x) \\log p(x)$
    
    Figure 1.1: Data mining process showing the steps from data collection 
    to knowledge discovery.
    """
    
    # Create chunker
    print("\n# Create chunker")
    chunker = create_semantic_chunker(
        min_chunk_size=100,
        max_chunk_size=400
    )
    
    # Chunk text
    print("\n# Chunk text")
    chunks = chunker.chunk_text(sample_text)
    print(f"\n✅ Created {len(chunks)} chunks\n")
    
    for i, chunk in enumerate(chunks, 1):
        print(f"Chunk {i} ({len(chunk)} chars):")
        print(f"{chunk[:100]}...")
        print("-" * 60)
    
    # Test with documents
    print("\n# Test with documents")
    doc = Document(
        page_content=sample_text,
        metadata={'source': 'test.pdf', 'page': 1}
    )
    
    chunked_docs = chunker.chunk_documents([doc])
    stats = chunker.get_chunk_statistics(chunked_docs)
    
    print("\n📊 Chunk Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}") 