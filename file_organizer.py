#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件整理核心模块

本模块提供文件自动分类和整理的核心功能，包括：
1. 与 Ollama 本地大模型的交互
2. 文件分类逻辑
3. 文件移动和复制操作
4. 错误处理和日志记录

作者: AI Assistant
创建时间: 2025-01-15
"""

import os
import shutil
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from pathlib import Path

try:
    import ollama
except ImportError:
    print("错误: 请安装 ollama 库: pip install ollama")
    raise

try:
    from PIL import Image
except ImportError:
    print("警告: PIL 库未安装，图片分析功能将不可用")
    Image = None

# 导入转移日志管理器
from transfer_log_manager import TransferLogManager


class FileOrganizerError(Exception):
    """文件整理器自定义异常类"""
    pass


class OllamaClient:
    """Ollama 客户端封装类"""
    
    def __init__(self, model_name: str = None, host: str = "http://localhost:11434"):
        """
        初始化 Ollama 客户端
        
        Args:
            model_name: 使用的模型名称，如果为None则自动选择第一个可用模型
            host: Ollama 服务地址
        """
        self.model_name = model_name
        self.host = host
        self.client = ollama.Client(host=host)
        
        # 验证连接和模型
        self._validate_connection()
        
    def _validate_connection(self) -> None:
        """验证与 Ollama 服务的连接"""
        try:
            # 检查服务是否运行
            models_response = self.client.list()
            
            # 处理不同的响应格式
            if hasattr(models_response, 'models'):
                models_list = models_response.models
            elif isinstance(models_response, dict) and 'models' in models_response:
                models_list = models_response['models']
            else:
                models_list = models_response if isinstance(models_response, list) else []
            
            # 提取模型名称
            self.available_models = []
            for model in models_list:
                if isinstance(model, dict):
                    if 'name' in model:
                        self.available_models.append(model['name'])
                    elif 'model' in model:
                        self.available_models.append(model['model'])
                elif hasattr(model, 'name'):
                    self.available_models.append(model.name)
                elif hasattr(model, 'model'):
                    self.available_models.append(model.model)
                else:
                    self.available_models.append(str(model))
            
            if not self.available_models:
                raise FileOrganizerError("没有可用的模型，请先拉取模型")
                
            # 如果没有指定模型或指定模型不存在，使用第一个可用模型
            if self.model_name is None or self.model_name not in self.available_models:
                if self.model_name is not None:
                    logging.warning(f"模型 {self.model_name} 不可用，使用 {self.available_models[0]}")
                self.model_name = self.available_models[0]
                logging.info(f"自动选择模型: {self.model_name}")
                
            logging.info(f"成功连接到 Ollama，使用模型: {self.model_name}")
            logging.info(f"可用模型列表: {self.available_models}")
            
        except Exception as e:
            raise FileOrganizerError(f"连接 Ollama 失败: {e}")
    
    def chat_with_retry(self, messages: List[Dict], max_retries: int = None) -> str:
        """使用重试机制进行对话，支持多模型切换"""
        if max_retries is None:
            max_retries = len(self.available_models)
        
        last_error = None
        models_to_try = [self.model_name] + [m for m in self.available_models if m != self.model_name]
        
        for attempt, model_name in enumerate(models_to_try[:max_retries]):
            try:
                logging.info(f"尝试使用模型 {model_name} (第 {attempt + 1} 次尝试)")
                
                response = self.client.chat(
                    model=model_name,
                    messages=messages
                )
                
                # 如果成功，更新当前使用的模型
                if model_name != self.model_name:
                    logging.info(f"模型切换: {self.model_name} -> {model_name}")
                    self.model_name = model_name
                
                return response['message']['content'].strip()
                
            except Exception as e:
                last_error = e
                logging.warning(f"模型 {model_name} 响应失败: {e}")
                
                # 如果不是最后一次尝试，继续下一个模型
                if attempt < max_retries - 1:
                    continue
        
        # 所有模型都失败了
        raise FileOrganizerError(f"所有可用模型都响应失败，最后错误: {last_error}")


class FileOrganizer:
    """文件整理器主类"""
    
    def __init__(self, model_name: str = None, enable_transfer_log: bool = True):
        """
        初始化文件整理器
        
        Args:
            model_name: 使用的 Ollama 模型名称，如果为None则自动选择第一个可用模型
            enable_transfer_log: 是否启用转移日志记录
        """
        self.model_name = model_name
        self.ollama_client = None
        self.enable_transfer_log = enable_transfer_log
        self.transfer_log_manager = None
        
        # 初始化转移日志管理器
        if self.enable_transfer_log:
            try:
                self.transfer_log_manager = TransferLogManager()
                logging.info("转移日志管理器初始化成功")
            except Exception as e:
                logging.warning(f"转移日志管理器初始化失败: {e}")
                self.enable_transfer_log = False
        self.setup_logging()
        
    def setup_logging(self) -> None:
        """设置日志记录"""
        log_filename = f"file_organizer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_path = os.path.join(os.path.dirname(__file__), "logs", log_filename)
        
        # 创建日志目录
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        logging.info("文件整理器初始化完成")
        
    def initialize_ollama(self) -> None:
        """初始化 Ollama 客户端"""
        try:
            self.ollama_client = OllamaClient(self.model_name)
            logging.info("Ollama 客户端初始化成功")
        except Exception as e:
            raise FileOrganizerError(f"初始化 Ollama 客户端失败: {e}")
            
    def scan_target_folders(self, target_directory: str) -> List[str]:
        """
        扫描目标目录，获取所有文件夹的完整路径（递归树形结构）
        
        Args:
            target_directory: 目标目录路径
            
        Returns:
            文件夹完整路径列表（相对于目标目录的路径）
        """
        try:
            target_path = Path(target_directory)
            if not target_path.exists():
                raise FileOrganizerError(f"目标目录不存在: {target_directory}")
                
            folders = []
            
            # 递归遍历所有子目录
            for item in target_path.rglob('*'):
                if item.is_dir():
                    # 获取相对于目标目录的路径
                    relative_path = item.relative_to(target_path)
                    folders.append(str(relative_path))
                    
            logging.info(f"扫描到 {len(folders)} 个目标文件夹（包含子目录）")
            return folders
            
        except Exception as e:
            raise FileOrganizerError(f"扫描目标文件夹失败: {e}")
    
    def _simple_classification(self, file_path: str, target_folders: List[str]) -> tuple:
        """
        简单的文件分类方法（基于文件名和目标文件夹的实时匹配）
        
        Args:
            file_path: 文件路径
            target_folders: 目标文件夹列表
            
        Returns:
            (推荐文件夹, 匹配理由, 是否成功) 的元组
        """
        file_name = Path(file_path).name.lower()
        file_extension = Path(file_path).suffix.lower()
        
        # 计算匹配分数（1-10分）
        folder_scores = {}
        
        for folder in target_folders:
            score = 0
            folder_lower = folder.lower()
            folder_parts = folder_lower.replace('【', '').replace('】', '').replace('-', ' ').replace('_', ' ').split()
            
            # 1. 文件名与文件夹名的直接匹配（最高权重）
            file_name_parts = file_name.replace(file_extension, '').replace('-', ' ').replace('_', ' ').split()
            
            # 计算文件名部分与文件夹名部分的匹配度
            matched_parts = 0
            total_parts = len(file_name_parts)
            
            for file_part in file_name_parts:
                if len(file_part) >= 2:  # 忽略太短的部分
                    for folder_part in folder_parts:
                        if len(folder_part) >= 2:
                            # 完全匹配
                            if file_part == folder_part:
                                matched_parts += 1
                                score += 3
                            # 包含匹配
                            elif file_part in folder_part or folder_part in file_part:
                                matched_parts += 0.5
                                score += 1.5
            
            # 2. 文件夹名与文件名的包含关系
            for folder_part in folder_parts:
                if len(folder_part) >= 3 and folder_part in file_name:
                    score += 2
            
            # 3. 文件名与文件夹名的包含关系
            for file_part in file_name_parts:
                if len(file_part) >= 3 and file_part in folder_lower:
                    score += 2
            
            # 4. 基于文件扩展名的通用匹配
            if file_extension:
                # 图片文件
                if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp']:
                    if any(keyword in folder_lower for keyword in ['图片', '图像', 'image', 'photo', 'pic']):
                        score += 1
                # 文档文件
                elif file_extension in ['.pdf', '.doc', '.docx', '.txt', '.md']:
                    if any(keyword in folder_lower for keyword in ['文档', '报告', 'doc', 'report', '资料']):
                        score += 1
                # 表格文件
                elif file_extension in ['.xls', '.xlsx', '.csv']:
                    if any(keyword in folder_lower for keyword in ['数据', '表格', 'data', 'excel', '统计']):
                        score += 1
                # 演示文件
                elif file_extension in ['.ppt', '.pptx']:
                    if any(keyword in folder_lower for keyword in ['演示', '幻灯片', 'ppt', 'presentation']):
                        score += 1
            
            # 计算最终匹配度（1-10分）
            if total_parts > 0:
                match_ratio = matched_parts / total_parts
                final_score = min(10, max(1, score * (1 + match_ratio)))
            else:
                final_score = min(10, max(1, score))
            
            folder_scores[folder] = final_score
        
        # 选择得分最高的文件夹
        if folder_scores:
            best_folder = max(folder_scores, key=folder_scores.get)
            best_score = folder_scores[best_folder]
            
            # 评分机制：大于等于6分才推荐迁移
            if best_score >= 6.0:
                return (best_folder, f"匹配度评分: {best_score:.1f}/10", True)
            else:
                return (None, f"最高匹配度仅 {best_score:.1f}/10，建议创建新文件夹", False)
        
        # 如果没有文件夹可匹配
        return (None, "没有可用的目标文件夹", False)
    
    def get_directory_tree_structure(self, target_directory: str) -> str:
        """
        获取目标目录的完整树形结构字符串
        
        Args:
            target_directory: 目标目录路径
            
        Returns:
            格式化的目录树结构字符串
        """
        try:
            target_path = Path(target_directory)
            if not target_path.exists():
                raise FileOrganizerError(f"目标目录不存在: {target_directory}")
            
            def build_tree(path: Path, prefix: str = "", is_last: bool = True) -> List[str]:
                """递归构建目录树"""
                lines = []
                if path != target_path:
                    connector = "└── " if is_last else "├── "
                    lines.append(f"{prefix}{connector}{path.name}")
                    prefix += "    " if is_last else "│   "
                
                # 获取所有子目录，按名称排序
                subdirs = sorted([item for item in path.iterdir() if item.is_dir()], key=lambda x: x.name)
                
                for i, subdir in enumerate(subdirs):
                    is_last_subdir = (i == len(subdirs) - 1)
                    lines.extend(build_tree(subdir, prefix, is_last_subdir))
                
                return lines
            
            tree_lines = build_tree(target_path)
            tree_structure = "\n".join(tree_lines)
            
            logging.info(f"生成目录树结构，共 {len(tree_lines)} 行")
            return tree_structure
            
        except Exception as e:
            raise FileOrganizerError(f"生成目录树结构失败: {e}")
    
    def classify_file(self, file_path: str, target_directory: str) -> tuple:
        """
        使用AI对单个文件进行分类
        
        Args:
            file_path: 文件路径
            target_directory: 目标目录路径
            
        Returns:
            (目标文件夹, 匹配理由, 是否成功) 的元组
        """
        try:
            if not self.ollama_client:
                self.initialize_ollama()
                
            file_name = Path(file_path).name
            prompt = self._build_classification_prompt(file_path, target_directory)
            
            logging.info(f"正在分类文件: {file_name}")
            
            # 使用重试机制调用模型进行分类
            classification_result = self.ollama_client.chat_with_retry([
                {
                    'role': 'user',
                    'content': prompt
                }
            ])
            
            logging.info(f"AI分类原始结果: {classification_result}")
            
            # 获取目标文件夹列表用于验证
            target_folders = self.scan_target_folders(target_directory)
            target_folder, match_reason = self._parse_classification_result(classification_result, target_folders)
            
            if target_folder and match_reason:
                logging.info(f"AI分类成功: {file_name} -> {target_folder}, 理由: {match_reason}")
                return target_folder, match_reason, True
            else:
                logging.warning(f"AI分类解析失败，使用简单分类: {file_name}")
                simple_result = self._simple_classification(file_path, target_folders)
                if simple_result[0]:  # simple_result 现在返回元组 (folder, reason, success)
                    return simple_result[0], simple_result[1], True
                else:
                    return None, "所有分类方法均失败", False
            
        except Exception as e:
            logging.error(f"AI分类失败: {e}")
            target_folders = self.scan_target_folders(target_directory)
            simple_result = self._simple_classification(file_path, target_folders)
            if simple_result[0]:  # simple_result 现在返回元组 (folder, reason, success)
                return simple_result[0], f"AI分类异常({str(e)})，使用简单规则: {simple_result[1]}", True
            else:
                return None, f"分类失败: {str(e)}", False
    
    def _build_classification_prompt(self, file_path: str, target_directory: str) -> str:
        """
        构建分类提示词
        
        Args:
            file_path: 文件路径
            target_directory: 目标目录路径
            
        Returns:
            分类提示词
        """
        file_name = Path(file_path).name
        file_extension = Path(file_path).suffix.lower()
        
        # 尝试读取文件内容（支持所有文件类型）
        file_content = ""
        content_readable = False
        
        # 首先尝试以文本方式读取
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.read()[:2000]  # 读取前2000个字符
                # 检查内容是否主要是可打印字符
                printable_ratio = sum(1 for c in file_content if c.isprintable() or c.isspace()) / len(file_content) if file_content else 0
                if printable_ratio > 0.7:  # 如果70%以上是可打印字符，认为是文本文件
                    content_readable = True
                else:
                    file_content = "文件内容为二进制格式，无法读取"
        except Exception:
            # 如果UTF-8失败，尝试其他编码
            for encoding in ['gbk', 'gb2312', 'latin-1']:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                        file_content = f.read()[:2000]
                        printable_ratio = sum(1 for c in file_content if c.isprintable() or c.isspace()) / len(file_content) if file_content else 0
                        if printable_ratio > 0.7:
                            content_readable = True
                            break
                        else:
                            file_content = "文件内容为二进制格式，无法读取"
                except Exception:
                    continue
            
            if not content_readable:
                file_content = "无法读取文件内容"
        
        # 获取目录树结构
        directory_structure = self.get_directory_tree_structure(target_directory)
        
        prompt = f"""
