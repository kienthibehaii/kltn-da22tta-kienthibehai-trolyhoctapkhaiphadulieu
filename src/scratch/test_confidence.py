"""Test confidence_score.py — không cần backend."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from langchain_core.documents import Document
from verification.confidence_score import (
    compute_confidence, format_confidence_block,
    build_source_block, extract_used_citation_indices,
    W_RETRIEVAL, W_RERANKER, W_CTX_COVERAGE, W_ANSWERABILITY,
)

# ── Mock data ─────────────────────────────────────────────────────────────────
docs_rich = [
    Document(
        page_content="Bài tập lớn chiếm 25% tổng điểm học phần. Kiểm tra lý thuyết chiếm 25%.",
        metadata={
            "source_file": "220269_AI.docx",
            "section": "7. Đánh giá học phần",
            "page_number": 7,
            "final_score": 0.82,
            "rerank_score": 0.78,
            "retrieval_score": 0.90,
        }
    ),
    Document(
        page_content="K-Means yêu cầu xác định trước số cụm K. Centroid cập nhật bằng trung bình.",
        metadata={
            "source_file": "10ClusBasic.pptx",
            "section": "K-Means",
            "page_number": 15,
            "final_score": 0.75,
            "rerank_score": 0.71,
            "retrieval_score": 0.80,
        }
    ),
]

docs_no_meta = [
    Document(page_content="Some content", metadata={"source_file": "file.pdf"}),
]

citations = [
    {"index": 1, "filename": "220269_AI.docx", "relevance_score": 0.82},
    {"index": 2, "filename": "10ClusBasic.pptx", "relevance_score": 0.75},
]

answer_with_cit = "Bài tập lớn chiếm 25% tổng điểm học phần. [1] K-Means yêu cầu xác định số cụm K. [2]"
answer_no_cit = "Đây là câu trả lời không có trích dẫn."
question = "Bài tập lớn chiếm bao nhiêu phần trăm?"

print("=" * 65)

# ── Test 1: Đầy đủ dữ liệu ───────────────────────────────────────────────────
print("\n[Test 1] Full data")
r1 = compute_confidence(
    docs_rich, citations,
    citation_coverage=0.80,
    reranker_scores=[0.78, 0.71],
    question=question,
    answer_text=answer_with_cit,
)
print(f"  available:         {r1.available}")
print(f"  score:             {r1.score}")
print(f"  percent:           {r1.percent}%")
print(f"  label:             {r1.label}")
print(f"  retrieval_score:   {r1.retrieval_score}")
print(f"  reranker_score:    {r1.reranker_score}")
print(f"  context_coverage:  {r1.context_coverage}")
print(f"  answerability:     {r1.answerability_score}")
print(f"  formula:           {r1.formula}")
print(f"  explanation:       {r1.explanation}")
print()
print(format_confidence_block(r1))

# ── Test 2: Không đủ dữ liệu ─────────────────────────────────────────────────
print("\n[Test 2] Insufficient data")
r2 = compute_confidence(
    docs_no_meta, [],
    citation_coverage=0.0,
    reranker_scores=None,
    question=None,
    answer_text=None,
)
print(f"  available: {r2.available}")
print(f"  label:     {r2.label}")
print(format_confidence_block(r2))

# ── Test 3: Không có doc ──────────────────────────────────────────────────────
print("\n[Test 3] No documents")
r3 = compute_confidence([], [], 0.0)
print(f"  available: {r3.available}")
print(f"  label:     {r3.label}")
print(format_confidence_block(r3))

# ── Test 4: Source block ──────────────────────────────────────────────────────
print("\n[Test 4] Source block")
used = extract_used_citation_indices(answer_with_cit)
print(f"  Used indices: {used}")
block = build_source_block(docs_rich, used)
print(block)

# ── Test 5: Answerability ─────────────────────────────────────────────────────
print("\n[Test 5] Answerability")
from verification.confidence_score import _compute_answerability
score = _compute_answerability("Bài tập lớn chiếm bao nhiêu phần trăm?", docs_rich)
print(f"  answerability for relevant question: {score:.3f}")
score2 = _compute_answerability("Thời tiết Hà Nội như thế nào?", docs_rich)
print(f"  answerability for irrelevant question: {score2:.3f}")

# ── Assertions ────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("ASSERTIONS:")

# 1. Weights sum to 1.0
assert abs(W_RETRIEVAL + W_RERANKER + W_CTX_COVERAGE + W_ANSWERABILITY - 1.0) < 1e-9
print("  [1] Weights sum to 1.0: OK")

# 2. Full data → available
assert r1.available, "Full data should be available"
assert 0 < r1.score <= 1, f"Score out of range: {r1.score}"
print(f"  [2] Full data available, score={r1.score}: OK")

# 3. Missing data → Not Available
assert not r2.available
assert r2.label == "Not Available"
print("  [3] Missing data → Not Available: OK")

# 4. No docs → Not Available
assert not r3.available
print("  [4] No docs → Not Available: OK")

# 5. Formula contains actual numbers (not placeholder)
assert r1.formula and "0." in r1.formula, f"Formula invalid: {r1.formula}"
print(f"  [5] Formula has real numbers: OK")

# 6. No fake 0.5 fallback in score when real data exists
if r1.reranker_score is not None:
    assert r1.reranker_score != 0.5 or (r1.reranker_score == 0.5 and
           any(d.metadata.get('rerank_score') == 0.5 for d in docs_rich)), \
        "Should not use fake 0.5 fallback"
print("  [6] No fake 0.5 fallback when real data present: OK")

# 7. Source block only contains used citations
assert "[1]" in block and "[2]" in block
assert "[3]" not in block
print("  [7] Source block contains only used citations: OK")

# 8. Answerability higher for relevant question
assert score > score2, f"Relevant should score higher: {score} vs {score2}"
print(f"  [8] Answerability: relevant({score:.2f}) > irrelevant({score2:.2f}): OK")

# 9. confidence_block output format
conf_text = format_confidence_block(r1)
assert "Độ tin cậy:" in conf_text
assert "Công thức:" in conf_text
assert "Not Available" not in conf_text
print("  [9] Confidence block format correct: OK")

conf_na = format_confidence_block(r3)
assert "Not Available" in conf_na
print("  [10] Not Available block format correct: OK")

print("\nALL ASSERTIONS PASSED")
