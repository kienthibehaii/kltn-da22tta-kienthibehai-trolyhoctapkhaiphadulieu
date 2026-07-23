# embed_store.py - Tạo embedding và lưu vào Chroma
import os
import sys
import pickle

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(errors='replace')
    except Exception:
        pass

from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from loader import load_all_documents
from config import USE_SEMANTIC_CHUNKING

# Nạp biến môi trường từ file .env
load_dotenv()

# Singleton cache đơn giản (không cần Streamlit)
_embeddings_instance = None

def get_embeddings():
    """
    Tạo hoặc load embedding model (singleton pattern).
    Dùng model từ config.py để đồng bộ toàn hệ thống.
    """
    global _embeddings_instance
    if _embeddings_instance is None:
        from config import EMBEDDING_MODEL_NAME
        print(f"...Đang khởi tạo embedding model: {EMBEDDING_MODEL_NAME}...")
        _embeddings_instance = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME
        )
        print("✅ Embedding model đã sẵn sàng.")
    return _embeddings_instance

def create_vector_store(chunks, persist_directory="chroma_db"):
    """
    Tạo embedding cho các chunks và lưu vào Chroma.
    - chunks: danh sách các Document đã chia nhỏ.
    - persist_directory: thư mục lưu dữ liệu Chroma.
    """
    persist_directory = os.path.abspath(persist_directory)
    # Khởi tạo mô hình embedding từ HuggingFace (cached)
    embeddings = get_embeddings()
    
    # Tạo Chroma vector store từ danh sách chunks
    # Nếu thư mục đã tồn tại, Chroma sẽ ghi đè hoặc nạp thêm (tùy tham số)
    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_directory
    )
    # Lưu xuống đĩa (mặc định Chroma tự lưu khi tạo, nhưng gọi persist để chắc chắn)
    vectordb.persist()
    print(f"✅ Đã lưu {vectordb._collection.count()} vectors vào {persist_directory}")
    
    # Lưu documents gốc để dùng cho BM25
    documents_path = os.path.join(persist_directory, "documents.pkl")
    with open(documents_path, 'wb') as f:
        pickle.dump(chunks, f)
    print(f"✅ Đã lưu {len(chunks)} documents gốc vào {documents_path}")
    
    return vectordb

def load_vector_store(persist_directory="chroma_db"):
    """
    Nạp vector store đã có sẵn từ đĩa (không cần tạo lại nếu dữ liệu không đổi).
    Sử dụng cached embeddings để tăng tốc.
    """
    persist_directory = os.path.abspath(persist_directory)
    embeddings = get_embeddings()
    vectordb = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings
    )
    print(f"✅ Đã nạp vector store với {vectordb._collection.count()} vectors.")
    return vectordb

def load_documents(persist_directory="chroma_db"):
    """
    Load documents gốc từ file
    """
    persist_directory = os.path.abspath(persist_directory)
    documents_path = os.path.join(persist_directory, "documents.pkl")
    if os.path.exists(documents_path):
        with open(documents_path, 'rb') as f:
            documents = pickle.load(f)
        print(f"Đã load {len(documents)} documents gốc từ {documents_path}")
        return documents
    else:
        print(f"⚠️ Không tìm thấy {documents_path}")
        print("Đang load lại từ thư mục data...")
        documents = load_all_documents("data", use_semantic_chunking=USE_SEMANTIC_CHUNKING)
        # Lưu lại để lần sau không phải load lại
        with open(documents_path, 'wb') as f:
            pickle.dump(documents, f)
        return documents

if __name__ == "__main__":
    # Bước 1: Đọc và chunk dữ liệu
    print("Đang đọc dữ liệu từ thư mục data...")
    chunks = load_all_documents("data", use_semantic_chunking=USE_SEMANTIC_CHUNKING)
    
    # Bước 2: Tạo embedding và lưu vào Chroma
    print("Đang tạo embedding và lưu vào Chroma...")
    vectordb = create_vector_store(chunks, persist_directory="chroma_db_new")
    print("Hoàn tất!")