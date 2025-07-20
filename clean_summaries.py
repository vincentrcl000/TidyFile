#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理ai_organize_result.json中包含思考过程的摘要
"""

import json
import os
from pathlib import Path

def clean_summary(summary):
    """清理摘要中的思考过程"""
    if not summary:
        return summary
    
    # 思考过程前缀列表
    think_prefixes = [
        '好的，', '好，', '嗯，', '我来', '我需要', '首先，', '让我', '现在我要',
        '用户希望', '用户要求', '用户让我', '根据', '基于', '考虑到', '让我先仔细看看',
        '用户给了我这个查询', '用户给了我这个任务', '用户给了一个任务',
        '首先，我得看一下', '首先，我要理解', '首先，我得仔细看看',
        '好的，用户让我', '用户让我生成', '内容来自文件', '重点包括', '首先，我需要确认'
    ]
    
    # 按句子分割
    sentences = summary.split('。')
    cleaned_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # 检查是否以思考过程开头
        is_think_sentence = False
        for prefix in think_prefixes:
            if sentence.lower().startswith(prefix.lower()):
                is_think_sentence = True
                break
        
        # 如果不是思考过程，保留这个句子
        if not is_think_sentence:
            cleaned_sentences.append(sentence)
    
    # 重新组合
    if cleaned_sentences:
        cleaned_summary = '。'.join(cleaned_sentences)
        # 确保以句号结尾
        if not cleaned_summary.endswith('。'):
            cleaned_summary += '。'
        return cleaned_summary
    else:
        # 如果清理后没有内容，返回原摘要的后半部分
        return summary[len(summary)//2:] if len(summary) > 50 else summary

def main():
    json_file = Path("ai_organize_result.json")
    
    if not json_file.exists():
        print(f"❌ 文件不存在: {json_file}")
        return
    
    # 备份原文件
    backup_file = json_file.with_suffix('.json.backup')
    if not backup_file.exists():
        import shutil
        shutil.copy2(json_file, backup_file)
        print(f"✅ 已备份原文件到: {backup_file}")
    
    # 读取JSON文件
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return
    
    if not isinstance(data, list):
        print("❌ JSON文件格式错误，期望数组格式")
        return
    
    # 清理摘要
    cleaned_count = 0
    for item in data:
        if '文件摘要' in item:
            original_summary = item['文件摘要']
            cleaned_summary = clean_summary(original_summary)
            
            if cleaned_summary != original_summary:
                item['文件摘要'] = cleaned_summary
                cleaned_count += 1
                print(f"🔧 清理摘要: {item.get('文件名', '未知文件')}")
                print(f"   原始: {original_summary[:100]}...")
                print(f"   清理后: {cleaned_summary[:100]}...")
                print()
    
    # 保存清理后的文件
    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 清理完成！共处理 {cleaned_count} 个摘要")
        print(f"✅ 已保存到: {json_file}")
    except Exception as e:
        print(f"❌ 保存文件失败: {e}")

if __name__ == "__main__":
    main()