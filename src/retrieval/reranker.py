# retrieval/reranker.py
"""
Retrieval Optimization Pipeline
Question -> HybridRetriever(k=20) -> CrossEncoder Reranker -> Top-5 -> LLM

Model priority (auto-select):
  1. BAAI/bge-reranker-v2-m3        (multilingual Vi+En, best quality)
  2. cross-encoder/ms-marco-MiniLM-L-6-v2  (English-focused, cached fallback)
  3. Heuristic fallback              (no model needed)

Score semantics:
  retrieval_score : RRF score from HybridRetriever (0-1)
  rerank_score    : sigmoid(cross_encoder_logit) 0-1
                    > 0.65 highly relevant
                    0.40-0.65 relevant
                    < 0.35 likely irrelevant (filtered)
  final_score     : 0.35 * retrieval + 0.65 * rerank
"""

import re
import math
import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# ── Model singleton ───────────────────────────────────────────────────────────
_model = None
_model_name_loaded = None

_CANDIDATE_MODELS = [
    "BAAI/bge-reranker-v2-m3",
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
]


def _load_model():
    global _model, _model_name_loaded
    if _model is not None:
        return _model, _model_name_loaded
    try:
        from sentence_transformers import CrossEncoder
    except ImportError:
        return None, None
    for name in _CANDIDATE_MODELS:
        try:
            m = CrossEncoder(name, max_length=512)
            _model = m
            _model_name_loaded = name
            print(f"Reranker loaded: {name}")
            return _model, _model_name_loaded
        except Exception as e:
            logger.warning(f"Cannot load {name}: {e}")
    return None, None


# ── Score data class ──────────────────────────────────────────────────────────
@dataclass
class ScoredDocument:
    document: Document
    retrieval_score: float = 0.0
    rerank_score: float = 0.0
    heuristic_score: float = 0.0
    final_score: float = 0.0
    rank_before: int = 0
    rank_after: int = 0

    @property
    def source(self):
        m = self.document.metadata
        return m.get("source_file") or m.get("source", "unknown")

    @property
    def section(self):
        m = self.document.metadata
        return m.get("section_title") or m.get("section", "")

    @property
    def page(self):
        m = self.document.metadata
        return m.get("page_number") or m.get("page", "?")


# ── Helpers ───────────────────────────────────────────────────────────────────
def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-float(x)))


def _extract_keywords(text: str) -> List[str]:
    stopwords = {
        'the','a','an','and','or','but','in','on','at','to','for',
        'of','with','by','from','is','are','was','were',
        'la','cua','va','co','duoc','trong','voi','cho','ve',
    }
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    return [w for w in text.split() if len(w) > 2 and w not in stopwords]


def _heuristic_score(query: str, doc: Document) -> float:
    terms = _extract_keywords(query)
    content = doc.page_content.lower()
    if not terms:
        return 0.0
    overlap = sum(1 for t in terms if t in content) / len(terms)
    freq = min(1.0, sum(content.count(t) for t in terms)
               / max(1, len(content.split())) * 10)
    return 0.6 * overlap + 0.4 * freq


_TECHNICAL_TERMS = {
    'code','python','implement','confusion','matrix','roc','auc',
    'algorithm','function','scikit','matplotlib','numpy','pandas',
    'accuracy','precision','recall','f1','model','training',
    'classification','clustering','regression','neural','deep',
    'thuat toan','ham','lap trinh','thu vien','ma nguon',
}

_SYLLABUS_TERMS = {
    'de cuong','tin chi','hoc phan','giang vien',
    'syllabus','credit','course outline',
}


def _is_technical_query(query: str) -> bool:
    q = query.lower()
    return any(t in q for t in _TECHNICAL_TERMS)


def _is_syllabus_doc(doc: Document) -> bool:
    c = doc.page_content.lower()
    syllabus_vi = ['de cuong', 'tin chi', 'hoc phan', 'giang vien',
                   '\u0111\u1ec1 c\u01b0\u01a1ng', 't\u00edn ch\u1ec9',
                   'h\u1ecdc ph\u1ea7n', 'gi\u1ea3ng vi\u00ean']
    return any(k in c for k in syllabus_vi + list(_SYLLABUS_TERMS))


