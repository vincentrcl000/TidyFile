#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI模型诊断工具

帮助用户诊断和修复AI模型连接问题

作者: AI Assistant
创建时间: 2025-01-15
"""

import json
import os
import sys
import subprocess
import requests
from pathlib import Path
from datetime import datetime

def check_ollama_installation():
    """检查Ollama是否已安装"""
    print("=" * 60)
    print("检查Ollama安装状态")
    print("=" * 60)
    
    # 检查ollama命令是否可用
    try:
        result = subprocess.run(['ollama', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✓ Ollama已安装: {result.stdout.strip()}")
            return True
        else:
            print("✗ Ollama命令执行失败")
            return False
    except FileNotFoundError:
        print("✗ Ollama未安装或不在PATH中")
        return False
    except subprocess.TimeoutExpired:
        print("✗ Ollama命令执行超时")
        return False
    except Exception as e:
        print(f"✗ 检查Ollama时出错: {e}")
        return False

def check_ollama_service():
    """检查Ollama服务是否运行"""
    print("\n检查Ollama服务状态")
    print("-" * 40)
    
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            print("✓ Ollama服务正在运行")
            return True
        else:
            print(f"✗ Ollama服务响应异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到Ollama服务 (localhost:11434)")
        return False
    except requests.exceptions.Timeout:
        print("✗ 连接Ollama服务超时")
        return False
    except Exception as e:
        print(f"✗ 检查Ollama服务时出错: {e}")
        return False

def check_available_models():
    """检查可用的模型"""
    print("\n检查可用模型")
    print("-" * 40)
    
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=10)
        if response.status_code == 200:
            models = response.json().get('models', [])
            if models:
                print(f"✓ 找到 {len(models)} 个可用模型:")
                for model in models:
                    print(f"  - {model.get('name', 'Unknown')}")
                return True
            else:
                print("⚠ 没有找到可用模型")
                return False
        else:
            print(f"✗ 获取模型列表失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 检查可用模型时出错: {e}")
        return False

def check_python_packages():
    """检查Python包依赖"""
    print("\n检查Python包依赖")
    print("-" * 40)
    
    required_packages = {
        'ollama': 'pip install ollama',
        'openai': 'pip install openai',
        'requests': 'pip install requests'
    }
    
    missing_packages = []
    
    for package, install_cmd in required_packages.items():
        try:
            __import__(package)
            print(f"✓ {package} 已安装")
        except ImportError:
            print(f"✗ {package} 未安装")
            print(f"  安装命令: {install_cmd}")
            missing_packages.append((package, install_cmd))
    
    return missing_packages

def check_network_connectivity():
    """检查网络连接"""
    print("\n检查网络连接")
    print("-" * 40)
    
    # 检查局域网Ollama
    try:
        response = requests.get('http://10.64.21.220:11434/api/tags', timeout=5)
        if response.status_code == 200:
            print("✓ 局域网Ollama服务可访问")
        else:
            print("✗ 局域网Ollama服务响应异常")
    except:
        print("✗ 局域网Ollama服务不可访问")
    
    # 检查局域网LM Studio
    try:
        response = requests.get('http://10.64.21.220:1234/v1/models', timeout=5)
        if response.status_code == 200:
            print("✓ 局域网LM Studio服务可访问")
        else:
            print("✗ 局域网LM Studio服务响应异常")
    except:
        print("✗ 局域网LM Studio服务不可访问")

def load_ai_config():
    """加载AI配置文件"""
    config_file = "ai_models_config.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"\n✓ 成功加载配置文件: {config_file}")
            return config
        except Exception as e:
            print(f"✗ 加载配置文件失败: {e}")
            return None
    else:
        print(f"✗ 配置文件不存在: {config_file}")
        return None

def diagnose_ai_models():
    """诊断AI模型配置"""
    print("\n诊断AI模型配置")
    print("-" * 40)
    
    config = load_ai_config()
    if not config:
        return
    
    models = config.get('models', [])
    enabled_models = [m for m in models if m.get('enabled', False)]
    
    print(f"总模型数: {len(models)}")
    print(f"启用模型数: {len(enabled_models)}")
    
    for i, model in enumerate(models, 1):
        name = model.get('name', 'Unknown')
        enabled = model.get('enabled', False)
        base_url = model.get('base_url', '')
        model_name = model.get('model_name', '')
        
        status = "✓" if enabled else "✗"
        print(f"{i}. {status} {name}")
        print(f"   URL: {base_url}")
        print(f"   模型: {model_name}")
        print(f"   状态: {'启用' if enabled else '禁用'}")

def provide_solutions():
    """提供解决方案"""
    print("\n" + "=" * 60)
    print("解决方案建议")
    print("=" * 60)
    
    print("\n1. 安装Ollama:")
    print("   Windows: 访问 https://ollama.ai/download")
    print("   macOS: brew install ollama")
    print("   Linux: curl -fsSL https://ollama.ai/install.sh | sh")
    
    print("\n2. 启动Ollama服务:")
    print("   ollama serve")
    
    print("\n3. 下载模型:")
    print("   ollama pull qwen2.5:3b")
    print("   ollama pull llama3.1:3b")
    
    print("\n4. 安装Python包:")
    print("   pip install ollama openai requests")
    
    print("\n5. 检查防火墙设置:")
    print("   确保端口11434和1234未被防火墙阻止")
    
    print("\n6. 测试连接:")
    print("   curl http://localhost:11434/api/tags")

def main():
    """主函数"""
    print("AI模型诊断工具")
    print("=" * 60)
    print(f"诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查Ollama安装
    ollama_installed = check_ollama_installation()
    
    # 检查Ollama服务
    if ollama_installed:
        ollama_running = check_ollama_service()
        if ollama_running:
            check_available_models()
    
    # 检查Python包
    missing_packages = check_python_packages()
    
    # 检查网络连接
    check_network_connectivity()
    
    # 诊断AI模型配置
    diagnose_ai_models()
    
    # 提供解决方案
    provide_solutions()
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

if __name__ == "__main__":
    main() 