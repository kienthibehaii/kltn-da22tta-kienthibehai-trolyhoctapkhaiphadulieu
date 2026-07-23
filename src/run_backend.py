#!/usr/bin/env python
# run_backend.py - Simple wrapper to run backend API
"""
Wrapper script để chạy backend API một cách đơn giản

Usage:
    python run_backend.py
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(errors='replace')
    except Exception:
        pass

if __name__ == "__main__":
    import uvicorn
    
    print("="*60)
    print("  🚀 RAG System Backend API")
    print("="*60)
    print()
    print("Starting server...")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/health")
    print("📊 Stats: http://localhost:8000/api/stats")
    print()
    print("Press Ctrl+C to stop")
    print("="*60)
    print()
    
    uvicorn.run(
        "backend_api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable auto-reload to prevent crashes
        log_level="info"
    )
