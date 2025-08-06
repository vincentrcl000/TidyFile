#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量添加链式标签工具（增强版）

为ai_organize_result.json中的现有记录批量添加链式标签
智能跳过已有链式标签的记录，支持删除分级标签和格式化标签

使用方法:
    python batch_add_chain_tags.py [选项]

支持的参数:
    --file, -f <文件路径>      指定要处理的JSON文件路径 (默认: ai_organize_result.json)
    --dry-run, -d             试运行模式，不修改原文件，只显示处理结果
    --force-update, -u        强制更新模式，重新生成所有链式标签（跳过去重检测）
    --sample, -s <数量>       显示样本数据，指定显示条数
    --scan-only               仅扫描链式标签情况，不进行处理
    --remove-level-tags       删除所有分级标签（1级标签、2级标签等）
    --format-tags             格式化链式标签，清理特殊字符和多余空格
    --clean-all               执行完整清理：删除分级标签 + 格式化链式标签
    --remove-failed           删除"最匹配的目标目录"为"分类失败"的记录
    --remove-empty-summary    删除"文件摘要"为"文件内容为空或过短"的记录
    --smart-tags              智能标签功能：使用AI推荐三级标签并追加到链式标签

使用示例:
    # 基础功能
    python batch_add_chain_tags.py                    # 正常处理（跳过已有链式标签的记录）
    python batch_add_chain_tags.py --dry-run          # 试运行，查看处理结果但不修改文件
    python batch_add_chain_tags.py --force-update     # 强制更新所有记录的链式标签
    python batch_add_chain_tags.py --file my_result.json  # 处理指定的JSON文件
    
    # 数据查看和分析
    python batch_add_chain_tags.py --scan-only        # 仅扫描当前链式标签情况
    python batch_add_chain_tags.py --sample 5         # 显示前5条记录的标签信息
    
    # 标签清理功能
    python batch_add_chain_tags.py --remove-level-tags    # 删除所有分级标签（1级标签、2级标签等）
    python batch_add_chain_tags.py --format-tags          # 格式化链式标签，清理特殊字符和多余空格
    python batch_add_chain_tags.py --clean-all            # 完整清理：删除分级标签 + 格式化链式标签
    
    # 记录清理功能
    python batch_add_chain_tags.py --remove-failed        # 删除"最匹配的目标目录"为"分类失败"的记录
    python batch_add_chain_tags.py --remove-empty-summary # 删除"文件摘要"为"文件内容为空或过短"的记录
    
    # 智能标签功能（增强版）
    python batch_add_chain_tags.py --smart-tags           # 智能标签功能：使用AI推荐三级标签
    python batch_add_chain_tags.py --smart-tags --dry-run # 智能标签功能试运行

功能说明:
    1. 自动备份原文件（格式: 原文件名.backup_YYYYMMDD_HHMMSS）
    2. 从"最终目标路径"中提取链式标签
    3. 支持多种路径分隔符（\、/、\\）
    4. 自动去掉盘符和一级目录（如"资料整理"）
    5. 不包含文件名，只包含目录路径
    6. 链式标签使用"/"分隔符
    7. 删除分级标签功能：移除所有"X级标签"字段
    8. 格式化标签功能：清理特殊字符、多余空格，保留年份数字
    9. 删除失败记录功能：移除"最匹配的目标目录"为"分类失败"的记录
    10. 删除空摘要记录功能：移除"文件摘要"为"文件内容为空或过短"的记录
    11. 智能标签功能（增强版）：
        - 自动调用 analyze_chain_tags.py 分析和生成 chain_tags_list.txt
        - 使用AI逐层推荐标签（一级→二级→三级）
        - 支持处理链式标签为空的记录和没有标签字段的记录（如在线文章）
        - 当任何级别匹配失败时，优雅地停止在上一级，避免强制推荐不相关标签
        - 提供详细的调试信息和推荐过程监控

