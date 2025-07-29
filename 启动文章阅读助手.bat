@echo off
chcp 65001 >nul
title TidyFile 文章阅读助手

echo ========================================
echo    TidyFile Article Reader Assistant
echo ========================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Python environment not found
    echo Please ensure Python 3.9 or higher is installed
    echo.
    pause
    exit /b 1
)

:: 检查主程序文件
if not exist "start_viewer_server.py" (
    echo [Error] Cannot find main program file start_viewer_server.py
    echo Please ensure running this script in the correct directory
    echo.
    pause
    exit /b 1
)

:: 检查HTML文件
if not exist "viewer.html" (
    echo [Warning] Cannot find viewer.html file, may affect functionality
    echo.
)

:: 检查JSON文件，如果不存在则创建
if not exist "ai_organize_result.json" (
    echo [Info] Creating empty JSON file
    echo [] > ai_organize_result.json
)

:: 检查端口80是否被占用
netstat -an | findstr :80 >nul
if not errorlevel 1 (
    echo [Info] Port 80 is occupied, will try other ports
    echo.
)

echo [Info] Starting Article Reader Assistant server...
echo.

:: 启动服务器
start /min python start_viewer_server.py

:: 等待服务器启动
timeout /t 2 /nobreak >nul

:: Note: Browser will be opened automatically by the server
:: No need to open browser here to avoid duplicate windows

echo.
echo [Success] Article Reader Assistant started!
echo If browser doesn't open automatically, please visit:
echo http://localhost/viewer.html
echo.
echo 按任意键退出...
pause >nul 