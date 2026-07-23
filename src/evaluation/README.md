# 📊 RAG Evaluation System

## ✅ Status: COMPLETE

## 📋 Overview

Hệ thống đánh giá chất lượng RAG hoàn chỉnh với retrieval metrics, generation metrics, citation metrics, automatic benchmarking, và visualization.

---

## 🎨 Features

### 1. Retrieval Metrics
- **Precision@K**: Tỷ lệ documents liên quan trong top-K
- **Recall@K**: Tỷ lệ documents liên quan được retrieve
- **MRR (Mean Reciprocal Rank)**: Trung bình reciprocal rank
- **NDCG (Normalized Discounted Cumulative Gain)**: Chất lượng ranking
- **Hit Rate@K**: Tỷ lệ queries có ít nhất 1 doc liên quan

### 2. Generation Metrics
- **BLEU**: N-gram overlap (machine translation quality)
- **ROUGE**: Recall-oriented n-gram overlap (summarization)
- **BERTScore**: Semantic similarity using BERT embeddings
- **Semantic Similarity**: Cosine similarity of embeddings

### 3. Citation Metrics
- **Citation Accuracy**: Độ chính xác của citations
- **Source Relevance**: Độ liên quan của sources
- **Hallucination Detection**: Phát hiện claims không được support
- **Citation Coverage**: Tỷ lệ answer có citations

### 4. Benchmarking
- Automatic benchmarking pipeline
- Experiment tracking
- Performance comparison
- Visualization (matplotlib charts)
- Export (CSV, JSON, PDF)

---

## 📦 Structure

```
evaluation/
├── __init__.py              # Package initialization
├── retrieval_eval.py        # Retrieval metrics
├── generation_eval.py       # Generation metrics
├── citation_eval.py         # Citation metrics
├── benchmark.py             # Benchmark system
├── dataset.json             # Test dataset
├── README.md                # This file
└── results/                 # Output directory
    ├── *.json               # JSON results
    ├── *.csv                # CSV results
    └── *.png                # Visualizations
```

---

## 🚀 Usage

### 1. Basic Usage

#### Retrieval Evaluation
```python
from evaluation import RetrievalEvaluator

evaluator = RetrievalEvaluator()

# Single query
metrics = evaluator.evaluate_query(
    retrieved=['doc1', 'doc2', 'doc3'],
    relevant={'doc1', 'doc3'},
    relevance_scores={'doc1': 1.0, 'doc3': 0.8},
    k_values=[1, 3, 5]
)

evaluator.print_metrics(metrics)
```

#### Generation Evaluation
```python
from evaluation import GenerationEvaluator

evaluator = GenerationEvaluator()

# Evaluate generation
metrics = evaluator.evaluate_generation(
    generated="Data mining discovers patterns in datasets.",
    reference="Data mining is the process of discovering patterns."
)

evaluator.print_metrics(metrics)
```

#### Citation Evaluation
```python
from evaluation import CitationEvaluator

evaluator = CitationEvaluator()

# Evaluate citations
metrics = evaluator.evaluate_citations(
    answer="Data mining discovers patterns [1].",
    query="What is data mining?",
    citations=[{'id': '1', 'claim': 'Data mining discovers patterns'}],
    sources={'1': 'Data mining is the process...'}
)

evaluator.print_metrics(metrics)
```

### 2. Complete Benchmark

```python
from evaluation import RAGBenchmark

# Create benchmark
benchmark = RAGBenchmark(
    dataset_path="evaluation/dataset.json",
    output_dir="evaluation/results"
)

# Define RAG system
def my_rag_system(query):
    # Your RAG implementation
    answer = "..."
    retrieved_docs = ['doc1', 'doc2', 'doc3']
    sources = {'doc1': '...', 'doc2': '...', 'doc3': '...'}
    return answer, retrieved_docs, sources

# Run benchmark
metrics = benchmark.run_benchmark(
    rag_system=my_rag_system,
    experiment_name="my_experiment",
    k_values=[1, 3, 5],
    verbose=True
)

# Visualize results
benchmark.visualize_results(metrics)

# Compare experiments
comparison = benchmark.compare_experiments()
```

---

## 📊 Metrics Explanation

### Retrieval Metrics

#### Precision@K
```
Precision@K = (# relevant docs in top-K) / K
```
- Measures accuracy of top-K results
- Higher = better quality
- Range: 0.0 to 1.0

#### Recall@K
```
Recall@K = (# relevant docs in top-K) / (# total relevant docs)
```
- Measures coverage of relevant docs
- Higher = more complete
- Range: 0.0 to 1.0

#### MRR (Mean Reciprocal Rank)
```
MRR = 1 / (rank of first relevant document)
```
- Measures how quickly relevant docs appear
- Higher = better ranking
- Range: 0.0 to 1.0