作者: AI Assistant
创建时间: 2025-01-15
更新时间: 2025-07-27
"""

import json
import os
import sys
import argparse
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Set, Tuple
from tidyfile.ai.client_manager import chat_with_ai

class ChainTagsBatchProcessor:
    """批量添加链式标签处理器"""
    
    def __init__(self, result_file: str = "ai_organize_result.json"):
        """
        初始化处理器
        
        Args:
            result_file: 结果文件路径
        """
        self.result_file = result_file
        self.backup_file_path = f"{result_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def backup_file(self) -> bool:
        """备份原文件"""
        try:
            if os.path.exists(self.result_file):
                import shutil
                shutil.copy2(self.result_file, self.backup_file_path)
                print(f"已备份原文件到: {self.backup_file_path}")
                return True
            else:
                print(f"警告 文件不存在: {self.result_file}")
                return False
        except Exception as e:
            print(f"备份文件失败: {e}")
            return False
    
    def load_data(self) -> List[Dict[str, Any]]:
        """加载JSON数据"""
        try:
            if not os.path.exists(self.result_file):
                print(f"失败 文件不存在: {self.result_file}")
                return []
            
            with open(self.result_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                print("失败 JSON文件格式错误，应该是数组格式")
                return []
            
            print(f"成功 成功加载 {len(data)} 条记录")
            return data
            
        except json.JSONDecodeError as e:
            print(f"失败 JSON文件格式错误: {e}")
            return []
        except Exception as e:
            print(f"失败 加载文件失败: {e}")
            return []
    
    def normalize_and_split_path(self, path: str) -> List[str]:
        """
        标准化并分割路径，支持多种路径分隔符
        
        Args:
            path: 原始路径字符串
            
        Returns:
            分割后的路径部分列表
        """
        if not path or not isinstance(path, str):
            return []
        
        # 标准化路径分隔符
        # 将反斜杠统一为正斜杠
        normalized_path = path.replace('\\', '/')
        
        # 处理Windows盘符（如 E:/）
        # 将 E:/ 转换为 E:/
        if ':' in normalized_path and normalized_path.index(':') == 1:
            # 确保盘符后面有分隔符
            if len(normalized_path) > 2 and normalized_path[2] != '/':
                normalized_path = normalized_path[:2] + '/' + normalized_path[2:]
        
        # 分割路径
        parts = normalized_path.split('/')
        
        # 过滤空字符串和空白字符
        filtered_parts = []
        for part in parts:
            part = part.strip()
            if part and part not in ['', '.', '..']:
                filtered_parts.append(part)
        
        return filtered_parts
    
    def extract_chain_tags_from_existing(self, item: Dict[str, Any]) -> str:
        """从现有记录中提取链式标签"""
        # 只从"最终目标路径"中提取（去掉盘符和一级目录）
        if "最终目标路径" in item:
            final_path = item["最终目标路径"]
            if final_path:
                # 使用改进的路径分割方法
                path_parts = self.normalize_and_split_path(final_path)
                
                # 如果是Windows路径，去掉盘符和一级目录
                if path_parts and ':' in path_parts[0]:
                    # 去掉盘符（如 E:）
                    path_parts = path_parts[1:]
                
                # 去掉一级目录（通常是"资料整理"等）
                if len(path_parts) > 1:
                    # 去掉文件名（最后一个部分）
                    directory_parts = path_parts[1:-1] if len(path_parts) > 2 else path_parts[1:]
                    return '/'.join(directory_parts)
                elif len(path_parts) == 1:
                    return ""
        
        return ""
    
    def pre_scan_chain_tags(self, data: List[Dict[str, Any]]) -> Dict[str, int]:
        """预扫描链式标签情况"""
        stats = {
            'existing_chain_tags': 0,
            'need_chain_tags': 0,
            'no_level_tags': 0
        }
        
        for item in data:
            # 检查是否已经有链式标签
            has_chain_tag = False
            if "标签" in item and isinstance(item["标签"], dict):
                if "链式标签" in item["标签"]:
                    has_chain_tag = True
                    stats['existing_chain_tags'] += 1
                    continue
            
            # 检查是否有链式标签
            chain_tags = self.extract_chain_tags_from_existing(item)
            if chain_tags:
                stats['need_chain_tags'] += 1
            else:
                stats['no_level_tags'] += 1
        
        return stats
    
    def add_chain_tags(self, data: List[Dict[str, Any]], dry_run: bool = False, force_update: bool = False) -> Dict[str, int]:
        """为数据添加链式标签"""
        stats = {
            'total': len(data),
            'processed': 0,
            'added_chain_tags': 0,
            'updated_chain_tags': 0,
            'already_have_chain_tags': 0,
            'no_level_tags': 0,
            'errors': 0,
            'skipped_details': []  # 记录跳过的详细信息
        }
        
        for i, item in enumerate(data):
            try:
                # 检查是否已经有链式标签
                has_chain_tag = False
                existing_chain_tag = ""
                
                if "标签" in item and isinstance(item["标签"], dict):
                    if "链式标签" in item["标签"]:
                        has_chain_tag = True
                        existing_chain_tag = item["标签"]["链式标签"]
                        
                        if not force_update:
                            # 如果不是强制更新模式，跳过已有链式标签的记录
                            stats['already_have_chain_tags'] += 1
                            
                            # 记录跳过的详细信息（只记录前10个）
                            if len(stats['skipped_details']) < 10:
                                file_name = item.get('文件名', '未知文件')
                                stats['skipped_details'].append({
                                    'file_name': file_name,
                                    'existing_chain_tag': existing_chain_tag
                                })
                            
                            continue
                
                # 提取链式标签
                chain_tags = self.extract_chain_tags_from_existing(item)
                
                if not chain_tags:
                    stats['no_level_tags'] += 1
                    continue
                
                # 使用提取的链式标签
                chain_path = chain_tags
                
                # 添加或更新链式标签
                if not dry_run:
                    if "标签" not in item:
                        item["标签"] = {}
                    
                    # 确保标签字段是字典
                    if not isinstance(item["标签"], dict):
                        item["标签"] = {}
                    
                    # 检查是否需要更新
                    if has_chain_tag and existing_chain_tag != chain_path:
                        # 强制更新模式下，如果链式标签不同，则更新
                        item["标签"]["链式标签"] = chain_path
                        stats['updated_chain_tags'] += 1
                    elif not has_chain_tag:
                        # 添加新的链式标签
                        item["标签"]["链式标签"] = chain_path
                        stats['added_chain_tags'] += 1
                    
                    # 不再添加级标签，只保留链式标签
                
                stats['processed'] += 1
                
                if (i + 1) % 100 == 0:
                    print(f"  已处理 {i + 1}/{len(data)} 条记录...")
                
            except Exception as e:
                print(f"失败 处理第 {i + 1} 条记录时出错: {e}")
                stats['errors'] += 1
        
        return stats
    
    def save_data(self, data: List[Dict[str, Any]]) -> bool:
        """保存数据到文件"""
        try:
            with open(self.result_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"成功 数据已保存到: {self.result_file}")
            return True
        except Exception as e:
            print(f"失败 保存文件失败: {e}")
            return False
    
    def process(self, dry_run: bool = False, force_update: bool = False) -> bool:
        """执行批量处理"""
        print("=" * 60)
        print("批量添加链式标签工具（增强版）")
        print("=" * 60)
        
        # 备份文件
        if not dry_run:
            if not self.backup_file():
                return False
        
        # 加载数据
        data = self.load_data()
        if not data:
            return False
        
        # 预扫描链式标签情况
        print(f"\n预扫描 {len(data)} 条记录的链式标签情况...")
        pre_scan_stats = self.pre_scan_chain_tags(data)
        print(f"  已有链式标签: {pre_scan_stats['existing_chain_tags']}")
        print(f"  需要添加链式标签: {pre_scan_stats['need_chain_tags']}")
        print(f"  无链式标签: {pre_scan_stats['no_level_tags']}")
        
        # 如果所有记录都有链式标签且不是强制更新模式，直接返回
        if pre_scan_stats['need_chain_tags'] == 0 and not force_update:
            print("\n成功 所有记录都已经有链式标签，无需处理")
            return True
        
        # 添加链式标签
        print(f"\n开始处理 {len(data)} 条记录...")
        if dry_run:
            print("警告 试运行模式，不会修改原文件")
        if force_update:
            print("警告 强制更新模式，将重新生成所有链式标签")
        
        stats = self.add_chain_tags(data, dry_run, force_update)
        
        # 显示统计信息
        print("\n" + "=" * 60)
        print("处理统计:")
        print(f"  总记录数: {stats['total']}")
        print(f"  已处理: {stats['processed']}")
        print(f"  新增链式标签: {stats['added_chain_tags']}")
        print(f"  更新链式标签: {stats['updated_chain_tags']}")
        print(f"  跳过已有链式标签: {stats['already_have_chain_tags']}")
        print(f"  无链式标签: {stats['no_level_tags']}")
        print(f"  处理错误: {stats['errors']}")
        
        # 显示跳过的详细信息
        if stats['already_have_chain_tags'] > 0:
            print(f"\n跳过的记录详情 (显示前{min(10, len(stats['skipped_details']))}个):")
            for i, detail in enumerate(stats['skipped_details'], 1):
                print(f"  {i}. {detail['file_name']}")
                print(f"     现有链式标签: {detail['existing_chain_tag']}")
            if stats['already_have_chain_tags'] > 10:
                print(f"  ... 还有 {stats['already_have_chain_tags'] - 10} 条记录已跳过")
        
        print("=" * 60)
        
        # 保存数据
        if not dry_run and (stats['added_chain_tags'] > 0 or stats['updated_chain_tags'] > 0):
            success = self.save_data(data)
            if success:
                print("\n成功 处理完成！")
            else:
                print("\n失败 保存失败！")
            return success
        elif dry_run:
            print("\n试运行完成，未修改原文件")
            return True
        else:
            print("\n无需修改文件")
            return True
    
    def scan_only(self):
        """仅扫描链式标签情况"""
        print("=" * 60)
        print("链式标签扫描工具")
        print("=" * 60)
        
        # 加载数据
        data = self.load_data()
        if not data:
            return
        
        # 扫描链式标签情况
        print(f"\n扫描 {len(data)} 条记录的链式标签情况...")
        stats = self.pre_scan_chain_tags(data)
        
        # 提取现有标签统计
        existing_tags = self.extract_existing_tags(data)
        
        # 显示详细统计
        print("\n" + "=" * 60)
        print("扫描统计:")
        print(f"  总记录数: {len(data)}")
        print(f"  已有链式标签: {stats['existing_chain_tags']}")
        print(f"  需要添加链式标签: {stats['need_chain_tags']}")
        print(f"  无链式标签: {stats['no_level_tags']}")
        
        # 计算百分比
        total = len(data)
        if total > 0:
            existing_pct = (stats['existing_chain_tags'] / total) * 100
            need_pct = (stats['need_chain_tags'] / total) * 100
            no_level_pct = (stats['no_level_tags'] / total) * 100
            
            print(f"\n百分比统计:")
            print(f"  已有链式标签: {existing_pct:.1f}%")
            print(f"  需要添加链式标签: {need_pct:.1f}%")
            print(f"  无链式标签: {no_level_pct:.1f}%")
        
        # 显示各级标签数量统计
        print(f"\n各级标签数量统计:")
        print(f"  1级标签数量: {len(existing_tags[1])}")
        print(f"  2级标签数量: {len(existing_tags[2])}")
        print(f"  3级标签数量: {len(existing_tags[3])}")
        print(f"  4级标签数量: {len(existing_tags[4])}")
        print(f"  5级标签数量: {len(existing_tags[5])}")
        print(f"  3级及以上标签总数: {len(existing_tags[3] | existing_tags[4] | existing_tags[5])}")
        
        # 显示前10个1级标签示例
        if existing_tags[1]:
            print(f"\n1级标签示例 (前10个):")
            for i, tag in enumerate(sorted(list(existing_tags[1]))[:10], 1):
                print(f"  {i}. {tag}")
            if len(existing_tags[1]) > 10:
                print(f"  ... 还有 {len(existing_tags[1]) - 10} 个1级标签")
        
        # 显示前10个2级标签示例
        if existing_tags[2]:
            print(f"\n2级标签示例 (前10个):")
            for i, tag in enumerate(sorted(list(existing_tags[2]))[:10], 1):
                print(f"  {i}. {tag}")
            if len(existing_tags[2]) > 10:
                print(f"  ... 还有 {len(existing_tags[2]) - 10} 个2级标签")
        
        print("=" * 60)
        
        if stats['need_chain_tags'] > 0:
            print(f"\n建议: 可以运行 'python batch_add_chain_tags.py --dry-run' 来试运行处理")
        else:
            print(f"\n成功 所有记录都已经有链式标签，无需处理")
    
    def show_sample(self, count: int = 3):
        """显示样本数据"""
        data = self.load_data()
        if not data:
            return
        
        print(f"\n显示前 {min(count, len(data))} 条记录的标签信息:")
        print("-" * 60)
        
        for i, item in enumerate(data[:count]):
            print(f"记录 {i + 1}:")
            print(f"  文件名: {item.get('文件名', 'N/A')}")
            print(f"  最终目标路径: {item.get('最终目标路径', 'N/A')}")
            print(f"  最匹配的目标目录: {item.get('最匹配的目标目录', 'N/A')}")
            
            if "标签" in item:
                print(f"  标签: {item['标签']}")
            else:
                print(f"  标签: 无")
            
            # 提取链式标签
            chain_tags = self.extract_chain_tags_from_existing(item)
            if chain_tags:
                print(f"  提取的链式标签: {chain_tags}")
            else:
                print(f"  提取的链式标签: 无")
            
            print()
    
    def remove_level_tags(self, data: List[Dict[str, Any]], dry_run: bool = False) -> Dict[str, int]:
        """删除所有分级标签"""
        stats = {
            'total': len(data),
            'processed': 0,
            'removed_level_tags': 0,
            'no_level_tags': 0,
            'errors': 0
        }
        
        for i, item in enumerate(data):
            try:
                if "标签" in item and isinstance(item["标签"], dict):
                    # 查找并删除所有分级标签
                    level_tags_to_remove = []
                    for key in item["标签"].keys():
                        if key.endswith("级标签") and key != "链式标签":
                            level_tags_to_remove.append(key)
                    
                    if level_tags_to_remove:
                        if not dry_run:
                            for key in level_tags_to_remove:
                                del item["标签"][key]
                        stats['removed_level_tags'] += len(level_tags_to_remove)
                    else:
                        stats['no_level_tags'] += 1
                else:
                    stats['no_level_tags'] += 1
                
                stats['processed'] += 1
                
                if (i + 1) % 100 == 0:
                    print(f"  已处理 {i + 1}/{len(data)} 条记录...")
                
            except Exception as e:
                print(f"失败 处理第 {i + 1} 条记录时出错: {e}")
                stats['errors'] += 1
        
        return stats
    
    def format_chain_tags(self, data: List[Dict[str, Any]], dry_run: bool = False) -> Dict[str, int]:
        """格式化链式标签"""
        stats = {
            'total': len(data),
            'processed': 0,
            'formatted_tags': 0,
            'no_chain_tags': 0,
            'errors': 0,
            'format_details': []  # 记录格式化详情
        }
        
        for i, item in enumerate(data):
            try:
                if "标签" in item and isinstance(item["标签"], dict):
                    if "链式标签" in item["标签"]:
                        original_tag = item["标签"]["链式标签"]
                        formatted_tag = self._format_single_tag(original_tag)
                        
                        if original_tag != formatted_tag:
                            if not dry_run:
                                item["标签"]["链式标签"] = formatted_tag
                            
                            stats['formatted_tags'] += 1
                            
                            # 记录格式化详情（只记录前10个）
                            if len(stats['format_details']) < 10:
                                file_name = item.get('文件名', '未知文件')
                                stats['format_details'].append({
                                    'file_name': file_name,
                                    'original': original_tag,
                                    'formatted': formatted_tag
                                })
                        else:
                            stats['no_chain_tags'] += 1
                    else:
                        stats['no_chain_tags'] += 1
                else:
                    stats['no_chain_tags'] += 1
                
                stats['processed'] += 1
                
                if (i + 1) % 100 == 0:
                    print(f"  已处理 {i + 1}/{len(data)} 条记录...")
                
            except Exception as e:
                print(f"失败 处理第 {i + 1} 条记录时出错: {e}")
                stats['errors'] += 1
        
        return stats
    
    def _format_single_tag(self, tag: str) -> str:
        """格式化单个标签"""
        if not tag:
            return tag
        
        # 按"/"分割标签
        parts = tag.split('/')
        formatted_parts = []
        
        for i, part in enumerate(parts):
            # 第一个部分（索引0）是一级目录
            is_first_level = (i == 0)
            formatted_part = self._format_tag_part(part.strip(), is_first_level)
            if formatted_part:  # 只保留非空部分
                formatted_parts.append(formatted_part)
        
        # 重新组合
        return '/'.join(formatted_parts)
    
    def _format_tag_part(self, part: str, is_first_level: bool = False) -> str:
        """格式化标签的单个部分"""
        if not part:
            return ""
        
        import re
        
        if is_first_level:
            # 一级目录：保留数字，只去除特殊符号和空格
            # 查找年份模式（4位数字，如2020、2021等）
            year_pattern = r'(19\d{2}|20\d{2})'
            years = re.findall(year_pattern, part)
            
            # 对于一级目录，我们需要特殊处理【】括号
            # 提取【】括号内的数字，然后移除括号
            bracket_numbers = re.findall(r'【(\d+)】', part)
            if bracket_numbers:
                # 移除【】括号及其内容
                cleaned = re.sub(r'【[^】]*】', '', part)
                # 在开头添加数字
                cleaned = bracket_numbers[0] + cleaned
            else:
                cleaned = part
            
            # 清理特殊字符，保留中文、英文、数字和基本标点
            # 保留的字符：中文、英文、数字、基本标点（-、_）
            cleaned = re.sub(r'[^\u4e00-\u9fff\w\s\-_]+', '', cleaned)
            
            # 清理多余空格
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            
            # 清理开头和结尾的标点符号
            cleaned = re.sub(r'^[-_\s]+|[-_\s]+$', '', cleaned)
        else:
            # 非一级目录：原有逻辑，去除数字（除了年份）
            # 第一步：移除【】括号及其内容
            cleaned = re.sub(r'【[^】]*】', '', part)
            
            # 第二步：移除()括号及其内容
            cleaned = re.sub(r'\([^)]*\)', '', cleaned)
            
            # 第三步：移除[]括号及其内容
            cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
            
            # 查找年份模式（4位数字，如2020、2021等）
            year_pattern = r'(19\d{2}|20\d{2})'
            years = re.findall(year_pattern, cleaned)
            
            # 移除其他数字（除了年份）
            # 使用更简单的方法：先移除所有数字，然后恢复年份
            cleaned = re.sub(r'\d+', '', cleaned)
            
            # 恢复年份
            for year in years:
                # 在合适的位置插入年份
                # 这里我们简单地在"年"字前插入年份
                if '年' in cleaned:
                    # 找到第一个"年"的位置
                    year_pos = cleaned.find('年')
                    # 检查"年"前是否已经有年份
                    before_year = cleaned[:year_pos]
                    if not any(y in before_year for y in years):
                        # 在"年"前插入年份
                        cleaned = cleaned[:year_pos] + year + cleaned[year_pos:]
                    break  # 只插入第一个年份
                else:
                    # 如果没有"年"字，就在开头插入年份
                    cleaned = year + cleaned
                    break
            
            # 清理特殊字符，只保留中文、英文、年份和基本标点
            # 保留的字符：中文、英文、年份、基本标点（-、_）
            cleaned = re.sub(r'[^\u4e00-\u9fff\w\s\-_]+', '', cleaned)
            
            # 清理多余空格
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            
            # 清理开头和结尾的标点符号
            cleaned = re.sub(r'^[-_\s]+|[-_\s]+$', '', cleaned)
            
            # 如果清理后为空，但有年份，则保留年份
            if not cleaned and years:
                return years[0]
        
        # 如果清理后为空，返回原标签
        if not cleaned:
            return part
        
        return cleaned
    
    def clean_all_tags(self, data: List[Dict[str, Any]], dry_run: bool = False) -> Dict[str, int]:
        """完整清理：删除分级标签 + 格式化链式标签"""
        print("开始完整清理...")
        
        # 第一步：删除分级标签
        print("1. 删除分级标签...")
        level_stats = self.remove_level_tags(data, dry_run)
        
        # 第二步：格式化链式标签
        print("2. 格式化链式标签...")
        format_stats = self.format_chain_tags(data, dry_run)
        
        # 合并统计信息
        combined_stats = {
            'total': level_stats['total'],
            'processed': level_stats['processed'],
            'removed_level_tags': level_stats['removed_level_tags'],
            'formatted_chain_tags': format_stats['formatted_tags'],
            'errors': level_stats['errors'] + format_stats['errors']
        }
        
        return combined_stats
    
    def _process_remove_level_tags(self, dry_run: bool = False) -> bool:
        """处理删除分级标签"""
        print("=" * 60)
        print("删除分级标签工具")
        print("=" * 60)
        
        # 备份文件
        if not dry_run:
            if not self.backup_file():
                return False
        
        # 加载数据
        data = self.load_data()
        if not data:
            return False
        
        # 删除分级标签
        print(f"\n开始处理 {len(data)} 条记录...")
        if dry_run:
            print("警告 试运行模式，不会修改原文件")
        
        stats = self.remove_level_tags(data, dry_run)
        
        # 显示统计信息
        print("\n" + "=" * 60)
        print("删除分级标签统计:")
        print(f"  总记录数: {stats['total']}")
        print(f"  已处理: {stats['processed']}")
        print(f"  删除的分级标签: {stats['removed_level_tags']}")
        print(f"  无分级标签: {stats['no_level_tags']}")
        print(f"  处理错误: {stats['errors']}")
        print("=" * 60)
        
        # 保存数据
        if not dry_run and stats['removed_level_tags'] > 0:
            success = self.save_data(data)
            if success:
                print("\n成功 删除分级标签完成！")
            else:
                print("\n失败 保存失败！")
            return success
        elif dry_run:
            print("\n试运行完成，未修改原文件")
            return True
        else:
            print("\n无需修改文件")
            return True
    
    def _process_format_tags(self, dry_run: bool = False) -> bool:
        """处理格式化标签"""
        print("=" * 60)
        print("格式化链式标签工具")
        print("=" * 60)
        
        # 备份文件
        if not dry_run:
            if not self.backup_file():
                return False
        
        # 加载数据
        data = self.load_data()
        if not data:
            return False
        
        # 先统计需要格式化的标签数量
        need_format_count = 0
        format_examples = []
        
        for item in data:
            if "标签" in item and isinstance(item["标签"], dict):
                if "链式标签" in item["标签"]:
                    original_tag = item["标签"]["链式标签"]
                    if original_tag:
                        # 检查是否需要格式化
                        formatted_tag = self._format_single_tag(original_tag)
                        if original_tag != formatted_tag:
                            need_format_count += 1
                            if len(format_examples) < 5:
                                format_examples.append({
                                    'original': original_tag,
                                    'formatted': formatted_tag
                                })
        
        print(f"检测到需要格式化的标签: {need_format_count} 个")
        
        if need_format_count == 0:
            print("成功 没有需要格式化的标签")
            return True
        
        # 显示格式化示例
        if format_examples:
            print(f"\n格式化示例:")
            for i, example in enumerate(format_examples, 1):
                print(f"  {i}. 原标签: {example['original']}")
                print(f"     格式化后: {example['formatted']}")
        
        # 格式化标签
        print(f"\n开始处理 {len(data)} 条记录...")
        if dry_run:
            print("警告 试运行模式，不会修改原文件")
        
        stats = self.format_chain_tags(data, dry_run)
        
        # 显示统计信息
        print("\n" + "=" * 60)
        print("格式化标签统计:")
        print(f"  总记录数: {stats['total']}")
        print(f"  已处理: {stats['processed']}")
        print(f"  格式化的标签: {stats['formatted_tags']}")
        print(f"  无需格式化: {stats['no_chain_tags']}")
        print(f"  处理错误: {stats['errors']}")
        
        # 显示格式化详情
        if stats['formatted_tags'] > 0 and stats['format_details']:
            print(f"\n格式化详情 (显示前{min(10, len(stats['format_details']))}个):")
            for i, detail in enumerate(stats['format_details'], 1):
                print(f"  {i}. {detail['file_name']}")
                print(f"     原标签: {detail['original']}")
                print(f"     格式化后: {detail['formatted']}")
            if stats['formatted_tags'] > 10:
                print(f"  ... 还有 {stats['formatted_tags'] - 10} 个标签已格式化")
        
        print("=" * 60)
        
        # 保存数据
        if not dry_run and stats['formatted_tags'] > 0:
            success = self.save_data(data)
            if success:
                print(f"\n成功 格式化标签完成！")
            else:
                print("\n失败 保存失败！")
            return success
        elif dry_run:
            print("\n试运行完成，未修改原文件")
            return True
        else:
            print("\n无需修改文件")
            return True
    
    def _process_clean_all(self, dry_run: bool = False) -> bool:
        """处理完整清理"""
        print("=" * 60)
        print("完整清理工具（删除分级标签 + 格式化链式标签）")
        print("=" * 60)
        
        # 备份文件
        if not dry_run:
            if not self.backup_file():
                return False
        
        # 加载数据
        data = self.load_data()
        if not data:
            return False
        
        # 完整清理
        print(f"\n开始处理 {len(data)} 条记录...")
        if dry_run:
            print("警告 试运行模式，不会修改原文件")
        
        stats = self.clean_all_tags(data, dry_run)
        
        # 显示统计信息
        print("\n" + "=" * 60)
        print("完整清理统计:")
        print(f"  总记录数: {stats['total']}")
        print(f"  已处理: {stats['processed']}")
        print(f"  删除的分级标签: {stats['removed_level_tags']}")
        print(f"  格式化的链式标签: {stats['formatted_chain_tags']}")
        print(f"  处理错误: {stats['errors']}")
        print("=" * 60)
        
        # 保存数据
        if not dry_run and (stats['removed_level_tags'] > 0 or stats['formatted_chain_tags'] > 0):
            success = self.save_data(data)
            if success:
                print("\n成功 完整清理完成！")
            else:
                print("\n失败 保存失败！")
            return success
        elif dry_run:
            print("\n试运行完成，未修改原文件")
            return True
        else:
            print("\n无需修改文件")
            return True
    
    def remove_failed_records(self, data: List[Dict[str, Any]], dry_run: bool = False) -> Dict[str, int]:
        """删除"最匹配的目标目录"为"分类失败"的记录"""
        stats = {
            'total': len(data),
            'processed': 0,
            'removed_failed_records': 0,
            'no_failed_records': 0,
            'errors': 0,
            'removed_details': []  # 记录删除的详细信息
        }
        
        # 创建新列表来存储保留的记录
        filtered_data = []
        
        for i, item in enumerate(data):
            try:
                # 检查是否为"分类失败"记录
                target_dir = item.get("最匹配的目标目录", "")
                if target_dir == "分类失败":
                    stats['removed_failed_records'] += 1
                    
                    # 记录删除的详细信息（只记录前10个）
                    if len(stats['removed_details']) < 10:
                        file_name = item.get('文件名', '未知文件')
                        stats['removed_details'].append({
                            'file_name': file_name,
                            'target_dir': target_dir
                        })
                    
                    # 不添加到新列表中（即删除）
                else:
                    # 保留非"分类失败"的记录
                    filtered_data.append(item)
                    stats['no_failed_records'] += 1
                
                stats['processed'] += 1
                
                if (i + 1) % 100 == 0:
                    print(f"  已处理 {i + 1}/{len(data)} 条记录...")
                
            except Exception as e:
                print(f"失败 处理第 {i + 1} 条记录时出错: {e}")
                stats['errors'] += 1
                # 出错时保留该记录
                filtered_data.append(item)
        
        # 更新原数据列表
        if not dry_run:
            data.clear()
            data.extend(filtered_data)
        
        return stats
    
    def remove_empty_summary_records(self, data: List[Dict[str, Any]], dry_run: bool = False) -> Dict[str, int]:
        """删除"文件摘要"为"文件内容为空或过短"的记录"""
        stats = {
            'total': len(data),
            'processed': 0,
            'removed_empty_summary_records': 0,
            'no_empty_summary_records': 0,
            'errors': 0,
            'removed_details': []  # 记录删除的详细信息
        }
        
        # 创建新列表来存储保留的记录
        filtered_data = []
        
        for i, item in enumerate(data):
            try:
                # 检查是否为"文件内容为空或过短"记录
                file_summary = item.get("文件摘要", "")
                if file_summary == "文件内容为空或过短":
                    stats['removed_empty_summary_records'] += 1
                    
                    # 记录删除的详细信息（只记录前10个）
                    if len(stats['removed_details']) < 10:
                        file_name = item.get('文件名', '未知文件')
                        stats['removed_details'].append({
                            'file_name': file_name,
                            'file_summary': file_summary
                        })
                    
                    # 不添加到新列表中（即删除）
                else:
                    # 保留非"文件内容为空或过短"的记录
                    filtered_data.append(item)
                    stats['no_empty_summary_records'] += 1
                
                stats['processed'] += 1
                
                if (i + 1) % 100 == 0:
                    print(f"  已处理 {i + 1}/{len(data)} 条记录...")
                
            except Exception as e:
                print(f"失败 处理第 {i + 1} 条记录时出错: {e}")
                stats['errors'] += 1
                # 出错时保留该记录
                filtered_data.append(item)
        
        # 更新原数据列表
        if not dry_run:
            data.clear()
            data.extend(filtered_data)
        
        return stats
    
    def _process_remove_failed(self, dry_run: bool = False) -> bool:
        """处理删除'分类失败'记录（已禁用）"""
        # 此功能已从一键优化中移除，直接返回成功
        print("删除'分类失败'记录功能已禁用")
        return True
    
    def _process_remove_empty_summary(self, dry_run: bool = False) -> bool:
        """处理删除'文件内容为空或过短'记录"""
        print("=" * 60)
        print("删除'文件内容为空或过短'记录工具")
        print("=" * 60)
        
        # 备份文件
        if not dry_run:
            if not self.backup_file():
                return False
        
        # 加载数据
        data = self.load_data()
        if not data:
            return False
        
        # 删除'文件内容为空或过短'记录
        print(f"\n开始处理 {len(data)} 条记录...")
        if dry_run:
            print("警告 试运行模式，不会修改原文件")
        
        stats = self.remove_empty_summary_records(data, dry_run)
        
        # 显示统计信息
        print("\n" + "=" * 60)
        print("删除'文件内容为空或过短'记录统计:")
        print(f"  总记录数: {stats['total']}")
        print(f"  已处理: {stats['processed']}")
        print(f"  删除的'文件内容为空或过短'记录: {stats['removed_empty_summary_records']}")
        print(f"  保留的记录: {stats['no_empty_summary_records']}")
        print(f"  处理错误: {stats['errors']}")
        
        # 显示删除详情
        if stats['removed_empty_summary_records'] > 0:
            if stats['removed_details']:
                print(f"\n删除详情 (显示前{min(10, len(stats['removed_details']))}个):")
                for i, detail in enumerate(stats['removed_details'], 1):
                    print(f"  {i}. {detail['file_name']}")
                    print(f"     文件摘要: {detail['file_summary']}")
                if stats['removed_empty_summary_records'] > 10:
                    print(f"  ... 还有 {stats['removed_empty_summary_records'] - 10} 条记录已删除")
            else:
                print(f"\n已删除 {stats['removed_empty_summary_records']} 条'文件内容为空或过短'记录")
        
        print("=" * 60)
        
        # 保存数据
        if not dry_run and stats['removed_empty_summary_records'] > 0:
            success = self.save_data(data)
            if success:
                print(f"\n成功 删除'文件内容为空或过短'记录完成！已删除 {stats['removed_empty_summary_records']} 条记录")
            else:
                print("\n失败 保存失败！")
            return success
        elif dry_run:
            print("\n试运行完成，未修改原文件")
            return True
        else:
            print("\n无需修改文件")
            return True
    
    def load_chain_tags_from_file(self) -> List[str]:
        """从chain_tags_list.txt文件加载链式标签列表"""
        chain_tags_file = "chain_tags_list.txt"
        chain_tags = []
        
        try:
            if os.path.exists(chain_tags_file):
                with open(chain_tags_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        tag = line.strip()
                        if tag:
                            chain_tags.append(tag)
                print(f"成功 从 {chain_tags_file} 加载了 {len(chain_tags)} 个链式标签")
            else:
                print(f"警告 链式标签文件不存在: {chain_tags_file}")
                print("  将使用现有数据提取标签")
        except Exception as e:
            print(f"失败 加载链式标签文件失败: {e}")
            print("  将使用现有数据提取标签")
        
        return chain_tags
    
    def extract_existing_tags(self, data: List[Dict[str, Any]]) -> Dict[int, Set[str]]:
        """提取现有的各级别标签"""
        level_tags: Dict[int, Set[str]] = {1: set(), 2: set(), 3: set(), 4: set(), 5: set()}
        
        for item in data:
            if "标签" in item and isinstance(item["标签"], dict):
                if "链式标签" in item["标签"]:
                    chain_tag = item["标签"]["链式标签"]
                    if chain_tag and isinstance(chain_tag, str):
                        parts = [part.strip() for part in chain_tag.split('/') if part.strip()]
                        for level, tag in enumerate(parts, 1):
                            if level <= 5:  # 只统计前5级
                                level_tags[level].add(tag)
        
        return level_tags
    
    def extract_tags_from_chain_tags_list(self, chain_tags_list: List[str]) -> Dict[int, Set[str]]:
        """从链式标签列表中提取各级别标签"""
        level_tags: Dict[int, Set[str]] = {1: set(), 2: set(), 3: set(), 4: set(), 5: set()}
        
        for chain_tag in chain_tags_list:
            if chain_tag and isinstance(chain_tag, str):
                parts = [part.strip() for part in chain_tag.split('/') if part.strip()]
                for level, tag in enumerate(parts, 1):
                    if level <= 5:  # 只统计前5级
                        level_tags[level].add(tag)
        
        return level_tags
    
    def get_sub_tags(self, chain_tags_list: List[str], parent_tags: List[str]) -> List[str]:
        """获取指定父标签下的子标签列表"""
        sub_tags = set()
        
        for chain_tag in chain_tags_list:
            if chain_tag and isinstance(chain_tag, str):
                parts = [part.strip() for part in chain_tag.split('/') if part.strip()]
                
                # 检查是否匹配父标签路径
                if len(parts) >= len(parent_tags):
                    match = True
                    for i, parent_tag in enumerate(parent_tags):
                        if i >= len(parts) or parts[i] != parent_tag:
                            match = False
                            break
                    
                    if match and len(parts) > len(parent_tags):
                        # 添加下一级标签
                        sub_tags.add(parts[len(parent_tags)])
        
        return sorted(list(sub_tags))
    
    def get_ai_recommendation_hierarchical(self, file_name: str, summary: str, target_path: str, chain_tags_list: List[str]) -> str:
        """使用AI逐层推荐标签（参考smart_file_classifier.py的方法）"""
        try:
            print(f"    [AI推荐] 开始为文件 '{file_name}' 推荐标签...")
            
            # 获取一级标签列表
            level1_tags = self.extract_tags_from_chain_tags_list(chain_tags_list)[1]
            level1_tags_list = sorted(list(level1_tags))
            
            if not level1_tags_list:
                print(f"    [AI推荐] 错误：没有找到一级标签")
                return ""
            
            print(f"    [AI推荐] 一级标签候选数量: {len(level1_tags_list)}")
            
            # 第一步：推荐一级标签
            level1_prompt = f"""不需要思考，直接输出。

