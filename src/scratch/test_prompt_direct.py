"""Test prompt template trực tiếp — không cần API, không tốn quota."""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── Giả lập context như RAG pipeline tạo ra ──────────────────────────────────
MOCK_DOCS = [
    {
        "idx": 1,
        "source_file": "220269_ Khai pha du lieu - AI.docx",
        "section": "7. Đánh giá học phần",
        "page": 7,
        "content": (
            "7. Đánh giá học phần\n"
            "Đánh giá quá trình | Hình thức đánh giá: Kiểm tra lý thuyết | "
            "Nội dung: Từ bài 1 đến bài 3 | Tỷ lệ %: 25%\n"
            "Đánh giá quá trình | Hình thức đánh giá: Bài tập lớn | "
            "Nội dung: Từ bài 2 đến bài 5 | Tỷ lệ %: 25%\n"
            "Đánh giá kết thúc học phần | Hình thức đánh giá: Trắc nghiệm | "
            "Nội dung: Kiến thức từ bài 1 đến bài 5 | Tỷ lệ %: 50%"
        ),
    },
    {
        "idx": 2,
        "source_file": "10ClusBasic.pptx",
        "section": "K-Means Algorithm",
        "page": 15,
        "content": (
            "Slide 15 — K-Means Algorithm\n"
            "K-Means partitions data into K clusters.\n"
            "Step 1: Initialize K centroids randomly.\n"
            "Step 2: Assign each point to nearest centroid.\n"
            "Step 3: Update centroid as mean of assigned points.\n"
            "Repeat until convergence."
        ),
    },
]

MOCK_DOCS_UNRELATED = [
    {
        "idx": 1,
        "source_file": "10ClusBasic.pptx",
        "section": "DBSCAN",
        "page": 22,
        "content": "DBSCAN uses density-based approach. Core point, border point, noise.",
    },
]


def build_prompt(docs, question):
    """Replicate rag.py prompt builder."""
    parts = []
    for doc in docs:
        loc = doc["source_file"]
        if doc.get("section"):
            loc += f" — {doc['section']}"
        if doc.get("page"):
            loc += f" (trang/slide {doc['page']})"
        parts.append(
            f"[{doc['idx']}] Nguồn: {loc}\n"
            f"Nội dung:\n{doc['content']}"
        )
    context = "\n\n---\n\n".join(parts)

    return f"""Bạn là trợ lý học thuật chuyên về môn Khai phá Dữ liệu.

════════════════════════════════════════════════════════════
NGUYÊN TẮC TUYỆT ĐỐI
════════════════════════════════════════════════════════════
1. CHỈ sử dụng thông tin từ CONTEXT bên dưới.
2. KHÔNG được suy luận, đoán mò, hoặc dùng kiến thức từ quá trình huấn luyện.
3. KHÔNG thêm thông tin không có trong CONTEXT, dù thông tin đó có vẻ đúng.
4. Nếu CONTEXT không chứa đủ thông tin để trả lời:
   → Viết đúng câu này: "Tôi không tìm thấy thông tin này trong tài liệu được cung cấp."
   → Dừng lại, không giải thích thêm, không đoán.

════════════════════════════════════════════════════════════
QUY TẮC TRÍCH DẪN (BẮT BUỘC)
════════════════════════════════════════════════════════════
- Mỗi câu có thông tin từ tài liệu PHẢI kết thúc bằng [N] (N là số thứ tự nguồn).
- Ví dụ đúng:
    Bài tập lớn chiếm 25% tổng điểm học phần. [1]
    K-Means yêu cầu xác định trước số cụm K. [2]
- Ví dụ sai:
    Bài tập lớn chiếm 25% (nguồn: Đề cương).   ← sai format
    K-Means là thuật toán phổ biến.              ← thiếu citation
- Nếu một câu dùng thông tin từ nhiều nguồn: K-Means là thuật toán phân cụm [1][3].
- Không gộp citation vào cuối đoạn — phải gắn từng câu.

════════════════════════════════════════════════════════════
ĐỊNH DẠNG ĐẦU RA
════════════════════════════════════════════════════════════
Phần trả lời:
  [nội dung với citation inline [N]]

Nguồn tài liệu:
  [1] [Tên file — Tên section — Trang/Slide]
  [2] [Tên file — Tên section — Trang/Slide]
  ...

Chỉ liệt kê nguồn nào thực sự được trích dẫn trong phần trả lời.

════════════════════════════════════════════════════════════
CONTEXT — TÀI LIỆU THAM KHẢO
════════════════════════════════════════════════════════════
{context}

════════════════════════════════════════════════════════════
CÂU HỎI
════════════════════════════════════════════════════════════
{question}

════════════════════════════════════════════════════════════
TRẢ LỜI (tiếng Việt, chỉ từ CONTEXT, có citation [N] từng câu)
════════════════════════════════════════════════════════════"""


