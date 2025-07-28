#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
链式标签层级统计分析工具

分析ai_organize_result.json中链式标签的各级别数量
按照层级分别统计去重后的标签数量

使用方法:
    python analyze_chain_tags.py [选项]

支持的参数:
    --file, -f <文件路径>      指定要分析的JSON文件路径 (默认: ai_organize_result.json)
    --sample, -s <数量>       显示样本数据，指定显示条数
    --verbose, -v             显示详细信息，包括每个级别的具体标签

使用示例:
    # 基本统计
    python analyze_chain_tags.py
    
    # 显示详细信息
    python analyze_chain_tags.py --verbose
    
    # 显示前10个样本
    python analyze_chain_tags.py --sample 10
    
    # 分析指定的JSON文件
    python analyze_chain_tags.py --file my_result.json

作者: AI Assistant
创建时间: 2025-01-15
"""

import json
import os
import sys
import argparse
from collections import defaultdict, Counter
from typing import Dict, List, Any, Set

class ChainTagsAnalyzer:
    """链式标签分析器"""
    
    def __init__(self, result_file: str = "ai_organize_result.json"):
        """
        初始化分析器
        
        Args:
            result_file: 结果文件路径
        """
        self.result_file = result_file
        
    def load_data(self) -> List[Dict[str, Any]]:
        """加载JSON数据"""
        try:
            if not os.path.exists(self.result_file):
                print(f"✗ 文件不存在: {self.result_file}")
                return []
            
            with open(self.result_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                print("✗ JSON文件格式错误，应该是数组格式")
                return []
            
            print(f"✓ 成功加载 {len(data)} 条记录")
            return data
            
        except json.JSONDecodeError as e:
            print(f"✗ JSON文件格式错误: {e}")
            return []
        except Exception as e:
            print(f"✗ 加载文件失败: {e}")
            return []
    
    def extract_chain_tags(self, data: List[Dict[str, Any]]) -> List[str]:
        """提取所有链式标签"""
        chain_tags = []
        
        for item in data:
            if "标签" in item and isinstance(item["标签"], dict):
                if "链式标签" in item["标签"]:
                    chain_tag = item["标签"]["链式标签"]
                    if chain_tag and isinstance(chain_tag, str):
                        chain_tags.append(chain_tag)
        
        return chain_tags
    
    def analyze_chain_tags(self, chain_tags: List[str]) -> Dict[str, Any]:
        """分析链式标签的层级结构"""
        # 各级别的标签集合
        level_tags: Dict[int, Set[str]] = defaultdict(set)
        # 各级别的标签计数
        level_counts: Dict[int, int] = defaultdict(int)
        # 各级别的具体标签列表
        level_tag_lists: Dict[int, List[str]] = defaultdict(list)
        
        total_records = len(chain_tags)
        valid_records = 0
        
        for chain_tag in chain_tags:
            if not chain_tag or not isinstance(chain_tag, str):
                continue
            
            valid_records += 1
            
            # 按"/"分割标签
            parts = [part.strip() for part in chain_tag.split('/') if part.strip()]
            
            # 统计每个级别的标签
            for level, tag in enumerate(parts, 1):
                level_tags[level].add(tag)
                level_tag_lists[level].append(tag)
        
        # 计算各级别的去重数量
        for level in sorted(level_tags.keys()):
            level_counts[level] = len(level_tags[level])
        
        return {
            'total_records': total_records,
            'valid_records': valid_records,
            'level_counts': dict(level_counts),
            'level_tags': {level: sorted(tags) for level, tags in level_tags.items()},
            'level_tag_lists': dict(level_tag_lists)
        }
    
    def show_sample_data(self, data: List[Dict[str, Any]], count: int = 5):
        """显示样本数据"""
        print(f"\n显示前 {min(count, len(data))} 条记录的链式标签:")
        print("-" * 60)
        
        chain_tags = self.extract_chain_tags(data)
        
        for i, chain_tag in enumerate(chain_tags[:count]):
            print(f"记录 {i + 1}: {chain_tag}")
            
            # 显示层级结构
            if chain_tag:
                parts = [part.strip() for part in chain_tag.split('/') if part.strip()]
                for level, tag in enumerate(parts, 1):
                    print(f"  {level}级标签: {tag}")
            print()
    
    def analyze(self, verbose: bool = False) -> bool:
        """执行分析"""
        print("=" * 60)
        print("链式标签层级统计分析")
        print("=" * 60)
        
        # 加载数据
        data = self.load_data()
        if not data:
            return False
        
        # 提取链式标签
        chain_tags = self.extract_chain_tags(data)
        print(f"\n找到 {len(chain_tags)} 条链式标签记录")
        
        if not chain_tags:
            print("✗ 没有找到链式标签记录")
            return False
        
        # 分析链式标签
        analysis = self.analyze_chain_tags(chain_tags)
        
        # 显示统计结果
        print("\n" + "=" * 60)
        print("链式标签层级统计结果:")
        print("=" * 60)
        print(f"总记录数: {analysis['total_records']}")
        print(f"有效链式标签记录: {analysis['valid_records']}")
        print(f"无效记录: {analysis['total_records'] - analysis['valid_records']}")
        
        print(f"\n各级别标签数量（去重后）:")
        print("-" * 40)
        
        if not analysis['level_counts']:
            print("没有找到有效的链式标签")
        else:
            for level in sorted(analysis['level_counts'].keys()):
                count = analysis['level_counts'][level]
                print(f"{level}级标签数量: {count}")
        
        # 显示详细信息
        if verbose and analysis['level_tags']:
            print(f"\n各级别具体标签:")
            print("-" * 40)
            
            for level in sorted(analysis['level_tags'].keys()):
                tags = analysis['level_tags'][level]
                print(f"\n{level}级标签 ({len(tags)}个):")
                for i, tag in enumerate(tags, 1):
                    print(f"  {i:2d}. {tag}")
        
        # 显示标签使用频率
        if verbose and analysis['level_tag_lists']:
            print(f"\n各级别标签使用频率（前10个）:")
            print("-" * 40)
            
            for level in sorted(analysis['level_tag_lists'].keys()):
                tag_list = analysis['level_tag_lists'][level]
                counter = Counter(tag_list)
                most_common = counter.most_common(10)
                
                print(f"\n{level}级标签使用频率:")
                for tag, count in most_common:
                    print(f"  {tag}: {count}次")
        
        print("=" * 60)
        return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="链式标签层级统计分析工具")
    parser.add_argument("--file", "-f", default="ai_organize_result.json", 
                       help="要分析的JSON文件路径 (默认: ai_organize_result.json)")
    parser.add_argument("--sample", "-s", type=int, default=0, 
                       help="显示样本数据 (指定显示条数)")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="显示详细信息，包括每个级别的具体标签")
    
    args = parser.parse_args()
    
    analyzer = ChainTagsAnalyzer(args.file)
    
    if args.sample > 0:
        data = analyzer.load_data()
        if data:
            analyzer.show_sample_data(data, args.sample)
    else:
        success = analyzer.analyze(args.verbose)
        if not success:
            sys.exit(1)

if __name__ == "__main__":
    main() 