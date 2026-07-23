# chunking/academic_chunker.py
"""
Academic Chunking Strategy cho RAG — thiết kế 3 tầng:

  Level 1 — Heading-based Chunking (DOCX/PDF có cấu trúc)
    Mỗi chunk = 1 section (Heading + nội dung ngay dưới).
    Bảo đảm heading không bao giờ bị tách khỏi nội dung.

  Level 2 — Section-based Chunking (slide PPTX, PDF không có heading)
    Mỗi chunk = 1 slide hoặc 1 trang.
    Nếu trang/slide > MAX_CHARS → split theo \n\n với overlap.

  Level 3 — Semantic Chunking (fallback cho đoạn văn dài)
    Áp dụng sau Level 1/2 cho những chunk còn quá lớn.
    Dùng câu-boundary splitting thay vì ký tự đơn thuần.

Mỗi chunk metadata:
    {
        "chunk_id":      str,   # MD5 hash unique per chunk
        "document_name": str,   # tên file gốc
        "source_file":   str,
        "source":        str,
        "section_title": str,   # heading hoặc "Slide N" / "Page N"
        "page_number":   int,
        "chunk_index":   int,   # index trong section (0 nếu không split)
        "file_type":     str,
        "created_at":    str,
        "embedding_model": str,
    }

Tại sao chunking cũ gây retrieval failure:
  1. RecursiveCharacterTextSplitter cắt theo số ký tự → heading bị tách khỏi nội dung.
  2. SemanticChunker load embedding model lúc import → chậm, gây timeout.
  3. Chunk quá dài (>1000 chars) → embedding bị loãng, signal yếu.
  4. Chunk quá ngắn (<100 chars) → không đủ context cho BM25 và vector search.
  5. Không giữ section_title trong metadata → không thể filter/boost theo heading.
"""

import re
import hashlib
from datetime import datetime
from typing import List, Optional
from langchain_core.documents import Document


# ── Constants ─────────────────────────────────────────────────────────────────
MIN_CHUNK_CHARS = 150    # chunk nhỏ hơn này bị merge với chunk kế
MAX_CHUNK_CHARS = 1200   # chunk lớn hơn này sẽ được split Level 3
OVERLAP_CHARS   = 100    # overlap khi split Level 3


# ── Helpers ───────────────────────────────────────────────────────────────────
def _make_chunk_id(document_name: str, section: str, idx: int, content: str) -> str:
    raw = f"{document_name}:{section}:{idx}:{content[:60]}"
    return hashlib.md5(raw.encode("utf-8", errors="replace")).hexdigest()[:16]


def _get_embedding_model() -> str:
    try:
        from config import EMBEDDING_MODEL_NAME
        return EMBEDDING_MODEL_NAME
    except Exception:
        return "sentence-transformers/all-MiniLM-L6-v2"


def _split_by_sentences(text: str, max_chars: int, overlap: int) -> List[str]:
    """
    Level 3: split văn bản dài theo ranh giới câu, không cắt giữa câu.
    Đảm bảo mỗi chunk không vượt max_chars.
    """
    # Tách câu theo dấu kết thúc câu + khoảng trắng
    sentence_pattern = re.compile(
        r'(?<=[.!?।])\s+(?=[A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴ\u00C0-\u024F\w\*\-\d])'
    )
    sentences = sentence_pattern.split(text)

    # Merge ngắn
    merged: List[str] = []
    buf = ""
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if len(buf) + len(sent) + 1 <= max_chars:
            buf = (buf + " " + sent).strip()
        else:
            if buf:
                merged.append(buf)
            buf = sent

    if buf:
        merged.append(buf)

    # Nếu một câu đơn vẫn > max_chars → split theo \n
    final: List[str] = []
    for chunk in merged:
        if len(chunk) <= max_chars:
            final.append(chunk)
        else:
            lines = chunk.split("\n")
            sub_buf = ""
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if len(sub_buf) + len(line) + 1 <= max_chars:
                    sub_buf = (sub_buf + "\n" + line).strip()
                else:
                    if sub_buf:
                        final.append(sub_buf)
                    sub_buf = line
            if sub_buf:
                final.append(sub_buf)

    return final if final else [text]


