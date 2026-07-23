#!/usr/bin/env python3
"""
Optimized Backend Startup
Load RAG pipeline with progress indicators
"""

import sys
import time

def print_progress(msg):
    print(f"⏳ {msg}...", flush=True)

def print_success(msg):
    print(f"✅ {msg}", flush=True)

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 STARTING RAG BACKEND API")
    print("="*60 + "\n")
    
    # Step 1: Import dependencies
    print_progress("Loading dependencies")
    start = time.time()
    
    from backend_api import app
    import uvicorn
    
    print_success(f"Dependencies loaded ({time.time()-start:.1f}s)")
    
    # Step 2: Start server (RAG loads in startup event)
    print("\n" + "="*60)
    print("📡 Starting FastAPI server on http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    print("🔍 Health: http://localhost:8000/health")
    print("="*60 + "\n")
    
    print("⚠️  NOTE: RAG pipeline will load in background (~30s)")
    print("    Frontend can connect immediately but RAG features")
    print("    will be available after loading completes.\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
