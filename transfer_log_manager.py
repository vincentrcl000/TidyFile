#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件转移日志管理器

本模块提供文件转移操作的详细日志记录和恢复功能，包括：
1. 转移操作的详细记录（JSON格式）
2. 基于日志的文件恢复功能
3. 日志文件的管理和查询
4. 操作历史的可视化展示

作者: AI Assistant
创建时间: 2025-01-15
"""

import os
import json
import shutil
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class TransferLogManager:
    """文件转移日志管理器"""
    
    def __init__(self, log_directory: str = None):
        """
        初始化转移日志管理器
        
        Args:
            log_directory: 日志文件存储目录，默认为当前目录下的transfer_logs文件夹
        """
        # 设置日志目录
        if log_directory is None:
            log_directory = os.path.join(os.path.dirname(__file__), "transfer_logs")
        
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # 当前操作的日志文件路径
        self.current_log_file = None
        
        # 设置日志记录
        self._setup_logging()
        
    def _setup_logging(self) -> None:
        """设置日志记录配置"""
        # 只在有实际转移操作时才创建日志文件
        self.logger = logging.getLogger('transfer_log_manager')
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加handler
        if not self.logger.handlers:
            # 使用StreamHandler而不是FileHandler，避免创建空文件
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _create_log_file(self) -> None:
        """创建转移操作日志文件"""
        log_filename = f"transfer_manager_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_path = self.log_directory / log_filename
        
        # 创建专用的文件handler
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        self.logger.info(f"创建转移日志文件: {log_path}")
        
    def start_transfer_session(self, session_name: str = None) -> str:
        """
        开始一个新的转移会话，创建对应的日志文件
        
        Args:
            session_name: 会话名称，如果为None则使用时间戳
            
        Returns:
            日志文件路径
        """
        if session_name is None:
            session_name = f"transfer_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 创建日志文件
        log_filename = f"{session_name}.json"
        self.current_log_file = self.log_directory / log_filename
        
        # 初始化日志文件结构
        initial_log = {
            "session_info": {
                "session_name": session_name,
                "start_time": datetime.now().isoformat(),
                "end_time": None,
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0
            },
            "operations": []
        }
        
        # 写入初始日志
        with open(self.current_log_file, 'w', encoding='utf-8') as f:
            json.dump(initial_log, f, ensure_ascii=False, indent=2)
        
        # 创建转移操作日志文件
        self._create_log_file()
        
        self.logger.info(f"开始转移会话: {session_name}")
        return str(self.current_log_file)
    
    def log_transfer_operation(self, 
                             source_path: str, 
                             target_path: str, 
                             operation_type: str,
                             target_folder: str = None,
                             success: bool = True,
                             error_message: str = None,
                             file_size: int = None,
                             file_hash: str = None,
                             md5: str = None,
                             ctime: float = None) -> None:
        """
        记录单个文件转移操作
        
        Args:
            source_path: 源文件路径
            target_path: 目标文件路径
            operation_type: 操作类型（copy/move/delete_duplicate）
            target_folder: 目标文件夹名称
            success: 操作是否成功
            error_message: 错误信息（如果失败）
            file_size: 文件大小（字节）
            file_hash: 文件哈希值（用于验证）
            md5: MD5哈希值（与file_hash相同，用于兼容性）
            ctime: 文件创建时间戳
        """
        if not self.current_log_file:
            raise ValueError("请先调用 start_transfer_session() 开始会话")
        
        # 参数验证和调试信息
        if not isinstance(source_path, str):
            self.logger.error(f"记录删除日志失败: source_path 应该是字符串，但收到了 {type(source_path)}: {source_path}")
            return
        
        if not isinstance(target_path, str):
            self.logger.error(f"记录删除日志失败: target_path 应该是字符串，但收到了 {type(target_path)}: {target_path}")
            return
        
        # 读取当前日志
        with open(self.current_log_file, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
        
        # 获取文件信息
        if file_size is None and source_path and isinstance(source_path, str) and os.path.exists(source_path):
            try:
                file_size = os.path.getsize(source_path)
            except:
                file_size = 0
        
        # 创建操作记录
        operation_record = {
            "operation_id": len(log_data["operations"]) + 1,
            "timestamp": datetime.now().isoformat(),
            "operation_type": operation_type,
            "source_path": source_path,
            "target_path": target_path,
            "target_folder": target_folder,
            "file_size": file_size,
            "file_hash": file_hash or md5,  # 使用md5作为file_hash的备选
            "md5": md5 or file_hash,  # 保存md5值
            "ctime": ctime,  # 保存创建时间
            "success": success,
            "error_message": error_message
        }
        
        # 添加到操作列表
        log_data["operations"].append(operation_record)
        
        # 更新统计信息
        log_data["session_info"]["total_operations"] += 1
        if success:
            log_data["session_info"]["successful_operations"] += 1
        else:
            log_data["session_info"]["failed_operations"] += 1
        
        # 写回文件
        with open(self.current_log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        # 记录到普通日志
        status = "成功" if success else "失败"
        self.logger.info(f"转移操作{status}: {source_path} -> {target_path}")
        if not success and error_message:
            self.logger.error(f"错误详情: {error_message}")
    
    def end_transfer_session(self) -> Dict:
        """
        结束当前转移会话
        
        Returns:
            会话统计信息
        """
        if not self.current_log_file:
            raise ValueError("没有活动的转移会话")
        
        # 读取当前日志
        with open(self.current_log_file, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
        
        # 更新结束时间
        log_data["session_info"]["end_time"] = datetime.now().isoformat()
        
        # 写回文件
        with open(self.current_log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        session_info = log_data["session_info"]
        self.logger.info(f"结束转移会话: {session_info['session_name']}")
        self.logger.info(f"总操作数: {session_info['total_operations']}, 成功: {session_info['successful_operations']}, 失败: {session_info['failed_operations']}")
        
        # 清除当前会话
        self.current_log_file = None
        
        return session_info
    
    def get_transfer_logs(self) -> List[str]:
        """
        获取所有转移日志文件列表
        
        Returns:
            日志文件路径列表
        """
        log_files = []
        for file_path in self.log_directory.glob("*.json"):
            log_files.append(str(file_path))
        
        # 按修改时间排序（最新的在前）
        log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return log_files
    
    def load_transfer_log(self, log_file_path: str) -> Dict:
        """
        加载指定的转移日志文件
        
        Args:
            log_file_path: 日志文件路径
            
        Returns:
            日志数据字典
        """
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise ValueError(f"无法加载日志文件 {log_file_path}: {e}")
    
    def restore_from_log(self, log_file_path: str, 
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
        # 加载日志数据
        log_data = self.load_transfer_log(log_file_path)
        operations = log_data["operations"]
        
        # 筛选要恢复的操作
        if operation_ids is None:
            # 恢复所有成功的操作
            target_operations = [op for op in operations if op["success"]]
        else:
            # 恢复指定的操作
            target_operations = [op for op in operations 
                               if op["operation_id"] in operation_ids and op["success"]]
        
        # 恢复结果统计
        restore_results = {
            "total_operations": len(target_operations),
            "successful_restores": 0,
            "failed_restores": 0,
            "skipped_operations": 0,
            "restore_details": [],
            "dry_run": dry_run
        }
        
        self.logger.info(f"开始恢复操作，目标操作数: {len(target_operations)}, 试运行: {dry_run}")
        
        # 逐个恢复操作
        for operation in target_operations:
            source_path = operation["source_path"]
            target_path = operation["target_path"]
            operation_type = operation["operation_type"]
            
            restore_detail = {
                "operation_id": operation["operation_id"],
                "source_path": source_path,
                "target_path": target_path,
                "operation_type": operation_type,
                "restore_success": False,
                "restore_message": ""
            }
            
            try:
                # 检查源文件是否还存在
                source_exists = source_path and isinstance(source_path, str) and os.path.exists(source_path)
                # 检查目标文件是否存在
                target_exists = target_path and isinstance(target_path, str) and os.path.exists(target_path)
                
                if not source_exists and not target_exists:
                    restore_detail["restore_message"] = "源文件和目标文件都不存在，无法恢复"
                    restore_results["skipped_operations"] += 1
                    self.logger.warning(f"跳过恢复 - 源文件和目标文件都不存在: {source_path} / {target_path}")
                    continue
                
                # 如果源文件还在，直接标记为恢复成功
                if source_exists:
                    restore_detail["restore_message"] = "源文件仍然存在，无需恢复"
                    restore_detail["restore_success"] = True
                    restore_results["successful_restores"] += 1
                    self.logger.info(f"源文件存在，无需恢复: {source_path}")
                    restore_results["restore_details"].append(restore_detail)
                    continue
                
                # 此时源文件不存在但目标文件存在，需要从目标位置恢复
                if not dry_run:
                    # 确保源目录存在
                    source_dir = os.path.dirname(source_path)
                    os.makedirs(source_dir, exist_ok=True)
                    
                    # 根据原操作类型进行恢复
                    if operation_type == "copy":
                        # 原来是复制，恢复时复制回去
                        shutil.copy2(target_path, source_path)
                        restore_detail["restore_message"] = "文件已从目标位置复制回源位置"
                    elif operation_type == "move":
                        # 原来是移动，恢复时移动回去
                        shutil.move(target_path, source_path)
                        restore_detail["restore_message"] = "文件已从目标位置移动回源位置"
                    else:
                        restore_detail["restore_message"] = f"未知操作类型: {operation_type}"
                        restore_results["failed_restores"] += 1
                        continue
                else:
                    restore_detail["restore_message"] = "试运行模式 - 将从目标位置恢复文件"
                
                restore_detail["restore_success"] = True
                restore_results["successful_restores"] += 1
                self.logger.info(f"恢复成功: {target_path} -> {source_path}")
                
            except Exception as e:
                restore_detail["restore_message"] = f"恢复失败: {str(e)}"
                restore_results["failed_restores"] += 1
                self.logger.error(f"恢复失败 {target_path}: {e}")
            
            restore_results["restore_details"].append(restore_detail)
        
        self.logger.info(f"恢复操作完成 - 成功: {restore_results['successful_restores']}, 失败: {restore_results['failed_restores']}, 跳过: {restore_results['skipped_operations']}")
        return restore_results
    
    def get_session_summary(self, log_file_path: str) -> Dict:
        """
        获取转移会话的摘要信息
        
        Args:
            log_file_path: 日志文件路径
            
        Returns:
            会话摘要信息
        """
        log_data = self.load_transfer_log(log_file_path)
        session_info = log_data["session_info"]
        operations = log_data["operations"]
        
        # 统计各种操作类型
        operation_types = {}
        target_folders = {}
        total_size = 0
        
        for op in operations:
            if op["success"]:
                # 统计操作类型
                op_type = op["operation_type"]
                operation_types[op_type] = operation_types.get(op_type, 0) + 1
                
                # 统计目标文件夹
                folder = op.get("target_folder", "未知")
                target_folders[folder] = target_folders.get(folder, 0) + 1
                
                # 统计文件大小
                if op.get("file_size"):
                    total_size += op["file_size"]
        
        return {
            "session_info": session_info,
            "operation_types": operation_types,
            "target_folders": target_folders,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
    
    def cleanup_old_logs(self, days_to_keep: int = 30) -> int:
        """
        清理旧的日志文件
        
        Args:
            days_to_keep: 保留的天数
            
        Returns:
            删除的文件数量
        """
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)
        deleted_count = 0
        
        for log_file in self.log_directory.glob("*.json"):
            try:
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_time:
                    log_file.unlink()
                    deleted_count += 1
                    self.logger.info(f"删除旧日志文件: {log_file}")
            except Exception as e:
                self.logger.error(f"删除日志文件失败 {log_file}: {e}")
        
        return deleted_count


