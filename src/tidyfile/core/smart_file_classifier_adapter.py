#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文件分类器适配器
将新的SmartFileClassifier适配到主程序的接口
"""
import os
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from tidyfile.core.smart_classifier import SmartFileClassifier

class SmartFileClassifierAdapter:
    """智能文件分类器适配器，适配主程序接口"""
    
    def __init__(self, model_name: str = None, enable_transfer_log: bool = True, timeout_seconds: int = 180):
        """
        初始化适配器
        
        Args:
            model_name: 模型名称（兼容旧接口，但新分类器使用ai_client_manager）
            enable_transfer_log: 是否启用传输日志（兼容旧接口）
            timeout_seconds: 单个文件处理超时时间（秒），默认3分钟
        """
        # 默认参数，可通过set_parameters方法动态设置
        self._content_extraction_length = 2000
        self._summary_length = 200
        self._timeout_seconds = timeout_seconds
        
        # 兼容旧接口的属性
        self.ai_parameters = {
            'content_extraction_length': self._content_extraction_length,
            'summary_length': self._summary_length,
            'timeout_seconds': self._timeout_seconds
        }
        
        # 传输日志相关（兼容旧接口）
        self.enable_transfer_log = enable_transfer_log
        self.transfer_logs = []
        
        # 初始化智能分类器
        self.classifier = SmartFileClassifier(
            content_extraction_length=self._content_extraction_length,
            summary_length=self._summary_length,
            timeout_seconds=self._timeout_seconds
        )
        
        logging.info(f"智能文件分类器适配器初始化完成（超时设置: {timeout_seconds}秒）")
    
    def set_parameters(self, content_extraction_length: int = None, summary_length: int = None, timeout_seconds: int = None):
        """设置分类参数"""
        if content_extraction_length is not None:
            self._content_extraction_length = content_extraction_length
            self.ai_parameters['content_extraction_length'] = content_extraction_length
            
        if summary_length is not None:
            self._summary_length = summary_length
            self.ai_parameters['summary_length'] = summary_length
            
        if timeout_seconds is not None:
            self._timeout_seconds = timeout_seconds
            self.ai_parameters['timeout_seconds'] = timeout_seconds
            
        # 重新初始化分类器
        self.classifier = SmartFileClassifier(
            content_extraction_length=self._content_extraction_length,
            summary_length=self._summary_length,
            timeout_seconds=self._timeout_seconds
        )
        
        logging.info(f"参数已更新: 内容提取长度={self._content_extraction_length}, 摘要长度={self._summary_length}, 超时时间={self._timeout_seconds}秒")
    
    def scan_files(self, source_directory: str) -> List[Dict[str, Any]]:
        """
        扫描源目录中的文件（兼容旧接口）
        
        Args:
            source_directory: 源目录路径
            
        Returns:
            文件信息列表
        """
        try:
            files = []
            source_path = Path(source_directory)
            
            if not source_path.exists():
                logging.error(f"源目录不存在: {source_directory}")
                return []
            
            # 扫描所有文件
            for file_path in source_path.rglob('*'):
                if file_path.is_file():
                    # 提取文件元数据
                    metadata = self.classifier.extract_file_metadata(str(file_path))
                    
                    files.append({
                        'path': str(file_path),
                        'name': file_path.name,
                        'size': metadata.get('file_size', 0),
                        'extension': metadata.get('file_extension', ''),
                        'created_time': metadata.get('created_time', ''),
                        'modified_time': metadata.get('modified_time', '')
                    })
            
            logging.info(f"扫描到 {len(files)} 个文件")
            return files
            
        except Exception as e:
            logging.error(f"扫描文件失败: {e}")
            return []
    
    def analyze_and_classify_file(self, file_path: str, target_directory: str) -> Dict[str, Any]:
        """
        分析并分类单个文件（兼容旧接口）
        
        Args:
            file_path: 文件路径
            target_directory: 目标目录
            
        Returns:
            分析结果字典
        """
        try:
            # 使用新的智能分类器
            result = self.classifier.classify_file(file_path, target_directory)
            
            # 转换为旧接口格式
            return {
                'file_path': result['file_path'],
                'file_name': result['file_name'],
                'file_metadata': result['file_metadata'],
                'extracted_content': result['extracted_content'],
                'content_summary': result['content_summary'],
                'recommended_folder': result['recommended_folder'],
                'chain_tags': result['chain_tags'],
                'match_reason': result['match_reason'],
                'success': result['success'],
                'timing_info': result['timing_info']
            }
            
        except Exception as e:
            logging.error(f"文件分析失败: {e}")
            return {
                'file_path': file_path,
                'file_name': Path(file_path).name,
                'file_metadata': {},
                'extracted_content': '',
                'content_summary': '',
                'recommended_folder': None,
                'chain_tags': [],
                'match_reason': f"分析失败: {str(e)}",
                'success': False,
                'error': str(e),
                'timing_info': {}
            }
    
    def organize_files(self, files=None, target_base_dir=None, copy_mode=True, 
                      source_directory=None, target_directory=None, 
                      progress_callback=None) -> Dict[str, Any]:
        """
        整理文件（兼容旧接口）
        
        Args:
            files: 文件列表（可选）
            target_base_dir: 目标基础目录（兼容旧接口）
            copy_mode: 是否复制模式（兼容旧接口）
            source_directory: 源目录
            target_directory: 目标目录
            progress_callback: 进度回调函数
            
        Returns:
            整理结果字典
        """
        try:
            if not source_directory or not target_directory:
                raise ValueError("源目录和目标目录不能为空")
            
            # 扫描源文件
            if files is None:
                files = self.scan_files(source_directory)
            
            if not files:
                return {
                    'success': False,
                    'message': '源目录中没有找到文件',
                    'total_files': 0,
                    'successful_moves': 0,
                    'failed_moves': 0,
                    'success': [],
                    'failed': []
                }
            
            total_files = len(files)
            successful_moves = 0
            failed_moves = 0
            success_list = []
            failed_list = []
            
            # 创建结果文件
            result_file = "smart_classify_result.json"
            
            for i, file_info in enumerate(files):
                file_path = str(file_info['path'])
                filename = file_info['name']
                
                # 更新进度
                if progress_callback:
                    progress_callback(i + 1, total_files, filename)
                
                try:
                    # 分析并分类文件
                    result = self.classify_file(file_path, target_directory)
                    
                    if result['success'] and result['recommended_folder']:
                        # 构建目标路径
                        target_path = os.path.join(target_directory, result['recommended_folder'], filename)
                        
                        # 创建目标目录
                        target_dir = os.path.dirname(target_path)
                        os.makedirs(target_dir, exist_ok=True)
                        
                        # 复制文件
                        import shutil
                        shutil.copy2(file_path, target_path)
                        
                        # 记录成功
                        success_list.append({
                            'source_path': file_path,
                            'target_path': target_path,
                            'target_folder': result['recommended_folder'],
                            'reason': result['match_reason']
                        })
                        successful_moves += 1
                        
                        logging.info(f"文件复制成功: {filename} -> {result['recommended_folder']}")
                    else:
                        # 分类失败，移动到"分类失败"文件夹
                        failed_folder = "分类失败"
                        failed_target_path = os.path.join(source_directory, failed_folder, filename)
                        
                        # 创建"分类失败"文件夹
                        failed_dir = os.path.join(source_directory, failed_folder)
                        os.makedirs(failed_dir, exist_ok=True)
                        
                        # 移动文件到"分类失败"文件夹
                        import shutil
                        shutil.move(file_path, failed_target_path)
                        
                        logging.info(f"文件分类失败，已移动到: {filename} -> {failed_folder}")
                        
                        # 记录失败
                        failed_list.append({
                            'source_path': file_path,
                            'target_path': failed_target_path,
                            'error': result.get('match_reason', '分类失败：无法匹配到合适的目录')
                        })
                        failed_moves += 1
                        logging.warning(f"文件分类失败: {filename}")
                    
                    # 写入结果到JSON文件
                    self.classifier.append_result_to_file(result_file, result, target_directory)
                    
                    # 同时写入到主程序期望的文件名
                    # 使用新的路径管理获取正确的文件路径
                    from tidyfile.utils.app_paths import get_app_paths
                    app_paths = get_app_paths()
                    ai_result_file = str(app_paths.ai_results_file)
                    
                    self.classifier.append_result_to_file(ai_result_file, result, target_directory)
                    
                    # 清理文件缓存
                    self.classifier.clear_file_cache(file_path)
                    
                except Exception as e:
                    error_msg = f"处理文件失败: {str(e)}"
                    failed_list.append({
                        'source_path': file_path,
                        'target_path': f"{source_directory}/处理失败/{filename}",
                        'error': error_msg
                    })
                    failed_moves += 1
                    logging.error(f"处理文件失败 {filename}: {e}")
            
            # 返回结果
            return {
                'success': True,
                'total_files': total_files,
                'successful_moves': successful_moves,
                'failed_moves': failed_moves,
                'success': success_list,
                'failed': failed_list,
                'result_file': result_file,
                'processed_files': total_files,  # 添加兼容字段
                'skipped_files': 0,  # 添加兼容字段
                'errors': []  # 添加兼容字段
            }
            
        except Exception as e:
            logging.error(f"文件整理失败: {e}")
            return {
                'success': False,
                'message': str(e),
                'total_files': 0,
                'successful_moves': 0,
                'failed_moves': 0,
                'success': [],
                'failed': []
            }
    
    def classify_file(self, file_path: str, target_directory: str) -> Dict[str, Any]:
        """
        分类单个文件（简化接口）
        
        Args:
            file_path: 文件路径
            target_directory: 目标目录
            
        Returns:
            分类结果
        """
        return self.classifier.classify_file(file_path, target_directory)
    
    # 兼容旧接口的属性访问
    @property
    def summary_length(self):
        return self._summary_length
    
    @summary_length.setter
    def summary_length(self, value):
        self.set_parameters(summary_length=value)
    
    @property
    def content_truncate(self):
        return self._content_extraction_length
    
    @content_truncate.setter
    def content_truncate(self, value):
        self.set_parameters(content_extraction_length=value)
    
    @property
    def content_extraction_length(self):
        return self._content_extraction_length
    
    @content_extraction_length.setter
    def content_extraction_length(self, value):
        self.set_parameters(content_extraction_length=value)
    
    @property
    def timeout_seconds(self):
        return self._timeout_seconds
    
    @timeout_seconds.setter
    def timeout_seconds(self, value):
        self.set_parameters(timeout_seconds=value) 