"""
Test the new _fast_route_query and _compute_answerability logic
to verify the cross-lingual fix works correctly.
"""
import sys
sys.path.insert(0, r'd:\DoAnTotNghiep\DATN\New folder (2)\New folder')
import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
os.chdir(r'd:\DoAnTotNghiep\DATN\New folder (2)\New folder')

# Test 1: _fast_route_query
from rag import _fast_route_query

test_q = "Hãy nêu định nghĩa về Khai phá dữ liệu (Data mining) và liệt kê 3 ứng dụng thực tế của nó trong kinh doanh hoặc đời sống"
result = _fast_route_query(test_q)
print("=" * 70)
print(f"TEST CÂUU HỎI: {test_q[:60]}...")
print(f"Intent: {result['intent']}")
print(f"Target patterns: {result['target_file_pattern']}")
print(f"Số queries tạo ra: {len(result['expanded_queries'])}")
for i, q in enumerate(result['expanded_queries']):
    print(f"  Query {i+1}: {q[:80]}...")
print()

# Test 2: _compute_answerability with mock English docs
from langchain_core.documents import Document
from verification.confidence_score import _compute_answerability

mock_docs = [
    Document(
        page_content="Data mining is the process of discovering patterns, correlations, anomalies, and useful insights from large datasets. Applications include business intelligence, fraud detection, marketing, and customer segmentation.",
        metadata={"source": "DM3.pdf"}
    ),
    Document(
        page_content="Knowledge Discovery in Databases (KDD) involves preprocessing, transformation, data mining, interpretation, and evaluation of patterns. Real-world applications span banking, healthcare, retail, and marketing.",
        metadata={"source": "01Intro.pptx"}
    )
]

score = _compute_answerability(test_q, mock_docs)
print("=" * 70)
print("TEST ANSWERABILITY (VI question vs EN docs):")
print(f"Score: {score:.3f} (mong muốn: >= 0.4)")
print(f"Kết quả: {'PASS ✅' if score >= 0.4 else 'FAIL ❌'}")
print()

# Test 3: Check a simple Vietnamese question score
test_q2 = "Thuật toán K-means hoạt động như thế nào và ứng dụng là gì?"
result2 = _fast_route_query(test_q2)
print("=" * 70)
print(f"TEST 2: {test_q2}")
print(f"Intent: {result2['intent']}")
for i, q in enumerate(result2['expanded_queries']):
    print(f"  Query {i+1}: {q[:80]}")