你是一个专业的文件分类专家。请根据文件信息从现有的一级标签中选择最合适的一个。

文件信息：
- 文件名/文章标题：{file_name}
- 文件摘要/文章摘要：{summary[:300] if summary else '无摘要'}
- 最终目标路径：{target_path}

现有一级标签（必须严格从以下列表中选择，不要添加任何序号、标点或额外字符）：
{chr(10).join(level1_tags_list[:50])}{'...' if len(level1_tags_list) > 50 else ''}

要求：
1. 只能从上述列表中选择一个标签
2. 标签必须与文件内容高度相关
3. 优先选择文件名或摘要中明确包含的标签
4. 如果找不到完全匹配的标签，选择语义最相关的标签
5. 如果所有标签都与文件内容不相关，请返回"无匹配"
6. 只返回标签名称，不要其他解释

请只返回一个最匹配的标签名称，如果没有合适的标签请返回"无匹配"：

/no_think"""

            messages = [
                {
                    'role': 'system',
                    'content': '你是一个专业的文件分类专家。专注于业务分类，推荐与文件内容最相关的一级标签。如果找不到相关标签，请返回"无匹配"。直接输出标签名称，不要包含任何思考过程、序号或解释。'
                },
                {
                    'role': 'user',
                    'content': level1_prompt
                }
            ]
            
            response = chat_with_ai(messages)
            level1_tag = self.clean_ai_response(response).strip()
            
            if not level1_tag or level1_tag == "无匹配" or level1_tag not in level1_tags:
                print(f"    [AI推荐] 一级标签推荐失败或无效: '{level1_tag}'")
                return ""
            
            print(f"    [AI推荐] 一级标签推荐成功: {level1_tag}")
            
            # 第二步：获取该一级标签下的二级标签
            level2_tags_list = self.get_sub_tags(chain_tags_list, [level1_tag])
            
            if not level2_tags_list:
                print(f"    [AI推荐] 一级标签 '{level1_tag}' 下没有二级标签")
                return level1_tag
            
            print(f"    [AI推荐] 二级标签候选数量: {len(level2_tags_list)}")
            
            # 推荐二级标签
            level2_prompt = f"""不需要思考，直接输出。

