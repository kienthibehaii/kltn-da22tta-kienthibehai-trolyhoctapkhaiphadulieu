#!/usr/bin/env python
# run_fullstack.py - Run both backend and frontend
"""
Script để chạy cả backend và frontend cùng lúc

Usage:
    python run_fullstack.py
"""

import subprocess
import sys
import os
import time
import signal

def run_backend():
    """Run backend in subprocess"""
    return subprocess.Popen(
        [sys.executable, "run_backend.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )

def run_frontend():
    """Run frontend in subprocess"""
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    return subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )

def main():
    print("="*60)
    print("  🚀 RAG System Full Stack")
    print("="*60)
    print()
    print("Starting backend and frontend...")
    print()
    
    backend_process = None
    frontend_process = None
    
    try:
        # Start backend
        print("1️⃣  Starting Backend API...")
        backend_process = run_backend()
        print("   ✅ Backend starting at http://localhost:8000")
        print()
        
        # Wait for backend to start
        print("   ⏳ Waiting for backend to initialize (15s)...")
        time.sleep(15)
        print()
        
        # Start frontend
        print("2️⃣  Starting Frontend React...")
        frontend_process = run_frontend()
        print("   ✅ Frontend starting at http://localhost:3000")
        print()
        
        # Main loop - keep running until Ctrl+C
        print("=" * 60)
        print("  ✅ Both servers are running!")
        print("=" * 60)
        print()
        print("🌐 Frontend: http://localhost:3000")
        print("🔌 Backend:  http://localhost:8000")
        print("📖 API Docs: http://localhost:8000/docs")
        print()
        print("Press Ctrl+C to stop both servers")
        print()
        
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if backend_process.poll() is not None:
                print("\n❌ Backend stopped unexpectedly")
                break
            if frontend_process.poll() is not None:
                print("\n❌ Frontend stopped unexpectedly")
                break
                
    except KeyboardInterrupt:
        print("\n\n👋 Stopping servers...")
        
    finally:
        # Cleanup
        if frontend_process is not None:
            print("   Stopping frontend...")
            frontend_process.terminate()
            try:
                frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                frontend_process.kill()
                
        if backend_process is not None:
            print("   Stopping backend...")
            backend_process.terminate()
            try:
                backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend_process.kill()
                
        print("   ✅ All servers stopped")
        print()

if __name__ == "__main__":
    main()