# ── Print prompts để verify structure ────────────────────────────────────────
print("="*65)
print("PROMPT STRUCTURE VERIFICATION")
print("="*65)

# Scenario 1: in-context
p1 = build_prompt(MOCK_DOCS, "Bài tập lớn chiếm bao nhiêu phần trăm điểm?")
print(f"\n[Scenario 1] In-context question")
print(f"  Prompt length: {len(p1)} chars")
print(f"  Has 'NGUYÊN TẮC TUYỆT ĐỐI': {'NGUYÊN TẮC TUYỆT ĐỐI' in p1}")
print(f"  Has 'Tôi không tìm thấy' instruction: {'Tôi không tìm thấy' in p1}")
print(f"  Has citation example [1]: {'[1]' in p1}")
print(f"  Has 'Nguồn tài liệu' section: {'Nguồn tài liệu' in p1}")
print(f"  Context includes source metadata: {'220269_' in p1 and 'Đánh giá học phần' in p1}")
print(f"  Context includes 25%: {'25%' in p1}")

# Scenario 2: out-of-context
p2 = build_prompt(MOCK_DOCS_UNRELATED, "Thời tiết Hà Nội hôm nay thế nào?")
print(f"\n[Scenario 2] Out-of-context question")
print(f"  Prompt instructs refusal: {'Tôi không tìm thấy' in p2}")
print(f"  No hallucination permission: {'kiến thức từ quá trình huấn luyện' in p2}")

# ── Assertions ────────────────────────────────────────────────────────────────
print("\n" + "="*65)
print("ASSERTIONS:")

# 1. Instruction rõ ràng không được dùng kiến thức ngoài
assert "KHÔNG được suy luận" in p1
assert "quá trình huấn luyện" in p1
print("  [1] 'No outside knowledge' instruction: OK")

# 2. Refusal instruction chính xác
assert "Tôi không tìm thấy thông tin này trong tài liệu được cung cấp." in p1
print("  [2] Exact refusal phrase present: OK")

# 3. Citation format example
assert "Bài tập lớn chiếm 25% tổng điểm học phần. [1]" in p1
print("  [3] Citation example in prompt: OK")

# 4. Source metadata được nhúng vào context
assert "220269_ Khai pha du lieu - AI.docx" in p1
assert "7. Đánh giá học phần" in p1
assert "trang/slide 7" in p1
print("  [4] Source metadata in context: OK")

# 5. Content từ doc được preserve đầy đủ
assert "25%" in p1
assert "Bài tập lớn" in p1
print("  [5] Document content preserved: OK")

# 6. Không có "dùng kiến thức chung" cho phép hallucination
assert "dùng kiến thức chung" not in p1
assert "kiến thức của bạn" not in p1
print("  [6] No 'use general knowledge' permission: OK")

# 7. Format output section rõ ràng
assert "Nguồn tài liệu:" in p1
assert "ĐỊNH DẠNG ĐẦU RA" in p1
print("  [7] Output format section present: OK")

# 8. Separator structure
assert "════" in p1  # visual separator
sections = ["NGUYÊN TẮC TUYỆT ĐỐI", "QUY TẮC TRÍCH DẪN", 
            "ĐỊNH DẠNG ĐẦU RA", "CONTEXT", "CÂU HỎI", "TRẢ LỜI"]
for s in sections:
    assert s in p1, f"Missing section: {s}"
print(f"  [8] All {len(sections)} sections present: OK")

print("\nALL ASSERTIONS PASSED")
print("="*65)
print("\nSAMPLE CONTEXT BLOCK (how docs appear in prompt):")
print("-"*40)
for doc in MOCK_DOCS[:1]:
    loc = f"{doc['source_file']} — {doc['section']} (trang/slide {doc['page']})"
    print(f"[{doc['idx']}] Nguồn: {loc}")
    print(f"Nội dung:\n{doc['content'][:200]}...")
