#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并发结果管理器

支持多个线程安全地写入ai_organize_result.json文件
使用文件锁和线程锁确保数据一致性

作者: AI Assistant
创建时间: 2025-01-15
"""

import json
import os
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
try:
    import fcntl  # Unix系统文件锁
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

try:
    import msvcrt  # Windows系统文件锁
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False

class ConcurrentResultManager:
    """并发结果管理器，支持多线程安全写入"""
    
    def __init__(self, result_file: str = "ai_organize_result.json"):
        self.result_file = result_file
        self.file_lock = threading.Lock()  # 线程锁
        self.backup_file = f"{result_file}.backup"
        self.setup_logging()
    
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def _acquire_file_lock(self, file_handle):
        """获取文件锁（跨平台）"""
        try:
            if os.name == 'nt' and HAS_MSVCRT:  # Windows
                msvcrt.locking(file_handle.fileno(), msvcrt.LK_NBLCK, 1)
                return True
            elif HAS_FCNTL:  # Unix/Linux
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            else:
                # 如果没有文件锁支持，只使用线程锁
                return True
        except (OSError, IOError):
            return False
    
    def _release_file_lock(self, file_handle):
        """释放文件锁（跨平台）"""
        try:
            if os.name == 'nt' and HAS_MSVCRT:  # Windows
                msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            elif HAS_FCNTL:  # Unix/Linux
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
        except (OSError, IOError):
            pass
    
    def _backup_file(self):
        """备份当前文件"""
        try:
            if os.path.exists(self.result_file):
                import shutil
                shutil.copy2(self.result_file, self.backup_file)
                logging.info(f"已备份文件: {self.backup_file}")
        except Exception as e:
            logging.warning(f"备份文件失败: {e}")
    
    def _restore_from_backup(self):
        """从备份恢复文件"""
        try:
            if os.path.exists(self.backup_file):
                import shutil
                shutil.copy2(self.backup_file, self.result_file)
                logging.info(f"已从备份恢复文件: {self.result_file}")
                return True
        except Exception as e:
            logging.error(f"从备份恢复失败: {e}")
        return False
    
    def read_existing_data(self) -> List[Dict[str, Any]]:
        """读取现有数据（线程安全）"""
        with self.file_lock:
            try:
                if os.path.exists(self.result_file):
                    with open(self.result_file, 'r', encoding='utf-8') as f:
                        if self._acquire_file_lock(f):
                            try:
                                content = f.read().strip()
                                if not content:  # 空文件
                                    logging.warning("AI结果文件为空，跳过读取")
                                    return []
                                
                                data = json.loads(content)
                                if not isinstance(data, list):
                                    logging.error("AI结果文件格式错误：根元素不是数组")
                                    logging.error("请手动检查文件格式或备份后重新处理")
                                    return []
                                return data
                            except json.JSONDecodeError as e:
                                logging.error(f"AI结果文件JSON格式错误: {e}")
                                logging.error("请手动检查文件格式或备份后重新处理")
                                return []
                            finally:
                                self._release_file_lock(f)
                        else:
                            logging.warning("无法获取文件锁，等待重试")
                            time.sleep(0.1)
                            return self.read_existing_data()
                return []
            except Exception as e:
                logging.error(f"读取文件失败: {e}")
                return []
    
    def atomic_write_data(self, data: List[Dict[str, Any]], operation_type: str = "未知操作") -> bool:
        """原子写入数据（使用临时文件确保写入安全）"""
        with self.file_lock:
            try:
                # 创建临时文件
                temp_file = f"{self.result_file}.tmp"
                
                # 先写入临时文件
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                # 原子性地替换原文件
                if os.name == 'nt':  # Windows
                    # Windows下使用替换操作
                    if os.path.exists(self.result_file):
                        os.remove(self.result_file)
                    os.rename(temp_file, self.result_file)
                else:  # Unix/Linux
                    # Unix下使用原子替换
                    os.replace(temp_file, self.result_file)
                
                logging.info(f"{operation_type} - 原子写入成功: {self.result_file}")
                return True
                
            except Exception as e:
                logging.error(f"原子写入失败: {e}")
                # 清理临时文件
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                return False

    def write_data(self, data: List[Dict[str, Any]], operation_type: str = "未知操作") -> bool:
        """写入数据（线程安全）"""
        with self.file_lock:
            try:
                # 写入新数据（如果文件不存在会自动创建）
                with open(self.result_file, 'w', encoding='utf-8') as f:
                    if self._acquire_file_lock(f):
                        try:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                            logging.info(f"{operation_type} - 数据写入成功: {self.result_file}")
                            return True
                        except Exception as e:
                            logging.error(f"写入数据失败: {e}")
                            return False
                        finally:
                            self._release_file_lock(f)
                    else:
                        logging.error("无法获取文件锁进行写入")
                        return False
            except Exception as e:
                logging.error(f"写入操作失败: {e}")
                return False
    
    def append_result(self, result: Dict[str, Any], operation_type: str = "文件操作") -> bool:
        """追加单个结果（线程安全）"""
        try:
            # 读取现有数据
            existing_data = self.read_existing_data()
            
            # 检查是否为重复文件
            if self._is_duplicate_result(result, existing_data):
                logging.info(f"跳过重复文件: {result.get('file_name', '未知文件')}")
                return True
            
            # 添加新结果
            existing_data.append(result)
            
            # 验证数据不为空
            if not existing_data:
                logging.error("数据为空，拒绝写入")
                return False
            
            # 使用原子写入
            return self.atomic_write_data(existing_data, operation_type)
            
        except Exception as e:
            logging.error(f"追加结果失败: {e}")
            return False
    
    def _is_duplicate_result(self, new_result: Dict[str, Any], existing_data: List[Dict[str, Any]]) -> bool:
        """检查是否为重复结果"""
        try:
            new_file_name = new_result.get('file_name', '')
            new_file_path = new_result.get('file_path', '')
            
            for existing in existing_data:
                existing_file_name = existing.get('文件名', '')
                existing_file_path = existing.get('最终目标路径', '')
                
                # 检查文件名和路径是否相同
                if (new_file_name == existing_file_name and 
                    new_file_path == existing_file_path):
                    return True
            
            return False
        except Exception as e:
            logging.error(f"检查重复结果失败: {e}")
            return False
    
    def batch_append_results(self, results: List[Dict[str, Any]], operation_type: str = "批量操作") -> bool:
        """批量追加结果（线程安全）"""
        try:
            # 读取现有数据
            existing_data = self.read_existing_data()
            
            # 过滤重复文件
            new_results = []
            for result in results:
                if not self._is_duplicate_result(result, existing_data):
                    new_results.append(result)
                else:
                    logging.info(f"跳过重复文件: {result.get('file_name', '未知文件')}")
            
            if not new_results:
                logging.info("没有新的结果需要添加")
                return True
            
            # 添加新结果
            existing_data.extend(new_results)
            
            # 验证数据不为空
            if not existing_data:
                logging.error("数据为空，拒绝写入")
                return False
            
            # 使用原子写入
            return self.atomic_write_data(existing_data, f"{operation_type} (添加{len(new_results)}个结果)")
            
        except Exception as e:
            logging.error(f"批量追加结果失败: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取文件统计信息（线程安全）"""
        try:
            data = self.read_existing_data()
            
            stats = {
                'total_entries': len(data),
                'success_count': 0,
                'failure_count': 0,
                'operation_types': {},
                'file_extensions': {},
                'recent_entries': []
            }
            
            for entry in data:
                # 统计处理状态
                status = entry.get('处理状态', '')
                if '成功' in status:
                    stats['success_count'] += 1
                elif '失败' in status:
                    stats['failure_count'] += 1
                
                # 统计操作类型
                op_type = entry.get('操作类型', '未知')
                stats['operation_types'][op_type] = stats['operation_types'].get(op_type, 0) + 1
                
                # 统计文件扩展名
                file_metadata = entry.get('文件元数据', {})
                ext = file_metadata.get('file_extension', '未知')
                stats['file_extensions'][ext] = stats['file_extensions'].get(ext, 0) + 1
            
            # 获取最近的条目
            stats['recent_entries'] = data[-10:] if len(data) > 10 else data
            
            return stats
            
        except Exception as e:
            logging.error(f"获取统计信息失败: {e}")
            return {}
    


    def cleanup_backup(self):
        """清理备份文件"""
        try:
            if os.path.exists(self.backup_file):
                os.remove(self.backup_file)
                logging.info("已清理备份文件")
        except Exception as e:
            logging.warning(f"清理备份文件失败: {e}")

# 全局实例
_result_manager = None

def get_result_manager() -> ConcurrentResultManager:
    """获取全局结果管理器实例"""
    global _result_manager
    if _result_manager is None:
        _result_manager = ConcurrentResultManager()
    return _result_manager

def append_file_reader_result(result: Dict[str, Any]) -> bool:
    """追加文件解读结果"""
    manager = get_result_manager()
    return manager.append_result(result, "文件解读")

def append_classification_result(result: Dict[str, Any]) -> bool:
    """追加文件分类结果"""
    manager = get_result_manager()
    return manager.append_result(result, "文件分类")

def batch_append_results(results: List[Dict[str, Any]], operation_type: str = "批量操作") -> bool:
    """批量追加结果"""
    manager = get_result_manager()
    return manager.batch_append_results(results, operation_type)

def get_result_statistics() -> Dict[str, Any]:
    """获取结果统计信息"""
    manager = get_result_manager()
    return manager.get_statistics()



 