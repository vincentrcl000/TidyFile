#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文件整理器 - 简单构建脚本
创建时间: 2025-07-22
"""

import os
import sys
import shutil
import subprocess
from datetime import datetime

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

def create_desktop_shortcut():
    """创建桌面快捷方式"""
    print("📋 创建桌面快捷方式...")
    
    # 获取桌面路径
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    exe_path = os.path.abspath("dist/智能文件整理器.exe")
    shortcut_path = os.path.join(desktop, "智能文件整理器.lnk")
    
    if os.path.exists(exe_path):
        try:
            # 使用PowerShell创建快捷方式
            ps_script = f'''
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{exe_path}"
$Shortcut.WorkingDirectory = "{os.path.dirname(exe_path)}"
$Shortcut.IconLocation = "{exe_path},0"
$Shortcut.Save()
'''
            
            result = subprocess.run([
                'powershell', '-Command', ps_script
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ 桌面快捷方式创建成功")
            else:
                print("⚠️ 桌面快捷方式创建失败，请手动创建")
        except Exception as e:
            print(f"⚠️ 创建快捷方式时出错: {e}")
    else:
        print("❌ 可执行文件不存在")

def main():
    """主函数"""
    print("🚀 智能文件整理器 - 简单构建")
    print("=" * 40)
    
    # 清理构建目录
    clean_build_dirs()
    
    # 构建可执行文件
    if not build_executable():
        return False
    
    # 创建桌面快捷方式
    create_desktop_shortcut()
    
    print("\n🎉 构建完成!")
    print("📁 可执行文件位置: dist/智能文件整理器.exe")
    print("📋 使用说明:")
    print("   • 双击运行可执行文件")
    print("   • 确保已安装Ollama并运行")
    print("   • 首次运行可能需要较长时间")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 