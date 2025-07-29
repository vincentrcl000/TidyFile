#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查JSON文件数据结构和过滤情况
"""

import json
from pathlib import Path

def analyze_json_data():
    """分析JSON文件数据"""
    json_file = Path('ai_organize_result.json')
    
    if not json_file.exists():
        print("❌ ai_organize_result.json 文件不存在")
        return
    
    print("=== JSON文件数据分析 ===")
    print(f"文件大小: {json_file.stat().st_size / 1024 / 1024:.2f} MB")
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"总记录数: {len(data)}")
        
        if len(data) == 0:
            print("❌ JSON文件为空")
            return
        
        # 分析第一条记录的结构
        first_item = data[0]
        print(f"\n第一条记录结构:")
        for key, value in first_item.items():
            if isinstance(value, str) and len(value) > 100:
                print(f"  {key}: {value[:100]}...")
            else:
                print(f"  {key}: {value}")
        
        # 分析处理状态
        status_counts = {}
        for item in data:
            status = item.get('处理状态', '无状态')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"\n处理状态统计:")
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")
        
        # 分析被过滤的数据
        filtered_out = [item for item in data if '迁移失败' in item.get('处理状态', '')]
        print(f"\n被过滤掉的数据:")
        print(f"  包含'迁移失败'的记录数: {len(filtered_out)}")
        
        if filtered_out:
            print("  被过滤掉的记录示例:")
            for i, item in enumerate(filtered_out[:3]):
                print(f"    {i+1}. {item.get('文件名', '无文件名')} - {item.get('处理状态', '无状态')}")
        
        # 分析有效数据
        valid_data = [item for item in data if '迁移失败' not in item.get('处理状态', '')]
        print(f"\n有效数据:")
        print(f"  有效记录数: {len(valid_data)}")
        
        if valid_data:
            print("  有效记录示例:")
            for i, item in enumerate(valid_data[:3]):
                print(f"    {i+1}. {item.get('文件名', '无文件名')} - {item.get('处理状态', '无状态')}")
        
        # 分析标签数据
        tag_counts = {}
        for item in data:
            tags = item.get('标签', {})
            chain_tag = tags.get('链式标签', '')
            if chain_tag:
                tag_counts[chain_tag] = tag_counts.get(chain_tag, 0) + 1
        
        print(f"\n标签统计:")
        print(f"  有链式标签的记录数: {len([item for item in data if item.get('标签', {}).get('链式标签', '')])}")
        print(f"  无链式标签的记录数: {len([item for item in data if not item.get('标签', {}).get('链式标签', '')])}")
        
        if tag_counts:
            print("  常见标签:")
            sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
            for tag, count in sorted_tags[:5]:
                print(f"    {tag}: {count}")
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON文件格式错误: {e}")
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")

if __name__ == "__main__":
    analyze_json_data()
    input("\n按回车键退出...") 