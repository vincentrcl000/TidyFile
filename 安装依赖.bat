@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo 🚀 智能文件整理器 - 依赖安装脚本
echo ========================================
echo.

echo 📋 本脚本将帮助您安装所有必要的依赖项
echo.

:: 检查Python是否安装
echo 🔍 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Python，请先安装Python 3.7+
    echo 📥 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python环境检查通过
echo.

:: 升级pip
echo 🔧 升级pip到最新版本...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo ⚠️ pip升级失败，继续安装依赖...
) else (
    echo ✅ pip升级成功
)
echo.

:: 安装Python依赖包
echo 📦 安装Python依赖包...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 依赖包安装失败，请检查网络连接或手动安装
    echo 💡 手动安装命令: pip install -r requirements.txt
    pause
    exit /b 1
) else (
    echo ✅ Python依赖包安装成功
)
echo.

:: 运行详细检查脚本
echo 🔍 运行详细依赖检查...
python install_dependencies.py

echo.
echo ========================================
echo 🎉 依赖安装脚本执行完成
echo ========================================
echo.
echo 📝 接下来您可以:
echo   • 运行 start.py 启动应用程序
echo   • 查看 DOC_CONVERSION_GUIDE.md 了解文档转换工具安装
echo   • 如有问题，请查看上方的详细检查结果
echo.
pause