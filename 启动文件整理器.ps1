# 智能文件整理器 - 新版本兼容版启动脚本
# 创建时间: 2025-07-25

Write-Host "🚀 启动智能文件整理器 - 新版本兼容版" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green

# 检查虚拟环境是否存在
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "❌ 虚拟环境不存在，正在创建..." -ForegroundColor Yellow
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 虚拟环境创建失败" -ForegroundColor Red
        Read-Host "按回车键退出"
        exit 1
    }
}

# 激活虚拟环境
Write-Host "✅ 激活虚拟环境..." -ForegroundColor Green
& ".venv\Scripts\Activate.ps1"

# 检查依赖是否已安装
Write-Host "🔍 检查依赖包..." -ForegroundColor Cyan
try {
    python -c "import PIL, ttkbootstrap, PyPDF2, docx, cv2, numpy, requests, openai, bs4" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "依赖包不完整"
    }
} catch {
    Write-Host "⚠️ 依赖包不完整，正在安装..." -ForegroundColor Yellow
    pip install Pillow ttkbootstrap PyPDF2 python-docx opencv-python numpy requests openai beautifulsoup4 html2text fake-useragent markdown send2trash chardet pyyaml coloredlogs pywin32 pypandoc
}

Write-Host "🎯 启动文件整理器..." -ForegroundColor Green
python gui_app_tabbed.py

Write-Host ""
Write-Host "程序已退出" -ForegroundColor Gray
Read-Host "按回车键退出" 