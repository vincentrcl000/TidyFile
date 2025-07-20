@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动智能文件整理器...
python start.py
if errorlevel 1 (
    echo.
    echo 启动失败，请检查Python环境和依赖包
    echo 如果是首次使用，请先运行: pip install -r requirements.txt
    pause
)