@echo off
chcp 65001 >nul
title 大肥鱼 AI 配置助手
echo ========================================================
echo           🐟 大肥鱼 AI 虚拟主播 - 配置助手
echo ========================================================
echo.
echo 请选择配置方式：
echo  [1] 打开网页可视化配置（推荐，带音色试听与人设微调）
echo  [2] 直接使用记事本打开配置文件修改
echo.
set /p choice=请输入数字 [1 或 2]: 

if "%choice%"=="1" (
    echo 正在打开配置网页...
    start http://localhost:8765
) else (
    echo 正在打开 config.json...
    notepad "%~dp0config.json"
)
exit
