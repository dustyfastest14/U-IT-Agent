@echo off
title U-IT-Agent Windows Diagnostic Agent
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

echo [!] Checking Python environment...

if exist "python\python.exe" (
    echo [*] Launching portable Python...
    "python\python.exe" "agent\main.py"
) else (
    echo [*] Portable Python not found, trying system Python...
    python "agent\main.py"
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Program exited with code %ERRORLEVEL%
    pause
)
