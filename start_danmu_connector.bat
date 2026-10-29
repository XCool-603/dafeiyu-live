@echo off
chcp 65001 >nul
title 抖音弹幕中继与测试连接器
echo ========================================================
echo        正在启动【抖音直播弹幕中继与仿真连接器】...
echo ========================================================
echo.
cd /d "%~dp0"
python douyin_danmu_connector.py
pause