你是一个专业的文件分类专家。请根据文件信息从现有的二级标签中选择最合适的一个。

文件信息：
- 文件名/文章标题：{file_name}
- 文件摘要/文章摘要：{summary[:300] if summary else '无摘要'}
- 最终目标路径：{target_path}
- 已选择的一级标签：{level1_tag}

现有二级标签（必须严格从以下列表中选择，不要添加任何序号、标点或额外字符）：
{chr(10).join(level2_tags_list[:50])}{'...' if len(level2_tags_list) > 50 else ''}

要求：
1. 只能从上述列表中选择一个标签
2. 标签必须与文件内容高度相关
3. 优先选择文件名或摘要中明确包含的标签
4. 如果找不到完全匹配的标签，选择语义最相关的标签
5. 如果所有标签都与文件内容不相关，请返回"无匹配"
6. 只返回标签名称，不要其他解释

请只返回一个最匹配的标签名称，如果没有合适的标签请返回"无匹配"：

/no_think"""

            messages = [
                {
                    'role': 'system',
                    'content': '你是一个专业的文件分类专家。专注于业务分类，推荐与文件内容最相关的二级标签。如果找不到相关标签，请返回"无匹配"。直接输出标签名称，不要包含任何思考过程、序号或解释。'
                },
                {
                    'role': 'user',
                    'content': level2_prompt
                }
            ]
            
            response = chat_with_ai(messages)
            level2_tag = self.clean_ai_response(response).strip()
            
            if not level2_tag or level2_tag == "无匹配" or level2_tag not in level2_tags_list:
                print(f"    [AI推荐] 二级标签推荐失败或无效: '{level2_tag}'")
                return level1_tag
            
            print(f"    [AI推荐] 二级标签推荐成功: {level2_tag}")
            
            # 第三步：获取该二级标签下的三级标签
            level3_tags_list = self.get_sub_tags(chain_tags_list, [level1_tag, level2_tag])
            
            if not level3_tags_list:
                print(f"    [AI推荐] 二级标签 '{level2_tag}' 下没有三级标签")
                return f"{level1_tag}/{level2_tag}"
            
            print(f"    [AI推荐] 三级标签候选数量: {len(level3_tags_list)}")
            
            # 推荐三级标签
            level3_prompt = f"""不需要思考，直接输出。

