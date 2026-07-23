@echo off
echo ========================================
echo   RAG System Backend API Server
echo ========================================
echo.
echo Starting FastAPI Backend Server...
echo.
echo API Documentation: http://localhost:8000/docs
echo Health Check: http://localhost:8000/health
echo.

REM Activate virtual environment if exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Start the backend server using run_backend.py
python run_backend.py

pause
