@echo off
echo ========================================
echo   Full Stack RAG System
echo ========================================
echo.
echo Starting Backend and Frontend...
echo.

REM Start Backend in new window
start "Backend API" cmd /k "call START_BACKEND_API.bat"

REM Wait for backend to start
echo Waiting for backend to start...
timeout /t 5 /nobreak

REM Start Frontend in new window
start "Frontend React" cmd /k "call START_FRONTEND.bat"

echo.
echo ========================================
echo   Both servers are starting...
echo ========================================
echo.
echo Backend API: http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo.
echo Press any key to exit (servers will keep running)
pause