你是一个专业的文件分类专家。请根据文件信息从现有的三级标签中选择最合适的一个。

文件信息：
- 文件名/文章标题：{file_name}
- 文件摘要/文章摘要：{summary[:300] if summary else '无摘要'}
- 最终目标路径：{target_path}
- 已选择的一级标签：{level1_tag}
- 已选择的二级标签：{level2_tag}

现有三级标签（必须严格从以下列表中选择，不要添加任何序号、标点或额外字符）：
{chr(10).join(level3_tags_list[:50])}{'...' if len(level3_tags_list) > 50 else ''}

要求：
1. 只能从上述列表中选择一个标签
2. 标签必须与文件内容高度相关
3. 优先选择文件名或摘要中明确包含的标签
4. 如果找不到完全匹配的标签，选择语义最相关的标签
5. 如果所有标签都与文件内容不相关，请返回"无匹配"
6. 只返回标签名称，不要其他解释

请只返回一个最匹配的标签名称，如果没有合适的标签请返回"无匹配"：

/no_think"""

            messages = [
                {
                    'role': 'system',
                    'content': '你是一个专业的文件分类专家。专注于业务分类，推荐与文件内容最相关的三级标签。如果找不到相关标签，请返回"无匹配"。直接输出标签名称，不要包含任何思考过程、序号或解释。'
                },
                {
                    'role': 'user',
                    'content': level3_prompt
                }
            ]
            
            response = chat_with_ai(messages)
            level3_tag = self.clean_ai_response(response).strip()
            
            if not level3_tag or level3_tag == "无匹配" or level3_tag not in level3_tags_list:
                print(f"    [AI推荐] 三级标签推荐失败或无效: '{level3_tag}'")
                return f"{level1_tag}/{level2_tag}"
            
            print(f"    [AI推荐] 三级标签推荐成功: {level3_tag}")
            
            # 返回完整的三级标签链
            final_chain = f"{level1_tag}/{level2_tag}/{level3_tag}"
            print(f"    [AI推荐] 最终推荐标签链: {final_chain}")
            return final_chain
            
        except Exception as e:
            print(f"    [AI推荐] 逐层推荐失败: {e}")
            return ""
    
    def get_ai_recommendation(self, file_name: str, summary: str, target_path: str, existing_tags: Dict[int, Set[str]]) -> str:
        """使用AI推荐三级标签（保持向后兼容）"""
        try:
            # 首先尝试从目标路径提取标签
            if target_path:
                path_parts = [part.strip() for part in target_path.split('/') if part.strip()]
                if len(path_parts) >= 3:
                    # 检查路径中的标签是否在现有标签中
                    level1_candidate = path_parts[0]
                    level2_candidate = path_parts[1] if len(path_parts) > 1 else ""
                    level3_candidate = path_parts[2] if len(path_parts) > 2 else ""
                    
                    # 验证标签是否在现有标签中
                    if (level1_candidate in existing_tags[1] and 
                        level2_candidate in existing_tags[2] and 
                        level3_candidate in (existing_tags[3] | existing_tags[4] | existing_tags[5])):
                        return f"{level1_candidate}/{level2_candidate}/{level3_candidate}"
            
            # 如果目标路径不适用，尝试使用AI服务
            try:
                # 构建现有标签列表
                level1_tags = sorted(list(existing_tags[1]))
                level2_tags = sorted(list(existing_tags[2]))
                level3_plus_tags = sorted(list(existing_tags[3] | existing_tags[4] | existing_tags[5]))
                
                # 构建提示词（参考smart_file_classifier.py的模式）
                prompt = f"""不需要思考，直接输出。

