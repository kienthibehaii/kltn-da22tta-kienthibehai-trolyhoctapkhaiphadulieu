# config.py - Centralized Configuration
"""
Centralized configuration for RAG system.
All constants, paths, and settings in one place.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# PATHS
# ============================================================================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = BASE_DIR / "chroma_db_new"
CACHE_DIR = BASE_DIR / ".cache"
LOG_DIR = BASE_DIR / "logs"

# Create directories if not exist
CACHE_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Cache file paths
BM25_CACHE_PATH = CACHE_DIR / "bm25_index.pkl"
DOCUMENTS_CACHE_PATH = CHROMA_DIR / "documents.pkl"

# ============================================================================
# API KEYS
# ============================================================================
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_API_KEYS = os.getenv("GEMINI_API_KEYS")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Normalize: dùng bất kỳ key nào có sẵn làm GOOGLE_API_KEY
if not GOOGLE_API_KEY and GEMINI_API_KEY:
    GOOGLE_API_KEY = GEMINI_API_KEY
elif not GOOGLE_API_KEY and GEMINI_API_KEYS:
    _keys = [k.strip() for k in GEMINI_API_KEYS.replace(';', ',').split(',') if k.strip()]
    if _keys:
        GOOGLE_API_KEY = _keys[0]

MONGODB_URI = os.getenv("MONGODB_URI")

# ============================================================================
# MODEL SETTINGS
# ============================================================================
# Embedding model
# Ghi chú: paraphrase-multilingual-MiniLM-L12-v2 tốt hơn cho tiếng Việt (471MB)
# nhưng cần đủ dung lượng disk (~500MB) để download lần đầu.
# Nếu disk không đủ, dùng lại all-MiniLM-L6-v2 (đã có sẵn trong cache).
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384

# LLM model
LLM_MODEL_NAME = "gemini-2.5-flash"
LLM_TEMPERATURE = 0.0
LLM_TIMEOUT = 60   # Tăng từ 10s → 60s để xử lý câu hỏi phức tạp
LLM_MAX_RETRIES = 2

# ============================================================================
# CHUNKING SETTINGS
# ============================================================================
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
USE_SEMANTIC_CHUNKING = True  # Set to True to enable semantic chunking

# ============================================================================
# RETRIEVAL SETTINGS
# ============================================================================
# Vector search
VECTOR_SEARCH_K = 5  # Number of results per sub-query

# Hybrid search — FIX-P10: Vector 70% > BM25 30%
USE_HYBRID_SEARCH = True
VECTOR_WEIGHT = 0.7
BM25_WEIGHT = 0.3

# Reranking — dùng BAAI/bge-reranker-v2-m3 (local, multilingual)
USE_RERANKING = True
RETRIEVE_K = 20          # candidates từ HybridRetriever trước khi rerank
RERANK_TOP_K = 5         # context cho LLM sau rerank
RERANK_THRESHOLD = 0.20  # filter docs dưới ngưỡng này (hạ từ 0.35 để không lọc hết tài liệu)
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"  # model ưu tiên

# ============================================================================
# TRANSLATION SETTINGS
# ============================================================================
ENABLE_TRANSLATION = False  # Tắt translation để tránh rate limit
TRANSLATION_MAX_RETRIES = 2
TRANSLATION_RETRY_DELAY = 2  # seconds

# ============================================================================
# PERFORMANCE SETTINGS
# ============================================================================
# Caching
ENABLE_EMBEDDING_CACHE = True
ENABLE_BM25_CACHE = True
ENABLE_VECTOR_DB_CACHE = True

# Async processing
ENABLE_ASYNC_PROCESSING = True
MAX_CONCURRENT_TASKS = 3

# Batch processing
EMBEDDING_BATCH_SIZE = 100
VECTOR_DB_BATCH_SIZE = 100

# ============================================================================
# UI SETTINGS
# ============================================================================
PAGE_TITLE = "Trợ lý Khai phá dữ liệu"
PAGE_ICON = "📚"
MAX_HISTORY_MESSAGES = 10
SESSION_TIMEOUT = 3600  # seconds

# ============================================================================
# LOGGING SETTINGS
# ============================================================================
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = LOG_DIR / "rag_system.log"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# ============================================================================
# RATE LIMITING
# ============================================================================
API_RATE_LIMIT = 15  # requests per minute
API_RATE_PERIOD = 60  # seconds

# ============================================================================
# VALIDATION
# ============================================================================
def validate_config():
    """Validate configuration settings"""
    errors = []
    
    if not GOOGLE_API_KEY and not os.getenv("GEMINI_API_KEYS") and not os.getenv("GEMINI_API_KEY"):
        errors.append("Neither GOOGLE_API_KEY nor GEMINI_API_KEY nor GEMINI_API_KEYS found in environment variables")
    
    if not DATA_DIR.exists():
        errors.append(f"Data directory not found: {DATA_DIR}")
    
    if CHUNK_SIZE < 100:
        errors.append(f"CHUNK_SIZE too small: {CHUNK_SIZE}")
    
    if CHUNK_OVERLAP >= CHUNK_SIZE:
        errors.append(f"CHUNK_OVERLAP must be less than CHUNK_SIZE")
    
    if VECTOR_WEIGHT + BM25_WEIGHT != 1.0:
        errors.append(f"VECTOR_WEIGHT + BM25_WEIGHT must equal 1.0")
    
    if errors:
        raise ValueError(f"Configuration errors:\n" + "\n".join(errors))
    
    return True

# Validate on import
validate_config()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def get_cache_path(name: str) -> Path:
    """Get cache file path"""
    return CACHE_DIR / f"{name}.pkl"

def get_log_path(name: str) -> Path:
    """Get log file path"""
    return LOG_DIR / f"{name}.log"

# ============================================================================
# EXPORT
# ============================================================================
__all__ = [
    # Paths
    'BASE_DIR', 'DATA_DIR', 'CHROMA_DIR', 'CACHE_DIR', 'LOG_DIR',
    'BM25_CACHE_PATH', 'DOCUMENTS_CACHE_PATH',
    
    # API Keys
    'GOOGLE_API_KEY', 'MONGODB_URI',
    
    # Model settings
    'EMBEDDING_MODEL_NAME', 'EMBEDDING_DIMENSION',
    'LLM_MODEL_NAME', 'LLM_TEMPERATURE', 'LLM_TIMEOUT', 'LLM_MAX_RETRIES',
    
    # Chunking
    'CHUNK_SIZE', 'CHUNK_OVERLAP', 'USE_SEMANTIC_CHUNKING',
    
    # Retrieval
    'VECTOR_SEARCH_K', 'USE_HYBRID_SEARCH', 'VECTOR_WEIGHT', 'BM25_WEIGHT',
    'USE_RERANKING', 'RETRIEVE_K', 'RERANK_TOP_K', 'RERANK_THRESHOLD', 'RERANK_MODEL',
    
    # Translation
    'ENABLE_TRANSLATION', 'TRANSLATION_MAX_RETRIES', 'TRANSLATION_RETRY_DELAY',
    
    # Performance
    'ENABLE_EMBEDDING_CACHE', 'ENABLE_BM25_CACHE', 'ENABLE_VECTOR_DB_CACHE',
    'ENABLE_ASYNC_PROCESSING', 'MAX_CONCURRENT_TASKS',
    'EMBEDDING_BATCH_SIZE', 'VECTOR_DB_BATCH_SIZE',
    
    # UI
    'PAGE_TITLE', 'PAGE_ICON', 'MAX_HISTORY_MESSAGES', 'SESSION_TIMEOUT',
    
    # Logging
    'LOG_LEVEL', 'LOG_FORMAT', 'LOG_FILE', 'LOG_MAX_BYTES', 'LOG_BACKUP_COUNT',
    
    # Rate limiting
    'API_RATE_LIMIT', 'API_RATE_PERIOD',
    
    # Functions
    'validate_config', 'get_cache_path', 'get_log_path'
]
