@echo off
chcp 65001 >nul
title AI结果查看器 - 局域网服务器

echo.
echo ========================================
echo    AI结果查看器 - 局域网服务器
echo ========================================
echo.

echo 正在启动支持局域网访问的HTTP服务器...
echo.

REM 激活虚拟环境（如果存在）
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo ✅ 虚拟环境已激活
) else (
    echo ⚠️ 未找到虚拟环境，使用系统Python
)

REM 启动服务器
python start_viewer_server.py

echo.
echo 服务器已停止
pause 