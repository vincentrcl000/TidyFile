#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文件整理器 - 可执行文件构建器

这个脚本用于将智能文件整理器打包成独立的可执行文件。
使用 PyInstaller 进行打包，生成包含所有依赖的 .exe 文件。

作者: AI Assistant
版本: 1.0
创建时间: 2024-01-01
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime


class ExeBuilder:
    """可执行文件构建器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.main_script = self.project_root / "start.py"
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        
    def check_dependencies(self) -> bool:
        """检查构建依赖"""
        print("检查构建依赖...")
        
        # 检查主脚本是否存在
        if not self.main_script.exists():
            print(f"[错误] 主脚本不存在: {self.main_script}")
            return False
        print(f"[成功] 主脚本存在: {self.main_script}")
        
        # 检查 PyInstaller
        try:
            result = subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], 
                                  capture_output=True, text=True, check=True)
            print(f"[成功] PyInstaller 版本: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("[错误] PyInstaller 未安装")
            return False
            
        return True
    
    def install_dependencies(self) -> bool:
        """安装项目依赖"""
        print("\n安装项目依赖...")
        
        # 检查是否存在 requirements.txt
        requirements_file = self.project_root / "requirements.txt"
        if requirements_file.exists():
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)], 
                             check=True)
                print("[成功] 项目依赖安装完成")
            except subprocess.CalledProcessError as e:
                print(f"[错误] 依赖安装失败: {e}")
                return False
        else:
            print("[信息] 未找到 requirements.txt，跳过依赖安装")
            
        return True
    
    def create_spec_file(self) -> Path:
        """创建 PyInstaller 规格文件"""
        print("\n创建 PyInstaller 规格文件...")
        
        spec_content = '''
# 文件整理器 PyInstaller 规格文件
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['start.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'requests',
        'json',
        'threading',
        'queue',
        'pathlib',
        'shutil',
        'datetime',
        'logging',
        'configparser',
        'urllib3',
        'charset_normalizer',
        'idna',
        'certifi'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='智能文件整理器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)
'''
        
        spec_file = self.project_root / "file_organizer.spec"
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
            
        print(f"[成功] 规格文件已创建: {spec_file}")
        return spec_file
    
    def build_executable(self, spec_file: Path) -> bool:
        """构建可执行文件"""
        print("\n开始构建可执行文件...")
        
        try:
            # 清理之前的构建
            if self.dist_dir.exists():
                shutil.rmtree(self.dist_dir)
            if self.build_dir.exists():
                shutil.rmtree(self.build_dir)
                
            # 运行 PyInstaller
            cmd = [sys.executable, "-m", "PyInstaller", "--clean", str(spec_file)]
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"[错误] PyInstaller 构建失败:")
                print(result.stderr)
                return False
                
            # 检查输出文件
            exe_file = self.dist_dir / "智能文件整理器.exe"
            if not exe_file.exists():
                print(f"[错误] 可执行文件未生成: {exe_file}")
                return False
                
            print(f"[成功] 可执行文件已生成: {exe_file}")
            print(f"[信息] 文件大小: {exe_file.stat().st_size / 1024 / 1024:.1f} MB")
            
            return True
            
        except Exception as e:
            print(f"[错误] 构建过程中发生异常: {e}")
            return False
    
    def create_installer_script(self):
        """创建安装脚本和使用说明"""
        print("\n创建安装脚本和使用说明...")
        
        # 创建安装脚本
        install_script = '''@echo off
chcp 65001 > nul
echo 智能文件整理器 - 安装脚本
echo ================================
echo.

echo 正在检查 Ollama 服务...
ping -n 1 localhost > nul 2>&1
if errorlevel 1 (
    echo [错误] 无法连接到本地网络
    echo 请确保网络连接正常
    pause
    exit /b 1
)

echo [成功] 网络连接正常
echo.
echo 使用说明:
echo 1. 请确保已安装并启动 Ollama 服务
echo 2. 请确保已下载所需的 AI 模型(如 gemma2)
echo 3. 双击 "智能文件整理器.exe" 开始使用
echo.
echo 如需安装 Ollama, 请访问: https://ollama.com
echo 安装模型命令: ollama pull gemma2
echo.
pause
'''
        
        install_bat = self.dist_dir / "安装说明.bat"
        with open(install_bat, 'w', encoding='gbk') as f:
            f.write(install_script)
            
        # 创建使用说明
        readme_content = (
            "# 智能文件整理器 v1.0\n\n"
            "## 功能介绍\n\n"
            "智能文件整理器是一个基于 AI 的文件自动分类工具, 能够:\n\n"
            "- 使用本地 AI 模型智能分析文件内容\n"
            "- 自动将文件分类到合适的文件夹\n"
            "- 提供友好的图形用户界面\n"
            "- 完全本地化处理, 保护隐私安全\n"
            "- 支持批量处理, 提高效率\n\n"
            "## 系统要求\n\n"
            "- Windows 10/11 (64位)\n"
            "- 至少 8GB 内存\n"
            "- 至少 5GB 可用磁盘空间\n"
            "- 已安装 Ollama 服务\n\n"
            "## 安装步骤\n\n"
            "### 1. 安装 Ollama\n\n"
            "1. 访问 [Ollama 官网](https://ollama.com) 下载安装包\n"
            "2. 运行安装程序，按提示完成安装\n"
            "3. 安装完成后，Ollama 会自动启动服务\n\n"
            "### 2. 下载 AI 模型\n\n"
            "打开命令提示符或 PowerShell, 运行以下命令:\n\n"
            "```bash\n"
            "# 下载推荐的轻量级模型 (约 1.5GB)\n"
            "ollama pull gemma2:2b\n\n"
            "# 或下载功能更强的模型 (约 4GB)\n"
            "ollama pull gemma2:7b\n"
            "```\n\n"
            "### 3. 运行文件整理器\n\n"
            "双击 `智能文件整理器.exe` 即可启动程序。\n\n"
            "## 使用方法\n\n"
            "1. **选择源目录**: 点击\"浏览\"按钮, 选择需要整理的文件夹\n"
            "2. **选择目标目录**: 选择已经建好分类文件夹的目标目录\n"
            "3. **预览分类**: 可以先点击\"预览分类结果\"查看 AI 的分类建议\n"
            "4. **开始整理**: 点击\"开始智能整理\"执行文件分类\n"
            "5. **确认操作**: 整理完成后, 可选择是否删除原文件\n\n"
            "## 目标目录结构示例\n\n"
            "目标目录应该包含以下类型的文件夹:\n\n"
            "```\n"
            "目标目录/\n"
            "├── 财经类/\n"
            "├── 技术类/\n"
            "├── 研究类/\n"
            "├── 学习类/\n"
            "├── 工作类/\n"
            "├── 生活类/\n"
            "├── 娱乐类/\n"
            "├── 健康类/\n"
            "└── 其他类/\n"
            "```\n\n"
            "## 注意事项\n\n"
            "- 首次使用时, AI 模型加载可能需要一些时间\n"
            "- 建议在整理前备份重要文件\n"
            "- 程序会先复制文件, 确认无误后再删除原文件\n"
            "- 所有操作都会记录在日志中, 便于追踪\n\n"
            "## 故障排除\n\n"
            "### Ollama 连接失败\n\n"
            "1. 确认 Ollama 服务正在运行\n"
            "2. 检查防火墙设置\n"
            "3. 重启 Ollama 服务:\n"
            "   ```bash\n"
            "   ollama serve\n"
            "   ```\n\n"
            "### 模型不可用\n\n"
            "1. 检查模型是否已下载:\n"
            "   ```bash\n"
            "   ollama list\n"
            "   ```\n"
            "2. 重新下载模型:\n"
            "   ```bash\n"
            "   ollama pull gemma2:2b\n"
            "   ```\n\n"
            "### 程序无法启动\n\n"
            "1. 确认系统满足最低要求\n"
            "2. 以管理员身份运行\n"
            "3. 检查杀毒软件是否误报\n\n"
            "## 技术支持\n\n"
            "如遇到问题，请检查程序目录下的日志文件，或联系技术支持。\n\n"
            "---\n\n"
            "构建时间: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n"
            "版本: v1.0\n"
        )
        
        readme_file = self.dist_dir / "使用说明.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
            
        print(f"[成功] 安装脚本已创建: {install_bat}")
        print(f"[成功] 使用说明已创建: {readme_file}")
        
    def build(self) -> bool:
        """执行完整的构建流程"""
        print("智能文件整理器 - 可执行文件构建器")
        print("=" * 50)
        
        try:
            # 检查依赖
            if not self.check_dependencies():
                return False
                
            # 安装项目依赖
            if not self.install_dependencies():
                return False
                
            # 创建规格文件
            spec_file = self.create_spec_file()
            
            # 构建可执行文件
            if not self.build_executable(spec_file):
                return False
                
            # 创建安装脚本
            self.create_installer_script()
            
            print("\n" + "=" * 50)
            print("构建完成！")
            print(f"输出目录: {self.dist_dir.absolute()}")
            print(f"可执行文件: 智能文件整理器.exe")
            print("\n使用方法：")
            print("1. 确保已安装 Ollama 并下载模型")
            print("2. 双击 '智能文件整理器.exe' 启动程序")
            print("3. 查看 '使用说明.md' 了解详细用法")
            
            return True
            
        except Exception as e:
            print(f"[错误] 构建过程中发生错误: {e}")
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="文件整理器可执行文件构建器")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="仅检查依赖，不执行构建"
    )
    
    args = parser.parse_args()
    
    builder = ExeBuilder()
    
    if args.check_only:
        # 仅检查依赖
        if builder.check_dependencies():
            print("\n[成功] 所有依赖检查通过，可以开始构建")
        else:
            print("\n[错误] 依赖检查失败，请解决问题后重试")
            sys.exit(1)
    else:
        # 执行完整构建
        if builder.build():
            print("\n构建成功完成！")
            sys.exit(0)
        else:
            print("\n构建失败！")
            sys.exit(1)


if __name__ == "__main__":
    main()