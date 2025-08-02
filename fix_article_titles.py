#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正ai_organize_result.json中的文章标题
将错误的标题替换为weixin_article.json中的原始标题
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import re

# 配置
WEIXIN_ARTICLE_JSON = Path("weixin_manager/weixin_article.json")
AI_RESULT_JSON = Path("ai_organize_result.json")
BACKUP_SUFFIX = f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def is_bad_title(title):
    """检查标题是否有问题"""
    if not title or len(title.strip()) == 0:
        return True
    
    # 检查是否是默认值或错误值
    bad_titles = [
        "无标题", "文章标题", "微信文章标题", "微信公众号文章标题",
        "title", "Title", "TITLE", "标题", "文章", "Article"
    ]
    
    if title.strip() in bad_titles:
        return True
    
    # 检查是否包含编码问题（乱码）
    try:
        # 尝试编码解码，如果失败可能是乱码
        title.encode('utf-8').decode('utf-8')
    except UnicodeError:
        return True
    
    # 检查是否包含大量特殊字符或数字（可能是编码问题）
    if len(title) > 10 and sum(1 for c in title if c.isascii() and not c.isalnum()) > len(title) * 0.3:
        return True
    
    # 检查是否包含明显的编码问题字符
    if re.search(r'[çåæéèêëìíîïðñòóôõöùúûüýþÿ]', title):
        return True
    
    return False

def load_json_safe(file_path):
    """安全加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[错误] 加载文件失败 {file_path}: {e}")
        return None

def save_json_safe(file_path, data):
    """安全保存JSON文件"""
    try:
        # 创建备份
        backup_path = file_path.with_suffix(f'{file_path.suffix}{BACKUP_SUFFIX}')
        if file_path.exists():
            import shutil
            shutil.copy2(file_path, backup_path)
            print(f"[备份] 已创建备份: {backup_path}")
        
        # 保存新文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[保存] 已保存到: {file_path}")
        return True
    except Exception as e:
        print(f"[错误] 保存文件失败 {file_path}: {e}")
        return False

def create_title_mapping(weixin_articles):
    """创建URL到原始标题的映射"""
    title_mapping = {}
    for article in weixin_articles:
        title = article.get('文章标题', '').strip()
        url = article.get('源文件路径', '').strip()
        if title and url:
            title_mapping[url] = title
    return title_mapping

def fix_article_titles():
    """修正文章标题"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始修正文章标题")
    print(f"[配置] 微信文章文件: {WEIXIN_ARTICLE_JSON}")
    print(f"[配置] AI结果文件: {AI_RESULT_JSON}")
    
    # 检查文件是否存在
    if not WEIXIN_ARTICLE_JSON.exists():
        print(f"[错误] 未找到微信文章文件: {WEIXIN_ARTICLE_JSON}")
        return False
    
    if not AI_RESULT_JSON.exists():
        print(f"[错误] 未找到AI结果文件: {AI_RESULT_JSON}")
        return False
    
    # 加载数据
    print("[加载] 正在加载微信文章数据...")
    weixin_articles = load_json_safe(WEIXIN_ARTICLE_JSON)
    if not weixin_articles:
        print("[错误] 微信文章数据加载失败")
        return False
    
    print("[加载] 正在加载AI结果数据...")
    ai_results = load_json_safe(AI_RESULT_JSON)
    if not ai_results:
        print("[错误] AI结果数据加载失败")
        return False
    
    print(f"[加载] 成功加载 {len(weixin_articles)} 篇微信文章")
    print(f"[加载] 成功加载 {len(ai_results)} 条AI分析记录")
    
    # 创建标题映射
    title_mapping = create_title_mapping(weixin_articles)
    print(f"[映射] 创建了 {len(title_mapping)} 个标题映射")
    
    # 统计信息
    total_records = len(ai_results)
    fixed_count = 0
    skipped_count = 0
    error_count = 0
    
    print(f"\n=== 开始修正文章标题 ===")
    print(f"总记录数: {total_records}")
    print("=" * 50)
    
    # 遍历AI结果记录
    for idx, record in enumerate(ai_results, 1):
        current_title = record.get('文章标题', '').strip()
        url = record.get('源文件路径', '').strip()
        
        if not url:
            error_count += 1
            print(f"[{idx}/{total_records}] 缺少URL，跳过")
            continue
        
        # 检查当前标题是否有问题
        if is_bad_title(current_title):
            # 查找原始标题
            original_title = title_mapping.get(url)
            if original_title:
                print(f"[{idx}/{total_records}] 修正标题:")
                print(f"  原标题: '{current_title}'")
                print(f"  新标题: '{original_title}'")
                print(f"  URL: {url[:50]}...")
                
                # 更新标题
                record['文章标题'] = original_title
                fixed_count += 1
            else:
                print(f"[{idx}/{total_records}] 标题有问题但找不到原始标题:")
                print(f"  当前标题: '{current_title}'")
                print(f"  URL: {url[:50]}...")
                error_count += 1
        else:
            skipped_count += 1
            if idx % 100 == 0:  # 每100条显示一次进度
                print(f"[{idx}/{total_records}] 标题正常，跳过")
    
    # 保存修正后的数据
    print(f"\n=== 修正完成 ===")
    print(f"总记录数: {total_records}")
    print(f"修正数量: {fixed_count}")
    print(f"跳过数量: {skipped_count}")
    print(f"错误数量: {error_count}")
    
    if fixed_count > 0:
        print(f"\n[保存] 正在保存修正后的数据...")
        if save_json_safe(AI_RESULT_JSON, ai_results):
            print(f"[成功] 标题修正完成，共修正 {fixed_count} 条记录")
            return True
        else:
            print(f"[错误] 保存失败")
            return False
    else:
        print(f"[信息] 没有需要修正的标题")
        return True

def main():
    """主函数"""
    print("文章标题修正工具")
    print("=" * 50)
    
    try:
        success = fix_article_titles()
        if success:
            print("\n[完成] 标题修正任务完成")
        else:
            print("\n[失败] 标题修正任务失败")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n[中断] 用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n[错误] 发生未预期的错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 