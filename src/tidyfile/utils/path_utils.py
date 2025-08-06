#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径标准化和标签提取工具

提供统一的路径处理和标签生成功能，确保所有模块使用相同的规则

单独执行使用方法:
    python path_utils.py <路径> [选项]

使用示例:
    # 标准化路径
    python path_utils.py "E:\\资料整理/【01】策略报告集合\\2016\\"
    
    # 提取路径标签
    python path_utils.py "E:/资料整理/【01】策略报告集合/2016/test.pdf" --extract-tags
    
    # 从最终目标路径提取链式标签
    python path_utils.py "E:/资料整理/【01】策略报告集合/2016/test.pdf" --final-path

支持的参数:
    --extract-tags, -e       提取路径标签
    --final-path, -f        从最终目标路径提取链式标签
    --normalize, -n         标准化路径（默认）

功能说明:
    1. 标准化路径分隔符（\、/、\\）
    2. 处理Windows盘符和路径格式
    3. 提取链式标签
    4. 自动去掉盘符和一级目录
    5. 不包含文件名，只包含目录路径

作者: AI Assistant
创建时间: 2025-07-27
"""

import os
from pathlib import Path
from typing import List, Dict, Any


def normalize_and_split_path(path: str) -> List[str]:
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


def extract_path_tags(file_path: str, base_folder: str = None) -> Dict[str, str]:
    """
    从文件路径中提取标签（去掉盘符和一级目录，从二级目录开始）
    
    Args:
        file_path: 文件路径
        base_folder: 基础文件夹路径（可选）
        
    Returns:
        包含链式标签的字典
    """
    tags = {}
    try:
        file_path_obj = Path(os.path.abspath(file_path)).resolve()
        file_parent = file_path_obj.parent
        
        # 使用统一的路径标准化方法
        path_parts = normalize_and_split_path(str(file_parent))
        
        # 去掉盘符和一级目录，从二级目录开始
        if path_parts and ':' in path_parts[0]:
            # 去掉盘符（如 E:）
            path_parts = path_parts[1:]
        
        # 去掉一级目录（通常是"资料整理"等）
        if len(path_parts) > 1:
            business_parts = path_parts[1:]
        elif len(path_parts) == 1:
            business_parts = path_parts
        else:
            business_parts = []
        
        # 生成链式标签
        if business_parts:
            chain_path = '/'.join(business_parts)
            tags["链式标签"] = chain_path
            
    except Exception as e:
        import logging
        logging.error(f"提取路径标签失败: {e}")
    
    return tags


def extract_chain_tags_from_final_path(final_path: str) -> str:
    """
    从最终目标路径中提取链式标签（与batch_add_chain_tags.py保持一致）
    
    Args:
        final_path: 最终目标路径
        
    Returns:
        链式标签字符串
    """
    if not final_path:
        return ""
    
    # 使用统一的路径标准化方法
    path_parts = normalize_and_split_path(final_path)
    
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


def build_chain_tags(level_tags: List[str]) -> Dict[str, str]:
    """
    构建包含链式标签的标签字典
    
    Args:
        level_tags: 级标签列表
        
    Returns:
        包含链式标签的字典
    """
    tags = {}
    
    # 添加链式标签
    if level_tags:
        chain_path = '/'.join(level_tags)
        tags["链式标签"] = chain_path
    
    return tags 


def main():
    """单独执行时的主函数"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="路径标准化和标签提取工具")
    parser.add_argument("path", help="要处理的路径")
    parser.add_argument("--extract-tags", "-e", action="store_true", help="提取路径标签")
    parser.add_argument("--final-path", "-f", action="store_true", help="从最终目标路径提取链式标签")
    parser.add_argument("--normalize", "-n", action="store_true", help="标准化路径（默认）")
    
    args = parser.parse_args()
    
    try:
        if args.extract_tags:
            print("=== 提取路径标签 ===")
            print(f"路径: {args.path}")
            tags = extract_path_tags(args.path)
            print(f"标签: {tags}")
        
        elif args.final_path:
            print("=== 从最终目标路径提取链式标签 ===")
            print(f"路径: {args.path}")
            chain_tags = extract_chain_tags_from_final_path(args.path)
            print(f"链式标签: {chain_tags}")
            tags = {"链式标签": chain_tags}
            print(f"标签字典: {tags}")
        
        else:
            print("=== 标准化路径 ===")
            print(f"原始路径: {args.path}")
            parts = normalize_and_split_path(args.path)
            print(f"标准化后: {parts}")
    
    except Exception as e:
        print(f"处理失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 