#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TidyFile Windows Executable Builder
Supports Windows platform only
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

def check_windows_platform():
    """检查是否为Windows平台"""
    if platform.system().lower() != "windows":
        print("✗ 此构建工具仅支持Windows平台")
        print("💡 请在其他平台上使用GitHub Actions自动构建")
        return False
    return True

def check_dependencies():
    """检查构建依赖"""
    try:
        import PyInstaller
        print("✓ PyInstaller 已安装")
    except ImportError:
        print("✗ PyInstaller 未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("✓ PyInstaller 安装完成")

def create_resources_dir():
    """创建资源目录"""
    resources_dir = Path("resources")
    resources_dir.mkdir(exist_ok=True)
    
    # 检查图标文件
    icon_files = ["TidyFile.ico", "Article_Reader.ico"]
    for icon_file in icon_files:
        icon_path = resources_dir / icon_file
        if not icon_path.exists():
            print(f"⚠ 图标文件 {icon_file} 不存在，将使用默认图标")
            # 创建一个简单的占位符文件
            icon_path.touch()

def build_executable():
    """构建可执行文件"""
    print("\n🚀 开始构建 Windows 版本...")
    
    # 构建命令
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=TidyFile-Windows-x64",
        "--add-data=resources;resources",
        "--add-data=scripts;scripts",
        "--paths=src",
        "--hidden-import=tkinter",
        "--hidden-import=ttkbootstrap", 
        "--hidden-import=flask",
        "--hidden-import=requests",
        "--hidden-import=PIL",
        "--hidden-import=PyPDF2",
        "--hidden-import=docx",
        "--hidden-import=concurrent.futures",
        "--hidden-import=threading",
        "--hidden-import=logging",
        "--hidden-import=json",
        "--hidden-import=pathlib",
        "--hidden-import=subprocess",
        "--hidden-import=socket",
        "--hidden-import=http.server",
        "--hidden-import=socketserver",
        "--hidden-import=webbrowser",
        "--hidden-import=psutil",
        "--hidden-import=gc",
        "--hidden-import=tempfile",
        "--hidden-import=shutil",
        "--hidden-import=hashlib",
        "--hidden-import=mimetypes",
        "--hidden-import=urllib.parse",
        "--hidden-import=collections",
        "--hidden-import=datetime",
        "--hidden-import=ssl",
        "--hidden-import=re",
        "--hidden-import=win32com.client",
        "--hidden-import=pythoncom",
        "--hidden-import=bs4",
        "--hidden-import=beautifulsoup4",
        "--hidden-import=html2text",
        "--hidden-import=markdown",
        "--hidden-import=openai",
        "--collect-all=tidyfile",
        "--clean",
        "main.py"
    ]
    
    # 添加图标
    icon_path = Path("resources/TidyFile.ico")
    if icon_path.exists():
        cmd.insert(-1, f"--icon=resources/TidyFile.ico")
    
    print(f"执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✓ 构建成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 构建失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def create_package():
    """创建分发包"""
    print(f"\n📦 创建 Windows 分发包...")
    
    dist_dir = Path("dist")
    exe_name = "TidyFile-Windows-x64.exe"
    exe_path = dist_dir / exe_name
    
    if not exe_path.exists():
        print(f"✗ 可执行文件 {exe_name} 不存在")
        return False
    
    try:
        # 创建ZIP包
        import zipfile
        zip_name = "TidyFile-Windows-x64.zip"
        with zipfile.ZipFile(dist_dir / zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(exe_path, exe_name)
        print(f"✓ 创建ZIP包: {zip_name}")
        
        return True
    except Exception as e:
        print(f"✗ 创建包失败: {e}")
        return False

def create_installer_package():
    """创建安装包"""
    print(f"\n📦 创建安装包...")
    
    dist_dir = Path("dist")
    exe_name = "TidyFile-Windows-x64.exe"
    exe_path = dist_dir / exe_name
    
    if not exe_path.exists():
        print(f"✗ 可执行文件 {exe_name} 不存在")
        return False
    
    try:
        # 创建安装包目录
        installer_dir = dist_dir / "TidyFile-Installer"
        installer_dir.mkdir(exist_ok=True)
        
        # 复制可执行文件
        shutil.copy2(exe_path, installer_dir / exe_name)
        
        # 复制启动脚本
        scripts_to_copy = [
            "scripts/start_tidyfile.vbs",
            "scripts/start_article_reader.vbs",
            "scripts/create_desktop_shortcuts.py"
        ]
        
        for script in scripts_to_copy:
            script_path = Path(script)
            if script_path.exists():
                shutil.copy2(script_path, installer_dir / script_path.name)
                print(f"✓ 复制脚本: {script_path.name}")
        
        # 复制资源文件
        resources_dir = Path("resources")
        if resources_dir.exists():
            installer_resources = installer_dir / "resources"
            shutil.copytree(resources_dir, installer_resources, dirs_exist_ok=True)
            print("✓ 复制资源文件")
        
        # 创建安装说明
        readme_content = """# TidyFile Windows 安装包

## 安装说明

1. 解压此文件夹到任意位置
2. 运行 `create_desktop_shortcuts.py` 创建桌面快捷方式
3. 双击桌面上的 "TidyFile" 或 "Article Reader" 图标启动程序

## 文件说明

- `TidyFile-Windows-x64.exe` - 主程序（便携版）
- `start_tidyfile.vbs` - TidyFile 启动脚本
- `start_article_reader.vbs` - 文章阅读助手启动脚本
- `create_desktop_shortcuts.py` - 桌面快捷方式创建工具
- `resources/` - 图标和资源文件

## 系统要求

- Windows 10/11
- Python 3.8+ (如果使用源代码版本)
- 4GB+ 内存
- 1GB+ 可用磁盘空间

## 技术支持

如有问题，请访问项目主页或提交 Issue。
"""
        
        with open(installer_dir / "README.txt", "w", encoding="utf-8") as f:
            f.write(readme_content)
        
        # 创建ZIP安装包
        import zipfile
        installer_zip = "TidyFile-Windows-Installer.zip"
        with zipfile.ZipFile(dist_dir / installer_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in installer_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(installer_dir)
                    zipf.write(file_path, arcname)
        
        print(f"✓ 创建安装包: {installer_zip}")
        return True
        
    except Exception as e:
        print(f"✗ 创建安装包失败: {e}")
        return False

def clean_build():
    """清理构建文件"""
    print("\n🧹 清理构建文件...")
    
    dirs_to_clean = ["build", "__pycache__"]
    files_to_clean = ["*.spec"]
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"✓ 删除目录: {dir_name}")
    
    for pattern in files_to_clean:
        for file_path in Path(".").glob(pattern):
            file_path.unlink()
            print(f"✓ 删除文件: {file_path}")

def main():
    """主函数"""
    print("🔧 TidyFile Windows 可执行文件构建工具")
    print("=" * 50)
    
    # 检查平台
    if not check_windows_platform():
        sys.exit(1)
    
    # 检查依赖
    check_dependencies()
    
    # 创建资源目录
    create_resources_dir()
    
    print(f"📋 当前平台: Windows")
    
    # 清理之前的构建
    clean_build()
    
    # 构建可执行文件
    if build_executable():
        # 创建分发包
        if create_package() and create_installer_package():
            print(f"\n🎉 构建完成！")
            print(f"📁 输出目录: dist/")
            print(f"📄 可执行文件: TidyFile-Windows-x64.exe")
            print(f"📦 分发包: TidyFile-Windows-x64.zip")
            print(f"📦 安装包: TidyFile-Windows-Installer.zip")
            
            # 显示文件大小
            exe_path = Path("dist") / "TidyFile-Windows-x64.exe"
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"📊 文件大小: {size_mb:.1f} MB")
        else:
            print("✗ 创建分发包失败")
            sys.exit(1)
    else:
        print("✗ 构建失败")
        sys.exit(1)

if __name__ == "__main__":
    main() 