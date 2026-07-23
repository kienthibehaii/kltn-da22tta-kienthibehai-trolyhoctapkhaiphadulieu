# services/rag-service/main.py
"""
RAG Service - Production Ready
Orchestrates the RAG pipeline with caching and async processing
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Optional
import httpx
import redis
import json
import hashlib
import time
import os
from celery import Celery

# ============================================================================
# CONFIGURATION
# ============================================================================
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:8011")
RETRIEVAL_SERVICE_URL = os.getenv("RETRIEVAL_SERVICE_URL", "http://localhost:8012")
RERANKING_SERVICE_URL = os.getenv("RERANKING_SERVICE_URL", "http://localhost:8013")
TRANSLATION_SERVICE_URL = os.getenv("TRANSLATION_SERVICE_URL", "http://localhost:8014")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# ============================================================================
# FASTAPI APP
# ============================================================================
app = FastAPI(
    title="RAG Service",
    description="Core RAG pipeline orchestration",
    version="1.0.0"
)

# Redis client
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# HTTP client
http_client = httpx.AsyncClient(timeout=60.0)

# Celery app
celery_app = Celery('tasks', broker=REDIS_URL, backend=REDIS_URL)

# ============================================================================
# MODELS
# ============================================================================

class QuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    use_context: bool = True
    use_cache: bool = True

class QuestionResponse(BaseModel):
    answer: str
    sources: List[Dict]
    citations: List[Dict]
    response_time: float
    from_cache: bool = False

# ============================================================================
# CACHE UTILITIES
# ============================================================================

def get_cache_key(prefix: str, data: str) -> str:
    """Generate cache key"""
    hash_value = hashlib.md5(data.encode()).hexdigest()
    return f"{prefix}:{hash_value}"

async def get_from_cache(key: str) -> Optional[Dict]:
    """Get from Redis cache"""
    try:
        cached = redis_client.get(key)
        if cached:
            return json.loads(cached)
    except:
        pass
    return None

async def set_to_cache(key: str, value: Dict, ttl: int = 3600):
    """Set to Redis cache with TTL"""
    try:
        redis_client.setex(key, ttl, json.dumps(value))
    except:
        pass

# ============================================================================
# RAG PIPELINE
# ============================================================================

async def rag_pipeline(question: str, use_cache: bool = True) -> Dict:
    """
    Complete RAG pipeline with caching
    
    Steps:
    1. Check cache
    2. Detect language & translate if needed
    3. Retrieve documents (hybrid search)
    4. Rerank documents
    5. Generate answer with LLM
    6. Translate back if needed
    7. Cache result
    """
    start_time = time.time()
    
    # Step 1: Check cache
    if use_cache:
        cache_key = get_cache_key("query", question)
        cached_result = await get_from_cache(cache_key)
        if cached_result:
            cached_result["from_cache"] = True
            cached_result["response_time"] = time.time() - start_time
            return cached_result
    
    # Step 2: Detect language
    lang_response = await http_client.post(
        f"{TRANSLATION_SERVICE_URL}/detect",
        json={"text": question}
    )
    language = lang_response.json()["language"]
    
    # Translate to English if Vietnamese
    question_en = question
    if language == "vi":
        trans_response = await http_client.post(
            f"{TRANSLATION_SERVICE_URL}/translate",
            json={"text": question, "target_lang": "en"}
        )
        question_en = trans_response.json()["translated_text"]
    
    # Step 3: Retrieve documents (hybrid search)
    retrieval_response = await http_client.post(
        f"{RETRIEVAL_SERVICE_URL}/search",
        json={"query": question_en, "k": 10, "method": "hybrid"}
    )
    documents = retrieval_response.json()["documents"]
    
    # Step 4: Rerank documents
    rerank_response = await http_client.post(
        f"{RERANKING_SERVICE_URL}/rerank",
        json={"query": question_en, "documents": documents, "top_k": 3}
    )
    reranked_docs = rerank_response.json()["documents"]
    
    # Step 5: Generate answer with Gemini
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        google_api_key=GOOGLE_API_KEY,
        temperature=0.3
    )
    
    context = "\n\n".join([doc["content"] for doc in reranked_docs])
    
    prompt = f"""Answer the question based on the context.

Context:
{context}

Question: {question_en}

Answer:"""
    
    answer = llm.invoke(prompt).content
    
    # Step 6: Translate back if needed
    if language == "vi":
        trans_response = await http_client.post(
            f"{TRANSLATION_SERVICE_URL}/translate",
            json={"text": answer, "target_lang": "vi"}
        )
        answer = trans_response.json()["translated_text"]
    
    # Step 7: Format result
    result = {
        "answer": answer,
        "sources": reranked_docs,
        "citations": [
            {
                "index": i + 1,
                "filename": doc["metadata"]["source"],
                "page": doc["metadata"].get("page", "N/A"),
                "content": doc["content"][:500],
                "relevance_score": doc.get("score", 0.0)
            }
            for i, doc in enumerate(reranked_docs)
        ],
        "response_time": time.time() - start_time,
        "from_cache": False
    }
    
    # Cache result
    if use_cache:
        await set_to_cache(cache_key, result, ttl=3600)
    
    return result

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "services": {
            "redis": "healthy" if redis_client.ping() else "unhealthy",
            "embedding": "checking...",
            "retrieval": "checking...",
            "reranking": "checking...",
            "translation": "checking..."
        }
    }

@app.post("/question", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask a question - main RAG endpoint
    """
    try:
        result = await rag_pipeline(request.question, request.use_cache)
        return QuestionResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/summary")
async def create_summary(topic: Optional[str] = None):
    """
    Create summary
    """
    query = f"Summarize about {topic}" if topic else "Summarize main concepts"
    result = await rag_pipeline(query)
    return result

@app.post("/quiz")
async def create_quiz(topic: Optional[str] = None, num_questions: int = 5):
    """
    Create quiz - async with Celery
    """
    task = celery_app.send_task(
        'generate_quiz',
        args=[topic, num_questions]
    )
    
    return {
        "task_id": task.id,
        "status": "processing",
        "message": "Quiz generation started"
    }

@app.get("/quiz/{task_id}")
async def get_quiz_result(task_id: str):
    """
    Get quiz result by task ID
    """
    task = celery_app.AsyncResult(task_id)
    
    if task.ready():
        return {
            "status": "completed",
            "result": task.result
        }
    else:
        return {
            "status": "processing",
            "progress": task.info.get('progress', 0) if task.info else 0
        }

# ============================================================================
# STARTUP & SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    print("🚀 RAG Service starting...")
    print(f"📡 Embedding Service: {EMBEDDING_SERVICE_URL}")
    print(f"📡 Retrieval Service: {RETRIEVAL_SERVICE_URL}")
    print(f"📡 Reranking Service: {RERANKING_SERVICE_URL}")
    print(f"📡 Translation Service: {TRANSLATION_SERVICE_URL}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await http_client.aclose()
    print("👋 RAG Service shutting down...")

# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
