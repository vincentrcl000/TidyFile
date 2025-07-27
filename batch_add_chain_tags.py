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

使用示例:
    # 正常处理（跳过已有链式标签的记录）
    python batch_add_chain_tags.py
    
    # 试运行，查看处理结果但不修改文件
    python batch_add_chain_tags.py --dry-run
    
    # 强制更新所有记录的链式标签
    python batch_add_chain_tags.py --force-update
    
    # 删除所有分级标签
    python batch_add_chain_tags.py --remove-level-tags
    
    # 格式化链式标签
    python batch_add_chain_tags.py --format-tags
    
    # 完整清理：删除分级标签 + 格式化链式标签
    python batch_add_chain_tags.py --clean-all
    
    # 显示前5条记录的标签信息
    python batch_add_chain_tags.py --sample 5
    
    # 仅扫描当前链式标签情况
    python batch_add_chain_tags.py --scan-only
    
    # 处理指定的JSON文件
    python batch_add_chain_tags.py --file my_result.json

功能说明:
    1. 自动备份原文件（格式: 原文件名.backup_YYYYMMDD_HHMMSS）
    2. 从"最终目标路径"中提取链式标签
    3. 支持多种路径分隔符（\、/、\\）
    4. 自动去掉盘符和一级目录（如"资料整理"）
    5. 不包含文件名，只包含目录路径
    6. 链式标签使用"/"分隔符
    7. 删除分级标签功能：移除所有"X级标签"字段
    8. 格式化标签功能：清理特殊字符、多余空格，保留年份数字

作者: AI Assistant
创建时间: 2025-01-15
更新时间: 2025-07-27
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

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
                print(f"✓ 已备份原文件到: {self.backup_file_path}")
                return True
            else:
                print(f"⚠ 文件不存在: {self.result_file}")
                return False
        except Exception as e:
            print(f"✗ 备份文件失败: {e}")
            return False
    
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
                print(f"✗ 处理第 {i + 1} 条记录时出错: {e}")
                stats['errors'] += 1
        
        return stats
    
    def save_data(self, data: List[Dict[str, Any]]) -> bool:
        """保存数据到文件"""
        try:
            with open(self.result_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✓ 数据已保存到: {self.result_file}")
            return True
        except Exception as e:
            print(f"✗ 保存文件失败: {e}")
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
            print("\n✓ 所有记录都已经有链式标签，无需处理")
            return True
        
        # 添加链式标签
        print(f"\n开始处理 {len(data)} 条记录...")
        if dry_run:
            print("⚠ 试运行模式，不会修改原文件")
        if force_update:
            print("⚠ 强制更新模式，将重新生成所有链式标签")
        
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
                print("\n✓ 处理完成！")
            else:
                print("\n✗ 保存失败！")
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
        
        print("=" * 60)
        
        if stats['need_chain_tags'] > 0:
            print(f"\n建议: 可以运行 'python batch_add_chain_tags_enhanced.py --dry-run' 来试运行处理")
        else:
            print(f"\n✓ 所有记录都已经有链式标签，无需处理")
    
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
                print(f"✗ 处理第 {i + 1} 条记录时出错: {e}")
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
                print(f"✗ 处理第 {i + 1} 条记录时出错: {e}")
                stats['errors'] += 1
        
        return stats
    
    def _format_single_tag(self, tag: str) -> str:
        """格式化单个标签"""
        if not tag:
            return tag
        
        # 按"/"分割标签
        parts = tag.split('/')
        formatted_parts = []
        
        for part in parts:
            formatted_part = self._format_tag_part(part.strip())
            if formatted_part:  # 只保留非空部分
                formatted_parts.append(formatted_part)
        
        # 重新组合
        return '/'.join(formatted_parts)
    
    def _format_tag_part(self, part: str) -> str:
        """格式化标签的单个部分"""
        if not part:
            return ""
        
        import re
        
        # 第一步：移除【】括号及其内容
        cleaned = re.sub(r'【[^】]*】', '', part)
        
        # 第二步：移除()括号及其内容
        cleaned = re.sub(r'\([^)]*\)', '', cleaned)
        
        # 第三步：移除[]括号及其内容
        cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
        
        # 第四步：移除数字（除了年份）
        # 查找年份模式（4位数字，如2020、2021等）
        year_pattern = r'(19\d{2}|20\d{2})'
        years = re.findall(year_pattern, cleaned)
        # 现在re.findall直接返回完整的年份字符串
        
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
        
        # 第五步：清理特殊字符，只保留中文、英文、年份和基本标点
        # 保留的字符：中文、英文、年份、基本标点（-、_）
        cleaned = re.sub(r'[^\u4e00-\u9fff\w\s\-_]+', '', cleaned)
        
        # 第六步：清理多余空格
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # 第七步：清理开头和结尾的标点符号
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
            print("⚠ 试运行模式，不会修改原文件")
        
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
                print("\n✓ 删除分级标签完成！")
            else:
                print("\n✗ 保存失败！")
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
        
        # 格式化标签
        print(f"\n开始处理 {len(data)} 条记录...")
        if dry_run:
            print("⚠ 试运行模式，不会修改原文件")
        
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
                print("\n✓ 格式化标签完成！")
            else:
                print("\n✗ 保存失败！")
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
            print("⚠ 试运行模式，不会修改原文件")
        
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
                print("\n✓ 完整清理完成！")
            else:
                print("\n✗ 保存失败！")
            return success
        elif dry_run:
            print("\n试运行完成，未修改原文件")
            return True
        else:
            print("\n无需修改文件")
            return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="批量添加链式标签工具（增强版）")
    parser.add_argument("--file", "-f", default="ai_organize_result.json", 
                       help="要处理的JSON文件路径 (默认: ai_organize_result.json)")
    parser.add_argument("--dry-run", "-d", action="store_true", 
                       help="试运行模式，不修改原文件")
    parser.add_argument("--sample", "-s", type=int, default=0, 
                       help="显示样本数据 (指定显示条数)")
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
    
    args = parser.parse_args()
    
    processor = ChainTagsBatchProcessor(args.file)
    
    if args.sample > 0:
        processor.show_sample(args.sample)
    elif args.scan_only:
        processor.scan_only()
    elif args.remove_level_tags:
        success = processor._process_remove_level_tags(args.dry_run)
        if success:
            print("\n✓ 删除分级标签完成！")
        else:
            print("\n✗ 删除分级标签失败！")
            sys.exit(1)
    elif args.format_tags:
        success = processor._process_format_tags(args.dry_run)
        if success:
            print("\n✓ 格式化标签完成！")
        else:
            print("\n✗ 格式化标签失败！")
            sys.exit(1)
    elif args.clean_all:
        success = processor._process_clean_all(args.dry_run)
        if success:
            print("\n✓ 完整清理完成！")
        else:
            print("\n✗ 完整清理失败！")
            sys.exit(1)
    else:
        success = processor.process(args.dry_run, args.force_update)
        if success:
            print("\n✓ 处理完成！")
        else:
            print("\n✗ 处理失败！")
            sys.exit(1)

if __name__ == "__main__":
    main() 