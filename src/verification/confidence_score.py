# verification/confidence_score.py
"""
Confidence Score Calculator — Minh bạch, không giả mạo.

Công thức:
    confidence = w1 * retrieval_score
               + w2 * reranker_score
               + w3 * context_coverage
               + w4 * answerability_score

    Weights: w1=0.25, w2=0.35, w3=0.20, w4=0.20  (tổng = 1.0)

Thành phần:
    retrieval_score    — trung bình final_score từ reranker (đã blend ret+rerank)
    reranker_score     — trung bình rerank_score (cross-encoder) riêng biệt
    context_coverage   — tỷ lệ câu trong answer được hỗ trợ bởi context [từ CitationVerifier]
    answerability_score— tỷ lệ token của câu hỏi xuất hiện trong context (local, no API)

Nếu thiếu dữ liệu đầu vào → trả về "Not Available" thay vì giả mạo.
Tiêu chí "đủ dữ liệu": phải có ít nhất 1 trong 3 score thực (không phải fallback 0.5).
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from langchain_core.documents import Document


# ── Weights (tổng = 1.0) ──────────────────────────────────────────────────────
W_RETRIEVAL     = 0.25
W_RERANKER      = 0.35
W_CTX_COVERAGE  = 0.20
W_ANSWERABILITY = 0.20

assert abs(W_RETRIEVAL + W_RERANKER + W_CTX_COVERAGE + W_ANSWERABILITY - 1.0) < 1e-9


# ── Data class ────────────────────────────────────────────────────────────────
@dataclass
class ConfidenceReport:
    # Overall
    available: bool = False             # False nếu không đủ dữ liệu
    score: float = 0.0                  # 0.0–1.0
    percent: int = 0                    # 0–100
    label: str = "Not Available"        # "Cao" | "Trung bình" | "Thấp" | "Not Available"

    # Component scores (None = không có dữ liệu thực)
    retrieval_score: Optional[float] = None
    reranker_score: Optional[float] = None
    context_coverage: Optional[float] = None
    answerability_score: Optional[float] = None

    # Meta
    num_sources: int = 0
    explanation: str = ""
    formula: str = ""                   # công thức đã dùng với số thực


# ── Answerability Score ───────────────────────────────────────────────────────
def _compute_answerability(question: str, source_docs: List[Document]) -> float:
    """
    Tính xem câu hỏi có thể được trả lời từ context không.
    Phương pháp: tỷ lệ keyword của câu hỏi xuất hiện trong tổng context.

    Hoàn toàn local, không cần API.
    Score 0–1: 1.0 = tất cả keyword có trong context.

    Hỗ trợ cross-lingual: từ khóa tiếng Việt được ánh xạ sang tiếng Anh
    trước khi so sánh với tài liệu tiếng Anh.
    """
    if not question or not source_docs:
        return 0.0

    # ── Cross-lingual bridge: VI → EN term mapping ────────────────────────────
    # Giúp tính answerability đúng khi câu hỏi tiếng Việt, tài liệu tiếng Anh
    _VI_EN_BRIDGE = {
        # Chủ đề chính
        "khai phá dữ liệu": "data mining knowledge",
        "khai phá":         "data mining",
        "khai thác dữ liệu": "data mining",
        "khám phá tri thức": "knowledge discovery",
        "k-means": "k means clustering centroid cluster",
        "kmeans": "k means clustering centroid cluster",
        "thuật toán": "algorithm",
        # Lý thuyết / định nghĩa
        "định nghĩa": "definition define",
        "khái niệm":  "concept",
        "là gì":      "what is",
        "nêu":        "describe",
        "giải thích": "explain",
        "trình bày":  "describe explain",
        "liệt kê":    "list enumerate",
        "ứng dụng":   "application",
        "ứng dụng thực tế": "applications real-world",
        "ví dụ thực tế":    "example real-world",
        "kinh doanh":       "business commerce",
        "đời sống":         "real-world everyday life",
        "so sánh":          "compare comparison",
        "ưu điểm":          "advantage benefit",
        "nhược điểm":       "disadvantage limitation",
        "bước":             "step process",
        "quy trình":        "process procedure",
        "hoạt động":        "work function",
        "nguyên lý":        "principle mechanism",
        # Thuật toán
        "phân cụm":        "clustering",
        "phân lớp":        "classification",
        "học máy":         "machine learning",
        "học không giám sát": "unsupervised",
        "học có giám sát": "supervised",
        "cây quyết định":  "decision tree",
        "hồi quy":         "regression",
        "tập phổ biến":    "frequent itemset",
        "luật kết hợp":    "association rule",
        "tiền xử lý":      "preprocessing",
        "ngoại lai":       "outlier",
        "rừng ngẫu nhiên": "random forest",
        "mạng nơ-ron":     "neural network",
        "mạng neuron":     "neural network",
        "học sâu":         "deep learning",
        "độ hỗ trợ":       "support",
        "độ tin cậy":      "confidence",
        "tăng cường":      "lift",
        "chuẩn hóa":       "normalization",
        "dữ liệu thiếu":   "missing values",
        "quá khớp":        "overfitting",
        "thiếu khớp":      "underfitting",
        "kho dữ liệu":     "data warehouse",
        "cơ sở dữ liệu":   "database",
        "độ chính xác":    "accuracy precision",
        "quy trình kdd":   "KDD process knowledge discovery",
    }

    # Tokenize câu hỏi
    stopwords = {
        'là','gì','như','thế','nào','và','có','được','trong','với','cho',
        'về','của','các','một','những','đó','này','khi','thì','để','hay',
        'hãy','nêu','trình','bày','liệt','kê','giải','thích','ứng',
        'người','mới','học','bạn','tôi','em','anh','chị',
        'nguoi','moi','hoc','ban','toi',
        'the','a','an','what','how','why','when','where','who','which',
        'beginner','newbie','student','learner',
    }
    q_lower = question.lower()

    # Áp dụng bridge: thêm bản dịch tiếng Anh vào danh sách term cần tìm
    extra_en_terms = []
    # Sắp xếp key dài trước để ưu tiên cụm từ dài hơn
    sorted_bridge = sorted(_VI_EN_BRIDGE.items(), key=lambda x: len(x[0]), reverse=True)
    q_remaining = q_lower
    for vi_term, en_term in sorted_bridge:
        if vi_term in q_remaining:
            extra_en_terms.extend(en_term.split())
            q_remaining = q_remaining.replace(vi_term, " ")

    q_clean = re.sub(r'[^\w\s]', ' ', q_remaining)
    q_terms_vi = [w for w in q_clean.split() if len(w) > 2 and w not in stopwords]

    # Gộp tổng từ khóa: tiếng Việt còn lại + tiếng Anh dịch sang
    all_terms = q_terms_vi + extra_en_terms
    # Loại trùng lặp
    seen = set()
    q_terms = [t for t in all_terms if not (t in seen or seen.add(t))]

    if not q_terms:
        return 0.0

    # Gộp tất cả context
    all_context = " ".join(doc.page_content.lower() for doc in source_docs)

    # Đếm keyword có trong context (tiếng Việt hoặc tiếng Anh)
    hits = sum(1 for term in q_terms if term in all_context)
    return round(hits / len(q_terms), 3)


# ── Source label builder ──────────────────────────────────────────────────────
def _source_label(doc: Document, idx: int) -> str:
    """Tạo label cho nguồn: 'Tên file — Section (trang N)'."""
    meta = doc.metadata
    src = meta.get("source_file") or meta.get("source", f"Tài liệu {idx}")
    section = meta.get("section_title") or meta.get("section", "")
    page = meta.get("page_number") or meta.get("page", "")
    label = src
    if section:
        label += f" — {section}"
    if page:
        label += f" (trang/slide {page})"
    return label


# ── Citation block formatter ──────────────────────────────────────────────────
def build_source_block(source_docs: List[Document], used_indices: List[int]) -> str:
    """
    Tạo block 'Nguồn tài liệu:' chỉ với các nguồn thực sự được cite.

    Args:
        source_docs: retrieved docs (index 0 = [1], 1 = [2], ...)
        used_indices: danh sách index [1,2,...] xuất hiện trong answer text
    """
    if not used_indices or not source_docs:
        return ""

    lines = ["", "**Nguồn tài liệu:**"]
    seen = set()
    for idx in sorted(set(used_indices)):
        if idx in seen:
            continue
        seen.add(idx)
        doc_i = idx - 1  # 1-based → 0-based
        if 0 <= doc_i < len(source_docs):
            label = _source_label(source_docs[doc_i], idx)
            lines.append(f"[{idx}] {label}")

    return "\n".join(lines)


def extract_used_citation_indices(answer_text: str) -> List[int]:
    """Trích xuất tất cả [N] xuất hiện trong answer text."""
    return [int(m) for m in re.findall(r'\[(\d+)\]', answer_text)]


# ── Main confidence calculator ────────────────────────────────────────────────
def compute_confidence(
    source_docs: List[Document],
    citations: List[Dict],
    citation_coverage: float,
    reranker_scores: Optional[List[float]] = None,
    question: Optional[str] = None,
    answer_text: Optional[str] = None,
) -> ConfidenceReport:
    """
    Tính confidence score minh bạch.

    Args:
        source_docs      : retrieved & reranked documents
        citations        : citation dicts từ format_source_citation
        citation_coverage: từ CitationVerifier (0–1)
        reranker_scores  : cross-encoder scores cho source_docs
        question         : câu hỏi gốc (để tính answerability)
        answer_text      : câu trả lời (để verify citations thực sự dùng)

    Returns:
        ConfidenceReport — nếu không đủ dữ liệu: available=False, label="Not Available"
    """
    if not source_docs:
        return ConfidenceReport(
            available=False,
            label="Not Available",
            explanation="Không có tài liệu nào được retrieve.",
            num_sources=0,
        )

    # ── 1. Retrieval score ────────────────────────────────────────────────────
    # Lấy final_score từ metadata (blend của retrieval + reranker từ pipeline)
    ret_scores_raw = []
    for doc in source_docs:
        fs = doc.metadata.get('final_score') or doc.metadata.get('relevance_score')
        if fs is not None:
            ret_scores_raw.append(float(fs))
    # Fallback từ citations nếu metadata không có
    if not ret_scores_raw:
        for cit in citations:
            rs = cit.get('relevance_score')
            if rs is not None and rs != 0.5:  # 0.5 là giả, bỏ qua
                ret_scores_raw.append(float(rs))

    retrieval_score = (sum(ret_scores_raw) / len(ret_scores_raw)
                       if ret_scores_raw else None)

    # ── 2. Reranker score ─────────────────────────────────────────────────────
    # Lấy rerank_score riêng từ metadata (không blend)
    rr_scores_raw = []
    for doc in source_docs:
        rs = doc.metadata.get('rerank_score')
        if rs is not None:
            rr_scores_raw.append(float(rs))
    # Fallback: dùng reranker_scores argument
    if not rr_scores_raw and reranker_scores:
        rr_scores_raw = [s for s in reranker_scores if s != 0.5]

    reranker_score = (sum(rr_scores_raw) / len(rr_scores_raw)
                      if rr_scores_raw else None)

    # ── 3. Context coverage ───────────────────────────────────────────────────
    ctx_cov = float(citation_coverage) if citation_coverage is not None else None

    # ── 4. Answerability score ────────────────────────────────────────────────
    answerability = None
    if question and source_docs:
        answerability = _compute_answerability(question, source_docs)

    # ── Check đủ dữ liệu ──────────────────────────────────────────────────────
    # Cần ít nhất 2 trong 4 thành phần là dữ liệu thực (không phải None)
    real_components = [x for x in [retrieval_score, reranker_score,
                                    ctx_cov, answerability]
                       if x is not None]
    if len(real_components) < 2:
        return ConfidenceReport(
            available=False,
            label="Not Available",
            explanation="Không đủ dữ liệu để tính confidence (cần ≥2 thành phần).",
            num_sources=len(source_docs),
        )

    # ── Tính score ────────────────────────────────────────────────────────────
    # Với các thành phần None: re-normalize weights
    components = {
        'retrieval':     (W_RETRIEVAL,     retrieval_score),
        'reranker':      (W_RERANKER,      reranker_score),
        'ctx_coverage':  (W_CTX_COVERAGE,  ctx_cov),
        'answerability': (W_ANSWERABILITY, answerability),
    }

    total_weight = sum(w for k, (w, v) in components.items() if v is not None)
    score_sum = sum(w * v for k, (w, v) in components.items() if v is not None)

    if total_weight == 0:
        return ConfidenceReport(
            available=False,
            label="Not Available",
            explanation="Tất cả thành phần đều None.",
            num_sources=len(source_docs),
        )

    # Normalize về 0–1 dù thiếu thành phần
    raw_score = score_sum / total_weight
    score = round(min(1.0, max(0.0, raw_score)), 3)
    percent = int(score * 100)

    # Label
    if percent >= 75:
        label = "Cao"
    elif percent >= 50:
        label = "Trung bình"
    else:
        label = "Thấp"

    # ── Công thức minh bạch ───────────────────────────────────────────────────
    formula_parts = []
    used_weights = {}
    for k, (w, v) in components.items():
        if v is not None:
            # Re-normalize weight
            adj_w = round(w / total_weight, 3)
            used_weights[k] = adj_w
            vi_name = {
                'retrieval':     'Retrieval',
                'reranker':      'Reranker',
                'ctx_coverage':  'CtxCoverage',
                'answerability': 'Answerability',
            }[k]
            formula_parts.append(f"{adj_w}×{vi_name}({v:.2f})")

    formula = f"Confidence = {' + '.join(formula_parts)} = {score:.3f}"

    # ── Explanation ───────────────────────────────────────────────────────────
    expl_parts = []
    if retrieval_score is not None:
        icon = "✓" if retrieval_score >= 0.6 else "⚠"
        expl_parts.append(f"{icon} Retrieval {int(retrieval_score*100)}%")
    if reranker_score is not None:
        icon = "✓" if reranker_score >= 0.6 else "⚠"
        expl_parts.append(f"{icon} Reranker {int(reranker_score*100)}%")
    if ctx_cov is not None:
        icon = "✓" if ctx_cov >= 0.6 else "⚠"
        expl_parts.append(f"{icon} Citations {int(ctx_cov*100)}%")
    if answerability is not None:
        icon = "✓" if answerability >= 0.5 else "⚠"
        expl_parts.append(f"{icon} Answerability {int(answerability*100)}%")

    explanation = " | ".join(expl_parts)

    return ConfidenceReport(
        available=True,
        score=score,
        percent=percent,
        label=label,
        retrieval_score=round(retrieval_score, 3) if retrieval_score is not None else None,
        reranker_score=round(reranker_score, 3) if reranker_score is not None else None,
        context_coverage=round(ctx_cov, 3) if ctx_cov is not None else None,
        answerability_score=round(answerability, 3) if answerability is not None else None,
        num_sources=len(source_docs),
        explanation=explanation,
        formula=formula,
    )


def format_confidence_block(report: ConfidenceReport) -> str:
    """
    Tạo block confidence để append vào cuối answer.

    Output mẫu:
        ---
        **Độ tin cậy: 78% (Cao)**
        Retrieval 82% | Reranker 75% | Citations 80% | Answerability 70%
        Công thức: 0.25×Retrieval(0.82) + 0.35×Reranker(0.75) + ... = 0.780
    hoặc:
        ---
        **Độ tin cậy: Not Available**
        Không đủ dữ liệu để tính confidence.
    """
    if not report.available:
        return (
            "\n\n---\n"
            f"**Độ tin cậy: Not Available**\n"
            f"_{report.explanation}_"
        )

    return (
        "\n\n---\n"
        f"**Độ tin cậy: {report.percent}% ({report.label})**\n"
        f"{report.explanation}\n"
        f"_Công thức: {report.formula}_"
    )
