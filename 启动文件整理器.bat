@echo off
chcp 65001 >nul
title TidyFile文件整理器
echo ================================================
echo     TidyFile文件整理器启动中...
echo ================================================

cd /d "%~dp0"

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python环境，请确保Python已安装并添加到PATH
    pause
    exit /b 1
)

REM 检查主程序文件
if not exist "gui_app_tabbed.py" (
    echo [错误] 找不到主程序文件 gui_app_tabbed.py
    pause
    exit /b 1
)

REM 启动程序
echo [信息] 正在启动文件整理器...
python gui_app_tabbed.py

if errorlevel 1 (
    echo [错误] 程序异常退出
    pause
    exit /b 1
)

echo [信息] 程序已正常退出
pause 