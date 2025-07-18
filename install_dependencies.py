#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖项安装脚本

功能：
- 自动安装Python依赖包
- 检测并提供外部工具安装指导
- 验证安装结果

作者：智能文件整理器
版本：1.0
更新日期：2024-12-24
"""

import subprocess
import sys
import os
import platform
from pathlib import Path

def run_command(command, description=""):
    """
    执行命令并返回结果
    
    Args:
        command: 要执行的命令
        description: 命令描述
    
    Returns:
        tuple: (success, output)
    """
    try:
        print(f"\n{'='*50}")
        print(f"正在执行: {description or command}")
        print(f"{'='*50}")
        
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            print(f"✅ 成功: {description or command}")
            if result.stdout:
                print(f"输出: {result.stdout.strip()}")
            return True, result.stdout
        else:
            print(f"❌ 失败: {description or command}")
            if result.stderr:
                print(f"错误: {result.stderr.strip()}")
            return False, result.stderr
            
    except Exception as e:
        print(f"❌ 执行异常: {e}")
        return False, str(e)

def install_python_dependencies():
    """
    安装Python依赖包
    """
    print("\n🔧 开始安装Python依赖包...")
    
    # 升级pip
    success, _ = run_command(
        "python -m pip install --upgrade pip",
        "升级pip到最新版本"
    )
    
    if not success:
        print("⚠️ pip升级失败，继续安装依赖...")
    
    # 安装requirements.txt中的依赖
    requirements_file = Path(__file__).parent / "requirements.txt"
    if requirements_file.exists():
        success, output = run_command(
            f"pip install -r {requirements_file}",
            "安装requirements.txt中的依赖包"
        )
        
        if success:
            print("✅ Python依赖包安装完成")
        else:
            print("❌ Python依赖包安装失败")
            print("请手动执行: pip install -r requirements.txt")
    else:
        print("❌ 找不到requirements.txt文件")

def check_external_tools():
    """
    检查外部工具的可用性
    """
    print("\n🔍 检查外部工具可用性...")
    
    tools = {
        "LibreOffice": {
            "commands": ["libreoffice --version", "soffice --version"],
            "install_guide": [
                "请访问 https://www.libreoffice.org/download/download/ 下载安装",
                "安装后确保LibreOffice在系统PATH中"
            ]
        },
        "unoconv": {
            "commands": ["unoconv --version"],
            "install_guide": [
                "需要先安装LibreOffice",
                "然后执行: pip install unoconv",
                "或从 https://github.com/unoconv/unoconv 获取"
            ]
        },
        "antiword": {
            "commands": ["antiword -v"],
            "install_guide": [
                "Windows用户请从 http://www.winfield.demon.nl/ 下载",
                "或使用Chocolatey: choco install antiword",
                "Linux用户: sudo apt-get install antiword"
            ]
        }
    }
    
    available_tools = []
    missing_tools = []
    
    for tool_name, tool_info in tools.items():
        found = False
        for command in tool_info["commands"]:
            success, _ = run_command(command, f"检查{tool_name}")
            if success:
                available_tools.append(tool_name)
                found = True
                break
        
        if not found:
            missing_tools.append((tool_name, tool_info["install_guide"]))
    
    print(f"\n📊 工具检查结果:")
    print(f"✅ 可用工具: {', '.join(available_tools) if available_tools else '无'}")
    print(f"❌ 缺失工具: {', '.join([t[0] for t in missing_tools]) if missing_tools else '无'}")
    
    if missing_tools:
        print("\n📋 安装指导:")
        for tool_name, install_guide in missing_tools:
            print(f"\n🔧 {tool_name}:")
            for step in install_guide:
                print(f"   • {step}")

def check_python_modules():
    """
    检查Python模块的可用性
    """
    print("\n🐍 检查Python模块...")
    
    required_modules = [
        "ollama", "PIL", "PyPDF2", "docx", "tkinter",
        "cv2", "numpy", "send2trash", "chardet", "yaml"
    ]
    
    optional_modules = [
        "win32com", "coloredlogs", "pytest"
    ]
    
    def check_module(module_name, optional=False):
        try:
            __import__(module_name)
            print(f"✅ {module_name}: 已安装")
            return True
        except ImportError:
            status = "⚠️" if optional else "❌"
            print(f"{status} {module_name}: {'缺失(可选)' if optional else '缺失(必需)'}")
            return False
    
    print("\n必需模块:")
    required_ok = all(check_module(mod) for mod in required_modules)
    
    print("\n可选模块:")
    for mod in optional_modules:
        check_module(mod, optional=True)
    
    return required_ok

def main():
    """
    主函数
    """
    print("🚀 智能文件整理器 - 依赖项安装脚本")
    print(f"Python版本: {sys.version}")
    print(f"操作系统: {platform.system()} {platform.release()}")
    
    # 1. 安装Python依赖
    install_python_dependencies()
    
    # 2. 检查Python模块
    modules_ok = check_python_modules()
    
    # 3. 检查外部工具
    check_external_tools()
    
    # 4. 总结
    print("\n" + "="*60)
    print("📋 安装总结")
    print("="*60)
    
    if modules_ok:
        print("✅ 核心Python依赖已满足，应用程序可以正常运行")
    else:
        print("❌ 部分核心依赖缺失，请检查上述错误信息")
    
    print("\n📝 注意事项:")
    print("• pywin32模块仅在Windows系统下可用，用于DOC文件转换")
    print("• unoconv和antiword是可选工具，用于增强文档转换能力")
    print("• 即使缺少这些工具，应用程序仍可处理大部分文件格式")
    
    print("\n🎯 下一步:")
    print("• 运行 python start.py 启动应用程序")
    print("• 查看 DOC_CONVERSION_GUIDE.md 获取详细的转换工具安装指导")
    
    input("\n按回车键退出...")

if __name__ == "__main__":
    main()