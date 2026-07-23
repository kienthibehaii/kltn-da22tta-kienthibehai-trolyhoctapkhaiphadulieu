@echo off
title MinerAI - Backend Server

REM Chuyen den thu muc chua file batch nay
cd /d "%~dp0"

echo ============================================================
echo   Dang tat tien trinh dang chiem cong 8000...
echo ============================================================

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Tat PID: %%a
    taskkill /PID %%a /F >nul 2>&1
)

ping -n 3 127.0.0.1 >nul

REM Kich hoat virtual environment neu co
if exist "venv\Scripts\activate.bat" (
    echo.
    echo Kich hoat virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo.
    echo ⚠️ Khong tim thay venv\Scripts\activate.bat
)

echo.
echo ============================================================
echo   Dang khoi dong Backend...
echo ============================================================
echo.

python run_backend.py
