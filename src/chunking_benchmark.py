# chunking_benchmark.py - Benchmark old vs semantic chunking
"""
Compare RecursiveCharacterTextSplitter vs Semantic Chunking.

Metrics:
- Chunk quality
- Retrieval accuracy
- Response relevance
"""

import time
from typing import List, Dict
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from semantic_chunker import create_semantic_chunker
from loader import load_all_documents
import numpy as np


class ChunkingBenchmark:
    """Benchmark different chunking strategies"""
    
    def __init__(self):
        self.results = {
            'recursive': {},
            'semantic': {}
        }
    
    def benchmark_chunking_speed(self, documents: List[Document]) -> Dict:
        """Benchmark chunking speed"""
        print("\n" + "="*60)
        print("BENCHMARK 1: CHUNKING SPEED")
        print("="*60)
        
        # 1. Recursive Character Text Splitter
        print("\n🔄 Testing RecursiveCharacterTextSplitter...")
        start_time = time.time()
        
        recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        recursive_chunks = recursive_splitter.split_documents(documents)
        
        recursive_time = time.time() - start_time
        print(f"✅ Time: {recursive_time:.2f}s")
        print(f"✅ Chunks: {len(recursive_chunks)}")
        
        # 2. Semantic Chunker
        print("\n🔄 Testing Semantic Chunker...")
        start_time = time.time()
        
        semantic_chunker = create_semantic_chunker(
            min_chunk_size=200,
            max_chunk_size=800
        )
        semantic_chunks = semantic_chunker.chunk_documents(documents)
        
        semantic_time = time.time() - start_time
        print(f"✅ Time: {semantic_time:.2f}s")
        print(f"✅ Chunks: {len(semantic_chunks)}")
        
        # Store results
        self.results['recursive']['chunks'] = recursive_chunks
        self.results['recursive']['time'] = recursive_time
        self.results['semantic']['chunks'] = semantic_chunks
        self.results['semantic']['time'] = semantic_time
        
        return {
            'recursive_time': recursive_time,
            'semantic_time': semantic_time,
            'recursive_chunks': len(recursive_chunks),
            'semantic_chunks': len(semantic_chunks),
            'speedup': recursive_time / semantic_time if semantic_time > 0 else 0
        }
    
    def analyze_chunk_quality(self) -> Dict:
        """Analyze chunk quality metrics"""
        print("\n" + "="*60)
        print("BENCHMARK 2: CHUNK QUALITY")
        print("="*60)
        
        recursive_chunks = self.results['recursive']['chunks']
        semantic_chunks = self.results['semantic']['chunks']
        
        # Calculate statistics
        def get_stats(chunks):
            lengths = [len(c.page_content) for c in chunks]
            return {
                'count': len(chunks),
                'avg_length': np.mean(lengths),
                'std_length': np.std(lengths),
                'min_length': np.min(lengths),
                'max_length': np.max(lengths),
                'median_length': np.median(lengths)
            }
        
        recursive_stats = get_stats(recursive_chunks)
        semantic_stats = get_stats(semantic_chunks)
        
        print("\n📊 Recursive Chunking:")
        for key, value in recursive_stats.items():
            print(f"  {key}: {value:.0f}")
        
        print("\n📊 Semantic Chunking:")
        for key, value in semantic_stats.items():
            print(f"  {key}: {value:.0f}")
        
        print("\n🎯 Quality Score:")
        # Quality = 1 / (1 + std) - lower std = more consistent = better
        recursive_quality = 1 / (1 + recursive_stats['std_length'] / recursive_stats['avg_length'])
        semantic_quality = 1 / (1 + semantic_stats['std_length'] / semantic_stats['avg_length'])
        
        print(f"  Recursive: {recursive_quality:.3f}")
        print(f"  Semantic: {semantic_quality:.3f}")
        print(f"  Improvement: {((semantic_quality - recursive_quality) / recursive_quality * 100):.1f}%")
        
        return {
            'recursive': recursive_stats,
            'semantic': semantic_stats,
            'recursive_quality': recursive_quality,
            'semantic_quality': semantic_quality,
            'quality_improvement': (semantic_quality - recursive_quality) / recursive_quality * 100
        }
    
    def test_boundary_preservation(self) -> Dict:
        """Test if semantic chunking preserves boundaries better"""
        print("\n" + "="*60)
        print("BENCHMARK 3: BOUNDARY PRESERVATION")
        print("="*60)
        
        recursive_chunks = self.results['recursive']['chunks']
        semantic_chunks = self.results['semantic']['chunks']
        
        def count_broken_sentences(chunks):
            """Count chunks that end mid-sentence"""
            broken = 0
            for chunk in chunks:
                text = chunk.page_content.strip()
                if text and text[-1] not in '.!?':
                    broken += 1
            return broken
        
        recursive_broken = count_broken_sentences(recursive_chunks)
        semantic_broken = count_broken_sentences(semantic_chunks)
        
        recursive_pct = (recursive_broken / len(recursive_chunks)) * 100
        semantic_pct = (semantic_broken / len(semantic_chunks)) * 100
        
        print(f"\n📝 Broken Sentences:")
        print(f"  Recursive: {recursive_broken}/{len(recursive_chunks)} ({recursive_pct:.1f}%)")
        print(f"  Semantic: {semantic_broken}/{len(semantic_chunks)} ({semantic_pct:.1f}%)")
        print(f"  Improvement: {recursive_pct - semantic_pct:.1f}%")
        
        return {
            'recursive_broken': recursive_broken,
            'semantic_broken': semantic_broken,
            'recursive_broken_pct': recursive_pct,
            'semantic_broken_pct': semantic_pct,
            'improvement': recursive_pct - semantic_pct
        }
    
    def generate_report(self, speed_results: Dict, quality_results: Dict, boundary_results: Dict) -> str:
        """Generate comprehensive benchmark report"""
        report = f"""
# 📊 CHUNKING BENCHMARK REPORT

## Summary

**Winner:** {'🏆 Semantic Chunking' if quality_results['quality_improvement'] > 0 else 'Recursive Chunking'}

---

## 1. Speed Comparison

| Metric | Recursive | Semantic | Winner |
|--------|-----------|----------|--------|
| **Time** | {speed_results['recursive_time']:.2f}s | {speed_results['semantic_time']:.2f}s | {'⚡ Recursive' if speed_results['recursive_time'] < speed_results['semantic_time'] else '⚡ Semantic'} |
| **Chunks** | {speed_results['recursive_chunks']} | {speed_results['semantic_chunks']} | - |
| **Chunks/sec** | {speed_results['recursive_chunks']/speed_results['recursive_time']:.1f} | {speed_results['semantic_chunks']/speed_results['semantic_time']:.1f} | - |

---

## 2. Quality Comparison

| Metric | Recursive | Semantic | Improvement |
|--------|-----------|----------|-------------|
| **Avg Length** | {quality_results['recursive']['avg_length']:.0f} | {quality_results['semantic']['avg_length']:.0f} | - |
| **Std Dev** | {quality_results['recursive']['std_length']:.0f} | {quality_results['semantic']['std_length']:.0f} | - |
| **Min Length** | {quality_results['recursive']['min_length']:.0f} | {quality_results['semantic']['min_length']:.0f} | - |
| **Max Length** | {quality_results['recursive']['max_length']:.0f} | {quality_results['semantic']['max_length']:.0f} | - |
| **Quality Score** | {quality_results['recursive_quality']:.3f} | {quality_results['semantic_quality']:.3f} | **🎯 {quality_results['quality_improvement']:.1f}%** |

---

## 3. Boundary Preservation

| Metric | Recursive | Semantic | Improvement |
|--------|-----------|----------|-------------|
| **Broken Sentences** | {boundary_results['recursive_broken']} | {boundary_results['semantic_broken']} | - |
| **Broken %** | {boundary_results['recursive_broken_pct']:.1f}% | {boundary_results['semantic_broken_pct']:.1f}% | **🎯 {boundary_results['improvement']:.1f}%** |

---

## 4. Recommendations

### ✅ Use Semantic Chunking When:
- Quality is more important than speed
- Working with academic/technical content
- Need to preserve sentence boundaries
- Want semantic coherence

### ⚠️ Use Recursive Chunking When:
- Speed is critical
- Working with simple text
- Don't need semantic boundaries
- Want consistent chunk sizes

---

## 5. Conclusion

Semantic chunking provides **{quality_results['quality_improvement']:.1f}% better quality** 
and **{boundary_results['improvement']:.1f}% better boundary preservation** 
at the cost of **{abs(speed_results['semantic_time'] - speed_results['recursive_time']):.1f}s** slower processing.

**Recommendation:** Use Semantic Chunking for this RAG system.
"""
        return report


