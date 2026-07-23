"""Test retrieval/reranker.py pipeline — Top-20 -> Reranker -> Top-5."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from langchain_core.documents import Document
from retrieval.reranker import create_reranker, ScoredDocument

# ── Simulate Top-20 candidates ────────────────────────────────────────────────
docs = [
    Document(page_content="K-Means is a partitioning clustering algorithm that divides data into K clusters by iteratively assigning points to nearest centroid and updating centroids.", metadata={"source_file": "10ClusBasic.pptx", "section": "K-Means", "page_number": 15}),
    Document(page_content="DBSCAN is a density-based clustering algorithm that groups points in high-density regions and marks outliers in low-density regions.", metadata={"source_file": "10ClusBasic.pptx", "section": "DBSCAN", "page_number": 22}),
    Document(page_content="Apriori algorithm mines frequent itemsets using minimum support threshold and anti-monotone property to prune candidates.", metadata={"source_file": "06FPBasic.pptx", "section": "Apriori", "page_number": 5}),
    Document(page_content="Hoc phan Khai pha du lieu - MSHP 220269 - 3 tin chi, hoc ky VI, nganh Tri tue nhan tao.", metadata={"source_file": "220269_AI.docx", "section": "Thong tin chung", "page_number": 1}),
    Document(page_content="Decision Tree uses information gain and entropy to select the best splitting attribute at each node.", metadata={"source_file": "08ClassBasic.pptx", "section": "Decision Tree", "page_number": 10}),
    Document(page_content="The K-Means algorithm requires the number of clusters K to be specified in advance. It minimizes within-cluster sum of squares (WCSS).", metadata={"source_file": "DM3.pdf", "section": "Chapter 10", "page_number": 420}),
    Document(page_content="Random Forest is an ensemble method using bagging of decision trees with random feature selection.", metadata={"source_file": "09ClassAdvanced.pptx", "section": "Random Forest", "page_number": 8}),
    Document(page_content="Support Vector Machine finds the optimal hyperplane that maximizes margin between two classes.", metadata={"source_file": "08ClassBasic.pptx", "section": "SVM", "page_number": 30}),
    Document(page_content="Phuong phap giang day: Dien giang, Van dap, Hoat dong nhom, Hoc dua tren du an.", metadata={"source_file": "220269_AI.docx", "section": "Phuong phap giang day", "page_number": 6}),
    Document(page_content="Silhouette score measures clustering quality by comparing intra-cluster cohesion to inter-cluster separation.", metadata={"source_file": "10ClusBasic.pptx", "section": "Evaluation", "page_number": 40}),
]

query = "K-Means clustering algorithm how does it work"

# Simulate retrieval scores (rank-decay)
n = len(docs)
retrieval_scores = [1.0 - (i / n) for i in range(n)]

# ── Run reranker ──────────────────────────────────────────────────────────────
reranker = create_reranker(retrieval_weight=0.35, rerank_weight=0.65, top_k=5, threshold=0.35)
results = reranker.rerank(query, docs, retrieval_scores=retrieval_scores, verbose=True)

# ── Assertions ────────────────────────────────────────────────────────────────
print("ASSERTIONS:")
assert len(results) >= 1, "Must return at least 1 result"
assert len(results) <= 5, "Must not exceed top_k=5"

# K-Means docs should be in top results
top_sources = [r.source for r in results]
kmeans_found = any('Clus' in s or 'DM3' in s for s in top_sources)
assert kmeans_found, f"K-Means docs should be in top results. Got: {top_sources}"
print(f"  K-Means in top results: {kmeans_found}")

# Syllabus docs should NOT be in top 3 for technical query
top3_sources = [r.source for r in results[:3]]
syllabus_in_top3 = any('220269' in s for s in top3_sources)
assert not syllabus_in_top3, f"Syllabus should not be in top 3 for technical query. Got: {top3_sources}"
print(f"  Syllabus filtered from top 3: OK")

# ScoredDocument has all fields
for r in results:
    assert isinstance(r, ScoredDocument)
    assert 0 <= r.retrieval_score <= 1
    assert 0 <= r.rerank_score <= 1
    assert 0 <= r.final_score <= 1
    assert r.rank_after > 0
    assert r.source != "unknown"
print(f"  All ScoredDocument fields valid: OK")

# backward compat
tuples = reranker.rerank_tuples(query, docs, retrieval_scores=retrieval_scores, top_k=3)
assert all(isinstance(t, tuple) and len(t) == 2 for t in tuples)
print(f"  rerank_tuples() backward compat: OK")

print(f"\nALL ASSERTIONS PASSED")
