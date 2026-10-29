@echo off
chcp 65001 >nul
title 大肥鱼 AI 虚拟直播中控
echo ========================================================
echo        正在启动【大肥鱼 AI 虚拟直播间】...
echo ========================================================
echo.
cd /d "%~dp0"
start "" http://localhost:8765
python server.py
pause
