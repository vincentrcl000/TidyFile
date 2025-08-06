@echo off
chcp 65001 >nul
echo 🔧 TidyFile 构建工具
echo ================================================

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Python未安装或未添加到PATH
    pause
    exit /b 1
)

echo ✓ Python已安装

REM 安装依赖
echo 📦 安装构建依赖...
pip install pyinstaller build twine

REM 运行构建脚本
echo 🚀 开始构建...
python scripts/build_executables.py

if errorlevel 1 (
    echo ✗ 构建失败
    pause
    exit /b 1
)

echo.
echo 🎉 构建完成！
echo 📁 输出文件在 dist/ 目录中
echo.
pause 