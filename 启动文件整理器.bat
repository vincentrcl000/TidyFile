@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动文件整理器...
echo.
python gui_app.py
if errorlevel 1 (
    echo.
    echo 启动失败！请检查：
    echo 1. 是否已安装Python
    echo 2. 是否已安装依赖包（运行：pip install -r requirements.txt）
    echo 3. 是否已启动Ollama服务
    echo.
    pause
)