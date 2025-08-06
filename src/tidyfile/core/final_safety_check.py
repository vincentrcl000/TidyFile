#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终安全检查脚本

检查所有可能导致 ai_organize_result.json 被清空的极端情况
并提供修复建议

作者: AI Assistant
创建时间: 2025-01-15
"""

import os
import json
import shutil
import time
from pathlib import Path
from datetime import datetime

def check_file_safety():
    """检查文件安全性"""
    target_file = "ai_organize_result.json"
    backup_dir = "backups"
    
    print("=" * 60)
    print("🔍 最终安全检查 - ai_organize_result.json")
    print("=" * 60)
    
    # 1. 检查文件是否存在
    if not os.path.exists(target_file):
        print(f"❌ 文件不存在: {target_file}")
        print("💡 建议: 检查是否有其他程序删除了该文件")
        return False
    
    # 2. 检查文件大小
    file_size = os.path.getsize(target_file)
    print(f"📊 文件大小: {file_size} 字节")
    
    if file_size == 0:
        print("❌ 文件为空！")
        print("💡 可能原因:")
        print("   - 启动脚本创建了空文件")
        print("   - 文件写入过程中被中断")
        print("   - 其他程序清空了文件")
        return False
    
    if file_size < 10:
        print("⚠️  文件异常小，可能正在写入中")
        return False
    
    # 3. 检查文件内容
    try:
        with open(target_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        if not content:
            print("❌ 文件内容为空")
            return False
            
        # 检查JSON格式
        if not (content.startswith('[') and content.endswith(']')):
            print("❌ JSON格式不完整")
            return False
            
        # 尝试解析JSON
        data = json.loads(content)
        if not isinstance(data, list):
            print("❌ JSON根元素不是数组")
            return False
            
        print(f"✅ JSON格式正确，包含 {len(data)} 条记录")
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return False
    
    # 4. 检查备份
    backup_files = list(Path(".").glob("*.backup_*.json"))
    if backup_files:
        print(f"📦 找到 {len(backup_files)} 个备份文件")
        for backup in backup_files[-3:]:  # 显示最近3个备份
            backup_size = backup.stat().st_size
            backup_time = datetime.fromtimestamp(backup.stat().st_mtime)
            print(f"   - {backup.name}: {backup_size} 字节, {backup_time}")
    else:
        print("⚠️  没有找到备份文件")
    
    # 5. 检查文件是否正在被写入
    print("\n🔍 检查文件写入状态...")
    initial_size = os.path.getsize(target_file)
    initial_mtime = os.path.getmtime(target_file)
    
    time.sleep(1)  # 等待1秒
    
    current_size = os.path.getsize(target_file)
    current_mtime = os.path.getmtime(target_file)
    
    if current_size != initial_size or current_mtime != initial_mtime:
        print("⚠️  文件正在被写入中")
        print("💡 建议: 等待写入完成后再运行程序")
        return False
    else:
        print("✅ 文件稳定，未被写入")
    
    return True

def identify_risk_sources():
    """识别风险源"""
    print("\n" + "=" * 60)
    print("🚨 识别潜在风险源")
    print("=" * 60)
    
    risk_files = [
        "启动文章阅读助手.bat",
        "启动文章阅读助手.ps1", 
        "启动文章阅读助手.vbs",
        "启动文章阅读助手_增强版.vbs",
        "启动HTTPS服务器.bat"
    ]
    
    for file in risk_files:
        if os.path.exists(file):
            print(f"⚠️  发现风险文件: {file}")
            try:
                with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if "ai_organize_result.json" in content and ("[]" in content or "echo []" in content):
                        print(f"   ❌ 该文件可能创建空JSON文件")
                        print(f"   💡 建议: 修改该文件，使用安全的文件创建方式")
            except Exception as e:
                print(f"   ⚠️  无法读取文件内容: {e}")
    
    # 检查其他可能写入的文件
    python_files = [
        "file_reader.py",
        "concurrent_result_manager.py",
        "smart_file_classifier.py",
        "multi_task_file_reader.py",
        "multi_process_file_reader.py"
    ]
    
    for file in python_files:
        if os.path.exists(file):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "ai_organize_result.json" in content:
                        print(f"📝 发现写入文件: {file}")
                        # 检查是否有不安全的写入操作
                        unsafe_patterns = [
                            "json.dump(data, f",
                            "with open.*w.*encoding",
                            "write_data",
                            "atomic_write_data"
                        ]
                        for pattern in unsafe_patterns:
                            if pattern in content:
                                print(f"   ⚠️  包含写入操作: {pattern}")
            except Exception as e:
                print(f"   ⚠️  无法读取文件内容: {e}")

def create_safe_backup():
    """创建安全备份"""
    print("\n" + "=" * 60)
    print("💾 创建安全备份")
    print("=" * 60)
    
    target_file = "ai_organize_result.json"
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"ai_organize_result.json.safe_backup_{timestamp}"
    
    try:
        if os.path.exists(target_file):
            shutil.copy2(target_file, backup_file)
            print(f"✅ 安全备份已创建: {backup_file}")
            return backup_file
        else:
            print("❌ 源文件不存在，无法创建备份")
            return None
    except Exception as e:
        print(f"❌ 创建备份失败: {e}")
        return None

def suggest_fixes():
    """提供修复建议"""
    print("\n" + "=" * 60)
    print("🔧 修复建议")
    print("=" * 60)
    
    print("1. 🛡️  启动脚本修复:")
    print("   - 修改启动脚本，不要创建空的JSON文件")
    print("   - 使用安全的文件检查方式")
    print("   - 添加文件完整性验证")
    
    print("\n2. 🔒 文件写入保护:")
    print("   - 所有写入操作都应使用原子性写入")
    print("   - 添加文件锁机制")
    print("   - 实现写入状态检测")
    
    print("\n3. 📦 备份策略:")
    print("   - 自动创建时间戳备份")
    print("   - 保留多个历史备份")
    print("   - 定期清理旧备份")
    
    print("\n4. ⚠️  异常处理:")
    print("   - 遇到问题时抛出异常而不是返回空列表")
    print("   - 实现自动恢复机制")
    print("   - 提供详细的错误日志")

def main():
    """主函数"""
    print("🔍 开始最终安全检查...")
    
    # 1. 检查文件安全性
    is_safe = check_file_safety()
    
    # 2. 识别风险源
    identify_risk_sources()
    
    # 3. 创建安全备份
    backup_file = create_safe_backup()
    
    # 4. 提供修复建议
    suggest_fixes()
    
    print("\n" + "=" * 60)
    if is_safe:
        print("✅ 安全检查完成 - 文件状态良好")
    else:
        print("❌ 安全检查完成 - 发现安全问题")
        if backup_file:
            print(f"💾 已创建安全备份: {backup_file}")
    print("=" * 60)

if __name__ == "__main__":
    main() 