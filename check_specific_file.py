#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查特定文件是否在JSON中
"""

import json
from pathlib import Path

def check_specific_file():
    """检查特定文件是否在JSON中"""
    json_file = Path('ai_organize_result.json')
    target_file = "【20161008】读懂中国保险业，这些文章不应错过.docx"
    
    if not json_file.exists():
        print("❌ ai_organize_result.json 文件不存在")
        return
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"JSON文件总记录数: {len(data)}")
        
        # 查找目标文件
        found_items = []
        for i, item in enumerate(data):
            if item.get('文件名') == target_file:
                found_items.append((i, item))
        
        if found_items:
            print(f"✅ 找到 {len(found_items)} 条匹配记录:")
            for index, item in found_items:
                print(f"\n记录 {index + 1}:")
                print(f"  文件名: {item.get('文件名')}")
                print(f"  处理状态: {item.get('处理状态')}")
                print(f"  处理时间: {item.get('处理时间')}")
                print(f"  最终目标路径: {item.get('最终目标路径')}")
                print(f"  标签: {item.get('标签', {})}")
        else:
            print(f"❌ 未找到文件: {target_file}")
            
            # 显示一些文件名示例
            print("\n文件名示例:")
            for i, item in enumerate(data[:10]):
                print(f"  {i+1}. {item.get('文件名', '无文件名')}")
            
            # 检查是否有类似的文件名
            similar_files = []
            for item in data:
                filename = item.get('文件名', '')
                if '保险' in filename and 'docx' in filename.lower():
                    similar_files.append(item)
            
            if similar_files:
                print(f"\n找到 {len(similar_files)} 个包含'保险'的docx文件:")
                for item in similar_files[:5]:
                    print(f"  - {item.get('文件名')}")
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON文件格式错误: {e}")
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")

if __name__ == "__main__":
    check_specific_file()
    input("\n按回车键退出...") 