#### NDCG@K (Normalized Discounted Cumulative Gain)
```
DCG@K = Σ (relevance_i / log2(i + 1))
NDCG@K = DCG@K / IDCG@K
```
- Measures ranking quality with graded relevance
- Considers position and relevance score
- Range: 0.0 to 1.0

#### Hit Rate@K
```
Hit Rate@K = 1 if any relevant doc in top-K, else 0
```
- Binary measure of success
- Range: 0.0 or 1.0

### Generation Metrics

#### BLEU (Bilingual Evaluation Understudy)
```
BLEU = BP * exp(Σ w_n * log(p_n))
```
- Measures n-gram overlap with reference
- Originally for machine translation
- Range: 0.0 to 1.0

#### ROUGE (Recall-Oriented Understudy for Gisting Evaluation)
```
ROUGE-N = (# overlapping n-grams) / (# n-grams in reference)
```
- Measures recall of n-grams
- ROUGE-1: unigrams
- ROUGE-2: bigrams
- ROUGE-L: longest common subsequence
- Range: 0.0 to 1.0

#### BERTScore
```
BERTScore = cosine_similarity(BERT(generated), BERT(reference))
```
- Semantic similarity using BERT embeddings
- More robust than n-gram metrics
- Range: 0.0 to 1.0

#### Semantic Similarity
```
Similarity = cosine_similarity(embed(generated), embed(reference))
```
- Cosine similarity of sentence embeddings
- Captures semantic meaning
- Range: 0.0 to 1.0

### Citation Metrics

#### Citation Accuracy
```
Accuracy = (# correct citations) / (# total citations)
```
- Measures correctness of citations
- Citation is correct if source supports claim
- Range: 0.0 to 1.0

#### Source Relevance
```
Relevance = token_overlap(query, source) / union(query, source)
```
- Measures relevance of cited sources to query
- Uses Jaccard similarity
- Range: 0.0 to 1.0

#### Hallucination Rate
```
Hallucination Rate = (# unsupported sentences) / (# total sentences)
```
- Measures claims not supported by sources
- Lower = better (less hallucination)
- Range: 0.0 to 1.0

#### Citation Coverage
```
Coverage = (# cited sentences) / (# total sentences)
```
- Measures percentage of answer with citations
- Higher = more transparent
- Range: 0.0 to 1.0

---

## 📈 Benchmark Results

### Example Output

```
============================================================
📊 BENCHMARK RESULTS: my_experiment
============================================================
Execution time: 23.18s
Dataset size: 5

📚 RETRIEVAL METRICS:
   Precision@1: 0.8000
   Recall@1: 0.2667
   NDCG@1: 0.8000
   Precision@3: 0.7333
   Recall@3: 0.7333
   NDCG@3: 0.7865
   MRR: 0.8667

📝 GENERATION METRICS:
   BLEU: 0.4240
   ROUGE-1: 0.6858
   ROUGE-2: 0.4866
   ROUGE-L: 0.6584
   Semantic Similarity: 0.8638

📚 CITATION METRICS:
   Citation Accuracy: 0.9000
   Source Relevance: 0.7500
   Hallucination Rate: 0.1000
   Citation Coverage: 0.8500
============================================================
```

### Visualization

The benchmark generates charts showing:
1. **Retrieval Metrics @K** - Bar chart comparing Precision, Recall, NDCG
2. **Generation Metrics** - Bar chart of BLEU, ROUGE, Semantic Similarity
3. **Citation Metrics** - Bar chart of Accuracy, Relevance, Support Rate, Coverage
4. **Overall Summary** - Text summary of top metrics

---

## 🧪 Testing

### Run Individual Tests

```bash
# Test retrieval evaluator
python -m evaluation.retrieval_eval

# Test generation evaluator
python -m evaluation.generation_eval

# Test citation evaluator
python -m evaluation.citation_eval

# Test benchmark system
python -m evaluation.benchmark
```

### Test Results
- ✅ Retrieval Evaluator: PASSED
- ✅ Generation Evaluator: PASSED
- ✅ Citation Evaluator: PASSED
- ✅ Benchmark System: PASSED

---

## 📝 Dataset Format

### dataset.json Structure

```json
[
  {
    "id": "q1",
    "query": "What is data mining?",
    "reference_answer": "Data mining is...",
    "relevant_docs": ["doc1", "doc2"],
    "relevance_scores": {
      "doc1": 1.0,
      "doc2": 0.9
    },
    "sources": {
      "doc1": "Source text...",
      "doc2": "Source text..."
    }
  }
]
```

### Fields
- **id**: Unique query identifier
- **query**: Question/query text
- **reference_answer**: Ground truth answer
- **relevant_docs**: List of relevant document IDs
- **relevance_scores**: Dict mapping doc_id to relevance (0.0-1.0)
- **sources**: Dict mapping doc_id to source text

