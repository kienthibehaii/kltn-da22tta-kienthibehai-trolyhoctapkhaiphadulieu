# verification/citation_verifier.py — Local Citation Verification (no API)
"""
Kiểm tra từng câu trong câu trả lời có được hỗ trợ bởi context không.
Hoạt động hoàn toàn local — không dùng thêm Gemini API call.

Thuật toán:
    1. Tách câu trả lời thành các câu.
    2. Mỗi câu có citation [N] → kiểm tra token overlap với document[N].
    3. Câu có citation nhưng overlap thấp → đánh dấu "low_support".
    4. Câu không có citation → đánh dấu "no_citation".
    5. Tính citation_coverage = (câu có citation hỗ trợ) / (tổng câu thực chất).
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from langchain_core.documents import Document


# ── Data classes ──────────────────────────────────────────────────────────────
@dataclass
class SentenceVerification:
    sentence: str
    citation_indices: List[int]         # [1, 2] etc.
    is_supported: bool                  # True if overlap >= threshold
    support_score: float                # 0.0 – 1.0
    status: str                         # "supported" | "low_support" | "no_citation" | "no_context"


@dataclass
class VerificationResult:
    sentences: List[SentenceVerification] = field(default_factory=list)
    citation_coverage: float = 0.0      # % sentences with valid citations
    supported_count: int = 0
    unsupported_count: int = 0
    no_citation_count: int = 0
    hallucination_risk: str = "low"     # "low" | "medium" | "high"
    verified_answer: str = ""           # answer with unsupported markers removed/flagged


# ── Core logic ────────────────────────────────────────────────────────────────
def _split_sentences(text: str) -> List[str]:
    """Split text into sentences, preserving citation markers."""
    # Split on . ! ? followed by space or newline, but not inside brackets
    parts = re.split(r'(?<=[.!?])\s+(?=[A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴ\*\-\d])', text)
    # Also split on newline + heading
    sentences = []
    for p in parts:
        sub = re.split(r'\n+(?=\d+\.\s|\*\*|#{1,3}\s)', p)
        sentences.extend(sub)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 15]


def _extract_citation_indices(sentence: str) -> List[int]:
    """Extract [1], [2], [3] etc. from a sentence."""
    return [int(m) for m in re.findall(r'\[(\d+)\]', sentence)]


def _token_overlap(text_a: str, text_b: str) -> float:
    """Compute Jaccard-like token overlap between two texts."""
    def tokenize(t):
        t = re.sub(r'[^\w\s]', ' ', t.lower())
        return set(w for w in t.split() if len(w) > 2)

    a_tokens = tokenize(text_a)
    b_tokens = tokenize(text_b)
    if not a_tokens:
        return 0.0
    intersection = a_tokens & b_tokens
    return len(intersection) / len(a_tokens)


def _is_substantive(sentence: str) -> bool:
    """Return True if sentence contains factual claims worth verifying."""
    # Skip pure headings, code fences, very short sentences
    if len(sentence) < 20:
        return False
    if sentence.startswith('```') or sentence.startswith('#'):
        return False
    # Skip sentences that are pure examples/greetings
    greet_patterns = ['xin chào', 'chào bạn', 'tôi sẽ', 'dưới đây', 'như sau']
    if any(p in sentence.lower() for p in greet_patterns):
        return False
    return True


# ── Public API ────────────────────────────────────────────────────────────────
class CitationVerifier:
    """
    Local citation verifier — no API calls required.

    Usage:
        verifier = CitationVerifier(overlap_threshold=0.15)
        result = verifier.verify(answer, source_docs)
    """

    def __init__(self, overlap_threshold: float = 0.15):
        """
        Args:
            overlap_threshold: Minimum token overlap to consider a citation supported.
                               0.15 = 15% of sentence tokens must appear in cited doc.
        """
        self.overlap_threshold = overlap_threshold

    def verify(
        self,
        answer: str,
        source_docs: List[Document],
        citations: Optional[List[Dict]] = None,
    ) -> VerificationResult:
        """
        Verify all sentences in answer against source_docs.

        Args:
            answer: The LLM-generated answer text.
            source_docs: Retrieved documents (index 0 = [1], index 1 = [2], ...).
            citations: Optional citation dicts from backend (for metadata).

        Returns:
            VerificationResult with per-sentence analysis.
        """
        if not source_docs:
            return VerificationResult(
                verified_answer=answer,
                hallucination_risk="high",
                citation_coverage=0.0,
            )

        sentences = _split_sentences(answer)
        verified_sentences: List[SentenceVerification] = []
        supported = unsupported = no_cit = 0

        for sent in sentences:
            indices = _extract_citation_indices(sent)
            substantive = _is_substantive(sent)

            if not indices:
                status = "no_citation" if substantive else "no_context"
                if substantive:
                    no_cit += 1
                verified_sentences.append(SentenceVerification(
                    sentence=sent,
                    citation_indices=[],
                    is_supported=not substantive,
                    support_score=0.0,
                    status=status,
                ))
                continue

            # Check each cited document
            best_score = 0.0
            for idx in indices:
                doc_index = idx - 1  # 1-based → 0-based
                if 0 <= doc_index < len(source_docs):
                    doc_text = source_docs[doc_index].page_content
                    score = _token_overlap(sent, doc_text)
                    best_score = max(best_score, score)

            is_supported = best_score >= self.overlap_threshold
            status = "supported" if is_supported else "low_support"

            if is_supported:
                supported += 1
            else:
                unsupported += 1

            verified_sentences.append(SentenceVerification(
                sentence=sent,
                citation_indices=indices,
                is_supported=is_supported,
                support_score=best_score,
                status=status,
            ))

        # Compute citation coverage over substantive sentences
        substantive_total = supported + unsupported + no_cit
        coverage = supported / substantive_total if substantive_total > 0 else 1.0

        # Hallucination risk
        if coverage >= 0.7:
            risk = "low"
        elif coverage >= 0.4:
            risk = "medium"
        else:
            risk = "high"

        # Build verified answer (flag low_support sentences lightly)
        verified_answer = _build_verified_answer(answer, verified_sentences)

        return VerificationResult(
            sentences=verified_sentences,
            citation_coverage=round(coverage, 3),
            supported_count=supported,
            unsupported_count=unsupported,
            no_citation_count=no_cit,
            hallucination_risk=risk,
            verified_answer=verified_answer,
        )


def _build_verified_answer(answer: str, verifications: List[SentenceVerification]) -> str:
    """Return answer unchanged — we don't modify LLM output, just track issues."""
    # Future: could strip or flag "low_support" sentences
    # For now return as-is to avoid breaking valid answers
    return answer


# ── Convenience function ──────────────────────────────────────────────────────
def verify_citations(
    answer: str,
    source_docs: List[Document],
    citations: Optional[List[Dict]] = None,
    threshold: float = 0.15,
) -> VerificationResult:
    """Convenience wrapper around CitationVerifier.verify()."""
    verifier = CitationVerifier(overlap_threshold=threshold)
    return verifier.verify(answer, source_docs, citations)
