@echo off
echo ========================================
echo   Frontend React - RAG System
echo ========================================
echo.
echo Starting React Development Server...
echo.
echo Frontend will run at: http://localhost:3000
echo Backend must be running at: http://localhost:8000
echo.

cd frontend

REM Check if node_modules exists
if not exist "node_modules\" (
    echo Installing dependencies...
    call npm install
    echo.
)

REM Start development server
echo Starting Vite dev server...
call npm run dev

pause
