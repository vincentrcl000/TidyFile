# TidyFile 文章阅读助手 - PowerShell启动脚本
# 创建时间: 2025-01-27
# 更新时间: 2025-01-27 - 增强跨电脑兼容性

param(
    [switch]$Silent
)

# 设置控制台编码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 显示启动信息
if (-not $Silent) {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "   TidyFile 文章阅读助手启动器" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
}

# 获取当前脚本目录
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptPath

# 检查Python是否安装
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
    if (-not $Silent) {
        Write-Host "[信息] 找到Python: $pythonVersion" -ForegroundColor Green
    }
} catch {
    Write-Host "[错误] 未找到Python环境" -ForegroundColor Red
    Write-Host "请确保已安装Python 3.9或更高版本" -ForegroundColor Yellow
    if (-not $Silent) {
        Read-Host "按回车键退出"
    }
    exit 1
}

# 检查主程序文件
if (-not (Test-Path "start_viewer_server.py")) {
    Write-Host "[错误] 找不到主程序文件 start_viewer_server.py" -ForegroundColor Red
    Write-Host "当前目录: $ScriptPath" -ForegroundColor Yellow
    if (-not $Silent) {
        Read-Host "按回车键退出"
    }
    exit 1
}

# 检查HTML文件
if (-not (Test-Path "viewer.html")) {
    Write-Host "[警告] 找不到 viewer.html 文件，可能影响功能" -ForegroundColor Yellow
}

# 检查JSON文件，如果不存在则创建
if (-not (Test-Path "ai_organize_result.json")) {
    Write-Host "[信息] 创建空的JSON文件" -ForegroundColor Green
    "[]" | Out-File -FilePath "ai_organize_result.json" -Encoding UTF8
}

# 检查端口80是否被占用
$port80InUse = Get-NetTCPConnection -LocalPort 80 -ErrorAction SilentlyContinue
if ($port80InUse) {
    Write-Host "[提示] 端口80已被占用，将尝试使用其他端口" -ForegroundColor Yellow
}

# 启动服务器
if (-not $Silent) {
    Write-Host "[信息] 正在启动文章阅读助手服务器..." -ForegroundColor Green
}

try {
    # 启动Python服务器进程
    $process = Start-Process -FilePath "python" -ArgumentList "start_viewer_server.py" -WindowStyle Minimized -PassThru
    
    # 等待服务器启动
    Start-Sleep -Seconds 2
    
    # Note: Browser will be opened automatically by the server
    # No need to open browser here to avoid duplicate windows
    
    if (-not $Silent) {
        Write-Host ""
        Write-Host "[成功] 文章阅读助手已启动！" -ForegroundColor Green
        Write-Host "如果浏览器没有自动打开，请手动访问：" -ForegroundColor Cyan
        Write-Host "http://localhost/viewer.html" -ForegroundColor White
        Write-Host ""
        Write-Host "服务器进程ID: $($process.Id)" -ForegroundColor Gray
        Write-Host "按 Ctrl+C 停止服务器" -ForegroundColor Gray
        Write-Host ""
        
        # 等待用户输入
        try {
            while (-not $process.HasExited) {
                Start-Sleep -Seconds 1
            }
        } catch {
            # 用户按了Ctrl+C
            Write-Host "[信息] 正在停止服务器..." -ForegroundColor Yellow
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
    
} catch {
    Write-Host "[错误] 启动服务器失败: $($_.Exception.Message)" -ForegroundColor Red
    if (-not $Silent) {
        Read-Host "按回车键退出"
    }
    exit 1
} 