你是一个专业的文件分类专家。请根据文件信息推荐一个包含三个级别的标签链。

文件信息：
- 文件名：{file_name}
- 文件摘要：{summary[:200] if summary else '无摘要'}
- 最终目标路径：{target_path}

现有标签库（必须严格从以下列表中选择，不要添加任何序号、标点或额外字符）：

一级标签（从中选择）：
{chr(10).join(level1_tags[:30])}{'...' if len(level1_tags) > 30 else ''}

二级标签（从中选择）：
{chr(10).join(level2_tags[:30])}{'...' if len(level2_tags) > 30 else ''}

三级标签（从中选择）：
{chr(10).join(level3_plus_tags[:30])}{'...' if len(level3_plus_tags) > 30 else ''}

要求：
1. 推荐格式：一级标签/二级标签/三级标签
2. 一级标签必须从现有一级标签中选择
3. 二级标签必须从现有二级标签中选择
4. 三级标签必须从现有三级及以上标签中选择
5. 标签要与文件内容高度相关
6. 优先选择有业务含义的分类标签，严格避免选择：
   - 年份标签（如2018年、2019年、2016年等）
   - 时间相关标签（如年度、中期、季度、策略会等）
   - 重复的标签
   - 与一级标签相同的标签
   - 无业务价值的通用标签（如策略报告集合、行业研究分类、专题报告等）
7. 标签要求：
   - 简洁精炼，每个标签不超过5个字
   - 只包含核心业务名词，严格不包含"分析"、"报告"、"研究"、"专题"、"策略"等后缀
   - 每个标签都必须与文件名或摘要内容直接相关，不能推荐与文件内容无关的标签
   - 严格检查相关性：标签中的关键词必须在文件名或摘要中明确出现
   - 禁止推荐：如果标签中的关键词在文件名和摘要中都没有出现，绝对不能推荐该标签
   - 推荐前优先检查：优先选择文件名或摘要中明确出现的标签
   - 只能推荐现有标签中存在的标签，不能创造新标签
   - 如果现有标签中没有与文件内容相关的标签，则只推荐一级标签
   - 推荐前必须从现有标签列表中查找，确保推荐的标签确实存在
   - 对于包含"策略"的文件，只能推荐现有标签中的"策略"、"策略专题"、"宏观策略"等
   - 禁止将多个词组合成新标签，如"期权指数"、"原油期货"等，除非这些组合标签在现有标签中存在
   - 优先匹配：优先推荐文件名或摘要中明确包含的现有标签
   - 如果找不到完全匹配的标签，可以选择语义相关的标签
   - 体现文件的核心业务内容，如：
     * 券商名称（如中信、东吴、海通、国盛等）- 必须在文件名或摘要中明确出现
     * 行业分类（如轻工制造、化工、金融等）- 必须在文件名或摘要中明确出现
     * 产品类型（如原油期货、纸浆期货、天然橡胶等）- 必须在文件名或摘要中明确出现
     * 核心概念（如期权指数、投资策略等）- 必须在文件名或摘要中明确出现
   - 示例：将"期权对标的指数走势的预测性分析"简化为"期权指数"
   - 检查示例：如果推荐"中信"，必须确认文件名或摘要中有"中信"字样
   - 如果找不到足够的相关标签，宁可少推荐，也不要推荐无关标签
   - 最终检查：推荐前确认标签与文件内容相关
8. 确保三个标签都不相同，且都有明确的业务含义
7. 只返回标签链，不要其他解释

请只返回一个最匹配的标签链，不要包含任何其他内容：

