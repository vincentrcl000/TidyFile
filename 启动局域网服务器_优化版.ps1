# AI文件整理器 - 局域网服务器 (优化版)
# PowerShell启动脚本

param(
    [int]$Port = 8080
)

# 设置控制台编码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   AI文件整理器 - 局域网服务器" -ForegroundColor Cyan
Write-Host "        优化版启动脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查Python环境
Write-Host "正在检查Python环境..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Python环境检查通过: $pythonVersion" -ForegroundColor Green
    } else {
        throw "Python未找到"
    }
} catch {
    Write-Host "❌ 错误: 未找到Python环境" -ForegroundColor Red
    Write-Host "请确保已安装Python并添加到系统PATH" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

Write-Host ""

# 检查ReportLab库
Write-Host "正在检查ReportLab库..." -ForegroundColor Yellow
try {
    $reportlabVersion = python -c "import reportlab; print(reportlab.__version__)" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ ReportLab版本: $reportlabVersion" -ForegroundColor Green
    } else {
        throw "ReportLab未安装"
    }
} catch {
    Write-Host "❌ ReportLab库未安装，正在安装..." -ForegroundColor Red
    pip install "reportlab>=3.6.0"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ ReportLab安装失败" -ForegroundColor Red
        Read-Host "按回车键退出"
        exit 1
    }
}

# 检查python-docx库
Write-Host "正在检查python-docx库..." -ForegroundColor Yellow
try {
    python -c "import docx" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ python-docx库已安装" -ForegroundColor Green
    } else {
        throw "python-docx未安装"
    }
} catch {
    Write-Host "❌ python-docx库未安装，正在安装..." -ForegroundColor Red
    pip install python-docx
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ python-docx安装失败" -ForegroundColor Red
        Read-Host "按回车键退出"
        exit 1
    }
}

Write-Host ""
Write-Host "✅ 依赖库检查完成" -ForegroundColor Green
Write-Host ""

# 获取本机IP地址
Write-Host "正在获取本机IP地址..." -ForegroundColor Yellow
try {
    $localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -like "192.168.*" -or $_.IPAddress -like "10.*" -or $_.IPAddress -like "172.*"} | Select-Object -First 1).IPAddress
    if ($localIP) {
        Write-Host "✅ 本机IP地址: $localIP" -ForegroundColor Green
    } else {
        $localIP = "127.0.0.1"
        Write-Host "⚠️  使用默认IP: $localIP" -ForegroundColor Yellow
    }
} catch {
    $localIP = "127.0.0.1"
    Write-Host "⚠️  使用默认IP: $localIP" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "正在启动服务器..." -ForegroundColor Yellow
Write-Host "端口: $Port" -ForegroundColor Cyan
Write-Host ""

# 尝试启动服务器
$ports = @($Port, 8081, 8082, 8083, 8084, 8085)

foreach ($tryPort in $ports) {
    Write-Host "尝试启动服务器，端口: $tryPort" -ForegroundColor Yellow
    
    try {
        # 检查端口是否被占用
        $connection = Test-NetConnection -ComputerName "localhost" -Port $tryPort -WarningAction SilentlyContinue
        if ($connection.TcpTestSucceeded) {
            Write-Host "⚠️  端口 $tryPort 已被占用，尝试下一个端口" -ForegroundColor Yellow
            continue
        }
    } catch {
        # 端口检查失败，继续尝试启动
    }
    
    # 启动服务器
    try {
        $process = Start-Process python -ArgumentList "start_viewer_server.py", $tryPort -PassThru -WindowStyle Normal
        Start-Sleep -Seconds 2
        
        if (-not $process.HasExited) {
            Write-Host ""
            Write-Host "✅ 服务器启动成功！" -ForegroundColor Green
            Write-Host ""
            Write-Host "访问地址:" -ForegroundColor Cyan
            Write-Host "- 本地访问: http://localhost:$tryPort" -ForegroundColor White
            Write-Host "- 局域网访问: http://$localIP`:$tryPort" -ForegroundColor White
            Write-Host ""
            Write-Host "按 Ctrl+C 停止服务器" -ForegroundColor Yellow
            
            # 等待用户输入
            Read-Host "按回车键退出"
            break
        } else {
            Write-Host "❌ 服务器启动失败，尝试下一个端口" -ForegroundColor Red
        }
    } catch {
        Write-Host "❌ 启动失败: $($_.Exception.Message)" -ForegroundColor Red
    }
}

if ($process.HasExited) {
    Write-Host ""
    Write-Host "❌ 所有端口都无法使用" -ForegroundColor Red
    Write-Host "可能的原因:" -ForegroundColor Yellow
    Write-Host "1. 所有端口都被占用" -ForegroundColor White
    Write-Host "2. 防火墙阻止" -ForegroundColor White
    Write-Host "3. 权限不足" -ForegroundColor White
    Write-Host ""
    Read-Host "按回车键退出"
    exit 1
} 