---

## 🔧 Configuration

### Benchmark Parameters

```python
benchmark = RAGBenchmark(
    dataset_path="evaluation/dataset.json",  # Test dataset
    output_dir="evaluation/results"          # Output directory
)

metrics = benchmark.run_benchmark(
    rag_system=my_rag_system,      # RAG function
    experiment_name="exp1",         # Experiment name
    k_values=[1, 3, 5, 10],        # K values for metrics
    verbose=True                    # Print progress
)
```

### Visualization Options

```python
benchmark.visualize_results(
    metrics=metrics,
    save_path="my_results.png"  # Custom save path
)
```

---

## 📊 Export Formats

### JSON Export
```json
{
  "experiment_name": "my_experiment",
  "timestamp": "2026-05-09T01:16:07",
  "dataset_size": 5,
  "execution_time": 23.18,
  "retrieval": {
    "precision@3": 0.7333,
    "recall@3": 0.7333,
    ...
  },
  "generation": {
    "bleu": 0.4240,
    "rouge-1": 0.6858,
    ...
  },
  "citation": {
    "citation_accuracy": 0.9000,
    ...
  }
}
```

### CSV Export
```csv
Metric Category,Metric Name,Value,Std Dev
Retrieval,precision@3,0.7333,0.1247
Retrieval,recall@3,0.7333,0.1247
Generation,bleu,0.4240,0.0856
...
```

---

## 🎯 Best Practices

### 1. Dataset Preparation
- Include diverse queries
- Provide accurate ground truth
- Use graded relevance scores (0.0-1.0)
- Include multiple relevant documents per query

### 2. Experiment Tracking
- Use descriptive experiment names
- Run multiple experiments for comparison
- Track configuration changes
- Document modifications

### 3. Metric Interpretation
- **Precision@3 > 0.7**: Good retrieval quality
- **Recall@3 > 0.6**: Good coverage
- **MRR > 0.8**: Excellent ranking
- **BLEU > 0.4**: Good generation quality
- **ROUGE-1 > 0.6**: Good content overlap
- **Semantic Similarity > 0.8**: High semantic match
- **Citation Accuracy > 0.9**: Excellent citation quality
- **Hallucination Rate < 0.2**: Low hallucination

### 4. Optimization
- Focus on metrics relevant to your use case
- Balance precision vs recall
- Optimize for user experience
- Monitor hallucination rate

---

## 🔍 Troubleshooting

### Issue: Low Retrieval Metrics
**Solutions**:
- Improve embedding quality
- Tune hybrid search weights
- Add reranking
- Expand document corpus

### Issue: Low Generation Metrics
**Solutions**:
- Improve prompt engineering
- Use better LLM model
- Provide more context
- Fine-tune generation parameters

### Issue: High Hallucination Rate
**Solutions**:
- Add citation requirements
- Implement fact-checking
- Use cross-encoder reranking
- Filter low-relevance sources

### Issue: Slow Benchmarking
**Solutions**:
- Reduce dataset size
- Use batch processing
- Cache embeddings
- Optimize RAG pipeline

---

## 📚 Dependencies

```txt
numpy>=1.24.3
sentence-transformers>=2.2.2
torch>=2.0.0
matplotlib>=3.5.0
scikit-learn>=1.0.0
```

---

## ✅ Completion Checklist

- [x] Implement RetrievalEvaluator (Precision, Recall, MRR, NDCG, Hit Rate)
- [x] Implement GenerationEvaluator (BLEU, ROUGE, BERTScore, Semantic Similarity)
- [x] Implement CitationEvaluator (Accuracy, Relevance, Hallucination, Coverage)
- [x] Create RAGBenchmark system
- [x] Add automatic benchmarking
- [x] Add experiment tracking
- [x] Add visualization (matplotlib charts)
- [x] Add export (CSV, JSON)
- [x] Create test dataset
- [x] Test all modules (4/4 PASSED)
- [x] Create documentation
- [x] Production-ready code

---

## 🎓 References

### Metrics
- **BLEU**: Papineni et al. (2002) - "BLEU: a Method for Automatic Evaluation of Machine Translation"
- **ROUGE**: Lin (2004) - "ROUGE: A Package for Automatic Evaluation of Summaries"
- **BERTScore**: Zhang et al. (2020) - "BERTScore: Evaluating Text Generation with BERT"
- **NDCG**: Järvelin & Kekäläinen (2002) - "Cumulated gain-based evaluation of IR techniques"

### Libraries
- **sentence-transformers**: https://www.sbert.net/
- **matplotlib**: https://matplotlib.org/
- **scikit-learn**: https://scikit-learn.org/

---

**Status**: ✅ Production-ready  
**Date**: 2026-05-09  
**Version**: 1.0.0