/no_think"""

                # 调用AI进行推荐（参考smart_file_classifier.py的模式）
                messages = [
                    {
                        'role': 'system',
                        'content': '你是一个专业的文件分类专家。专注于业务分类，推荐简洁精炼的标签（每个标签不超过5个字），只包含核心业务名词，不包含"分析"、"报告"、"研究"等后缀。优先推荐与文件名或摘要内容直接相关的标签，如果找不到完全匹配的标签，可以选择语义相关的标签。优先选择券商名称、行业分类、产品类型等有业务价值的标签。避免选择年份、时间相关标签和无业务价值的通用标签。直接输出标签链，不要包含任何思考过程、标签、序号或解释。'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
                
                response = chat_with_ai(messages)
                response = self.clean_ai_response(response)
                
                # 验证格式
                if '/' in response and response.count('/') == 2:
                    parts = [part.strip() for part in response.split('/')]
                    if len(parts) == 3 and all(parts):
                        return response
                
                return ""
                
            except Exception as ai_error:
                print(f"AI服务调用失败: {ai_error}")
                # 如果AI服务失败，尝试基于文件名和摘要的简单推荐
                return self._simple_recommendation(file_name, summary, existing_tags)
            
        except Exception as e:
            print(f"推荐失败: {e}")
            return ""
    
    def clean_ai_response(self, response: str) -> str:
        """清理AI响应中的思考过程（参考smart_file_classifier.py）"""
        try:
            if not response:
                return response
            
            # 清理可能的思考过程标签和内容
            response = response.replace('<think>', '').replace('</think>', '').strip()
            
            # 去掉其他常见的思考过程标记
            response = re.sub(r'好的，我现在需要.*?：', '', response, flags=re.DOTALL)
            response = re.sub(r'让我分析一下.*?：', '', response, flags=re.DOTALL)
            response = re.sub(r'我来为您.*?：', '', response, flags=re.DOTALL)
            
            # 清理多余的空白字符
            response = re.sub(r'\n\s*\n', '\n', response)
            response = response.strip()
            
            return response
        except Exception as e:
            print(f"清理AI响应失败: {e}")
            return response
    
    def _simple_recommendation(self, file_name: str, summary: str, existing_tags: Dict[int, Set[str]]) -> str:
        """简单的基于规则的推荐"""
        try:
            # 基于文件名和摘要的关键词匹配
            content = f"{file_name} {summary}".lower()
            
            # 一级标签推荐
            level1_candidates = []
            for tag in existing_tags[1]:
                if any(keyword in content for keyword in tag.lower().split()):
                    level1_candidates.append(tag)
            
            if not level1_candidates:
                # 如果没有匹配，使用最常见的标签
                level1_candidates = list(existing_tags[1])
            
            # 二级标签推荐
            level2_candidates = []
            for tag in existing_tags[2]:
                if any(keyword in content for keyword in tag.lower().split()):
                    level2_candidates.append(tag)
            
            if not level2_candidates:
                level2_candidates = list(existing_tags[2])
            
            # 三级标签推荐
            level3_candidates = []
            for tag in (existing_tags[3] | existing_tags[4] | existing_tags[5]):
                if any(keyword in content for keyword in tag.lower().split()):
                    level3_candidates.append(tag)
            
            if not level3_candidates:
                level3_candidates = list(existing_tags[3] | existing_tags[4] | existing_tags[5])
            
            # 选择第一个候选标签
            if level1_candidates and level2_candidates and level3_candidates:
                return f"{level1_candidates[0]}/{level2_candidates[0]}/{level3_candidates[0]}"
            
            return ""
            
        except Exception as e:
            print(f"简单推荐失败: {e}")
            return ""
    
    def is_tag_similar(self, tag1: str, tag2: str) -> bool:
        """判断两个标签是否相似"""
        if tag1 == tag2:
            return True
        
        # 简单的相似度判断
        tag1_clean = re.sub(r'[^\u4e00-\u9fff\w]', '', tag1.lower())
        tag2_clean = re.sub(r'[^\u4e00-\u9fff\w]', '', tag2.lower())
        
        if tag1_clean == tag2_clean:
            return True
        
        # 检查包含关系
        if tag1_clean in tag2_clean or tag2_clean in tag1_clean:
            return True
        
        return False
    
    def is_tag_relevant_to_content(self, tag: str, file_name: str, summary: str) -> bool:
        """判断标签是否与文件内容相关"""
        if not tag or not file_name:
            return True  # 如果信息不足，默认保留
        
        # 提取关键词
        content = f"{file_name} {summary}".lower()
        tag_lower = tag.lower()
        
        # 简单的相关性判断
        # 1. 直接包含
        if tag_lower in content:
            return True
        
        # 2. 关键词匹配
        tag_words = re.findall(r'[\u4e00-\u9fff]+|\w+', tag_lower)
        content_words = re.findall(r'[\u4e00-\u9fff]+|\w+', content)
        
        # 计算匹配的关键词数量
        matches = sum(1 for word in tag_words if word in content_words)
        if matches >= len(tag_words) * 0.5:  # 至少50%的关键词匹配
            return True
        
        return False
    
    def smart_add_tags(self, data: List[Dict[str, Any]], dry_run: bool = False) -> Dict[str, int]:
        """智能添加标签 - 针对链式标签为空或没有标签字段的记录"""
        stats = {
            'total': len(data),
            'processed': 0,
            'empty_chain_tags': 0,
            'no_tags_field': 0,
            'ai_recommendations': 0,
            'tags_added': 0,
            'errors': 0,
            'recommendation_details': []  # 记录推荐详情
        }
        
        # 加载链式标签列表
        chain_tags_list = self.load_chain_tags_from_file()
        if not chain_tags_list:
            print("失败 无法加载链式标签列表，将使用现有数据提取标签")
            existing_tags = self.extract_existing_tags(data)
            print(f"提取到现有标签：1级{len(existing_tags[1])}个，2级{len(existing_tags[2])}个，3级及以上{len(existing_tags[3] | existing_tags[4] | existing_tags[5])}个")
        else:
            print(f"成功 使用链式标签列表进行逐层推荐，共 {len(chain_tags_list)} 个标签")
        
        for i, item in enumerate(data):
            try:
                # 获取文件信息（支持本地文件和在线文章）
                file_name = item.get('文件名', '') or item.get('文章标题', '')
                summary = item.get('文件摘要', '') or item.get('文章摘要', '') or item.get('摘要', '') or ''
                target_path = item.get('最终目标路径', '')
                
                if not file_name:
                    stats['processed'] += 1
                    continue
                
                print(f"\n[{i + 1}/{len(data)}] 处理文件: {file_name}")
                
                # 检查标签字段
                has_tags_field = "标签" in item and isinstance(item["标签"], dict)
                current_chain_tag = ""
                
                if has_tags_field:
                    current_chain_tag = item["标签"].get("链式标签", "")
                    if current_chain_tag and current_chain_tag.strip():
                        print(f"    [跳过] 已有链式标签: {current_chain_tag}")
                        stats['processed'] += 1
                        continue
                    else:
                        stats['empty_chain_tags'] += 1
                        print(f"    [处理] 链式标签为空")
                else:
                    stats['no_tags_field'] += 1
                    print(f"    [处理] 没有标签字段，需要创建")
                
                # 使用AI推荐标签
                if chain_tags_list:
                    # 使用新的逐层推荐方法
                    ai_recommendation = self.get_ai_recommendation_hierarchical(
                        file_name,
                        summary,
                        target_path,
                        chain_tags_list
                    )
                else:
                    # 使用原有的推荐方法
                    existing_tags = self.extract_existing_tags(data)
                    ai_recommendation = self.get_ai_recommendation(
                        file_name,
                        summary,
                        target_path,
                        existing_tags
                    )
                
                if ai_recommendation:
                    stats['ai_recommendations'] += 1
                    
                    # 直接使用AI推荐的标签
                    final_chain_tag = ai_recommendation
                    
                    # 更新标签
                    if not dry_run:
                        if "标签" not in item:
                            item["标签"] = {}
                        if not isinstance(item["标签"], dict):
                            item["标签"] = {}
                        
                        item["标签"]["链式标签"] = final_chain_tag
                        print(f"    [成功] 添加链式标签: {final_chain_tag}")
                    else:
                        print(f"    [试运行] 将添加链式标签: {final_chain_tag}")
                    
                    stats['tags_added'] += 1
                    
                    # 记录推荐详情（只记录前10个）
                    if len(stats['recommendation_details']) < 10:
                        stats['recommendation_details'].append({
                            'file_name': file_name,
                            'original': current_chain_tag or '空',
                            'ai_recommendation': ai_recommendation,
                            'final': final_chain_tag
                        })
                else:
                    print(f"    [失败] AI推荐失败，无法生成标签")
                
                stats['processed'] += 1
                
                # 每处理10个文件显示一次进度
                if (i + 1) % 10 == 0:
                    print(f"\n--- 进度: 已处理 {i + 1}/{len(data)} 条记录 ---")
                
            except Exception as e:
                print(f"失败 处理第 {i + 1} 条记录时出错: {e}")
                stats['errors'] += 1
        
        return stats
    
    def _process_smart_tags(self, dry_run: bool = False) -> bool:
        """处理智能标签功能"""
        print("=" * 60)
        print("智能标签功能（增强版）")
        print("=" * 60)
        
        # 备份文件
        if not dry_run:
            if not self.backup_file():
                return False
        
        # 加载数据
        data = self.load_data()
        if not data:
            return False
        
        # 先调用 analyze_chain_tags.py 分析和生成 chain_tags_list.txt
        print("\n第一步：调用 analyze_chain_tags.py 分析和生成链式标签列表...")
        try:
            import subprocess
            import sys
            
            # 检查 analyze_chain_tags.py 是否存在
            analyze_script = "analyze_chain_tags.py"
            if not os.path.exists(analyze_script):
                print(f"失败 找不到 {analyze_script} 文件")
                return False
            
            # 调用 analyze_chain_tags.py（静默模式，不显示输出）
            print(f"正在执行: python {analyze_script}")
            result = subprocess.run([sys.executable, analyze_script], 
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if result.returncode == 0:
                print("成功 analyze_chain_tags.py 执行成功")
            else:
                print(f"失败 analyze_chain_tags.py 执行失败")
                return False
                
        except Exception as e:
            print(f"失败 调用 analyze_chain_tags.py 时出错: {e}")
            return False
        
        # 检查 chain_tags_list.txt 是否生成成功
        if not os.path.exists("chain_tags_list.txt"):
            print("失败 chain_tags_list.txt 文件未生成")
            return False
        
        # 显示生成的文件信息
        try:
            with open("chain_tags_list.txt", 'r', encoding='utf-8') as f:
                chain_tags_count = sum(1 for line in f if line.strip())
            print(f"成功 chain_tags_list.txt 文件已生成，包含 {chain_tags_count} 个唯一标签")
        except Exception as e:
            print(f"成功 chain_tags_list.txt 文件已生成")
        
        print("准备开始智能标签处理...")
        
        # 先统计需要处理的记录数量
        empty_count = 0
        no_tags_field_count = 0
        
        for item in data:
            has_tags_field = "标签" in item and isinstance(item["标签"], dict)
            current_chain_tag = ""
            
            if has_tags_field:
                current_chain_tag = item["标签"].get("链式标签", "")
                if not current_chain_tag or not current_chain_tag.strip():
                    empty_count += 1
            else:
                no_tags_field_count += 1
        
        total_need_process = empty_count + no_tags_field_count
        print(f"检测到需要处理的记录:")
        print(f"  链式标签为空的记录: {empty_count} 条")
        print(f"  没有标签字段的记录: {no_tags_field_count} 条")
        print(f"  总计需要处理: {total_need_process} 条")
        
        if total_need_process == 0:
            print("成功 没有需要处理的记录")
            return True
        
        # 智能添加标签
        print(f"\n开始处理 {len(data)} 条记录...")
        if dry_run:
            print("警告 试运行模式，不会修改原文件")
        
        stats = self.smart_add_tags(data, dry_run)
        
        # 显示统计信息
        print("\n" + "=" * 60)
        print("智能标签统计:")
        print(f"  总记录数: {stats['total']}")
        print(f"  已处理: {stats['processed']}")
        print(f"  链式标签为空的记录: {stats['empty_chain_tags']}")
        print(f"  没有标签字段的记录: {stats['no_tags_field']}")
        print(f"  AI推荐次数: {stats['ai_recommendations']}")
        print(f"  标签添加次数: {stats['tags_added']}")
        print(f"  处理错误: {stats['errors']}")
        
        # 显示推荐详情
        if stats['recommendation_details']:
            print(f"\n推荐详情 (显示前{len(stats['recommendation_details'])}个):")
            for i, detail in enumerate(stats['recommendation_details'], 1):
                print(f"  {i}. {detail['file_name']}")
                print(f"     原标签: {detail['original']}")
                print(f"     AI推荐: {detail['ai_recommendation']}")
                print(f"     最终标签: {detail['final']}")
                print()
        
        print("=" * 60)
        
        # 保存数据
        if not dry_run and stats['tags_added'] > 0:
            success = self.save_data(data)
            if success:
                print(f"\n成功 智能标签处理完成！")
            else:
                print("\n失败 保存失败！")
            return success
        elif dry_run:
            print("\n试运行完成，未修改原文件")
            return True
        else:
            print("\n无需修改文件")
            return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="批量添加链式标签工具（增强版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  基础功能:
    python batch_add_chain_tags.py                    # 正常处理
    python batch_add_chain_tags.py --dry-run          # 试运行
    python batch_add_chain_tags.py --force-update     # 强制更新
    
  数据查看:
    python batch_add_chain_tags.py --scan-only        # 扫描标签情况
    python batch_add_chain_tags.py --sample 5         # 显示样本数据
    
  标签清理:
    python batch_add_chain_tags.py --remove-level-tags    # 删除分级标签
    python batch_add_chain_tags.py --format-tags          # 格式化标签
    python batch_add_chain_tags.py --clean-all            # 完整清理
    
  智能标签:
    python batch_add_chain_tags.py --smart-tags           # 智能推荐标签
    python batch_add_chain_tags.py --smart-tags --dry-run # 智能推荐试运行
        """
    )
    parser.add_argument("--file", "-f", default="ai_organize_result.json", 
                       help="要处理的JSON文件路径 (默认: ai_organize_result.json)")
    parser.add_argument("--dry-run", "-d", action="store_true", 
                       help="试运行模式，不修改原文件，只显示处理结果")
    parser.add_argument("--sample", "-s", type=int, default=0, 
                       help="显示样本数据，指定显示条数")
    parser.add_argument("--scan-only", action="store_true", 
                       help="仅扫描链式标签情况，不进行处理")
    parser.add_argument("--force-update", "-u", action="store_true", 
                       help="强制更新模式，重新生成所有链式标签（跳过去重检测）")
    parser.add_argument("--remove-level-tags", action="store_true", 
                       help="删除所有分级标签（1级标签、2级标签等）")
    parser.add_argument("--format-tags", action="store_true", 
                       help="格式化链式标签，清理特殊字符和多余空格")
    parser.add_argument("--clean-all", action="store_true", 
                       help="执行完整清理：删除分级标签 + 格式化链式标签")
    parser.add_argument("--remove-failed", action="store_true", 
                       help="删除'最匹配的目标目录'为'分类失败'的记录")
    parser.add_argument("--remove-empty-summary", action="store_true", 
                       help="删除'文件摘要'为'文件内容为空或过短'的记录")
    parser.add_argument("--smart-tags", action="store_true", 
                       help="智能标签功能：使用AI逐层推荐标签，自动调用analyze_chain_tags.py")
    
    args = parser.parse_args()
    
    processor = ChainTagsBatchProcessor(args.file)
    
    if args.sample > 0:
        processor.show_sample(args.sample)
    elif args.scan_only:
        processor.scan_only()
    elif args.remove_level_tags:
        success = processor._process_remove_level_tags(args.dry_run)
        if success:
            print("\n成功 删除分级标签完成！")
        else:
            print("\n失败 删除分级标签失败！")
            sys.exit(1)
    elif args.format_tags:
        success = processor._process_format_tags(args.dry_run)
        if success:
            print("\n成功 格式化标签完成！")
        else:
            print("\n失败 格式化标签失败！")
            sys.exit(1)
    elif args.clean_all:
        success = processor._process_clean_all(args.dry_run)
        if success:
            print("\n成功 完整清理完成！")
        else:
            print("\n失败 完整清理失败！")
            sys.exit(1)
    elif args.remove_failed:
        success = processor._process_remove_failed(args.dry_run)
        if success:
            print("\n成功 删除'分类失败'记录完成！")
        else:
            print("\n失败 删除'分类失败'记录失败！")
            sys.exit(1)
    elif args.remove_empty_summary:
        success = processor._process_remove_empty_summary(args.dry_run)
        if success:
            print("\n成功 删除'文件内容为空或过短'记录完成！")
        else:
            print("\n失败 删除'文件内容为空或过短'记录失败！")
            sys.exit(1)
    elif args.smart_tags:
        success = processor._process_smart_tags(args.dry_run)
        if success:
            print("\n成功 智能标签处理完成！")
        else:
            print("\n失败 智能标签处理失败！")
            sys.exit(1)
    else:
        success = processor.process(args.dry_run, args.force_update)
        if success:
            print("\n成功 处理完成！")
        else:
            print("\n失败 处理失败！")
            sys.exit(1)

if __name__ == "__main__":
    main() 