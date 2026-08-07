@echo off
chcp 65001 >nul
title U-IT-Agent Windows 诊断助手
cd /d "%~dp0"

echo [!] 正在检测 Python 运行环境...

if exist "python\python.exe" (
    echo [*] 使用 U 盘便携式 Python: python\python.exe
    "python\python.exe" agent\main.py
) else (
    echo [*] 便携 Python 未检测到，尝试调用系统全局 Python...
    python agent\main.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [X] 程序异常退出或未找到 Python 环境。
    echo     请参考 README.md 将 Windows 便携版 Python 解压至 python/ 目录。
    pause
)