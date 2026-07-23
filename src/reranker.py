# reranker.py - Reranking module để cải thiện độ chính xác
import os
from typing import List, Tuple, Optional
from langchain_core.documents import Document
from dotenv import load_dotenv
import re

load_dotenv()

# Cross-encoder model (loaded once, reused across requests)
_cross_encoder = None

def _get_cross_encoder():
    """Load cross-encoder model lazily (once per process)"""
    global _cross_encoder
    if _cross_encoder is None:
        try:
            from sentence_transformers import CrossEncoder
            _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)
            print("✅ Cross-encoder reranker loaded: ms-marco-MiniLM-L-6-v2")
        except Exception as e:
            print(f"⚠️ Could not load cross-encoder: {e}. Falling back to heuristic.")
            _cross_encoder = None
    return _cross_encoder


class Reranker:
    """
    Reranker để chấm điểm và sắp xếp lại documents theo độ liên quan.
    Ưu tiên cross-encoder (chính xác, local) > heuristic (nhanh, fallback).
    """

    def __init__(self, method="cross-encoder"):
        """
        Args:
            method: "cross-encoder" (default), "heuristic", "hybrid"
        """
        self.method = method
    
    def rerank(self, query: str, documents: List[Document],
               top_k: int = 3) -> List[Tuple[Document, float]]:
        """Rerank documents theo độ liên quan với query"""
        if not documents:
            return []

        print(f"🔄 Reranking {len(documents)} documents...")

        if self.method == "cross-encoder":
            ce = _get_cross_encoder()
            if ce is not None:
                scored_docs = self._cross_encoder_rerank(query, documents, ce)
            else:
                scored_docs = self._heuristic_rerank(query, documents)
        elif self.method == "heuristic":
            scored_docs = self._heuristic_rerank(query, documents)
        else:  # hybrid: cross-encoder + heuristic fallback
            ce = _get_cross_encoder()
            if ce is not None:
                scored_docs = self._cross_encoder_rerank(query, documents, ce)
            else:
                scored_docs = self._heuristic_rerank(query, documents)

        scored_docs.sort(key=lambda x: x[1], reverse=True)
        top_docs = scored_docs[:top_k]

        print(f"✅ Đã chọn top {len(top_docs)} documents")
        for i, (doc, score) in enumerate(top_docs, 1):
            print(f"   {i}. Score: {score:.3f} - {doc.page_content[:80]}...")

        return top_docs

    def _cross_encoder_rerank(self, query: str, documents: List[Document], model) -> List[Tuple[Document, float]]:
        """Rerank dùng cross-encoder (ms-marco). Score được normalize về [0, 1].
        
        Kết hợp cross-encoder score với heuristic để xử lý tốt cả tiếng Anh và tiếng Việt.
        """
        import math
        pairs = [(query, doc.page_content[:512]) for doc in documents]
        try:
            raw_scores = model.predict(pairs)
            # ms-marco scores are logits; apply sigmoid to normalize to [0,1]
            ce_scores = [1 / (1 + math.exp(-float(s))) for s in raw_scores]
            
            # Kết hợp cross-encoder (70%) + heuristic (30%) để xử lý docs tiếng Việt tốt hơn
            heuristic_results = self._heuristic_rerank(query, documents)
            h_scores = {id(doc): score for doc, score in heuristic_results}
            
            combined = []
            for doc, ce_score in zip(documents, ce_scores):
                h_score = h_scores.get(id(doc), 0.0)
                final_score = 0.70 * ce_score + 0.30 * h_score
                combined.append((doc, final_score))
            
            return combined
        except Exception as e:
            print(f"⚠️ Cross-encoder error: {e}. Falling back to heuristic.")
            return self._heuristic_rerank(query, documents)
    
    def _heuristic_rerank(self, query: str, documents: List[Document]) -> List[Tuple[Document, float]]:
        """
        Rerank bằng heuristic rules
        """
        query_lower = query.lower()
        query_terms = self._extract_keywords(query_lower)
        
        # Phát hiện loại câu hỏi để áp dụng penalty phù hợp
        is_technical_query = any(kw in query_lower for kw in [
            'code', 'python', 'implement', 'confusion matrix', 'roc', 'auc',
            'algorithm', 'function', 'scikit', 'matplotlib', 'numpy',
            'confusion', 'accuracy', 'precision', 'recall', 'f1',
            'ma trận', 'thuật toán', 'hàm', 'lập trình', 'thư viện'
        ])
        
        scored_docs = []
        
        for doc in documents:
            content_lower = doc.page_content.lower()
            source = doc.metadata.get('source', '').lower()
            
            # 1. Keyword overlap (40%)
            keyword_score = self._calculate_keyword_overlap(query_terms, content_lower)
            
            # 2. Query term frequency (30%)
            frequency_score = self._calculate_term_frequency(query_terms, content_lower)
            
            # 3. Document length penalty (15%)
            length_score = self._calculate_length_score(doc.page_content)
            
            # 4. Keyword position bonus (15%)
            position_score = self._calculate_position_score(query_terms, content_lower)
            
            # Tổng hợp score
            total_score = (
                0.40 * keyword_score +
                0.30 * frequency_score +
                0.15 * length_score +
                0.15 * position_score
            )
            
            # Penalty: đề cương/syllabus không nên được ưu tiên cho câu hỏi kỹ thuật
            is_syllabus = any(kw in content_lower for kw in [
                'đề cương', 'tín chỉ', 'học phần', 'giảng viên', 'kiểm tra',
                'syllabus', 'credit', 'course outline', 'thi trắc nghiệm'
            ])
            if is_technical_query and is_syllabus:
                total_score *= 0.4  # Giảm 60% score cho đề cương khi hỏi kỹ thuật
            
            scored_docs.append((doc, total_score))
        
        return scored_docs
    
    def _llm_rerank(self, query: str, documents: List[Document]) -> List[Tuple[Document, float]]:
        """
        Rerank bằng LLM (Gemini)
        
        LLM đánh giá độ liên quan của từng document với query
        """
        scored_docs = []
        
        for i, doc in enumerate(documents, 1):
            print(f"   Đánh giá document {i}/{len(documents)}...")
            
            prompt = f"""Evaluate the relevance of the following document to the query.

Query: {query}

Document:
{doc.page_content[:500]}

Rate the relevance on a scale of 0.0 to 1.0:
- 1.0: Highly relevant, directly answers the query
- 0.7-0.9: Relevant, contains useful information
- 0.4-0.6: Somewhat relevant, tangentially related
- 0.1-0.3: Barely relevant, mentions related topics
- 0.0: Not relevant at all

Respond with ONLY a number between 0.0 and 1.0, nothing else."""
            
            try:
                response = self.llm.invoke(prompt)
                score_text = response.content.strip()
                
                # Parse score
                score = float(re.findall(r'0\.\d+|1\.0|0|1', score_text)[0])
                score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
                
            except Exception as e:
                print(f"⚠️ Lỗi đánh giá document {i}: {e}")
                score = 0.5  # Default score
            
            scored_docs.append((doc, score))
        
        return scored_docs
    
    def _hybrid_rerank(self, query: str, documents: List[Document]) -> List[Tuple[Document, float]]:
        """
        Rerank bằng hybrid: heuristic + LLM cho top candidates
        
        1. Dùng heuristic để lọc nhanh
        2. Dùng LLM để đánh giá chính xác top candidates
        """
        # Bước 1: Heuristic rerank tất cả
        heuristic_scores = self._heuristic_rerank(query, documents)
        heuristic_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Bước 2: Lấy top 5 candidates để LLM đánh giá
        top_candidates = heuristic_scores[:5]
        remaining = heuristic_scores[5:]
        
        # Bước 3: LLM rerank top candidates
        print(f"   🤖 LLM đánh giá top {len(top_candidates)} candidates...")
        llm_scored = []
        for doc, heuristic_score in top_candidates:
            llm_score = self._llm_score_single(query, doc)
            
            # Kết hợp heuristic + LLM (70% LLM, 30% heuristic)
            combined_score = 0.7 * llm_score + 0.3 * heuristic_score
            llm_scored.append((doc, combined_score))
        
        # Kết hợp lại
        final_scores = llm_scored + remaining
        
        return final_scores
    
    def _llm_score_single(self, query: str, doc: Document) -> float:
        """
        Đánh giá một document bằng LLM
        """
        prompt = f"""Rate relevance (0.0-1.0):

Query: {query}
Document: {doc.page_content[:400]}

Score (number only):"""
        
        try:
            response = self.llm.invoke(prompt)
            score_text = response.content.strip()
            score = float(re.findall(r'0\.\d+|1\.0|0|1', score_text)[0])
            return max(0.0, min(1.0, score))
        except:
            return 0.5
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Trích xuất keywords từ text
        """
        # Remove punctuation
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Split và loại bỏ stopwords
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                    'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
                    'là', 'của', 'và', 'có', 'được', 'trong', 'với', 'cho', 'về'}
        
        words = text.split()
        keywords = [w for w in words if len(w) > 2 and w not in stopwords]
        
        return keywords
    
    def _calculate_keyword_overlap(self, query_terms: List[str], content: str) -> float:
        """
        Tính tỷ lệ keywords xuất hiện trong content
        """
        if not query_terms:
            return 0.0
        
        matches = sum(1 for term in query_terms if term in content)
        return matches / len(query_terms)
    
    def _calculate_term_frequency(self, query_terms: List[str], content: str) -> float:
        """
        Tính tần suất xuất hiện của query terms
        """
        if not query_terms:
            return 0.0
        
        total_freq = sum(content.count(term) for term in query_terms)
        
        # Normalize by content length
        content_words = len(content.split())
        if content_words == 0:
            return 0.0
        
        normalized_freq = total_freq / content_words
        
        # Scale to [0, 1]
        return min(1.0, normalized_freq * 10)
    
    def _calculate_length_score(self, content: str) -> float:
        """
        Tính điểm dựa trên độ dài
        Ưu tiên documents có độ dài vừa phải
        """
        length = len(content)
        
        # Optimal length: 200-800 characters
        if 200 <= length <= 800:
            return 1.0
        elif length < 200:
            return length / 200
        else:  # length > 800
            return max(0.5, 1.0 - (length - 800) / 2000)
    
    def _calculate_position_score(self, query_terms: List[str], content: str) -> float:
        """
        Tính điểm dựa trên vị trí keywords
        Keywords ở đầu document có điểm cao hơn
        """
        if not query_terms:
            return 0.0
        
        # Tìm vị trí đầu tiên của mỗi keyword
        positions = []
        for term in query_terms:
            pos = content.find(term)
            if pos != -1:
                positions.append(pos)
        
        if not positions:
            return 0.0
        
        # Tính điểm dựa trên vị trí trung bình
        avg_position = sum(positions) / len(positions)
        content_length = len(content)
        
        # Normalize: keywords ở đầu (0-20%) có điểm cao
        normalized_pos = avg_position / content_length
        
        if normalized_pos < 0.2:
            return 1.0
        elif normalized_pos < 0.5:
            return 0.7
        else:
            return 0.4
    
    def filter_irrelevant(self, scored_docs: List[Tuple[Document, float]], 
                         threshold: float = 0.3) -> List[Tuple[Document, float]]:
        """
        Lọc bỏ documents không liên quan.
        FIX-P7: Luôn giữ ít nhất 1 document để tránh context rỗng gây hallucination.
        """
        if not scored_docs:
            return []

        filtered = [(doc, score) for doc, score in scored_docs if score >= threshold]
        
        removed_count = len(scored_docs) - len(filtered)
        if removed_count > 0:
            print(f"🗑️  Đã loại bỏ {removed_count} documents không liên quan (score < {threshold})")
        
        # Luôn giữ ít nhất 1 doc tốt nhất để tránh empty context
        if not filtered:
            best = max(scored_docs, key=lambda x: x[1])
            print(f"⚠️  Không doc nào đạt threshold, giữ lại doc tốt nhất (score={best[1]:.3f})")
            return [best]
        
        return filtered

def create_reranker(method="cross-encoder") -> Reranker:
    """
    Tạo reranker instance.
    Default: cross-encoder (chính xác, chạy local, không cần API).
    Fallback: heuristic nếu model không load được.
    """
    return Reranker(method=method)