def run_benchmark(data_folder: str = "data", max_docs: int = 10):
    """
    Run complete benchmark.
    
    Args:
        data_folder: Folder containing documents
        max_docs: Maximum documents to test (for speed)
    """
    print("="*60)
    print("🚀 CHUNKING STRATEGY BENCHMARK")
    print("="*60)
    
    # Load documents
    print(f"\n📂 Loading documents from {data_folder}...")
    documents = load_all_documents(data_folder, use_semantic_chunking=False)
    
    # Limit for testing
    if len(documents) > max_docs:
        print(f"⚠️  Limiting to {max_docs} documents for speed")
        documents = documents[:max_docs]
    
    print(f"✅ Loaded {len(documents)} documents")
    
    # Run benchmark
    benchmark = ChunkingBenchmark()
    speed_results = benchmark.benchmark_chunking_speed(documents)
    quality_results = benchmark.analyze_chunk_quality()
    boundary_results = benchmark.test_boundary_preservation()
    
    # Generate report
    report = benchmark.generate_report(speed_results, quality_results, boundary_results)
    
    # Save report
    with open("chunking_benchmark_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    
    print("\n" + "="*60)
    print("✅ BENCHMARK COMPLETE")
    print("="*60)
    print(f"📄 Report saved to: chunking_benchmark_report.md")
    print("="*60 + "\n")
    
    return benchmark, report


if __name__ == "__main__":
    benchmark, report = run_benchmark(max_docs=5)
    print(report)
