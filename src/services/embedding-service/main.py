# services/embedding-service/main.py
"""
Embedding Service - Production Ready
Generates embeddings with caching and batch processing
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import redis
import json
import hashlib
import os
import torch
from sentence_transformers import SentenceTransformer

# ============================================================================
# CONFIGURATION
# ============================================================================
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
MODEL_NAME = os.getenv("MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "32"))
USE_GPU = os.getenv("USE_GPU", "false").lower() == "true"

# ============================================================================
# FASTAPI APP
# ============================================================================
app = FastAPI(
    title="Embedding Service",
    description="Generate embeddings with caching",
    version="1.0.0"
)

# Redis client
redis_client = redis.from_url(REDIS_URL, decode_responses=False)

# Load model
device = "cuda" if USE_GPU and torch.cuda.is_available() else "cpu"
model = SentenceTransformer(MODEL_NAME, device=device)

print(f"✅ Model loaded: {MODEL_NAME}")
print(f"🖥️  Device: {device}")

# ============================================================================
# MODELS
# ============================================================================

class EmbedRequest(BaseModel):
    texts: List[str]
    use_cache: bool = True

class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    cached_count: int
    generated_count: int

# ============================================================================
# CACHE UTILITIES
# ============================================================================

def get_embedding_cache_key(text: str) -> str:
    """Generate cache key for embedding"""
    hash_value = hashlib.md5(text.encode()).hexdigest()
    return f"embedding:{hash_value}"

def get_cached_embedding(text: str) -> List[float]:
    """Get embedding from cache"""
    try:
        key = get_embedding_cache_key(text)
        cached = redis_client.get(key)
        if cached:
            return json.loads(cached)
    except:
        pass
    return None

def cache_embedding(text: str, embedding: List[float], ttl: int = 604800):
    """Cache embedding (TTL: 7 days)"""
    try:
        key = get_embedding_cache_key(text)
        redis_client.setex(key, ttl, json.dumps(embedding))
    except:
        pass

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "model": MODEL_NAME,
        "device": device,
        "redis": "healthy" if redis_client.ping() else "unhealthy"
    }

@app.post("/embed", response_model=EmbedResponse)
async def generate_embeddings(request: EmbedRequest):
    """
    Generate embeddings for texts
    
    Features:
    - Caching (7 days TTL)
    - Batch processing
    - GPU support
    """
    texts = request.texts
    use_cache = request.use_cache
    
    embeddings = []
    texts_to_embed = []
    text_indices = []
    cached_count = 0
    
    # Check cache first
    for i, text in enumerate(texts):
        if use_cache:
            cached_emb = get_cached_embedding(text)
            if cached_emb:
                embeddings.append(cached_emb)
                cached_count += 1
                continue
        
        # Need to generate
        embeddings.append(None)
        texts_to_embed.append(text)
        text_indices.append(i)
    
    # Generate embeddings for uncached texts
    if texts_to_embed:
        # Batch processing
        generated_embeddings = []
        for i in range(0, len(texts_to_embed), BATCH_SIZE):
            batch = texts_to_embed[i:i + BATCH_SIZE]
            batch_embeddings = model.encode(
                batch,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            generated_embeddings.extend(batch_embeddings.tolist())
        
        # Fill in generated embeddings and cache them
        for idx, emb in zip(text_indices, generated_embeddings):
            embeddings[idx] = emb
            if use_cache:
                cache_embedding(texts[idx], emb)
    
    return EmbedResponse(
        embeddings=embeddings,
        cached_count=cached_count,
        generated_count=len(texts_to_embed)
    )

@app.post("/embed_single")
async def generate_single_embedding(text: str, use_cache: bool = True):
    """
    Generate embedding for single text
    """
    # Check cache
    if use_cache:
        cached_emb = get_cached_embedding(text)
        if cached_emb:
            return {
                "embedding": cached_emb,
                "from_cache": True
            }
    
    # Generate
    embedding = model.encode(text, convert_to_numpy=True).tolist()
    
    # Cache
    if use_cache:
        cache_embedding(text, embedding)
    
    return {
        "embedding": embedding,
        "from_cache": False
    }

# ============================================================================
# STARTUP
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    print("🚀 Embedding Service starting...")
    print(f"📊 Batch size: {BATCH_SIZE}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("👋 Embedding Service shutting down...")

# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8011, reload=False)