def _make_doc(
    content: str,
    document_name: str,
    source: str,
    section_title: str,
    page_number: int,
    chunk_index: int,
    file_type: str,
    created_at: str,
    embedding_model: str,
) -> Document:
    """Tạo Document với metadata đầy đủ."""
    chunk_id = _make_chunk_id(document_name, section_title, chunk_index, content)
    return Document(
        page_content=content.strip(),
        metadata={
            "chunk_id":       chunk_id,
            "document_name":  document_name,
            "source_file":    document_name,
            "source":         source,
            "section_title":  section_title,
            "section":        section_title,
            "page_number":    page_number,
            "page":           page_number,
            "chunk_index":    chunk_index,
            "file_type":      file_type,
            "created_at":     created_at,
            "embedding_model": embedding_model,
        },
    )


# ── Level 1: Heading-based Chunking ──────────────────────────────────────────
def heading_based_chunk(docs: List[Document]) -> List[Document]:
    """
    Level 1: Nhóm các Document theo section_title từ load_docx.
    load_docx đã chia theo heading — mỗi Document là 1 section.
    Level 1 chỉ cần:
      - Loại bỏ chunk quá ngắn (merge vào chunk trước)
      - Split chunk quá dài bằng Level 3 (sentence-based)
      - Đảm bảo section_title luôn có mặt ở đầu content

    Input: output từ load_docx (mỗi doc = 1 heading-section)
    """
    embedding_model = _get_embedding_model()
    result: List[Document] = []
    pending: Optional[Document] = None   # chunk ngắn chờ merge

    for doc in docs:
        content = doc.page_content.strip()
        if not content:
            continue

        meta = doc.metadata
        doc_name   = meta.get("source_file", meta.get("document_name", "unknown"))
        source     = meta.get("source", doc_name)
        section    = meta.get("section", meta.get("section_title", ""))
        page_num   = int(meta.get("page_number", meta.get("page", 1)) or 1)
        file_type  = meta.get("file_type", "docx")
        created_at = meta.get("created_at", datetime.utcnow().isoformat())

        # Đảm bảo section_title xuất hiện đầu content (để embedding capture heading)
        if section and not content.startswith(section):
            content = f"{section}\n{content}"

        # Chunk nhỏ → merge vào pending
        if len(content) < MIN_CHUNK_CHARS:
            if pending is not None:
                merged = pending.page_content + "\n\n" + content
                if len(merged) <= MAX_CHUNK_CHARS * 1.5:
                    pending = _make_doc(
                        merged, doc_name, source,
                        pending.metadata["section_title"],
                        pending.metadata["page_number"], 0,
                        file_type, created_at, embedding_model,
                    )
                    continue
                else:
                    result.append(pending)
                    pending = None
            # Không có pending → tạo pending mới từ chunk ngắn này
            pending = _make_doc(
                content, doc_name, source, section, page_num, 0,
                file_type, created_at, embedding_model,
            )
            continue

        # Flush pending
        if pending is not None:
            result.append(pending)
            pending = None

        # Chunk vừa → giữ nguyên
        if len(content) <= MAX_CHUNK_CHARS:
            result.append(_make_doc(
                content, doc_name, source, section, page_num, 0,
                file_type, created_at, embedding_model,
            ))
            continue

        # Chunk quá lớn → Level 3 (sentence split), mỗi sub-chunk giữ heading ở đầu
        sub_texts = _split_by_sentences(content, MAX_CHUNK_CHARS, OVERLAP_CHARS)
        for i, sub in enumerate(sub_texts):
            if not sub.strip():
                continue
            # Đảm bảo heading xuất hiện trong mỗi sub-chunk để embedding capture context
            sub_with_heading = sub if section in sub else f"{section}\n{sub}"
            result.append(_make_doc(
                sub_with_heading, doc_name, source, section, page_num, i,
                file_type, created_at, embedding_model,
            ))

    if pending is not None:
        result.append(pending)

    return result


