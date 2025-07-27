@echo off
chcp 65001 >nul
echo 🚀 启动智能文件整理器 - 新版本兼容版
echo ================================================

REM 检查虚拟环境是否存在
if not exist ".venv\Scripts\python.exe" (
    echo ❌ 虚拟环境不存在，正在创建...
    python -m venv .venv
    if errorlevel 1 (
        echo ❌ 虚拟环境创建失败
        pause
        exit /b 1
    )
)

REM 激活虚拟环境并启动程序
echo ✅ 激活虚拟环境...
call .venv\Scripts\activate.bat

REM 检查依赖是否已安装
echo 🔍 检查依赖包...
python -c "import PIL, ttkbootstrap, PyPDF2, docx, cv2, numpy, requests, openai, bs4" 2>nul
if errorlevel 1 (
    echo ⚠️ 依赖包不完整，正在安装...
    pip install Pillow ttkbootstrap PyPDF2 python-docx opencv-python numpy requests openai beautifulsoup4 html2text fake-useragent markdown send2trash chardet pyyaml coloredlogs pywin32 pypandoc
)

echo 🎯 启动文件整理器...
python gui_app_tabbed.py

echo.
echo 程序已退出
pause 