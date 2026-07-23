# hybrid_retriever.py - Hybrid Search kết hợp Vector + BM25
import os
import pickle
import threading
from typing import List, Dict, Tuple
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
import numpy as np

class HybridRetriever:
    """
    Hybrid Retriever kết hợp:
    1. Vector Search (semantic similarity)
    2. BM25 Keyword Search (lexical matching)
    
    Sau đó rerank kết quả theo độ liên quan
    """
    
    def __init__(self, vectordb, documents: List[Document], 
                 vector_weight=0.5, bm25_weight=0.5, 
                 bm25_index_path="chroma_db_new/bm25_index.pkl"):
        """
        Khởi tạo Hybrid Retriever
        
        Args:
            vectordb: Chroma vector database
            documents: Danh sách documents gốc
            vector_weight: Trọng số cho vector search (0-1)
            bm25_weight: Trọng số cho BM25 search (0-1)
            bm25_index_path: Đường dẫn lưu BM25 index
        """
        self.vectordb = vectordb
        self.documents = documents
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.bm25_index_path = bm25_index_path
        self._vectordb_lock = threading.Lock()  # Thread-safety lock for ChromaDB
        
        # Tạo hoặc load BM25 index
        if os.path.exists(bm25_index_path):
            print(f"📂 Đang load BM25 index từ {bm25_index_path}...")
            self.load_bm25_index(bm25_index_path)
        else:
            print("🔍 Đang tạo BM25 index mới...")
            self._create_bm25_index()
            # Auto-save sau khi tạo
            self.save_bm25_index(bm25_index_path)
            print(f"✅ Đã tạo và lưu BM25 index với {len(self.documents)} documents")
    
    def _create_bm25_index(self):
        """
        Tạo BM25 index từ documents
        """
        # Tokenize documents
        tokenized_docs = [self._tokenize(doc.page_content) for doc in self.documents]
        
        # Tạo BM25 index
        self.bm25 = BM25Okapi(tokenized_docs)
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text thành list of tokens.
        FIX-P5: Thêm bigram cho tiếng Việt để xử lý cụm từ như 'khai phá', 'phân cụm'.
        """
        text = text.lower()
        import re
        text = re.sub(r'[^\w\s]', ' ', text)
        words = [t for t in text.split() if len(t) > 1]  # len > 1 thay vì > 2

        tokens = list(words)

        # Thêm bigrams quan trọng cho tiếng Việt
        vi_bigram_pairs = {
            ('khai', 'phá'), ('phân', 'cụm'), ('phân', 'lớp'), ('học', 'máy'),
            ('dữ', 'liệu'), ('mạng', 'nơ-ron'), ('cây', 'quyết'), ('quyết', 'định'),
            ('hồi', 'quy'), ('véc', 'tơ'), ('luật', 'kết'), ('kết', 'hợp'),
            ('tập', 'phổ'), ('phổ', 'biến'), ('tiền', 'xử'), ('xử', 'lý'),
            ('knowledge', 'discovery'), ('data', 'mining'), ('decision', 'tree'),
            ('random', 'forest'), ('naive', 'bayes'), ('support', 'vector'),
            ('neural', 'network'), ('deep', 'learning'), ('k', 'means'),
        }
        for i in range(len(words) - 1):
            pair = (words[i], words[i+1])
            if pair in vi_bigram_pairs:
                tokens.append(f"{words[i]}_{words[i+1]}")

        return tokens
    
    def _vector_search(self, query: str, k: int = 10, filter: dict = None) -> List[Tuple[Document, float]]:
        """Tìm kiếm bằng vector similarity (thread-safe)"""
        with self._vectordb_lock:
            results = self.vectordb.similarity_search_with_score(query, k=k, filter=filter)

        # ChromaDB cosine distance ∈ [0, 2] → similarity ∈ [0, 1]
        # Công thức đúng: similarity = 1 - distance/2
        results_with_similarity = []
        for doc, distance in results:
            similarity = max(0.0, 1.0 - distance / 2.0)
            results_with_similarity.append((doc, similarity))

        return results_with_similarity
    
    def _bm25_search(self, query: str, k: int = 10, filter: dict = None) -> List[Tuple[Document, float]]:
        """
        Tìm kiếm bằng BM25
        
        Args:
            query: Câu query
            k: Số lượng kết quả
            filter: Metadata filter (tùy chọn)
        
        Returns:
            List of (document, score) tuples
        """
        # Tokenize query
        tokenized_query = self._tokenize(query)
        
        # Tính BM25 scores
        scores = self.bm25.get_scores(tokenized_query)
        
        # Lấy top k
        top_k_indices = np.argsort(scores)[::-1]
        
        results = []
        max_score = None
        
        for idx in top_k_indices:
            if len(results) >= k:
                break
                
            doc = self.documents[idx]
            
            # Apply filter
            if filter:
                match = True
                for key, val in filter.items():
                    doc_val = doc.metadata.get(key)
                    if isinstance(val, dict) and "$in" in val:
                        allowed_vals = val["$in"]
                        if key == "source":
                            doc_source = doc_val or ""
                            import os
                            match_found = False
                            for allowed_val in allowed_vals:
                                if allowed_val in doc_source or allowed_val in os.path.basename(doc_source):
                                    match_found = True
                                    break
                            if not match_found:
                                match = False
                                break
                        elif doc_val not in allowed_vals:
                            match = False
                            break
                    else:
                        if key == "source":
                            doc_source = doc_val or ""
                            import os
                            if os.path.basename(doc_source) != val and doc_source != val:
                                match = False
                                break
                        elif doc_val != val:
                            match = False
                            break
                if not match:
                    continue
                    
            if scores[idx] > 0:
                if max_score is None:
                    max_score = scores[idx]
                normalized_score = scores[idx] / max_score if max_score > 0 else 0
                results.append((doc, normalized_score))
        
        return results
    
    def _reciprocal_rank_fusion(self, 
                                 vector_results: List[Tuple[Document, float]], 
                                 bm25_results: List[Tuple[Document, float]],
                                 k: int = 60) -> List[Tuple[Document, float]]:
        """
        Kết hợp kết quả từ vector và BM25 bằng Reciprocal Rank Fusion
        
        Args:
            vector_results: Kết quả từ vector search
            bm25_results: Kết quả từ BM25 search
            k: Constant cho RRF (mặc định: 60)
        
        Returns:
            List of (document, fused_score) tuples
        """
        # Tạo dict để lưu scores
        doc_scores = {}
        
        # Thêm scores từ vector search
        for rank, (doc, score) in enumerate(vector_results, 1):
            doc_id = id(doc)  # Sử dụng id của document
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    'doc': doc,
                    'vector_score': 0,
                    'bm25_score': 0,
                    'vector_rank': 0,
                    'bm25_rank': 0
                }
            doc_scores[doc_id]['vector_score'] = score
            doc_scores[doc_id]['vector_rank'] = rank
        
        # Thêm scores từ BM25 search
        for rank, (doc, score) in enumerate(bm25_results, 1):
            doc_id = id(doc)
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    'doc': doc,
                    'vector_score': 0,
                    'bm25_score': 0,
                    'vector_rank': 0,
                    'bm25_rank': 0
                }
            doc_scores[doc_id]['bm25_score'] = score
            doc_scores[doc_id]['bm25_rank'] = rank
        
        # Tính RRF score
        for doc_id in doc_scores:
            vector_rank = doc_scores[doc_id]['vector_rank']
            bm25_rank = doc_scores[doc_id]['bm25_rank']
            
            rrf_score = 0
            if vector_rank > 0:
                rrf_score += self.vector_weight / (k + vector_rank)
            if bm25_rank > 0:
                rrf_score += self.bm25_weight / (k + bm25_rank)
            
            doc_scores[doc_id]['rrf_score'] = rrf_score
        
        # Sắp xếp theo RRF score
        sorted_docs = sorted(doc_scores.values(), 
                           key=lambda x: x['rrf_score'], 
                           reverse=True)
        
        # Trả về list of (document, score)
        results = [(item['doc'], item['rrf_score']) for item in sorted_docs]
        
        return results
    
    def _weighted_score_fusion(self,
                               vector_results: List[Tuple[Document, float]], 
                               bm25_results: List[Tuple[Document, float]]) -> List[Tuple[Document, float]]:
        """
        Kết hợp kết quả bằng weighted score
        
        Args:
            vector_results: Kết quả từ vector search
            bm25_results: Kết quả từ BM25 search
        
        Returns:
            List of (document, fused_score) tuples
        """
        # Tạo dict để lưu scores
        doc_scores = {}
        
        # Thêm scores từ vector search
        for doc, score in vector_results:
            doc_content = doc.page_content
            if doc_content not in doc_scores:
                doc_scores[doc_content] = {
                    'doc': doc,
                    'vector_score': 0,
                    'bm25_score': 0
                }
            doc_scores[doc_content]['vector_score'] = score
        
        # Thêm scores từ BM25 search
        for doc, score in bm25_results:
            doc_content = doc.page_content
            if doc_content not in doc_scores:
                doc_scores[doc_content] = {
                    'doc': doc,
                    'vector_score': 0,
                    'bm25_score': 0
                }
            doc_scores[doc_content]['bm25_score'] = score
        
        # Tính weighted score
        for doc_content in doc_scores:
            vector_score = doc_scores[doc_content]['vector_score']
            bm25_score = doc_scores[doc_content]['bm25_score']
            
            weighted_score = (self.vector_weight * vector_score + 
                            self.bm25_weight * bm25_score)
            
            doc_scores[doc_content]['weighted_score'] = weighted_score
        
        # Sắp xếp theo weighted score
        sorted_docs = sorted(doc_scores.values(), 
                           key=lambda x: x['weighted_score'], 
                           reverse=True)
        
        # Trả về list of (document, score)
        results = [(item['doc'], item['weighted_score']) for item in sorted_docs]
        
        return results
    
    def invoke(self, query: str, k: int = 5, fusion_method: str = "rrf", filter: dict = None) -> List[Document]:
        """
        Tìm kiếm hybrid (THREAD-SAFE: chạy tuần tự để tránh ChromaDB 'Already borrowed')
        
        Args:
            query: Câu query
            k: Số lượng kết quả cuối cùng
            fusion_method: Phương pháp fusion ("rrf" hoặc "weighted")
            filter: Bộ lọc metadata
        
        Returns:
            List of documents
        """
        # Chạy tuần tự Vector + BM25 (không dùng ThreadPoolExecutor) để tránh
        # lỗi ChromaDB "Already borrowed" khi được gọi từ thread pool bên ngoài
        vector_results = self._vector_search(query, k * 2, filter)
        bm25_results = self._bm25_search(query, k * 2, filter)
        
        print(f"🔍 Vector: {len(vector_results)} | BM25: {len(bm25_results)} results")
        
        # 2. Fusion
        if fusion_method == "rrf":
            fused_results = self._reciprocal_rank_fusion(vector_results, bm25_results)
        else:
            fused_results = self._weighted_score_fusion(vector_results, bm25_results)
        
        # 3. Lấy top k
        top_k_results = fused_results[:k]
        print(f"✅ Trả về {len(top_k_results)} kết quả sau fusion")
        
        # Trả về chỉ documents (không có scores)
        return [doc for doc, score in top_k_results]
    
    def get_relevant_documents(self, query: str, k: int = 5, filter: dict = None) -> List[Document]:
        """
        Alias cho invoke() để tương thích với LangChain retriever interface
        """
        return self.invoke(query, k=k, filter=filter)
    
    def save_bm25_index(self, filepath: str = "bm25_index.pkl"):
        """
        Lưu BM25 index ra file
        """
        with open(filepath, 'wb') as f:
            pickle.dump({
                'bm25': self.bm25,
                'documents': self.documents
            }, f)
        print(f"✅ Đã lưu BM25 index vào {filepath}")
    
    def load_bm25_index(self, filepath: str = "bm25_index.pkl"):
        """
        Load BM25 index từ file
        """
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.bm25 = data['bm25']
            self.documents = data['documents']
        print(f"✅ Đã load BM25 index từ {filepath}")

def create_hybrid_retriever(vectordb, documents: List[Document],
                           k: int = 10,
                           vector_weight: float = 0.5,
                           bm25_weight: float = 0.5) -> HybridRetriever:
    """
    Tạo hybrid retriever
    
    Args:
        vectordb: Chroma vector database
        documents: Danh sách documents gốc
        k: Số lượng documents trả về (default: 10)
        vector_weight: Trọng số cho vector search (0-1)
        bm25_weight: Trọng số cho BM25 search (0-1)
    
    Returns:
        HybridRetriever instance
    """
    retriever = HybridRetriever(vectordb, documents, vector_weight, bm25_weight)
    retriever.k = k  # Set k value
    return retriever
