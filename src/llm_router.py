import os
import socket
import threading
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# ============================================================================
# CACHING & HEALTH CHECK (singleton pattern)
# ============================================================================

# Cache LLM instances để tránh tạo lại mỗi lần gọi
_llm_cache = {}
_cache_lock = threading.Lock()

# One-time Ollama health check
_ollama_checked = False
_ollama_available = False

def _check_ollama_health():
    """Kiểm tra Ollama có đang chạy không (chỉ 1 lần duy nhất)"""
    global _ollama_checked, _ollama_available
    if _ollama_checked:
        return _ollama_available
    
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    # Parse URL để lấy host và port
    try:
        # Extract host:port from URL like http://localhost:11434
        from urllib.parse import urlparse
        parsed = urlparse(ollama_base_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 11434
        
        # Quick TCP connect check with 2s timeout
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        
        _ollama_available = (result == 0)
        if _ollama_available:
            print(f"[LLM Router] ✅ Ollama đang chạy tại {ollama_base_url}")
        else:
            print(f"[LLM Router] ⚠️ Ollama không chạy tại {ollama_base_url} → Bỏ qua Ollama, dùng Gemini trực tiếp (tiết kiệm ~15s/call)")
    except Exception as e:
        _ollama_available = False
        print(f"[LLM Router] ⚠️ Không thể kiểm tra Ollama: {e} → Dùng Gemini trực tiếp")
    
    _ollama_checked = True
    return _ollama_available

def get_llm(task_type="general", require_json=False, attempt=0, api_key=None, temperature=None):
    """
    Hybrid LLM Router: Returns an LLM configuration based on the task difficulty/requirements.
    
    OPTIMIZED: Cache LLM instances + skip Ollama if not running.
    
    Args:
        task_type: "general" | "complex" | "quiz_generation" | "quiz_evaluation"
        require_json: If true, ensures the model is better suited for strict JSON output.
        attempt: The current retry attempt. If > 0, skips Ollama to save time.
        api_key: Optional API key for Google Gemini (enables rotation)
        
    Returns:
        A Langchain ChatModel (with fallback configured if applicable)
    """
    global _ollama_checked, _ollama_available
    
    # Cache key: kết hợp task_type + api_key + require_json
    temp_value = 0.2 if temperature is None else float(temperature)
    cache_key = f"{task_type}|{api_key or 'default'}|{require_json}|{temp_value}"
    
    with _cache_lock:
        if cache_key in _llm_cache:
            return _llm_cache[cache_key]
    
    gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    gemini_api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    
    # 1. Khởi tạo Gemini
    gemini_llm = None
    try:
        gemini_llm = ChatGoogleGenerativeAI(
            model=gemini_model_name,
            google_api_key=gemini_api_key,
            temperature=temp_value,
            timeout=60
        )
    except Exception as e:
        print(f"[LLM Router] Không thể khởi tạo Gemini: {e}")

    # 2. Kiểm tra Ollama (one-time health check)
    # Nếu attempt > 0 hoặc task khó → bỏ qua Ollama luôn
    should_try_ollama = (
        os.getenv("ENABLE_OLLAMA", "false").lower() in {"1", "true", "yes", "on"}
        and
        task_type not in ["complex", "quiz_generation"]
        and attempt == 0
        and gemini_llm is not None  # Chỉ dùng Ollama nếu có Gemini làm fallback
    )
    
    if should_try_ollama:
        ollama_running = _check_ollama_health()
    else:
        ollama_running = False
    
    result_llm = None
    
    if ollama_running and gemini_llm:
        # Hybrid mode: Ollama → fallback → Gemini
        try:
            # Try multiple import paths for ChatOllama (version compatibility)
            try:
                from langchain_community.chat_models import ChatOllama
            except ImportError:
                try:
                    from langchain_community.chat_models.ollama import ChatOllama
                except ImportError:
                    from langchain_ollama import ChatOllama
            ollama_model_name = os.getenv("OLLAMA_MODEL", "qwen2.5")
            ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            ollama_llm = ChatOllama(
                model=ollama_model_name,
                base_url=ollama_base_url,
                temperature=temp_value,
                timeout=15
            )
            if require_json:
                ollama_llm = ollama_llm.bind(format="json")
            
            result_llm = ollama_llm.with_fallbacks([gemini_llm], exceptions_to_handle=(Exception,))
            print(f"[LLM Router] Hybrid (Ollama→Gemini) cho: {task_type}")
        except Exception as e:
            print(f"[LLM Router] Ollama init failed: {e}, dùng Gemini")
            result_llm = gemini_llm
    elif gemini_llm:
        # Gemini only (skip Ollama để tiết kiệm 15s timeout)
        if require_json:
            result_llm = gemini_llm
        else:
            result_llm = gemini_llm
        print(f"[LLM Router] Gemini trực tiếp cho: {task_type}")
    else:
        raise ValueError("Cả Ollama và Gemini đều không khả dụng!")
    
    # Cache instance
    with _cache_lock:
        _llm_cache[cache_key] = result_llm
    
    return result_llm
