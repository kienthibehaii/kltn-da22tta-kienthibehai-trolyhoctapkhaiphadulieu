#!/usr/bin/env python
# run_frontend.py - Simple wrapper to run frontend
"""
Wrapper script để chạy frontend React

Usage:
    python run_frontend.py
"""

import subprocess
import sys
import os

if __name__ == "__main__":
    print("="*60)
    print("  🎨 RAG System Frontend (React)")
    print("="*60)
    print()
    print("Starting Vite dev server...")
    print("🌐 Frontend: http://localhost:3000")
    print("🔌 Backend: http://localhost:8000 (must be running)")
    print()
    print("Press Ctrl+C to stop")
    print("="*60)
    print()
    
    # Change to frontend directory
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    
    # Check if node_modules exists
    node_modules = os.path.join(frontend_dir, "node_modules")
    if not os.path.exists(node_modules):
        print("📦 Installing dependencies...")
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
        print()
    
    # Run npm dev
    try:
        subprocess.run(["npm", "run", "dev"], cwd=frontend_dir, check=True)
    except KeyboardInterrupt:
        print("\n\n👋 Frontend stopped")
        sys.exit(0)