# ── Core Reranker ─────────────────────────────────────────────────────────────
class CrossEncoderReranker:
    """
    Cross-Encoder Reranker with transparent debug logging.

    Pipeline:
        Top-20 candidates (from HybridRetriever)
            -> score each (query, doc) pair with CrossEncoder
            -> blend: final = 0.35 * retrieval + 0.65 * rerank
            -> filter(threshold=0.35)
            -> top-5 for LLM
    """

    def __init__(
        self,
        retrieval_weight: float = 0.35,
        rerank_weight: float = 0.65,
        top_k: int = 5,
        threshold: float = 0.35,
    ):
        self.retrieval_weight = retrieval_weight
        self.rerank_weight = rerank_weight
        self.top_k = top_k
        self.threshold = threshold

    def score(
        self,
        query: str,
        documents: List[Document],
        retrieval_scores: Optional[List[float]] = None,
    ) -> List[ScoredDocument]:
        """Score all documents. Returns unsorted list of ScoredDocument."""
        if not documents:
            return []

        model, model_name = _load_model()
        is_tech = _is_technical_query(query)

        # Cross-encoder scores
        if model is not None:
            pairs = [(query, doc.page_content[:512]) for doc in documents]
            try:
                logits = model.predict(pairs)
                ce_scores = [_sigmoid(float(l)) for l in logits]
            except Exception as e:
                logger.warning(f"CrossEncoder predict failed: {e}. Using heuristic.")
                ce_scores = [_heuristic_score(query, doc) for doc in documents]
        else:
            ce_scores = [_heuristic_score(query, doc) for doc in documents]

        # Retrieval scores (rank-decay if not provided)
        if retrieval_scores and len(retrieval_scores) == len(documents):
            ret_scores = retrieval_scores
        else:
            n = len(documents)
            ret_scores = [1.0 - (i / n) for i in range(n)]

        scored = []
        for rank, (doc, ce, ret) in enumerate(zip(documents, ce_scores, ret_scores), 1):
            h = _heuristic_score(query, doc)
            final = self.rerank_weight * ce + self.retrieval_weight * ret
            if is_tech and _is_syllabus_doc(doc):
                final *= 0.35

            scored.append(ScoredDocument(
                document=doc,
                retrieval_score=round(ret, 4),
                rerank_score=round(ce, 4),
                heuristic_score=round(h, 4),
                final_score=round(final, 4),
                rank_before=rank,
            ))

        return scored

    def rerank(
        self,
        query: str,
        documents: List[Document],
        retrieval_scores: Optional[List[float]] = None,
        top_k: Optional[int] = None,
        verbose: bool = True,
    ) -> List[ScoredDocument]:
        """Full reranking pipeline with debug log."""
        if not documents:
            return []

        k = top_k or self.top_k
        _, model_name = _load_model()

        if verbose:
            print(f"\n{'='*62}")
            print(f"RERANKER  model={model_name or 'heuristic'}")
            print(f"  query  : {query[:75]}")
            print(f"  input  : {len(documents)} candidates -> top {k}")
            print(f"  blend  : {self.rerank_weight}*rerank + {self.retrieval_weight}*retrieval")

        scored = self.score(query, documents, retrieval_scores)
        scored.sort(key=lambda s: s.final_score, reverse=True)
        for i, sd in enumerate(scored, 1):
            sd.rank_after = i

        if verbose:
            print(f"\n  {'Bef':>3} {'Aft':>3}  {'Ret':>6}  {'Rerank':>7}  {'Final':>7}  Src/Section")
            print(f"  {'---':>3} {'---':>3}  {'------':>6}  {'-------':>7}  {'-------':>7}  {'---'}")
            for sd in scored:
                ok = "OK" if sd.final_score >= self.threshold else "--"
                src = sd.source[:18]
                sec = sd.section[:18] if sd.section else ""
                print(f"  {sd.rank_before:>3} {sd.rank_after:>3}  "
                      f"{sd.retrieval_score:6.3f}  {sd.rerank_score:7.3f}  "
                      f"{sd.final_score:7.3f}  [{ok}] {src}/{sec}")

        # Filter
        filtered = [sd for sd in scored if sd.final_score >= self.threshold]
        removed = len(scored) - len(filtered)
        if not filtered:
            if verbose:
                print(f"\n  WARNING: no docs above {self.threshold}, keeping top 1")
            filtered = scored[:1]
        elif removed and verbose:
            print(f"\n  Removed {removed} docs below threshold {self.threshold}")

        final_docs = filtered[:k]

        if verbose:
            print(f"\n  -- Final Context (top {len(final_docs)}) --")
            for i, sd in enumerate(final_docs, 1):
                print(f"  [{i}] final={sd.final_score:.3f} "
                      f"ret={sd.retrieval_score:.3f} "
                      f"rerank={sd.rerank_score:.3f}")
                print(f"      src={sd.source}  sec={sd.section}  p={sd.page}")
                print(f"      {sd.document.page_content[:90]}...")
            print(f"{'='*62}\n")

        return final_docs

    def rerank_tuples(
        self,
        query: str,
        documents: List[Document],
        retrieval_scores: Optional[List[float]] = None,
        top_k: Optional[int] = None,
    ) -> List[Tuple[Document, float]]:
        """Backward-compatible interface returning (doc, final_score) tuples."""
        results = self.rerank(query, documents, retrieval_scores, top_k)
        return [(sd.document, sd.final_score) for sd in results]


# ── Factory ───────────────────────────────────────────────────────────────────
def create_reranker(
    retrieval_weight: float = 0.35,
    rerank_weight: float = 0.65,
    top_k: int = 5,
    threshold: float = 0.35,
) -> CrossEncoderReranker:
    return CrossEncoderReranker(
        retrieval_weight=retrieval_weight,
        rerank_weight=rerank_weight,
        top_k=top_k,
        threshold=threshold,
    )
