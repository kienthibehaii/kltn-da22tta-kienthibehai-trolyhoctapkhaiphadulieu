# services/retrieval-service/main.py
"""
Retrieval Service - Production Ready
Handles vector search, BM25 search, and hybrid fusion
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import redis
import json
import hashlib
import os
import chromadb
from rank_bm25 import BM25Okapi
import numpy as np
import pickle

# ============================================================================
# CONFIGURATION
# ============================================================================
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")

# ============================================================================
# FASTAPI APP
# ============================================================================
app = FastAPI(
    title="Retrieval Service",
    description="Vector and BM25 search with hybrid fusion",
    version="1.0.0"
)

# Redis client
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# ChromaDB client
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_collection("documents")

# Load BM25 index
bm25_index_path = os.path.join(CHROMA_PATH, "bm25_index.pkl")
if os.path.exists(bm25_index_path):
    with open(bm25_index_path, 'rb') as f:
        bm25_data = pickle.load(f)
        bm25_index = bm25_data['bm25']
        bm25_documents = bm25_data['documents']
    print(f"✅ BM25 index loaded: {len(bm25_documents)} documents")
else:
    bm25_index = None
    bm25_documents = []
    print("⚠️ BM25 index not found")

# ============================================================================
# MODELS
# ============================================================================

class SearchRequest(BaseModel):
    query: str
    k: int = 5
    method: str = "hybrid"  # "vector", "bm25", "hybrid"
    vector_weight: float = 0.5
    bm25_weight: float = 0.5

class SearchResponse(BaseModel):
    documents: List[Dict]
    method: str
    total_results: int

# ============================================================================
# CACHE UTILITIES
# ============================================================================

def get_cache_key(query: str, method: str, k: int) -> str:
    """Generate cache key"""
    data = f"{query}:{method}:{k}"
    hash_value = hashlib.md5(data.encode()).hexdigest()
    return f"retrieval:{hash_value}"

async def get_from_cache(key: str) -> Optional[List[Dict]]:
    """Get from cache"""
    try:
        cached = redis_client.get(key)
        if cached:
            return json.loads(cached)
    except:
        pass
    return None

async def set_to_cache(key: str, value: List[Dict], ttl: int = 1800):
    """Set to cache (TTL: 30 minutes)"""
    try:
        redis_client.setex(key, ttl, json.dumps(value))
    except:
        pass

# ============================================================================
# SEARCH FUNCTIONS
# ============================================================================

def vector_search(query: str, k: int = 10) -> List[Dict]:
    """
    Vector similarity search using ChromaDB
    """
    results = collection.query(
        query_texts=[query],
        n_results=k
    )
    
    documents = []
    for i in range(len(results['ids'][0])):
        doc = {
            "id": results['ids'][0][i],
            "content": results['documents'][0][i],
            "metadata": results['metadatas'][0][i],
            "distance": results['distances'][0][i] if 'distances' in results else 0.0,
            "score": 1 / (1 + results['distances'][0][i]) if 'distances' in results else 1.0
        }
        documents.append(doc)
    
    return documents

def bm25_search(query: str, k: int = 10) -> List[Dict]:
    """
    BM25 keyword search
    """
    if not bm25_index:
        return []
    
    # Tokenize query
    query_tokens = query.lower().split()
    
    # Get BM25 scores
    scores = bm25_index.get_scores(query_tokens)
    
    # Get top k indices
    top_k_indices = np.argsort(scores)[::-1][:k]
    
    # Normalize scores
    max_score = scores[top_k_indices[0]] if len(top_k_indices) > 0 and scores[top_k_indices[0]] > 0 else 1.0
    
    documents = []
    for idx in top_k_indices:
        if scores[idx] > 0:
            doc = bm25_documents[idx]
            documents.append({
                "id": f"bm25_{idx}",
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": scores[idx] / max_score
            })
    
    return documents

def hybrid_search(query: str, k: int = 10, vector_weight: float = 0.5, bm25_weight: float = 0.5) -> List[Dict]:
    """
    Hybrid search: Vector + BM25 with RRF fusion
    """
    # Get results from both methods
    vector_results = vector_search(query, k=k*2)
    bm25_results = bm25_search(query, k=k*2)
    
    # Reciprocal Rank Fusion
    doc_scores = {}
    rrf_k = 60
    
    # Add vector scores
    for rank, doc in enumerate(vector_results, 1):
        doc_id = doc['content']  # Use content as unique ID
        if doc_id not in doc_scores:
            doc_scores[doc_id] = {
                'doc': doc,
                'score': 0
            }
        doc_scores[doc_id]['score'] += vector_weight / (rrf_k + rank)
    
    # Add BM25 scores
    for rank, doc in enumerate(bm25_results, 1):
        doc_id = doc['content']
        if doc_id not in doc_scores:
            doc_scores[doc_id] = {
                'doc': doc,
                'score': 0
            }
        doc_scores[doc_id]['score'] += bm25_weight / (rrf_k + rank)
    
    # Sort by score
    sorted_docs = sorted(doc_scores.values(), key=lambda x: x['score'], reverse=True)
    
    # Return top k
    return [item['doc'] for item in sorted_docs[:k]]

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "chroma_documents": collection.count(),
        "bm25_documents": len(bm25_documents),
        "redis": "healthy" if redis_client.ping() else "unhealthy"
    }

@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Search documents
    
    Methods:
    - vector: Vector similarity search only
    - bm25: BM25 keyword search only
    - hybrid: Combination of both (recommended)
    """
    # Check cache
    cache_key = get_cache_key(request.query, request.method, request.k)
    cached_results = await get_from_cache(cache_key)
    
    if cached_results:
        return SearchResponse(
            documents=cached_results,
            method=request.method,
            total_results=len(cached_results)
        )
    
    # Perform search
    if request.method == "vector":
        documents = vector_search(request.query, request.k)
    elif request.method == "bm25":
        documents = bm25_search(request.query, request.k)
    elif request.method == "hybrid":
        documents = hybrid_search(
            request.query,
            request.k,
            request.vector_weight,
            request.bm25_weight
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid search method")
    
    # Cache results
    await set_to_cache(cache_key, documents)
    
    return SearchResponse(
        documents=documents,
        method=request.method,
        total_results=len(documents)
    )

# ============================================================================
# STARTUP
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    print("🚀 Retrieval Service starting...")
    print(f"📊 ChromaDB documents: {collection.count()}")
    print(f"📊 BM25 documents: {len(bm25_documents)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("👋 Retrieval Service shutting down...")

# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8012, reload=False)
