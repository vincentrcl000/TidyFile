#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件整理器启动脚本
提供友好的启动体验和错误处理
"""

import sys
import os
import subprocess
import time
from pathlib import Path

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 8):
        print("❌ 错误：需要Python 3.8或更高版本")
        print(f"当前版本：{sys.version}")
        return False
    return True

def check_dependencies():
    """检查依赖包"""
    try:
        import tkinter
        import requests
        import ollama
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖包：{e}")
        print("请运行：pip install -r requirements.txt")
        return False

def check_ollama_service():
    """检查Ollama服务状态"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            return True
        else:
            return False
    except:
        return False

def start_ollama_service():
    """尝试启动Ollama服务"""
    try:
        print("🚀 正在启动Ollama服务...")
        # 在后台启动ollama serve
        subprocess.Popen(["ollama", "serve"], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        
        # 等待服务启动
        for i in range(10):
            time.sleep(1)
            if check_ollama_service():
                print("✅ Ollama服务启动成功")
                return True
            print(f"⏳ 等待服务启动... ({i+1}/10)")
        
        print("⚠️ Ollama服务启动超时，但程序仍可使用简单规则分类")
        return False
    except Exception as e:
        print(f"⚠️ 无法启动Ollama服务：{e}")
        print("程序将使用简单规则分类功能")
        return False

def main():
    """主启动函数"""
    print("=" * 50)
    print("🗂️  智能文件整理器")
    print("=" * 50)
    
    # 检查Python版本
    if not check_python_version():
        input("按任意键退出...")
        return
    
    # 检查依赖包
    if not check_dependencies():
        input("按任意键退出...")
        return
    
    # 检查Ollama服务
    if not check_ollama_service():
        print("⚠️ Ollama服务未运行")
        choice = input("是否尝试自动启动Ollama服务？(y/n): ").lower()
        if choice == 'y':
            start_ollama_service()
        else:
            print("程序将使用简单规则分类功能")
    else:
        print("✅ Ollama服务运行正常")
    
    # 启动GUI应用
    try:
        print("\n🚀 正在启动图形界面...")
        import gui_app
        gui_app.main()
    except KeyboardInterrupt:
        print("\n👋 用户取消启动")
    except Exception as e:
        print(f"\n❌ 启动失败：{e}")
        print("\n请检查错误信息并重试")
        input("按任意键退出...")

if __name__ == "__main__":
    main()