# ── Level 2: Section-based Chunking (PPTX / PDF) ─────────────────────────────
def section_based_chunk(docs: List[Document]) -> List[Document]:
    """
    Level 2: Dành cho slide PPTX và trang PDF.
    load_ppt trả về mỗi slide là 1 Document, load_pdf trả về mỗi trang là 1 Document.
    Level 2:
      - Slide/trang vừa → giữ nguyên
      - Slide/trang quá dài → split Level 3

    Input: output từ load_ppt hoặc load_pdf
    """
    embedding_model = _get_embedding_model()
    result: List[Document] = []

    for doc in docs:
        content = doc.page_content.strip()
        if not content:
            continue

        meta = doc.metadata
        doc_name   = meta.get("source_file", meta.get("document_name", "unknown"))
        source     = meta.get("source", doc_name)
        file_type  = meta.get("file_type", "pdf")
        created_at = meta.get("created_at", datetime.utcnow().isoformat())

        # Tạo section_title: "Slide N" hoặc "Page N"
        if file_type == "pptx":
            slide_num = int(meta.get("slide", meta.get("page_number", 1)) or 1)
            section = f"Slide {slide_num}"
            page_num = slide_num
        else:
            page_num = int(meta.get("page_number", meta.get("page", 1)) or 1)
            section = f"Page {page_num}"

        if len(content) <= MAX_CHUNK_CHARS:
            # Inject section label vào đầu content để embedding capture context
            full = content if section in content else f"{section}\n{content}"
            result.append(_make_doc(
                full, doc_name, source, section, page_num, 0,
                file_type, created_at, embedding_model,
            ))
        else:
            sub_texts = _split_by_sentences(content, MAX_CHUNK_CHARS, OVERLAP_CHARS)
            for i, sub in enumerate(sub_texts):
                if not sub.strip():
                    continue
                sub_with_section = sub if section in sub else f"{section}\n{sub}"
                result.append(_make_doc(
                    sub_with_section, doc_name, source, section, page_num, i,
                    file_type, created_at, embedding_model,
                ))

    return result


# ── Dispatcher ────────────────────────────────────────────────────────────────
def smart_chunk(docs: List[Document]) -> List[Document]:
    """
    Dispatcher: tự động chọn Level 1 hoặc Level 2 dựa trên file_type.
    Level 3 (sentence split) được áp dụng tự động bên trong khi chunk quá lớn.

    DOCX         → Level 1 (heading-based)
    PPTX / PDF   → Level 2 (section-based)
    """
    if not docs:
        return []

    # Nhóm theo file_type
    docx_docs = [d for d in docs if d.metadata.get("file_type") == "docx"]
    other_docs = [d for d in docs if d.metadata.get("file_type") != "docx"]

    result: List[Document] = []

    if docx_docs:
        print(f"📐 Level 1 (heading-based): {len(docx_docs)} DOCX sections...")
        result.extend(heading_based_chunk(docx_docs))

    if other_docs:
        print(f"📄 Level 2 (section-based): {len(other_docs)} PDF/PPTX pages...")
        result.extend(section_based_chunk(other_docs))

    # Filter empty
    result = [d for d in result if d.page_content.strip()]

    print(f"✅ smart_chunk: {len(docs)} raw docs → {len(result)} chunks")
    _print_chunk_stats(result)
    return result


def _print_chunk_stats(chunks: List[Document]):
    if not chunks:
        return
    lengths = [len(c.page_content) for c in chunks]
    avg = sum(lengths) / len(lengths)
    mn, mx = min(lengths), max(lengths)
    short = sum(1 for l in lengths if l < MIN_CHUNK_CHARS)
    long_ = sum(1 for l in lengths if l > MAX_CHUNK_CHARS)
    print(f"   Chunk stats: avg={avg:.0f} min={mn} max={mx} "
          f"short(<{MIN_CHUNK_CHARS})={short} long(>{MAX_CHUNK_CHARS})={long_}")