你是一个专业的文件分类助手。请阅读原文件内容，根据文件内容判断文件应该归类到下列哪个文件夹中，注意，每个文件根据文件内容只匹配一个文件夹，匹配原则是：

- 优先匹配：文件内容主题和文件夹名及文件路径名最相符
- 降级匹配：如果读取不到文件内容，则用原文件名和目标文件夹名及文件夹路径名来匹配

文件信息：
- 原文件名：{file_name}
- 文件扩展名：{file_extension}
- 文件内容：{file_content if content_readable else "无法读取内容"}

目标目录文件夹清单如下：
{directory_structure}

输出格式要求：
原文件名|目标文件夹|匹配理由

其中匹配理由格式为：
内容匹配：{{用不多于20个字描述匹配理由}}
或者
无法读取内容，采用文件夹名匹配：{{用不多于20个字描述匹配理由}}

请严格按照上述格式输出，只输出一行结果。
"""
        
        return prompt
        
    def _parse_classification_result(self, result: str, target_folders: List[str]) -> tuple:
        """
        解析模型返回的分类结果
        
        Args:
            result: 模型返回的原始结果
            target_folders: 有效的目标文件夹列表
            
        Returns:
            (目标文件夹, 匹配理由) 的元组，如果解析失败返回 (None, None)
        """
        try:
            # 清理结果字符串
            result = result.strip()
            
            # 解析格式：原文件名|目标文件夹|匹配理由
            parts = result.split('|')
            if len(parts) != 3:
                logging.warning(f"分类结果格式不正确，期望3个部分，实际得到{len(parts)}个: {result}")
                return None, None
            
            original_filename = parts[0].strip()
            target_folder = parts[1].strip()
            match_reason = parts[2].strip()
            
            # 验证文件夹是否存在于目标列表中
            if target_folder in target_folders:
                return target_folder, match_reason
            else:
                # 尝试模糊匹配
                for valid_folder in target_folders:
                    if target_folder in valid_folder or valid_folder in target_folder:
                        return valid_folder, f"{match_reason}（模糊匹配：{target_folder}）"
                        
                logging.warning(f"目标文件夹 '{target_folder}' 不在有效列表中")
                return None, None
            
        except Exception as e:
            logging.warning(f"解析分类结果失败: {e}, 原始结果: {result}")
            return None, None
            
    def scan_source_files(self, source_directory: str) -> List[str]:
        """
        扫描源目录，获取所有需要整理的文件
        
        Args:
            source_directory: 源目录路径
            
        Returns:
            文件路径列表
        """
        try:
            source_path = Path(source_directory)
            if not source_path.exists():
                raise FileOrganizerError(f"源目录不存在: {source_directory}")
                
            files = []
            for item in source_path.rglob('*'):
                if item.is_file():
                    files.append(str(item))
                    
            logging.info(f"扫描到 {len(files)} 个待整理文件")
            return files
            
        except Exception as e:
            raise FileOrganizerError(f"扫描源文件失败: {e}")
            
    def scan_files(self, source_directory: str) -> List[Dict[str, str]]:
        """
        扫描源目录，获取所有需要整理的文件（返回详细信息）
        
        Args:
            source_directory: 源目录路径
            
        Returns:
            文件信息列表，每个元素包含 'name', 'path', 'size' 等信息
        """
        try:
            source_path = Path(source_directory)
            if not source_path.exists():
                raise FileOrganizerError(f"源目录不存在: {source_directory}")
                
            files = []
            for item in source_path.rglob('*'):
                if item.is_file():
                    files.append({
                        'name': item.name,
                        'path': str(item),
                        'size': item.stat().st_size,
                        'extension': item.suffix.lower()
                    })
                    
            logging.info(f"扫描到 {len(files)} 个待整理文件")
            return files
            
        except Exception as e:
            raise FileOrganizerError(f"扫描源文件失败: {e}")
            
    def get_target_folders(self, target_directory: str) -> List[str]:
        """
        获取目标目录中的文件夹列表（别名方法）
        
        Args:
            target_directory: 目标目录路径
            
        Returns:
            文件夹名称列表
        """
        return self.scan_target_folders(target_directory)
        
    def preview_classification(self, source_directory: str, target_directory: str) -> List[Dict[str, any]]:
        """
        预览文件分类结果（递归处理所有文件）
        
        Args:
            source_directory: 源目录路径
            target_directory: 目标目录路径
            
        Returns:
            分类预览结果列表
        """
        try:
            source_files = self.scan_source_files(source_directory)
            
            if not source_files:
                raise FileOrganizerError("源目录中没有找到文件")
            
            preview_results = []
            
            logging.info(f"开始预览分类，共 {len(source_files)} 个文件")
            
            for i, file_path in enumerate(source_files, 1):
                file_name = Path(file_path).name
                
                try:
                    logging.info(f"正在处理文件 {i}/{len(source_files)}: {file_name}")
                    
                    # 使用新的单文件分类方法
                    if not self.ollama_client:
                        self.initialize_ollama()
                    
                    target_folder, match_reason, success = self.classify_file(file_path, target_directory)
                    
                    if success and target_folder:
                        preview_results.append({
                            'file_path': file_path,
                            'file_name': file_name,
                            'target_folder': target_folder,
                            'match_reason': match_reason,
                            'classification_method': 'AI',
                            'success': True
                        })
                        logging.info(f"文件 {file_name} 分类成功: {target_folder} ({match_reason})")
                    else:
                        preview_results.append({
                            'file_path': file_path,
                            'file_name': file_name,
                            'target_folder': None,
                            'match_reason': match_reason or "分类失败",
                            'classification_method': 'Failed',
                            'success': False,
                            'error': match_reason
                        })
                        logging.warning(f"文件 {file_name} 分类失败: {match_reason}")
                    
                except Exception as e:
                    error_msg = f"处理文件时出错: {str(e)}"
                    logging.error(f"文件 {file_name} 处理异常: {e}")
                    preview_results.append({
                        'file_path': file_path,
                        'file_name': file_name,
                        'target_folder': None,
                        'match_reason': error_msg,
                        'classification_method': 'Error',
                        'success': False,
                        'error': error_msg
                    })
            
            success_count = sum(1 for result in preview_results if result['success'])
            logging.info(f"预览分类完成，成功分类 {success_count}/{len(preview_results)} 个文件")
            return preview_results
            
        except Exception as e:
            raise FileOrganizerError(f"预览分类失败: {e}")
            
    def _simple_classification_preview(self, files: List[Dict[str, str]], target_folders: List[str]) -> List[Dict[str, any]]:
        """
        简单的文件分类预览（基于文件扩展名和关键词）
        
        Args:
            files: 文件信息列表
            target_folders: 目标文件夹列表
            
        Returns:
            分类预览结果列表
        """
        preview_results = []
        
        for file_info in files:
            filename = file_info['name'].lower()
            extension = file_info.get('extension', '')
            
            recommended_folders = []
            
            # 基于文件名关键词匹配目标文件夹
            # 提取文件名中的关键词
            filename_keywords = []
            
            # 常见的保险相关关键词映射
            keyword_mapping = {
                '保监会': ['保监会', '监管', '银保监'],
                '保险公司': ['保险公司', '险企', '寿险公司', '财险公司'],
                '人身险': ['人身险', '寿险', '人寿', '生命', '个险'],
                '财产险': ['财产险', '财险', '车险', '意外险'],
                '再保险': ['再保险', '再保', 'reinsurance'],
                '保险资管': ['资管', '投资', '资产管理', '投资管理'],
                '保险中介': ['中介', '代理', '经纪', '公估'],
                '新兴业态': ['科技', '互联网', '数字化', '创新', '新兴'],
                '他山之石': ['海外', '国外', '境外', '国际', '全球'],
                '综合': ['综合', '行业', '整体', '全面'],
                '互助': ['互助', '相互'],
                '产品': ['产品', '险种'],
                '估值': ['估值', '定价', '精算'],
                '保险并购': ['并购', '收购', '重组'],
                '保险策略': ['策略', '战略'],
                '信保': ['信保', '信用保险'],
                '健康险': ['健康险', '医疗险', '健康'],
                '偿付能力': ['偿付能力', '偿二代', 'solvency'],
                '养老': ['养老', '年金'],
                '农险': ['农险', '农业保险'],
                '周报': ['周报', '周刊'],
                '数字化': ['数字化', '信息化', '智能化'],
                '渠道': ['渠道', '销售', '营销'],
                '科技保险': ['科技保险', '保险科技', 'insurtech']
            }
            
            # 计算每个目标文件夹的匹配分数
            folder_scores = {}
            
            for folder in target_folders:
                score = 0
                folder_lower = folder.lower()
                
                # 直接匹配文件夹名称
                for keyword_category, keywords in keyword_mapping.items():
                    if any(keyword in folder_lower for keyword in keywords):
                        # 检查文件名是否包含相关关键词
                        if any(keyword in filename for keyword in keywords):
                            score += 10
                        # 检查文件夹名称是否在文件名中
                        folder_name_clean = folder.replace('【', '').replace('】', '').replace('-', '').replace('7', '').replace('4', '')
                        if any(part in filename for part in folder_name_clean.split() if len(part) > 1):
                            score += 5
                            
                # 基于文件扩展名的通用匹配
                if extension == '.pdf':
                    score += 1  # PDF文件通常是研究报告
                    
                folder_scores[folder] = score
            
            # 选择得分最高的文件夹
            if folder_scores:
                max_score = max(folder_scores.values())
                if max_score > 0:
                    recommended_folders = [folder for folder, score in folder_scores.items() if score == max_score]
                else:
                    # 如果没有匹配，尝试基于文件名内容进行模糊匹配
                    recommended_folders = self._fuzzy_match_folders(filename, target_folders)
            
            # 如果仍然没有匹配，使用默认策略
            if not recommended_folders:
                # 优先选择"综合"或"其他"类文件夹
                default_folders = [folder for folder in target_folders if any(keyword in folder.lower() for keyword in ['综合', '其他'])]
                if default_folders:
                    recommended_folders = [default_folders[0]]
                elif target_folders:
                    recommended_folders = [target_folders[0]]
                    
            preview_results.append({
                'file': file_info,
                'recommended_folders': recommended_folders[:3]  # 最多3个
            })
            
        return preview_results
        
    def _fuzzy_match_folders(self, filename: str, target_folders: List[str]) -> List[str]:
        """
        基于文件名进行模糊匹配
        
        Args:
            filename: 文件名
            target_folders: 目标文件夹列表
            
        Returns:
            匹配的文件夹列表
        """
        filename_lower = filename.lower()
        matched_folders = []
        
        # 提取文件名中的关键信息
        for folder in target_folders:
            folder_clean = folder.lower().replace('【', '').replace('】', '').replace('-', '').replace('7', '').replace('4', '')
            folder_parts = [part for part in folder_clean.split() if len(part) > 1]
            
            # 检查文件夹名称的任何部分是否在文件名中
            for part in folder_parts:
                if part in filename_lower and len(part) > 2:  # 至少3个字符的匹配
                    matched_folders.append(folder)
                    break
                    
        return matched_folders if matched_folders else []
            
    def organize_file(self, file_path: str, target_directory: str, target_folders: List[str]) -> Tuple[bool, str]:
        """
        整理单个文件
        
        Args:
            file_path: 文件路径
            target_directory: 目标目录
            target_folders: 目标文件夹列表
            
        Returns:
            (是否成功, 错误信息或目标路径)
        """
        try:
            if not self.ollama_client:
                self.initialize_ollama()
                
            file_path_obj = Path(file_path)
            filename = file_path_obj.name
            
            # 使用 AI 分类文件
            recommended_folders = self.ollama_client.classify_file(filename, target_folders)
            
            if not recommended_folders:
                return False, "无法确定目标文件夹"
                
            # 选择第一个推荐的文件夹
            target_folder = recommended_folders[0]
            target_folder_path = Path(target_directory) / target_folder
            
            # 确保目标文件夹存在
            target_folder_path.mkdir(parents=True, exist_ok=True)
            
            # 构建目标文件路径
            target_file_path = target_folder_path / filename
            
            # 如果目标文件已存在，添加时间戳
            if target_file_path.exists():
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                name_parts = filename.rsplit('.', 1)
                if len(name_parts) == 2:
                    new_filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                else:
                    new_filename = f"{filename}_{timestamp}"
                target_file_path = target_folder_path / new_filename
                
            # 复制文件
            shutil.copy2(file_path, target_file_path)
            
            logging.info(f"文件已复制: {file_path} -> {target_file_path}")
            return True, str(target_file_path)
            
        except Exception as e:
            error_msg = f"整理文件失败: {e}"
            logging.error(error_msg)
            return False, error_msg
            
    def organize_files(self, files=None, target_folders=None, target_base_dir=None, copy_mode=True, source_directory=None, target_directory=None, dry_run=False) -> Dict[str, any]:
        """
        安全地批量整理文件（使用新的单文件分类方法）
        
        Args:
            files: 文件信息列表（新接口）
            target_folders: 目标文件夹列表（新接口）
            target_base_dir: 目标基础目录（新接口）
            copy_mode: 是否为复制模式，False为移动模式（新接口）
            source_directory: 源目录路径（旧接口兼容）
            target_directory: 目标目录路径（旧接口兼容）
            dry_run: 是否为试运行模式
            
        Returns:
            整理结果统计
        """
        try:
            # 兼容旧接口
            if source_directory and target_directory:
                target_folders = self.scan_target_folders(target_directory)
                files = self.scan_files(source_directory)
                target_base_dir = target_directory
                copy_mode = True
                
            # 验证参数
            if not files or not target_folders or not target_base_dir:
                raise FileOrganizerError("缺少必要参数")
                
            # 开始转移日志会话
            log_session_name = None
            if self.enable_transfer_log and self.transfer_log_manager and not dry_run:
                try:
                    session_name = f"organize_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    log_session_name = self.transfer_log_manager.start_transfer_session(session_name)
                    logging.info(f"开始转移日志会话: {session_name}")
                except Exception as e:
                    logging.warning(f"启动转移日志会话失败: {e}")
                
            # 初始化 Ollama 客户端（如果需要AI分类）
            use_ai_classification = True
            try:
                if not self.ollama_client:
                    self.initialize_ollama()
            except Exception as e:
                logging.warning(f"AI分类不可用，使用简单规则分类: {e}")
                use_ai_classification = False
            
            if not target_folders:
                raise FileOrganizerError("目标目录中没有文件夹")
                
            if not files:
                raise FileOrganizerError("没有文件需要整理")
                
            # 整理统计
            results = {
                'total_files': len(files),
                'processed_files': 0,
                'successful_moves': 0,
                'failed_moves': 0,
                'skipped_files': 0,
                'success': [],
                'failed': [],
                'errors': [],
                'move_details': [],
                'ai_responses': [],
                'start_time': datetime.now(),
                'end_time': None,
                'transfer_log_file': log_session_name,
                'dry_run': dry_run
            }
            
            logging.info(f"开始安全文件整理，共 {len(files)} 个文件")
            
            # 逐个处理文件
            for i, file_info in enumerate(files, 1):
                file_path = file_info['path']
                filename = file_info['name']
                
                try:
                    logging.info(f"正在处理文件 {i}/{len(files)}: {filename}")
                    
                    # 使用新的单文件分类方法
                    if use_ai_classification:
                        target_folder, match_reason, success = self.ollama_client.classify_file(file_path, target_base_dir)
                    else:
                        # 使用简单规则分类
                        simple_result = self._simple_classification(file_path, target_folders)
                        if simple_result:
                            target_folder, match_reason, success = simple_result
                        else:
                            target_folder, match_reason, success = target_folders[0], "默认分类", True
                    
                    # 记录AI响应
                    results['ai_responses'].append({
                        'file_name': filename,
                        'target_folder': target_folder,
                        'match_reason': match_reason,
                        'success': success
                    })
                    
                    if not success or not target_folder:
                        error_msg = f"文件 {filename} 分类失败: {match_reason}"
                        logging.warning(error_msg)
                        results['errors'].append(error_msg)
                        results['failed_moves'] += 1
                        results['failed'].append({
                            'source_path': file_path,
                            'error': error_msg
                        })
                        continue
                    
                    # 构建目标路径
                    target_folder_path = Path(target_base_dir) / target_folder
                    target_file_path = target_folder_path / filename
                    
                    # 安全验证：确保目标文件夹存在
                    if not target_folder_path.exists():
                        error_msg = f"目标文件夹不存在: {target_folder}"
                        logging.error(error_msg)
                        results['errors'].append(error_msg)
                        results['failed_moves'] += 1
                        results['failed'].append({
                            'source_path': file_path,
                            'error': error_msg
                        })
                        continue
                    
                    # 处理文件名冲突
                    original_target_path = target_file_path
                    if target_file_path.exists():
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        name_parts = filename.rsplit('.', 1)
                        if len(name_parts) == 2:
                            new_filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                        else:
                            new_filename = f"{filename}_{timestamp}"
                        target_file_path = target_folder_path / new_filename
                        logging.info(f"文件名冲突，重命名为: {target_file_path.name}")
                    
                    # 安全执行文件操作
                    if not dry_run:
                        try:
                            # 验证源文件仍然存在
                            if not Path(file_path).exists():
                                error_msg = f"源文件不存在: {file_path}"
                                logging.error(error_msg)
                                results['errors'].append(error_msg)
                                results['failed_moves'] += 1
                                results['failed'].append({
                                    'source_path': file_path,
                                    'error': error_msg
                                })
                                continue
                            
                            # 执行复制或移动
                            if copy_mode:
                                shutil.copy2(file_path, target_file_path)
                                operation = "copy"
                                operation_cn = "复制"
                            else:
                                shutil.move(file_path, target_file_path)
                                operation = "move"
                                operation_cn = "移动"
                            
                            # 验证操作成功
                            if target_file_path.exists():
                                if not copy_mode and Path(file_path).exists():
                                    error_msg = f"文件移动验证失败: {filename}"
                                    logging.error(error_msg)
                                    results['errors'].append(error_msg)
                                    results['failed_moves'] += 1
                                    results['failed'].append({
                                        'source_path': file_path,
                                        'error': error_msg
                                    })
                                    continue
                                
                                logging.info(f"文件安全{operation_cn}成功: {filename} -> {target_folder} ({match_reason})")
                                results['successful_moves'] += 1
                            else:
                                error_msg = f"文件{operation_cn}验证失败: {filename}"
                                logging.error(error_msg)
                                results['errors'].append(error_msg)
                                results['failed_moves'] += 1
                                results['failed'].append({
                                    'source_path': file_path,
                                    'error': error_msg
                                })
                                continue
                                
                        except Exception as move_error:
                            error_msg = f"{operation_cn}文件 {filename} 时出错: {move_error}"
                            logging.error(error_msg)
                            results['errors'].append(error_msg)
                            results['failed_moves'] += 1
                            results['failed'].append({
                                'source_path': file_path,
                                'error': error_msg
                            })
                            continue
                    else:
                        operation = "copy" if copy_mode else "move"
                        operation_cn = "复制" if copy_mode else "移动"
                        logging.info(f"[试运行] 文件将{operation_cn}: {filename} -> {target_folder} ({match_reason})")
                        results['successful_moves'] += 1
                        
                    # 记录转移日志
                    if self.enable_transfer_log and self.transfer_log_manager and not dry_run:
                        try:
                            file_size = file_info.get('size', 0)
                            self.transfer_log_manager.log_transfer_operation(
                                source_path=file_path,
                                target_path=str(target_file_path),
                                operation_type=operation,
                                target_folder=target_folder,
                                success=True,
                                file_size=file_size
                            )
                        except Exception as e:
                            logging.warning(f"记录转移日志失败: {e}")
                        
                    results['success'].append({
                        'source_path': file_path,
                        'target_path': str(target_file_path),
                        'target_folder': target_folder,
                        'operation': operation
                    })
                    
                    results['move_details'].append({
                        'source_file': file_path,
                        'file_name': filename,
                        'target_folder': target_folder,
                        'target_path': str(target_file_path),
                        'match_reason': match_reason,
                        'classification_method': 'AI' if use_ai_classification else 'Simple',
                        'renamed': str(target_file_path) != str(original_target_path),
                        'operation': operation
                    })
                    
                except Exception as e:
                    error_msg = f"处理文件 {filename} 时出现异常: {e}"
                    logging.error(error_msg)
                    results['errors'].append(error_msg)
                    results['failed_moves'] += 1
                    
                    # 记录失败的转移日志
                    if self.enable_transfer_log and self.transfer_log_manager and not dry_run:
                        try:
                            operation_type = "copy" if copy_mode else "move"
                            self.transfer_log_manager.log_transfer_operation(
                                source_path=file_path,
                                target_path="",
                                operation_type=operation_type,
                                target_folder="",
                                success=False,
                                error_message=error_msg
                            )
                        except Exception as log_e:
                            logging.warning(f"记录失败转移日志失败: {log_e}")
                    
                    results['failed'].append({
                        'source_path': file_path,
                        'error': error_msg
                    })
                    
                finally:
                    results['processed_files'] += 1
                    
            results['end_time'] = datetime.now()
            
            # 结束转移日志会话
            if self.enable_transfer_log and self.transfer_log_manager and not dry_run:
                try:
                    session_summary = self.transfer_log_manager.end_transfer_session()
                    logging.info(f"转移日志会话结束: {session_summary}")
                except Exception as e:
                    logging.warning(f"结束转移日志会话失败: {e}")
            
            logging.info(f"安全文件整理完成: 成功 {results['successful_moves']}, 失败 {results['failed_moves']}, 跳过 {results['skipped_files']}")
            return results
            
        except Exception as e:
            raise FileOrganizerError(f"批量整理文件失败: {e}")
    
    def get_transfer_logs(self) -> List[str]:
        """
        获取所有转移日志文件列表
        
        Returns:
            日志文件路径列表
        """
        if not self.enable_transfer_log or not self.transfer_log_manager:
            raise FileOrganizerError("转移日志功能未启用")
        
        return self.transfer_log_manager.get_transfer_logs()
    
    def get_transfer_log_summary(self, log_file_path: str) -> Dict:
        """
        获取转移日志的摘要信息
        
        Args:
            log_file_path: 日志文件路径
            
        Returns:
            日志摘要信息
        """
        if not self.enable_transfer_log or not self.transfer_log_manager:
            raise FileOrganizerError("转移日志功能未启用")
        
        return self.transfer_log_manager.get_session_summary(log_file_path)
    
    def restore_files_from_log(self, log_file_path: str, 
                              operation_ids: List[int] = None,
                              dry_run: bool = True) -> Dict:
        """
        根据转移日志恢复文件
        
        Args:
            log_file_path: 日志文件路径
            operation_ids: 要恢复的操作ID列表，如果为None则恢复所有成功的操作
            dry_run: 是否为试运行模式（只检查不实际操作）
            
        Returns:
            恢复结果统计
        """
        if not self.enable_transfer_log or not self.transfer_log_manager:
            raise FileOrganizerError("转移日志功能未启用")
        
        try:
            restore_results = self.transfer_log_manager.restore_from_log(
                log_file_path=log_file_path,
                operation_ids=operation_ids,
                dry_run=dry_run
            )
            
            logging.info(f"文件恢复完成: 成功 {restore_results['successful_restores']}, 失败 {restore_results['failed_restores']}, 跳过 {restore_results['skipped_operations']}")
            return restore_results
            
        except Exception as e:
            raise FileOrganizerError(f"文件恢复失败: {e}")
    
    def cleanup_old_transfer_logs(self, days_to_keep: int = 30) -> int:
        """
        清理旧的转移日志文件
        
        Args:
            days_to_keep: 保留的天数
            
        Returns:
            删除的文件数量
        """
        if not self.enable_transfer_log or not self.transfer_log_manager:
            raise FileOrganizerError("转移日志功能未启用")
        
        return self.transfer_log_manager.cleanup_old_logs(days_to_keep)
    
    def remove_duplicate_files(self, target_folder_path: str, dry_run: bool = True) -> Dict:
        """
        删除指定目标文件夹中的重复文件
        
        重复文件的判断标准：
        1. 文件名完全一致
        2. 文件大小完全一致
        
        Args:
            target_folder_path: 目标文件夹路径
            dry_run: 是否为试运行模式（只检查不实际删除）
            
        Returns:
            删除结果统计
        """
        try:
            target_path = Path(target_folder_path)
            if not target_path.exists() or not target_path.is_dir():
                raise FileOrganizerError(f"目标文件夹不存在或不是有效目录: {target_folder_path}")
            
            # 扫描所有文件
            all_files = []
            for file_path in target_path.rglob('*'):
                if file_path.is_file():
                    try:
                        file_size = file_path.stat().st_size
                        all_files.append({
                            'path': file_path,
                            'name': file_path.name,
                            'size': file_size,
                            'relative_path': file_path.relative_to(target_path)
                        })
                    except Exception as e:
                        logging.warning(f"无法获取文件信息: {file_path}, 错误: {e}")
                        continue
            
            # 按文件名和大小分组查找重复文件
            file_groups = {}
            for file_info in all_files:
                key = (file_info['name'], file_info['size'])
                if key not in file_groups:
                    file_groups[key] = []
                file_groups[key].append(file_info)
            
            # 找出重复文件组（每组包含2个或更多文件）
            duplicate_groups = {k: v for k, v in file_groups.items() if len(v) > 1}
            
            results = {
                'total_files_scanned': len(all_files),
                'duplicate_groups_found': len(duplicate_groups),
                'total_duplicates_found': sum(len(group) - 1 for group in duplicate_groups.values()),
                'files_to_delete': [],
                'files_deleted': [],
                'deletion_errors': [],
                'dry_run': dry_run
            }
            
            # 处理每个重复文件组
            for (filename, filesize), duplicate_files in duplicate_groups.items():
                # 保留第一个文件，删除其余的
                files_to_keep = duplicate_files[0]
                files_to_delete = duplicate_files[1:]
                
                logging.info(f"发现重复文件组: {filename} ({filesize} bytes), 共 {len(duplicate_files)} 个文件")
                logging.info(f"保留文件: {files_to_keep['relative_path']}")
                
                for file_to_delete in files_to_delete:
                    file_path = file_to_delete['path']
                    relative_path = file_to_delete['relative_path']
                    
                    results['files_to_delete'].append({
                        'path': str(file_path),
                        'relative_path': str(relative_path),
                        'size': filesize,
                        'name': filename
                    })
                    
                    if not dry_run:
                        try:
                            file_path.unlink()
                            results['files_deleted'].append({
                                'path': str(file_path),
                                'relative_path': str(relative_path),
                                'size': filesize,
                                'name': filename
                            })
                            logging.info(f"已删除重复文件: {relative_path}")
                        except Exception as e:
                            error_msg = f"删除文件失败: {relative_path}, 错误: {e}"
                            results['deletion_errors'].append({
                                'path': str(file_path),
                                'relative_path': str(relative_path),
                                'error': str(e)
                            })
                            logging.error(error_msg)
                    else:
                        logging.info(f"[试运行] 将删除重复文件: {relative_path}")
            
            # 记录统计信息
            if dry_run:
                logging.info(f"重复文件扫描完成 [试运行模式]: 扫描文件 {results['total_files_scanned']} 个, "
                           f"发现重复组 {results['duplicate_groups_found']} 个, "
                           f"待删除重复文件 {results['total_duplicates_found']} 个")
            else:
                logging.info(f"重复文件删除完成: 扫描文件 {results['total_files_scanned']} 个, "
                           f"发现重复组 {results['duplicate_groups_found']} 个, "
                           f"成功删除 {len(results['files_deleted'])} 个, "
                           f"删除失败 {len(results['deletion_errors'])} 个")
            
            return results
            
        except Exception as e:
            raise FileOrganizerError(f"删除重复文件失败: {e}")


if __name__ == "__main__":
    # 简单的命令行测试
    import sys
    
    if len(sys.argv) != 3:
        print("用法: python file_organizer.py <源目录> <目标目录>")
        sys.exit(1)
        
    source_dir = sys.argv[1]
    target_dir = sys.argv[2]
    
    try:
        organizer = FileOrganizer()
        results = organizer.organize_files(source_dir, target_dir)
        
        print(f"\n整理完成!")
        print(f"总文件数: {results['total_files']}")
        print(f"成功: {results['success_count']}")
        print(f"失败: {results['failed_count']}")
        
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)