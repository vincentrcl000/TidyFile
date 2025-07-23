#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试分类问题
"""
import os
import sys
import logging
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from file_organizer_ai import FileOrganizer

def debug_classification_issue():
    """调试分类问题"""
    print("=== 调试分类问题 ===")
    
    # 初始化文件整理器
    organizer = FileOrganizer()
    
    # 测试目标目录
    target_directory = r"D:\资料整理"
    
    print(f"🎯 目标目录: {target_directory}")
    
    # 跳过目录扫描，直接测试相关性计算
    print("\n📁 跳过目录扫描，直接测试相关性计算...")
    
    # 测试一个具体的文件
    test_file_content = """
    华创证券化工行业2018年度投资策略：中国制造，全球龙头
    
    本报告分析了中国化工行业在全球市场中的竞争力和发展趋势。
    报告指出，中国化工企业正逐步成为全球龙头，具备技术、成本和规模优势。
    建议关注具备核心技术、高成长性及国际化布局的龙头企业。
    """
    
    test_file_summary = "该文件为华创证券化工行业2018年度投资策略报告，重点分析中国制造在全球化工行业的竞争力与发展趋势。"
    
    print(f"\n📄 测试文件内容: {test_file_content[:100]}...")
    print(f"📝 测试文件摘要: {test_file_summary}")
    
    # 测试相关性计算
    print("\n🔍 测试相关性计算...")
    
    # 模拟AI推荐的路径
    test_paths = [
        "【16】合作项目资料\\养老",
        "【7-4-1】综合",
        "【7-4-5】人身险",
        "【7-4-6】财产险"
    ]
    
    for path in test_paths:
        relevance_score = organizer._calculate_folder_relevance(
            test_file_content, test_file_summary, path
        )
        print(f"📊 {path}: 相关性评分 {relevance_score:.3f}")
    
    # 测试关键词提取
    print("\n🔍 测试关键词提取...")
    for path in test_paths:
        keywords = organizer._extract_folder_keywords(path)
        print(f"🔑 {path}: 关键词 {keywords}")
    
    # 测试相关性过滤
    print("\n🔍 测试相关性过滤...")
    filtered_paths = organizer._filter_irrelevant_folders(
        test_file_content, test_file_summary, test_paths, target_directory
    )
    print(f"✅ 过滤后的路径: {filtered_paths}")

if __name__ == "__main__":
    debug_classification_issue() 