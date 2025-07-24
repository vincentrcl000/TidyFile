#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件目录智能整理模块

本模块提供简化的目录整理功能，包括：
1. 扫描用户选择的目录结构
2. 使用AI判断哪些文件夹没有业务意义
3. 删除无意义的文件夹后重新创建目录结构

作者: AI Assistant
创建时间: 2025-01-15
更新时间: 2025-07-22
"""

import os
import logging
import json
import shutil
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
import threading
from ai_client_manager import chat_with_ai

class DirectoryOrganizerError(Exception):
    pass



class DirectoryOrganizer:
    def __init__(self, model_name: str = None):
        self.model_name = model_name
        self.setup_logging()
    
    def setup_logging(self) -> None:
        """设置日志配置"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
        logging.info("目录整理器初始化完成")
    
    def initialize_ollama(self) -> None:
        """初始化AI客户端（使用统一的AI管理器）"""
        try:
            # 使用统一的AI管理器，无需单独初始化
            logging.info("AI客户端已通过统一管理器初始化")
        except Exception as e:
            raise DirectoryOrganizerError(f"初始化 AI 客户端失败: {e}")
    
    def scan_directory_structure(self, directory_paths: List[str]) -> Dict[str, Any]:
        """
        扫描多个目录的结构
        
        Args:
            directory_paths: 要扫描的目录路径列表
            
        Returns:
            包含目录结构信息的字典
        """
        try:
            all_structures = {}
            total_directories = 0
            total_files = 0
            
            for directory_path in directory_paths:
                path = Path(directory_path)
                if not path.exists() or not path.is_dir():
                    logging.warning(f"目录不存在或不是有效目录: {directory_path}")
                    continue
                
                structure = self._scan_single_directory(path)
                all_structures[directory_path] = structure
                total_directories += structure['directory_count']
                total_files += structure['file_count']
            
            result = {
                'source_directories': directory_paths,
                'structures': all_structures,
                'total_directories': total_directories,
                'total_files': total_files,
                'scan_time': datetime.now().isoformat()
            }
            
            logging.info(f"目录结构扫描完成，共扫描 {len(directory_paths)} 个目录，{total_directories} 个子目录，{total_files} 个文件")
            return result
            
        except Exception as e:
            raise DirectoryOrganizerError(f"扫描目录结构失败: {e}")
    
    def _scan_single_directory(self, directory_path: Path) -> Dict[str, Any]:
        """扫描单个目录的结构"""
        try:
            directories = []
            files = []
            directory_count = 0
            file_count = 0
            
            # 递归扫描所有子目录和文件
            for item in directory_path.rglob('*'):
                if item.is_dir():
                    relative_path = item.relative_to(directory_path)
                    if str(relative_path) != '.':
                        directories.append(str(relative_path))
                        directory_count += 1
                else:
                    relative_path = item.relative_to(directory_path)
                    files.append(str(relative_path))
                    file_count += 1
            
            return {
                'root_path': str(directory_path),
                'directories': directories,
                'files': files,
                'directory_count': directory_count,
                'file_count': file_count,
                'full_structure': self._build_full_directory_structure(directory_path)
            }
            
        except Exception as e:
            logging.error(f"扫描目录 {directory_path} 失败: {e}")
            return {
                'root_path': str(directory_path),
                'directories': [],
                'files': [],
                'directory_count': 0,
                'file_count': 0,
                'full_structure': {},
                'error': str(e)
            }
    
    def _build_full_directory_structure(self, root_path: Path) -> Dict[str, Any]:
        """构建完整的目录结构树"""
        try:
            structure = {
                'name': root_path.name,
                'path': str(root_path),
                'type': 'directory',
                'children': []
            }
            
            for item in root_path.iterdir():
                if item.is_dir():
                    try:
                        # 检查是否有访问权限
                        list(item.iterdir())
                        
                        # 过滤掉$开头的目录
                        if item.name.startswith('$'):
                            continue
                            
                        child_structure = self._build_full_directory_structure(item)
                        structure['children'].append(child_structure)
                    except PermissionError:
                        continue
                    except Exception as e:
                        logging.warning(f"扫描子目录失败 {item}: {e}")
                        continue
                else:
                    # 添加文件信息
                    file_info = {
                        'name': item.name,
                        'path': str(item.relative_to(root_path)),
                        'type': 'file',
                        'extension': item.suffix.lower(),
                        'size': item.stat().st_size if item.exists() else 0
                    }
                    structure['children'].append(file_info)
            
            return structure
            
        except Exception as e:
            logging.error(f"构建目录结构失败 {root_path}: {e}")
            return {
                'name': root_path.name,
                'path': str(root_path),
                'type': 'directory',
                'children': [],
                'error': str(e)
            }
    
    def generate_directory_recommendation(self, selected_directories: List[str]) -> Dict[str, Any]:
        """
        基于用户选择的目录生成简化的目录结构推荐
        
        Args:
            selected_directories: 用户选择的目录路径列表
            
        Returns:
            包含推荐目录结构的字典
        """
        try:
            # 第一步：扫描用户选择的目录，生成树结构
            logging.info(f"开始扫描用户选择的 {len(selected_directories)} 个目录")
            scan_result = self.scan_selected_directories(selected_directories)
            
            # 第二步：使用AI判断哪些文件夹没有业务意义
            try:
                recommended_structure = self._get_ai_filtered_structure(scan_result, selected_directories[0] if selected_directories else "")
                logging.info("AI过滤生成成功")
            except Exception as ai_error:
                logging.warning(f"AI过滤失败，使用基于规则的过滤: {ai_error}")
                recommended_structure = self._generate_rule_based_filtering(scan_result)
            
            result = {
                'selected_directories': selected_directories,
                'scan_result': scan_result,
                'recommended_structure': recommended_structure,
                'recommendation_time': datetime.now().isoformat()
            }
            
            logging.info("目录结构推荐生成完成")
            return result
            
        except Exception as e:
            raise DirectoryOrganizerError(f"生成目录推荐失败: {e}")
    
    def _get_ai_filtered_structure(self, scan_result: Dict[str, Any], target_folder: str) -> Dict[str, Any]:
        """使用AI过滤无意义的文件夹"""
        try:
            # 构建传递给AI的目录结构
            directory_list = self._build_directory_list_for_ai(scan_result)
            
            prompt = f"""{directory_list}

以上是我当前的文件目录结构，请帮我判断哪些文件夹是有业务意义的，应该保留。

请直接输出需要保留的文件夹名称列表，每行一个文件夹名，不要包含任何其他说明文字。
只保留有业务意义的文件夹，删除以下类型的文件夹：
- 临时文件夹（temp、tmp、临时等）
- 下载文件夹（download、下载等）
- 纯数字编号文件夹（如123、456等）
- 系统文件夹（$开头的）
- 备份文件夹（backup、备份等）
- 缓存文件夹（cache、缓存等）
- 日志文件夹（log、日志等）

请直接输出保留的文件夹名称列表，每行一个名称，不要包含路径分隔符、编号或其他字符。"""

            messages = [
                {
                    'role': 'system',
                    'content': '你是一个专业的目录结构分析专家。直接输出需要保留的文件夹名称列表，每行一个名称，不要包含任何其他内容。'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
            
            response = chat_with_ai(messages)
            
            # 解析AI响应，提取路径列表
            filtered_paths = self._parse_ai_filtered_response(response)
            
            # 构建推荐结构
            result = {
                "recommended_structure": filtered_paths,
                "organization_principles": [
                    "删除临时文件夹",
                    "删除下载文件夹", 
                    "删除纯数字编号文件夹",
                    "删除系统文件夹",
                    "保留有业务意义的文件夹"
                ],
                "summary": f"AI过滤完成，共保留 {len(filtered_paths)} 个有意义的目录路径"
            }
            
            return result
                
        except Exception as e:
            logging.error(f"获取AI过滤失败: {e}")
            raise DirectoryOrganizerError(f"获取AI过滤失败: {e}")
    
    def _build_directory_list_for_ai(self, scan_result: Dict[str, Any]) -> str:
        """构建传递给AI的目录结构列表"""
        try:
            directory_list = []
            
            for source_dir, structure_info in scan_result['directory_structures'].items():
                tree_structure = structure_info['tree_structure']
                directory_list.append(f"=== {source_dir} ===")
                directory_list.append(tree_structure)
                directory_list.append("")
            
            return "\n".join(directory_list)
            
        except Exception as e:
            logging.error(f"构建目录列表失败: {e}")
            return "目录结构构建失败"
    
    def _parse_ai_filtered_response(self, response: str) -> List[str]:
        """解析AI响应中的过滤后路径列表"""
        try:
            paths = []
            lines = response.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 跳过包含说明文字的行
                skip_keywords = [
                    '推荐', '整理', '说明', '注意', '要求', '原则', '删除', '保留',
                    '需要', '检查', '可能', '比如', '用户', '给出', '结构', '还有',
                    '重复', '不同', '仔细', '看原', 'think', '<', '>', '：', ':'
                ]
                if any(keyword in line for keyword in skip_keywords):
                    continue
                
                # 跳过包含特殊字符的行
                if any(char in line for char in ['<', '>', '：', ':', '？', '?', '！', '!']):
                    continue
                
                # 跳过编号行（如 "1.", "2." 等）
                if line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                    # 提取路径部分
                    parts = line.split('.', 1)
                    if len(parts) >= 2:
                        path = parts[1].strip()
                        if path and path not in paths and self._is_valid_path(path):
                            paths.append(path)
                elif ('\\' in line or '/' in line) and not line.startswith('-'):
                    # 直接路径格式
                    if line not in paths and self._is_valid_path(line):
                        paths.append(line)
                elif line.endswith('/') or line.endswith('\\'):
                    # 目录路径
                    if line not in paths and self._is_valid_path(line):
                        paths.append(line)
                elif len(line) > 0 and len(line) < 100:  # 简单的目录名
                    if line not in paths and self._is_valid_path(line):
                        paths.append(line)
            
            return paths
            
        except Exception as e:
            logging.error(f"解析AI响应失败: {e}")
            return []
    
    def _is_valid_path(self, path: str) -> bool:
        """检查路径是否有效"""
        try:
            # 检查是否包含无效字符
            invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
            if any(char in path for char in invalid_chars):
                return False
            
            # 检查长度
            if len(path) > 255:
                return False
            
            # 检查是否为空或只包含空白字符
            if not path.strip():
                return False
            
            return True
        except:
            return False
    
    def _generate_rule_based_filtering(self, scan_result: Dict[str, Any]) -> Dict[str, Any]:
        """基于规则的目录过滤"""
        try:
            all_directories = []
            
            # 收集所有目录路径
            for source_dir, structure_info in scan_result['directory_structures'].items():
                tree_structure = structure_info['tree_structure']
                directories = self._extract_directories_from_tree(tree_structure)
                all_directories.extend(directories)
            
            # 基于规则过滤目录
            filtered_directories = self._filter_directories_by_rules(all_directories)
            
            result = {
                "recommended_structure": filtered_directories,
                "organization_principles": [
                    "删除临时文件夹（temp、tmp、临时等）",
                    "删除下载文件夹（download、下载等）",
                    "删除纯数字编号文件夹",
                    "删除系统文件夹（$开头的）",
                    "保留有业务意义的文件夹"
                ],
                "summary": f"规则过滤完成，共保留 {len(filtered_directories)} 个有意义的目录路径"
            }
            
            return result
            
        except Exception as e:
            logging.error(f"规则过滤失败: {e}")
            return {
                "recommended_structure": [],
                "organization_principles": ["过滤失败"],
                "summary": f"规则过滤失败: {str(e)}"
            }
    
    def _extract_directories_from_tree(self, tree_structure: str) -> List[str]:
        """从树结构中提取所有目录路径"""
        try:
            directories = []
            lines = tree_structure.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 只处理以 / 结尾的行（目录）
                if line.endswith('/'):
                    # 提取目录名
                    dir_name = line.split('── ')[-1].replace('/', '')
                    if dir_name and not dir_name.startswith('$'):
                        directories.append(dir_name)
            
            return directories
            
        except Exception as e:
            logging.error(f"提取目录失败: {e}")
            return []
    
    def _filter_directories_by_rules(self, directories: List[str]) -> List[str]:
        """基于规则过滤目录列表"""
        try:
            if not directories:
                return []
            
            # 定义需要过滤的目录类型
            filter_keywords = [
                'temp', 'tmp', '临时', 'download', '下载', 'backup', '备份',
                '副本', 'copy', 'cache', '缓存', 'log', '日志', 'old', '旧'
            ]
            
            # 定义纯数字模式
            import re
            number_pattern = re.compile(r'^\d+$')
            
            filtered_dirs = []
            for dir_name in directories:
                # 检查是否应该被过滤
                should_filter = False
                
                # 检查关键词
                for keyword in filter_keywords:
                    if keyword.lower() in dir_name.lower():
                        should_filter = True
                        break
                
                # 检查纯数字
                if number_pattern.match(dir_name):
                    should_filter = True
                
                # 检查系统文件夹
                if dir_name.startswith('$'):
                    should_filter = True
                
                # 如果不需要过滤，则保留
                if not should_filter:
                    filtered_dirs.append(dir_name)
            
            return filtered_dirs
            
        except Exception as e:
            logging.error(f"规则过滤目录失败: {e}")
            return directories
    
    def create_recommended_structure(self, target_directory: str, recommended_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据推荐结构创建目录
        
        Args:
            target_directory: 目标目录路径
            recommended_structure: 推荐的目录结构
            
        Returns:
            创建结果
        """
        try:
            if not recommended_structure or not recommended_structure.get('recommended_structure'):
                raise DirectoryOrganizerError("没有有效的推荐结构")
            
            target_path = Path(target_directory)
            if not target_path.exists():
                target_path.mkdir(parents=True, exist_ok=True)
            
            created_directories = []
            failed_directories = []
            
            # 创建推荐的目录结构
            for path_str in recommended_structure['recommended_structure']:
                try:
                    # 处理路径分隔符
                    if '/' in path_str:
                        path_parts = path_str.split('/')
                    else:
                        path_parts = [path_str]
                    
                    # 创建完整路径
                    full_path = target_path
                    for part in path_parts:
                        if part.strip():
                            full_path = full_path / part.strip()
                    
                    # 创建目录
                    if not full_path.exists():
                        full_path.mkdir(parents=True, exist_ok=True)
                        created_directories.append(str(full_path))
                        logging.info(f"创建目录: {full_path}")
                    else:
                        logging.info(f"目录已存在: {full_path}")
                        
                except Exception as e:
                    failed_directories.append(f"{path_str}: {str(e)}")
                    logging.error(f"创建目录失败 {path_str}: {e}")
            
            result = {
                'target_directory': target_directory,
                'created_directories': created_directories,
                'failed_directories': failed_directories,
                'total_created': len(created_directories),
                'total_failed': len(failed_directories),
                'creation_time': datetime.now().isoformat()
            }
            
            logging.info(f"目录创建完成: 成功 {len(created_directories)} 个, 失败 {len(failed_directories)} 个")
            return result
            
        except Exception as e:
            raise DirectoryOrganizerError(f"创建推荐结构失败: {e}")
    
    def get_system_drives(self) -> List[str]:
        """获取系统驱动器列表"""
        try:
            import string
            drives = []
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    drives.append(drive)
            return drives
        except Exception as e:
            logging.error(f"获取系统驱动器失败: {e}")
            return []
    
    def scan_drive_structure(self, drive_path: str, max_depth: int = 1) -> List[Dict[str, Any]]:
        """扫描驱动器结构"""
        try:
            drive_path = Path(drive_path)
            if not drive_path.exists():
                return []
            
            items = []
            
            try:
                for item in drive_path.iterdir():
                    if item.is_dir():
                        # 过滤系统目录
                        if item.name.startswith('$'):
                            continue
                        
                        item_info = {
                            'name': item.name,
                            'path': str(item),
                            'type': 'directory',
                            'has_children': False
                        }
                        
                        # 检查是否有子目录
                        try:
                            if max_depth > 1:
                                children = list(item.iterdir())
                                item_info['has_children'] = any(child.is_dir() and not child.name.startswith('$') for child in children)
                        except PermissionError:
                            pass
                        
                        items.append(item_info)
                        
            except PermissionError:
                pass
            
            # 按名称排序
            items.sort(key=lambda x: x['name'].lower())
            return items
            
        except Exception as e:
            logging.error(f"扫描驱动器结构失败: {e}")
            return []
    
    def scan_selected_directories(self, selected_directories: List[str]) -> Dict[str, Any]:
        """
        扫描用户选择的目录，生成类似tree命令的目录结构
        
        Args:
            selected_directories: 用户选择的目录路径列表
            
        Returns:
            包含目录结构的字典
        """
        try:
            logging.info(f"开始扫描 {len(selected_directories)} 个选择的目录")
            
            all_structures = {}
            total_directories = 0
            total_files = 0
            
            for directory_path in selected_directories:
                path = Path(directory_path)
                if not path.exists() or not path.is_dir():
                    logging.warning(f"目录不存在或不是目录: {directory_path}")
                    continue
                
                logging.info(f"扫描目录: {directory_path}")
                
                # 生成类似tree命令的目录结构
                tree_structure = self._generate_tree_structure(path)
                
                all_structures[directory_path] = {
                    'tree_structure': tree_structure,
                    'scan_time': datetime.now().isoformat()
                }
                
                # 统计信息
                dir_count, file_count = self._count_items(tree_structure)
                total_directories += dir_count
                total_files += file_count
                
                logging.info(f"目录 {directory_path} 扫描完成: {dir_count} 个目录, {file_count} 个文件")
            
            result = {
                'selected_directories': selected_directories,
                'directory_structures': all_structures,
                'total_directories': total_directories,
                'total_files': total_files,
                'scan_time': datetime.now().isoformat()
            }
            
            logging.info(f"所有目录扫描完成: 总计 {total_directories} 个目录, {total_files} 个文件")
            return result
            
        except Exception as e:
            logging.error(f"扫描选择的目录失败: {e}")
            raise DirectoryOrganizerError(f"扫描选择的目录失败: {e}")
    
    def _generate_tree_structure(self, root_path: Path) -> str:
        """生成类似tree命令的目录结构字符串"""
        try:
            tree_lines = []
            tree_lines.append(f"{root_path.name}/")
            
            def add_directory(path: Path, prefix: str, is_last: bool):
                """递归添加目录到树结构"""
                items = []
                
                # 获取目录和文件
                try:
                    for item in path.iterdir():
                        if item.is_dir() and not item.name.startswith('$'):  # 过滤系统目录
                            items.append((item, True))
                        elif item.is_file():
                            items.append((item, False))
                except PermissionError:
                    return
                
                # 排序：目录在前，文件在后，按名称排序
                items.sort(key=lambda x: (not x[1], x[0].name.lower()))
                
                for i, (item, is_dir) in enumerate(items):
                    is_last_item = i == len(items) - 1
                    current_prefix = "└── " if is_last_item else "├── "
                    next_prefix = "    " if is_last_item else "│   "
                    
                    if is_dir:
                        tree_lines.append(f"{prefix}{current_prefix}{item.name}/")
                        add_directory(item, prefix + next_prefix, is_last_item)
                    else:
                        tree_lines.append(f"{prefix}{current_prefix}{item.name}")
            
            add_directory(root_path, "", True)
            return "\n".join(tree_lines)
            
        except Exception as e:
            logging.error(f"生成树结构失败: {e}")
            return f"{root_path.name}/ (扫描失败: {e})"
    
    def _count_items(self, tree_structure: str) -> Tuple[int, int]:
        """统计树结构中的目录和文件数量"""
        lines = tree_structure.split('\n')
        dir_count = 0
        file_count = 0
        
        for line in lines:
            if line.strip().endswith('/'):
                dir_count += 1
            elif line.strip() and not line.strip().endswith('/'):
                file_count += 1
        
        return dir_count, file_count 