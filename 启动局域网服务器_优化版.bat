@echo off
chcp 65001 >nul
title AI文件整理器 - 局域网服务器 (优化版)

echo ========================================
echo    AI文件整理器 - 局域网服务器
echo           优化版启动脚本
echo ========================================
echo.

echo 正在检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Python环境
    echo 请确保已安装Python并添加到系统PATH
    pause
    exit /b 1
)

echo ✅ Python环境检查通过
echo.

echo 正在检查依赖库...
python -c "import reportlab; print(f'✅ ReportLab版本: {reportlab.__version__}')" 2>nul
if errorlevel 1 (
    echo ❌ ReportLab库未安装，正在安装...
    pip install reportlab>=3.6.0
    if errorlevel 1 (
        echo ❌ ReportLab安装失败
        pause
        exit /b 1
    )
)

python -c "import docx; print('✅ python-docx库已安装')" 2>nul
if errorlevel 1 (
    echo ❌ python-docx库未安装，正在安装...
    pip install python-docx
    if errorlevel 1 (
        echo ❌ python-docx安装失败
        pause
        exit /b 1
    )
)

echo ✅ 依赖库检查完成
echo.

echo 正在启动服务器...
echo 注意: 使用8080端口避免权限问题
echo.

REM 尝试启动服务器
python start_viewer_server.py 8080

if errorlevel 1 (
    echo.
    echo ❌ 服务器启动失败
    echo 可能的原因:
    echo 1. 端口8080被占用
    echo 2. 防火墙阻止
    echo 3. 权限不足
    echo.
    echo 正在尝试其他端口...
    
    REM 尝试其他端口
    for %%p in (8081 8082 8083 8084 8085) do (
        echo 尝试端口 %%p...
        python start_viewer_server.py %%p
        if not errorlevel 1 (
            echo ✅ 服务器在端口 %%p 启动成功
            goto :success
        )
    )
    
    echo ❌ 所有端口都无法使用
    pause
    exit /b 1
)

:success
echo.
echo ✅ 服务器启动成功！
echo.
echo 访问地址:
echo - 本地访问: http://localhost:8080
echo - 局域网访问: http://[本机IP]:8080
echo.
echo 按 Ctrl+C 停止服务器
pause 