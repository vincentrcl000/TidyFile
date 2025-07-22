#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文件整理器 - Windows安装包制作脚本
创建时间: 2025-07-22
"""

import os
import sys
import shutil
import subprocess
import json
from pathlib import Path
from datetime import datetime

def check_dependencies():
    """检查必要的依赖"""
    required_packages = ['pyinstaller', 'inno-setup']
    
    missing_packages = []
    for package in required_packages:
        try:
            if package == 'inno-setup':
                # 检查Inno Setup是否安装
                result = subprocess.run(['iscc', '/?'], capture_output=True, text=True)
                if result.returncode != 0:
                    missing_packages.append(package)
            else:
                __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少必要的依赖包: {', '.join(missing_packages)}")
        print("请安装以下依赖:")
        for package in missing_packages:
            if package == 'inno-setup':
                print("  - Inno Setup: https://jrsoftware.org/isinfo.php")
            else:
                print(f"  - {package}: pip install {package}")
        return False
    
    print("✅ 所有依赖检查通过")
    return True

def clean_build_dirs():
    """清理构建目录"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"🧹 清理目录: {dir_name}")
            shutil.rmtree(dir_name)

def build_executable():
    """使用PyInstaller构建可执行文件"""
    print("🔨 开始构建可执行文件...")
    
    # 使用spec文件构建
    result = subprocess.run([
        'pyinstaller', 
        '--clean',
        'TidyFile.spec'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ 构建失败: {result.stderr}")
        return False
    
    print("✅ 可执行文件构建完成")
    return True

def create_inno_script():
    """创建Inno Setup脚本"""
    print("📝 创建Inno Setup脚本...")
    
    # 获取版本信息
    version = "1.0.0"
    build_date = datetime.now().strftime("%Y-%m-%d")
    
    inno_script = f"""[Setup]
AppName=智能文件整理器
AppVersion={version}
AppPublisher=智能文件整理器开发团队
AppPublisherURL=https://github.com/your-repo
AppSupportURL=https://github.com/your-repo/issues
AppUpdatesURL=https://github.com/your-repo/releases
DefaultDirName={{autopf}}\\智能文件整理器
DefaultGroupName=智能文件整理器
OutputDir=installer
OutputBaseFilename=智能文件整理器_安装程序_v{version}
SetupIconFile=TidyFile.ico
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{{cm:CreateQuickLaunchIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
Source: "dist\\智能文件整理器.exe"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "TidyFile.ico"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "favicon.ico"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "favicon.svg"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "ai_result_viewer.html"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "weixin_article_renderer.html"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "weixin_article_template.html"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "start_viewer_server.py"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "weixin_manager\\*"; DestDir: "{{app}}\\weixin_manager"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "transfer_logs\\*"; DestDir: "{{app}}\\transfer_logs"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "ai_organize_result.json"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "用户手册.md"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "DOC_CONVERSION_GUIDE.md"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "微信信息管理使用说明.md"; DestDir: "{{app}}"; Flags: ignoreversion

[Icons]
Name: "{{group}}\\智能文件整理器"; Filename: "{{app}}\\智能文件整理器.exe"; IconFilename: "{{app}}\\TidyFile.ico"
Name: "{{group}}\\卸载智能文件整理器"; Filename: "{{uninstallexe}}"
Name: "{{commondesktop}}\\智能文件整理器"; Filename: "{{app}}\\智能文件整理器.exe"; IconFilename: "{{app}}\\TidyFile.ico"; Tasks: desktopicon
Name: "{{userappdata}}\\Microsoft\\Internet Explorer\\Quick Launch\\智能文件整理器"; Filename: "{{app}}\\智能文件整理器.exe"; IconFilename: "{{app}}\\TidyFile.ico"; Tasks: quicklaunchicon

[Run]
Filename: "{{app}}\\智能文件整理器.exe"; Description: "{{cm:LaunchProgram,智能文件整理器}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
end;
"""
    
    with open('installer_script.iss', 'w', encoding='utf-8') as f:
        f.write(inno_script)
    
    print("✅ Inno Setup脚本创建完成")
    return True

def build_installer():
    """构建安装程序"""
    print("🔨 开始构建安装程序...")
    
    # 确保installer目录存在
    os.makedirs('installer', exist_ok=True)
    
    # 运行Inno Setup编译
    result = subprocess.run([
        'iscc',
        'installer_script.iss'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ 安装程序构建失败: {result.stderr}")
        return False
    
    print("✅ 安装程序构建完成")
    return True

def create_version_info():
    """创建版本信息文件"""
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
        }
    }
    
    with open('version_info.json', 'w', encoding='utf-8') as f:
        json.dump(version_info, f, ensure_ascii=False, indent=2)
    
    print("✅ 版本信息文件创建完成")

def main():
    """主函数"""
    print("🚀 智能文件整理器 - Windows安装包制作")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        return False
    
    # 清理构建目录
    clean_build_dirs()
    
    # 构建可执行文件
    if not build_executable():
        return False
    
    # 创建Inno Setup脚本
    if not create_inno_script():
        return False
    
    # 构建安装程序
    if not build_installer():
        return False
    
    # 创建版本信息
    create_version_info()
    
    print("\n🎉 安装包制作完成!")
    print("📁 安装程序位置: installer/智能文件整理器_安装程序_v1.0.0.exe")
    print("📋 功能特点:")
    print("   • 桌面快捷方式创建")
    print("   • 开始菜单集成")
    print("   • 管理员权限安装")
    print("   • 中文界面支持")
    print("   • 自动卸载支持")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 