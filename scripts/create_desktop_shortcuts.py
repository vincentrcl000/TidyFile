#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TidyFile Desktop Shortcuts Creator
Creates desktop shortcuts for TidyFile and Article Reader
"""

import os
import sys
import winreg
from pathlib import Path
import subprocess

def get_desktop_path():
    """获取桌面路径"""
    try:
        # 尝试从注册表获取桌面路径
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                           r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
            desktop_path = winreg.QueryValueEx(key, "Desktop")[0]
            return Path(desktop_path)
    except:
        # 如果注册表方法失败，使用默认路径
        return Path.home() / "Desktop"

def create_shortcut(target_path, shortcut_name, icon_path=None, description=""):
    """创建桌面快捷方式"""
    try:
        import winshell
        from win32com.client import Dispatch
        
        desktop_path = get_desktop_path()
        shortcut_path = desktop_path / f"{shortcut_name}.lnk"
        
        # 创建快捷方式
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.Targetpath = str(target_path)
        shortcut.WorkingDirectory = str(target_path.parent)
        shortcut.Description = description
        
        # 设置图标
        if icon_path and icon_path.exists():
            shortcut.IconLocation = str(icon_path)
        
        shortcut.save()
        print(f"✓ 创建快捷方式: {shortcut_name}")
        return True
        
    except ImportError:
        print("✗ 缺少必要的库，请安装: pip install pywin32 winshell")
        return False
    except Exception as e:
        print(f"✗ 创建快捷方式失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 TidyFile 桌面快捷方式创建工具")
    print("=" * 50)
    
    # 获取当前目录
    current_dir = Path.cwd()
    
    # 检查资源文件
    resources_dir = current_dir / "resources"
    tidyfile_icon = resources_dir / "TidyFile.ico"
    article_reader_icon = resources_dir / "Article_Reader.ico"
    
    # 创建资源目录
    resources_dir.mkdir(exist_ok=True)
    
    # 检查图标文件
    if not tidyfile_icon.exists():
        print(f"⚠ 图标文件 {tidyfile_icon} 不存在，将使用默认图标")
        tidyfile_icon = None
    
    if not article_reader_icon.exists():
        print(f"⚠ 图标文件 {article_reader_icon} 不存在，将使用默认图标")
        article_reader_icon = None
    
    # 创建TidyFile快捷方式
    tidyfile_vbs = current_dir / "scripts" / "start_tidyfile.vbs"
    if tidyfile_vbs.exists():
        success1 = create_shortcut(
            target_path=tidyfile_vbs,
            shortcut_name="TidyFile",
            icon_path=tidyfile_icon,
            description="TidyFile - AI-powered file organization and analysis tool"
        )
    else:
        print(f"✗ 找不到文件: {tidyfile_vbs}")
        success1 = False
    
    # 创建Article Reader快捷方式
    article_reader_vbs = current_dir / "scripts" / "start_article_reader.vbs"
    if article_reader_vbs.exists():
        success2 = create_shortcut(
            target_path=article_reader_vbs,
            shortcut_name="Article Reader",
            icon_path=article_reader_icon,
            description="TidyFile Article Reader - Web-based file viewer and reader"
        )
    else:
        print(f"✗ 找不到文件: {article_reader_vbs}")
        success2 = False
    
    # 总结
    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 所有快捷方式创建成功！")
        print("📁 桌面快捷方式:")
        print("   - TidyFile")
        print("   - Article Reader")
    elif success1 or success2:
        print("⚠ 部分快捷方式创建成功")
    else:
        print("✗ 快捷方式创建失败")
        print("💡 请确保已安装必要的依赖:")
        print("   pip install pywin32 winshell")
    
    print("\n按任意键退出...")
    input()

if __name__ == "__main__":
    main() 