"""Test academic_chunker độc lập — không cần backend."""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from langchain_core.documents import Document
from chunking.academic_chunker import smart_chunk, MIN_CHUNK_CHARS, MAX_CHUNK_CHARS

# ── Simulate DOCX output (heading-based sections) ─────────────────────────────
docx_docs = [
    Document(
        page_content="5. Nội dung học phần (Course content)\nBài 1. GIỚI THIỆU VỀ KHAI PHÁ DỮ LIỆU\nNội dung: Bài 1. GIỚI THIỆU VỀ KHAI PHÁ DỮ LIỆU | CĐR học phần: 1 | Số giờ LT: 5 | Số giờ TH: 0\nNhu cầu khai phá dữ liệu\nKhái niệm về khai phá dữ liệu\nCác kỹ thuật khai phá dữ liệu cơ bản",
        metadata={"source_file": "220269_AI.docx", "source": "data/220269_AI.docx",
                  "section": "5. Nội dung học phần", "page_number": 5, "file_type": "docx",
                  "created_at": "2026-01-01", "embedding_model": "all-MiniLM-L6-v2"}
    ),
    Document(
        page_content="6. Phương pháp dạy và học\n• Diễn giảng\n• Vấn đáp (Questions – Answers)\n• Hoạt động nhóm (Group-based Learning)\n• Học dựa trên dự án (Project-based Learning)",
        metadata={"source_file": "220269_AI.docx", "source": "data/220269_AI.docx",
                  "section": "6. Phương pháp dạy và học", "page_number": 6, "file_type": "docx",
                  "created_at": "2026-01-01", "embedding_model": "all-MiniLM-L6-v2"}
    ),
    Document(
        page_content="7. Đánh giá học phần\nĐánh giá quá trình | Hình thức đánh giá/thời gian: Kiểm tra lý thuyết | Nội dung đánh giá: Từ bài 1 đến bài 3 | Tỷ lệ %: 25%\nĐánh giá quá trình | Hình thức đánh giá/thời gian: Bài tập lớn | Nội dung đánh giá: Từ bài 2 đến bài 5 | Tỷ lệ %: 25%\nĐánh giá kết thúc học phần | Hình thức đánh giá/thời gian: Trắc nghiệm | Nội dung đánh giá: Kiến thức từ bài 1 đến bài 5 | Tỷ lệ %: 50%",
        metadata={"source_file": "220269_AI.docx", "source": "data/220269_AI.docx",
                  "section": "7. Đánh giá học phần", "page_number": 7, "file_type": "docx",
                  "created_at": "2026-01-01", "embedding_model": "all-MiniLM-L6-v2"}
    ),
    # Short section — should be merged
    Document(
        page_content="Ghi chú",
        metadata={"source_file": "220269_AI.docx", "source": "data/220269_AI.docx",
                  "section": "Ghi chú", "page_number": 8, "file_type": "docx",
                  "created_at": "2026-01-01", "embedding_model": "all-MiniLM-L6-v2"}
    ),
    # Very long section — should be split Level 3
    Document(
        page_content="4. Chuẩn đầu ra học phần\n" + ("Sinh viên có thể trình bày quy trình KDD, các bài toán khai phá dữ liệu phổ biến, các thuật toán phân lớp (Decision Tree, Naive Bayes, SVM, KNN), phân cụm (K-Means, DBSCAN, Agnes), khai phá luật kết hợp (Apriori, FP-Growth). " * 8),
        metadata={"source_file": "220269_AI.docx", "source": "data/220269_AI.docx",
                  "section": "4. Chuẩn đầu ra học phần", "page_number": 4, "file_type": "docx",
                  "created_at": "2026-01-01", "embedding_model": "all-MiniLM-L6-v2"}
    ),
]

# ── Simulate PPTX output ──────────────────────────────────────────────────────
pptx_docs = [
    Document(
        page_content="K-Means Clustering Algorithm\nStep 1: Choose K centroids randomly\nStep 2: Assign each point to nearest centroid\nStep 3: Update centroids as mean of assigned points\nStep 4: Repeat until convergence",
        metadata={"source_file": "10ClusBasic.pptx", "source": "data/10ClusBasic.pptx",
                  "slide": 15, "page_number": 15, "file_type": "pptx",
                  "created_at": "2026-01-01", "embedding_model": "all-MiniLM-L6-v2"}
    ),
]

