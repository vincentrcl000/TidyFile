#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文件整理器 - 简单安装包制作脚本
创建时间: 2025-07-22
"""

import os
import sys
import shutil
import zipfile
import json
from datetime import datetime
from pathlib import Path

def create_installer_package():
    """创建安装包"""
    print("📦 开始创建安装包...")
    
    # 检查可执行文件是否存在
    exe_path = "dist/智能文件整理器.exe"
    if not os.path.exists(exe_path):
        print("❌ 可执行文件不存在，请先运行 build_simple.py")
        return False
    
    # 创建安装包目录
    installer_dir = "installer_package"
    if os.path.exists(installer_dir):
        shutil.rmtree(installer_dir)
    os.makedirs(installer_dir)
    
    # 复制必要文件
    files_to_copy = [
        ("dist/智能文件整理器.exe", "智能文件整理器.exe"),
        ("TidyFile.ico", "TidyFile.ico"),
        ("favicon.ico", "favicon.ico"),
        ("favicon.svg", "favicon.svg"),
        ("ai_result_viewer.html", "ai_result_viewer.html"),
        ("weixin_article_renderer.html", "weixin_article_renderer.html"),
        ("weixin_article_template.html", "weixin_article_template.html"),
        ("start_viewer_server.py", "start_viewer_server.py"),
        ("ai_organize_result.json", "ai_organize_result.json"),
        ("requirements.txt", "requirements.txt"),
        ("用户手册.md", "用户手册.md"),
        ("README.md", "README.md"),
        ("DOC_CONVERSION_GUIDE.md", "DOC_CONVERSION_GUIDE.md"),
        ("微信信息管理使用说明.md", "微信信息管理使用说明.md"),
    ]
    
    for src, dst in files_to_copy:
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(installer_dir, dst))
            print(f"📋 复制: {src} -> {dst}")
    
    # 复制目录
    dirs_to_copy = [
        ("weixin_manager", "weixin_manager"),
        ("transfer_logs", "transfer_logs"),
    ]
    
    for src, dst in dirs_to_copy:
        if os.path.exists(src):
            shutil.copytree(src, os.path.join(installer_dir, dst))
            print(f"📁 复制目录: {src} -> {dst}")
    
    # 创建安装脚本
    install_script = '''@echo off
chcp 65001 >nul
echo ========================================
echo 智能文件整理器 - 安装程序
echo ========================================
echo.

:: 检查是否以管理员身份运行
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ 检测到管理员权限
) else (
    echo ⚠️ 建议以管理员身份运行此安装程序
    echo.
)

:: 创建安装目录
set INSTALL_DIR=%ProgramFiles%\\智能文件整理器
echo 📁 安装目录: %INSTALL_DIR%

if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
    echo ✅ 创建安装目录
) else (
    echo ⚠️ 安装目录已存在，将覆盖现有文件
)

:: 复制文件
echo.
echo 📋 正在复制文件...
xcopy /E /I /Y "智能文件整理器.exe" "%INSTALL_DIR%\\"
xcopy /E /I /Y "TidyFile.ico" "%INSTALL_DIR%\\"
xcopy /E /I /Y "favicon.ico" "%INSTALL_DIR%\\"
xcopy /E /I /Y "favicon.svg" "%INSTALL_DIR%\\"
xcopy /E /I /Y "ai_result_viewer.html" "%INSTALL_DIR%\\"
xcopy /E /I /Y "weixin_article_renderer.html" "%INSTALL_DIR%\\"
xcopy /E /I /Y "weixin_article_template.html" "%INSTALL_DIR%\\"
xcopy /E /I /Y "start_viewer_server.py" "%INSTALL_DIR%\\"
xcopy /E /I /Y "ai_organize_result.json" "%INSTALL_DIR%\\"
xcopy /E /I /Y "requirements.txt" "%INSTALL_DIR%\\"
xcopy /E /I /Y "用户手册.md" "%INSTALL_DIR%\\"
xcopy /E /I /Y "README.md" "%INSTALL_DIR%\\"
xcopy /E /I /Y "DOC_CONVERSION_GUIDE.md" "%INSTALL_DIR%\\"
xcopy /E /I /Y "微信信息管理使用说明.md" "%INSTALL_DIR%\\"

if exist "weixin_manager" (
    xcopy /E /I /Y "weixin_manager" "%INSTALL_DIR%\\weixin_manager\\"
)
if exist "transfer_logs" (
    xcopy /E /I /Y "transfer_logs" "%INSTALL_DIR%\\transfer_logs\\"
)

echo ✅ 文件复制完成

:: 创建桌面快捷方式
echo.
echo 📋 创建桌面快捷方式...
set DESKTOP=%USERPROFILE%\\Desktop
set SHORTCUT=%DESKTOP%\\智能文件整理器.lnk

powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT%'); $Shortcut.TargetPath = '%INSTALL_DIR%\\智能文件整理器.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = '%INSTALL_DIR%\\TidyFile.ico'; $Shortcut.Save()"

if exist "%SHORTCUT%" (
    echo ✅ 桌面快捷方式创建成功
) else (
    echo ⚠️ 桌面快捷方式创建失败
)

:: 创建开始菜单快捷方式
echo.
echo 📋 创建开始菜单快捷方式...
set START_MENU=%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\智能文件整理器
if not exist "%START_MENU%" mkdir "%START_MENU%"

set START_SHORTCUT=%START_MENU%\\智能文件整理器.lnk
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%START_SHORTCUT%'); $Shortcut.TargetPath = '%INSTALL_DIR%\\智能文件整理器.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = '%INSTALL_DIR%\\TidyFile.ico'; $Shortcut.Save()"

if exist "%START_SHORTCUT%" (
    echo ✅ 开始菜单快捷方式创建成功
) else (
    echo ⚠️ 开始菜单快捷方式创建失败
)

:: 创建卸载脚本
echo.
echo 📋 创建卸载脚本...
set UNINSTALL_SCRIPT=%INSTALL_DIR%\\卸载智能文件整理器.bat

echo @echo off > "%UNINSTALL_SCRIPT%"
echo chcp 65001 ^>nul >> "%UNINSTALL_SCRIPT%"
echo echo ======================================== >> "%UNINSTALL_SCRIPT%"
echo echo 智能文件整理器 - 卸载程序 >> "%UNINSTALL_SCRIPT%"
echo echo ======================================== >> "%UNINSTALL_SCRIPT%"
echo echo. >> "%UNINSTALL_SCRIPT%"
echo echo 正在卸载智能文件整理器... >> "%UNINSTALL_SCRIPT%"
echo echo. >> "%UNINSTALL_SCRIPT%"
echo echo 删除桌面快捷方式... >> "%UNINSTALL_SCRIPT%"
echo if exist "%%USERPROFILE%%\\Desktop\\智能文件整理器.lnk" del "%%USERPROFILE%%\\Desktop\\智能文件整理器.lnk" >> "%UNINSTALL_SCRIPT%"
echo echo 删除开始菜单快捷方式... >> "%UNINSTALL_SCRIPT%"
echo if exist "%%APPDATA%%\\Microsoft\\Windows\\Start Menu\\Programs\\智能文件整理器" rmdir /S /Q "%%APPDATA%%\\Microsoft\\Windows\\Start Menu\\Programs\\智能文件整理器" >> "%UNINSTALL_SCRIPT%"
echo echo 删除安装目录... >> "%UNINSTALL_SCRIPT%"
echo rmdir /S /Q "%INSTALL_DIR%" >> "%UNINSTALL_SCRIPT%"
echo echo. >> "%UNINSTALL_SCRIPT%"
echo echo ✅ 卸载完成 >> "%UNINSTALL_SCRIPT%"
echo pause >> "%UNINSTALL_SCRIPT%"

echo ✅ 卸载脚本创建完成

:: 创建注册表项
echo.
echo 📋 创建注册表项...
reg add "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\智能文件整理器" /v "DisplayName" /t REG_SZ /d "智能文件整理器" /f
reg add "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\智能文件整理器" /v "UninstallString" /t REG_SZ /d "%INSTALL_DIR%\\卸载智能文件整理器.bat" /f
reg add "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\智能文件整理器" /v "DisplayIcon" /t REG_SZ /d "%INSTALL_DIR%\\TidyFile.ico" /f
reg add "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\智能文件整理器" /v "Publisher" /t REG_SZ /d "智能文件整理器开发团队" /f
reg add "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\智能文件整理器" /v "DisplayVersion" /t REG_SZ /d "1.0.0" /f

echo ✅ 注册表项创建完成

echo.
echo ========================================
echo 🎉 安装完成！
echo ========================================
echo.
echo 📁 安装位置: %INSTALL_DIR%
echo 📋 桌面快捷方式: %DESKTOP%\\智能文件整理器.lnk
echo 📋 开始菜单: 智能文件整理器
echo.
echo 📖 使用说明:
echo   • 双击桌面快捷方式启动程序
echo   • 确保已安装Ollama并运行
echo   • 首次运行可能需要较长时间
echo   • 查看用户手册.md了解详细功能
echo.
echo 🗑️ 卸载方法:
echo   • 运行: %INSTALL_DIR%\\卸载智能文件整理器.bat
echo   • 或通过控制面板卸载
echo.
pause
'''
    
    with open(os.path.join(installer_dir, "安装智能文件整理器.bat"), 'w', encoding='utf-8') as f:
        f.write(install_script)
    
    print("✅ 安装脚本创建完成")
    
    # 创建版本信息
    version_info = {
        "version": "1.0.0",
        "build_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "features": [
            "AI智能文件分类",
            "文件内容摘要生成", 
            "智能目录推荐",
            "微信文章管理",
            "文件去重功能",
            "转移日志管理",
            "文档格式转换",
            "批量文件处理"
        ],
        "requirements": {
            "python": "3.8+",
            "ollama": "0.1.0+",
            "windows": "Windows 10+"
        },
        "install_instructions": [
            "1. 解压安装包到任意目录",
            "2. 以管理员身份运行 '安装智能文件整理器.bat'",
            "3. 按照提示完成安装",
            "4. 确保已安装Ollama并运行",
            "5. 双击桌面快捷方式启动程序"
        ]
    }
    
    with open(os.path.join(installer_dir, "版本信息.json"), 'w', encoding='utf-8') as f:
        json.dump(version_info, f, ensure_ascii=False, indent=2)
    
    print("✅ 版本信息创建完成")
    
    # 创建ZIP包
    zip_filename = f"智能文件整理器_v1.0.0_安装包_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(installer_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, installer_dir)
                zipf.write(file_path, arcname)
                print(f"📦 添加到ZIP: {arcname}")
    
    print(f"✅ ZIP包创建完成: {zip_filename}")
    
    # 清理临时目录
    shutil.rmtree(installer_dir)
    print("🧹 清理临时文件完成")
    
    return True

def main():
    """主函数"""
    print("🚀 智能文件整理器 - 安装包制作")
    print("=" * 50)
    
    if create_installer_package():
        print("\n🎉 安装包制作完成!")
        print("📁 安装包位置: 智能文件整理器_v1.0.0_安装包_*.zip")
        print("📋 安装包特点:")
        print("   • 自解压ZIP格式")
        print("   • 自动创建桌面快捷方式")
        print("   • 自动创建开始菜单快捷方式")
        print("   • 注册表集成")
        print("   • 卸载脚本")
        print("   • 管理员权限支持")
        print("   • 中文界面")
        return True
    else:
        print("\n❌ 安装包制作失败!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 