@echo off
chcp 65001 >nul
title U-IT-Agent Windows 诊断助手
echo [!] 正在启动 U-IT-Agent...
python agent/main.py
pause
