# services/api-gateway/main.py
"""
API Gateway - Production Ready
Handles routing, authentication, rate limiting, and monitoring
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import time
import redis
from typing import Optional
import os
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

# ============================================================================
# CONFIGURATION
# ============================================================================
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:8001")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8002")

# ============================================================================
# PROMETHEUS METRICS
# ============================================================================
REQUEST_COUNT = Counter(
    'api_gateway_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'api_gateway_request_duration_seconds',
    'Request duration',
    ['method', 'endpoint']
)

# ============================================================================
# FASTAPI APP
# ============================================================================
app = FastAPI(
    title="RAG System API Gateway",
    description="Production-ready API Gateway for RAG System",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis client
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# HTTP client
http_client = httpx.AsyncClient(timeout=60.0)

# ============================================================================
# MIDDLEWARE
# ============================================================================

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Record metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(process_time)
    
    return response

# ============================================================================
# RATE LIMITING
# ============================================================================

async def check_rate_limit(request: Request, limit: int = 15, window: int = 60):
    """
    Rate limiting: 15 requests per minute per IP
    """
    client_ip = request.client.host
    key = f"rate_limit:{client_ip}"
    
    try:
        current = redis_client.get(key)
        
        if current is None:
            redis_client.setex(key, window, 1)
            return True
        
        if int(current) >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {limit} requests per {window} seconds."
            )
        
        redis_client.incr(key)
        return True
    
    except redis.RedisError:
        # If Redis fails, allow request (fail open)
        return True

# ============================================================================
# AUTHENTICATION
# ============================================================================

async def verify_token(request: Request):
    """
    Verify JWT token
    """
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = auth_header.split(" ")[1]
    
    try:
        # Verify with auth service
        response = await http_client.post(
            f"{AUTH_SERVICE_URL}/verify",
            json={"token": token}
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return response.json()
    
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "environment": ENVIRONMENT,
        "services": {}
    }
    
    # Check Redis
    try:
        redis_client.ping()
        health_status["services"]["redis"] = "healthy"
    except:
        health_status["services"]["redis"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check RAG Service
    try:
        response = await http_client.get(f"{RAG_SERVICE_URL}/health", timeout=5.0)
        health_status["services"]["rag_service"] = "healthy" if response.status_code == 200 else "unhealthy"
    except:
        health_status["services"]["rag_service"] = "unhealthy"
        health_status["status"] = "degraded"
    
    return health_status

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type="text/plain")

# ============================================================================
# PROXY ROUTES
# ============================================================================

@app.post("/api/question")
async def question(request: Request):
    """Proxy to RAG service - Question endpoint"""
    await check_rate_limit(request)
    
    body = await request.json()
    
    try:
        response = await http_client.post(
            f"{RAG_SERVICE_URL}/question",
            json=body
        )
        return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail="RAG service unavailable")

@app.post("/api/summary")
async def summary(request: Request):
    """Proxy to RAG service - Summary endpoint"""
    await check_rate_limit(request)
    
    body = await request.json()
    
    try:
        response = await http_client.post(
            f"{RAG_SERVICE_URL}/summary",
            json=body
        )
        return response.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="RAG service unavailable")

@app.post("/api/quiz")
async def quiz(request: Request):
    """Proxy to RAG service - Quiz endpoint"""
    await check_rate_limit(request)
    
    body = await request.json()
    
    try:
        response = await http_client.post(
            f"{RAG_SERVICE_URL}/quiz",
            json=body
        )
        return response.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="RAG service unavailable")

# ============================================================================
# STARTUP & SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    print(f"🚀 API Gateway starting in {ENVIRONMENT} mode...")
    print(f"📡 RAG Service: {RAG_SERVICE_URL}")
    print(f"🔐 Auth Service: {AUTH_SERVICE_URL}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await http_client.aclose()
    print("👋 API Gateway shutting down...")

# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=ENVIRONMENT == "development"
    )