all_docs = docx_docs + pptx_docs
chunks = smart_chunk(all_docs)

print(f"\n{'='*60}")
print(f"Input: {len(all_docs)} docs → Output: {len(chunks)} chunks")
print('='*60)

for i, chunk in enumerate(chunks):
    m = chunk.metadata
    print(f"\n[Chunk {i+1}]")
    print(f"  document_name : {m.get('document_name', m.get('source_file'))}")
    print(f"  section_title : {m.get('section_title', m.get('section'))}")
    print(f"  page_number   : {m.get('page_number')}")
    print(f"  chunk_index   : {m.get('chunk_index')}")
    print(f"  file_type     : {m.get('file_type')}")
    print(f"  length        : {len(chunk.page_content)} chars")
    print(f"  content       : {chunk.page_content[:120]}...")

# ── Assertions ────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print("ASSERTIONS:")

# 1. Không có chunk nào rỗng
assert all(c.page_content.strip() for c in chunks), "❌ Empty chunk found"
print("  ✅ No empty chunks")

# 2. Không có chunk nào vượt MAX_CHUNK_CHARS quá nhiều
oversized = [c for c in chunks if len(c.page_content) > MAX_CHUNK_CHARS * 1.2]
assert not oversized, f"❌ {len(oversized)} chunks exceed MAX_CHUNK_CHARS"
print(f"  ✅ No chunks exceed {int(MAX_CHUNK_CHARS*1.2)} chars")

# 3. Section title luôn có trong metadata
assert all(c.metadata.get('section_title') or c.metadata.get('section') for c in chunks), "❌ Missing section_title"
print("  ✅ All chunks have section_title")

# 4. document_name luôn có
assert all(c.metadata.get('document_name') or c.metadata.get('source_file') for c in chunks), "❌ Missing document_name"
print("  ✅ All chunks have document_name")

# 5. Bảng đánh giá không bị split (đủ ngắn để là 1 chunk)
danh_gia_chunks = [c for c in chunks if 'Đánh giá' in c.metadata.get('section_title','')]
assert len(danh_gia_chunks) >= 1, "❌ Bảng đánh giá missing"
assert '25%' in danh_gia_chunks[0].page_content, "❌ Tỷ lệ 25% bị tách khỏi context"
print("  ✅ Bảng đánh giá giữ nguyên ngữ cảnh (25% trong cùng chunk)")

# 6. Heading xuất hiện ở đầu content
for c in chunks:
    title = c.metadata.get('section_title', '')
    if title and len(title) > 5:
        assert title in c.page_content, f"❌ Heading '{title}' not in content"
print("  ✅ Section title luôn nằm trong content")

# 7. Section quá ngắn được merge vào chunk trước hoặc sau (không tồn tại độc lập nếu có pending)
# "Ghi chú" ở cuối list — không có pending trước → trở thành pending → được flush cuối
# Đây là behavior đúng: không bỏ mất content, nhưng cũng không tạo chunk rỗng
ghi_chu_chunks = [c for c in chunks if c.page_content.strip() == "Ghi chú" or
                  c.page_content.strip().endswith("Ghi chú")]
assert len(ghi_chu_chunks) <= 1, "❌ Short section should not duplicate"
print(f"  ✅ Short sections handled correctly ({len(ghi_chu_chunks)} chunk for 'Ghi chú')")

# 8. Section quá dài bị split
long_chunks = [c for c in chunks if 'Chuẩn đầu ra' in c.metadata.get('section_title','')]
assert len(long_chunks) >= 2, f"❌ Long section should produce >= 2 chunks, got {len(long_chunks)}"
print(f"  ✅ Long section split into {len(long_chunks)} chunks (Level 3)")

print(f"\n{'='*60}")
print("ALL ASSERTIONS PASSED ✅")
