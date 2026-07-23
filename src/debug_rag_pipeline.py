# debug_rag_pipeline.py - Công cụ debug toàn diện cho RAG pipeline
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class RAGDebugger:
    """Debug từng bước trong RAG pipeline"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.success = []
        
    def log_error(self, step, message):
        self.errors.append(f"❌ [{step}] {message}")
        print(f"❌ [{step}] {message}")
    
    def log_warning(self, step, message):
        self.warnings.append(f"⚠️  [{step}] {message}")
        print(f"⚠️  [{step}] {message}")
    
    def log_success(self, step, message):
        self.success.append(f"✅ [{step}] {message}")
        print(f"✅ [{step}] {message}")
    
    def print_summary(self):
        print("\n" + "="*60)
        print("📊 TỔNG KẾT DEBUG")
        print("="*60)
        print(f"✅ Thành công: {len(self.success)}")
        print(f"⚠️  Cảnh báo: {len(self.warnings)}")
        print(f"❌ Lỗi: {len(self.errors)}")
        
        if self.errors:
            print("\n🔴 CÁC LỖI CẦN SỬA:")
            for err in self.errors:
                print(f"  {err}")
        
        if self.warnings:
            print("\n🟡 CÁC CẢNH BÁO:")
            for warn in self.warnings:
                print(f"  {warn}")
    
    # BƯỚC 1: Kiểm tra môi trường
    def check_environment(self):
        print("\n" + "="*60)
        print("BƯỚC 1: KIỂM TRA MÔI TRƯỜNG")
        print("="*60)
        
        # Kiểm tra Python version
        python_version = sys.version_info
        if python_version.major == 3 and python_version.minor >= 8:
            self.log_success("Python", f"Version {python_version.major}.{python_version.minor}.{python_version.micro}")
        else:
            self.log_error("Python", f"Cần Python 3.8+, hiện tại: {python_version.major}.{python_version.minor}")
        
        # Kiểm tra API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            self.log_success("API Key", f"Đã tìm thấy (độ dài: {len(api_key)})")
        else:
            self.log_error("API Key", "Không tìm thấy GOOGLE_API_KEY trong .env")
        
        # Kiểm tra thư viện
        required_libs = [
            "langchain",
            "langchain_google_genai",
            "chromadb",
            "pypdf",
            "pptx",
            "streamlit",
            "rank_bm25"
        ]
        
        for lib in required_libs:
            try:
                __import__(lib)
                self.log_success("Library", f"{lib} đã cài đặt")
            except ImportError:
                self.log_error("Library", f"{lib} chưa cài đặt - chạy: pip install {lib}")
    
    # BƯỚC 2: Kiểm tra dữ liệu
    def check_data(self, data_folder="data"):
        print("\n" + "="*60)
        print("BƯỚC 2: KIỂM TRA DỮ LIỆU")
        print("="*60)
        
        if not os.path.exists(data_folder):
            self.log_error("Data Folder", f"Thư mục {data_folder} không tồn tại!")
            return False
        
        files = os.listdir(data_folder)
        pdf_files = [f for f in files if f.endswith('.pdf')]
        pptx_files = [f for f in files if f.endswith('.pptx')]
        
        if not pdf_files and not pptx_files:
            self.log_error("Data Files", "Không tìm thấy file PDF hoặc PPTX nào!")
            return False
        
        self.log_success("Data Files", f"Tìm thấy {len(pdf_files)} PDF, {len(pptx_files)} PPTX")
        
        # Kiểm tra từng file
        for pdf in pdf_files:
            file_path = os.path.join(data_folder, pdf)
            size = os.path.getsize(file_path)
            if size == 0:
                self.log_error("PDF", f"{pdf} có kích thước 0 bytes!")
            else:
                self.log_success("PDF", f"{pdf} ({size/1024:.1f} KB)")
        
        for pptx in pptx_files:
            file_path = os.path.join(data_folder, pptx)
            size = os.path.getsize(file_path)
            if size == 0:
                self.log_error("PPTX", f"{pptx} có kích thước 0 bytes!")
            else:
                self.log_success("PPTX", f"{pptx} ({size/1024:.1f} KB)")
        
        return True
    
    # BƯỚC 3: Test load documents
    def test_load_documents(self, data_folder="data"):
        print("\n" + "="*60)
        print("BƯỚC 3: TEST LOAD DOCUMENTS")
        print("="*60)
        
        try:
            from loader import load_all_documents
            
            print("🔄 Đang load documents...")
            chunks = load_all_documents(data_folder, use_semantic_chunking=False)
            
            if not chunks:
                self.log_error("Load", "Không load được document nào!")
                return None
            
            self.log_success("Load", f"Load thành công {len(chunks)} chunks")
            
            # Kiểm tra chunk đầu tiên
            first_chunk = chunks[0]
            print(f"\n📄 Chunk đầu tiên:")
            print(f"  - Độ dài: {len(first_chunk.page_content)} ký tự")
            print(f"  - Metadata: {first_chunk.metadata}")
            print(f"  - Nội dung (100 ký tự đầu): {first_chunk.page_content[:100]}...")
            
            # Thống kê
            total_chars = sum(len(c.page_content) for c in chunks)
            avg_chars = total_chars / len(chunks)
            
            print(f"\n📊 Thống kê chunks:")
            print(f"  - Tổng số chunks: {len(chunks)}")
            print(f"  - Tổng ký tự: {total_chars:,}")
            print(f"  - Trung bình: {avg_chars:.0f} ký tự/chunk")
            
            # Cảnh báo nếu chunk quá nhỏ hoặc quá lớn
            if avg_chars < 200:
                self.log_warning("Chunking", f"Chunk trung bình quá nhỏ ({avg_chars:.0f} ký tự)")
            elif avg_chars > 2000:
                self.log_warning("Chunking", f"Chunk trung bình quá lớn ({avg_chars:.0f} ký tự)")
            else:
                self.log_success("Chunking", f"Kích thước chunk hợp lý ({avg_chars:.0f} ký tự)")
            
            return chunks
            
        except Exception as e:
            self.log_error("Load", f"Lỗi khi load: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None
    
    # BƯỚC 4: Test embedding
    def test_embedding(self, chunks):
        print("\n" + "="*60)
        print("BƯỚC 4: TEST EMBEDDING")
        print("="*60)
        
        if not chunks:
            self.log_error("Embedding", "Không có chunks để test!")
            return None
        
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            
            print("🔄 Đang khởi tạo embedding model...")
            embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            
            # Test embed 1 chunk
            test_text = chunks[0].page_content[:500]
            print(f"🔄 Đang embed text mẫu ({len(test_text)} ký tự)...")
            
            vector = embeddings.embed_query(test_text)
            
            self.log_success("Embedding", f"Tạo vector thành công (dimension: {len(vector)})")
            print(f"  - Vector đầu tiên (5 số): {vector[:5]}")
            
            return embeddings
            
        except Exception as e:
            self.log_error("Embedding", f"Lỗi khi tạo embedding: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None
    
    # BƯỚC 5: Test vector store
    def test_vector_store(self, chunks, persist_directory="chroma_db_test"):
        print("\n" + "="*60)
        print("BƯỚC 5: TEST VECTOR STORE")
        print("="*60)
        
        if not chunks:
            self.log_error("Vector Store", "Không có chunks để test!")
            return None
        
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            from langchain_community.vectorstores import Chroma
            
            print("🔄 Đang tạo vector store...")
            embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            
            # Chỉ test với 10 chunks đầu tiên để nhanh
            test_chunks = chunks[:10]
            
            vectordb = Chroma.from_documents(
                documents=test_chunks,
                embedding=embeddings,
                persist_directory=persist_directory
            )
            
            count = vectordb._collection.count()
            self.log_success("Vector Store", f"Tạo thành công {count} vectors")
            
            # Test search
            print("\n🔍 Test search với query: 'clustering'")
            results = vectordb.similarity_search("clustering", k=3)
            
            if results:
                self.log_success("Search", f"Tìm thấy {len(results)} kết quả")
                print(f"\n📄 Kết quả đầu tiên:")
                print(f"  - Nội dung: {results[0].page_content[:200]}...")
                print(f"  - Metadata: {results[0].metadata}")
            else:
                self.log_warning("Search", "Không tìm thấy kết quả nào")
            
            return vectordb
            
        except Exception as e:
            self.log_error("Vector Store", f"Lỗi: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None
    
    # BƯỚC 6: Test retriever
    def test_retriever(self, vectordb):
        print("\n" + "="*60)
        print("BƯỚC 6: TEST RETRIEVER")
        print("="*60)
        
        if not vectordb:
            self.log_error("Retriever", "Không có vector store để test!")
            return None
        
        try:
            retriever = vectordb.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )
            
            # Test với nhiều query khác nhau
            test_queries = [
                "What is clustering?",
                "Phân cụm là gì?",
                "data mining",
                "association rules"
            ]
            
            for query in test_queries:
                print(f"\n🔍 Query: '{query}'")
                docs = retriever.get_relevant_documents(query)
                
                if docs:
                    self.log_success("Retriever", f"Tìm thấy {len(docs)} documents")
                    print(f"  - Doc đầu: {docs[0].page_content[:100]}...")
                else:
                    self.log_warning("Retriever", f"Không tìm thấy doc cho query: {query}")
            
            return retriever
            
        except Exception as e:
            self.log_error("Retriever", f"Lỗi: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None
    
    # BƯỚC 7: Test LLM (Gemini)
    def test_llm(self):
        print("\n" + "="*60)
        print("BƯỚC 7: TEST LLM (GEMINI)")
        print("="*60)
        
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                self.log_error("LLM", "Không tìm thấy GOOGLE_API_KEY!")
                return None
            
            print("🔄 Đang khởi tạo Gemini...")
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-exp",
                google_api_key=api_key,
                temperature=0.3
            )
            
            # Test với câu hỏi đơn giản
            test_prompt = "What is 2+2? Answer in one word."
            print(f"🔄 Test prompt: '{test_prompt}'")
            
            response = llm.invoke(test_prompt)
            answer = response.content if hasattr(response, 'content') else str(response)
            
            self.log_success("LLM", f"Gemini phản hồi: '{answer}'")
            
            return llm
            
        except Exception as e:
            self.log_error("LLM", f"Lỗi: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None
    
    # BƯỚC 8: Test RAG chain
    def test_rag_chain(self, vectordb):
        print("\n" + "="*60)
        print("BƯỚC 8: TEST RAG CHAIN")
        print("="*60)
        
        if not vectordb:
            self.log_error("RAG Chain", "Không có vector store!")
            return None
        
        try:
            from rag import create_qa_chain, ask_question
            
            print("🔄 Đang tạo QA chain...")
            qa_chain, retriever = create_qa_chain(vectordb, use_hybrid=False)
            
            self.log_success("RAG Chain", "Tạo chain thành công")
            
            # Test với câu hỏi
            test_question = "What is clustering?"
            print(f"\n🔍 Test question: '{test_question}'")
            print("🔄 Đang gọi RAG pipeline...")
            
            answer, sources, citations = ask_question(
                qa_chain, retriever, test_question, use_rerank=False
            )
            
            self.log_success("RAG Answer", f"Nhận được câu trả lời ({len(answer)} ký tự)")
            print(f"\n📝 Câu trả lời:")
            print(f"{answer[:300]}...")
            
            print(f"\n📚 Số nguồn: {len(sources)}")
            print(f"📚 Số citations: {len(citations)}")
            
            if citations:
                print(f"\n📄 Citation đầu tiên:")
                print(f"  - File: {citations[0]['filename']}")
                print(f"  - Page: {citations[0]['page']}")
                print(f"  - Content: {citations[0]['content'][:100]}...")
            
            return qa_chain, retriever
            
        except Exception as e:
            self.log_error("RAG Chain", f"Lỗi: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None, None
    
    # BƯỚC 9: Test reranking
    def test_reranking(self, retriever):
        print("\n" + "="*60)
        print("BƯỚC 9: TEST RERANKING")
        print("="*60)
        
        if not retriever:
            self.log_error("Reranking", "Không có retriever!")
            return
        
        try:
            from reranker import create_reranker
            
            print("🔄 Đang tạo reranker...")
            reranker = create_reranker(method="hybrid")
            
            # Lấy documents
            query = "clustering algorithms"
            docs = retriever.get_relevant_documents(query)[:10]
            
            if not docs:
                self.log_warning("Reranking", "Không có docs để rerank!")
                return
            
            print(f"🔄 Đang rerank {len(docs)} documents...")
            scored_docs = reranker.rerank(query, docs, top_k=3)
            
            self.log_success("Reranking", f"Rerank thành công, top 3:")
            for i, (doc, score) in enumerate(scored_docs, 1):
                print(f"  {i}. Score: {score:.3f} - {doc.page_content[:80]}...")
            
        except Exception as e:
            self.log_error("Reranking", f"Lỗi: {str(e)}")
            import traceback
            print(traceback.format_exc())
    
    # BƯỚC 10: Test hybrid search
    def test_hybrid_search(self, vectordb, chunks):
        print("\n" + "="*60)
        print("BƯỚC 10: TEST HYBRID SEARCH")
        print("="*60)
        
        if not vectordb or not chunks:
            self.log_error("Hybrid Search", "Thiếu vectordb hoặc chunks!")
            return
        
        try:
            from hybrid_retriever import create_hybrid_retriever
            
            print("🔄 Đang tạo hybrid retriever...")
            hybrid_retriever = create_hybrid_retriever(
                vectordb, chunks[:10], vector_weight=0.5, bm25_weight=0.5
            )
            
            # Test search
            query = "clustering"
            print(f"🔍 Test query: '{query}'")
            results = hybrid_retriever.invoke(query, k=5)
            
            self.log_success("Hybrid Search", f"Tìm thấy {len(results)} kết quả")
            
            for i, doc in enumerate(results[:3], 1):
                print(f"  {i}. {doc.page_content[:80]}...")
            
        except Exception as e:
            self.log_error("Hybrid Search", f"Lỗi: {str(e)}")
            import traceback
            print(traceback.format_exc())


def main():
    """Chạy debug toàn bộ pipeline"""
    print("="*60)
    print("🔧 RAG PIPELINE DEBUGGER")
    print("="*60)
    print(f"⏰ Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    debugger = RAGDebugger()
    
    # Chạy từng bước
    debugger.check_environment()
    
    if debugger.check_data("data"):
        chunks = debugger.test_load_documents("data")
        
        if chunks:
            embeddings = debugger.test_embedding(chunks)
            
            if embeddings:
                vectordb = debugger.test_vector_store(chunks)
                
                if vectordb:
                    retriever = debugger.test_retriever(vectordb)
                    
                    llm = debugger.test_llm()
                    
                    if llm:
                        qa_chain, retriever = debugger.test_rag_chain(vectordb)
                        
                        if retriever:
                            debugger.test_reranking(retriever)
                            debugger.test_hybrid_search(vectordb, chunks)
    
    # In tổng kết
    debugger.print_summary()
    
    print("\n" + "="*60)
    print("✅ HOÀN TẤT DEBUG")
    print("="*60)


if __name__ == "__main__":
    main()
