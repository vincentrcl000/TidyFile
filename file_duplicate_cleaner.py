#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件去重功能模块
"""
import os
import logging
from pathlib import Path
import hashlib
from transfer_log_manager import TransferLogManager

class DuplicateCleanerError(Exception):
    pass

def _calc_md5(file_path, chunk_size=65536):
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            md5.update(chunk)
    return md5.hexdigest()

def remove_duplicate_files(target_folder_paths: list, dry_run: bool = True, log_session_name: str = None, keep_oldest: bool = True) -> dict:
    """
    删除指定目标文件夹中的重复文件（文件大小+MD5判断），并写入日志
    
    Args:
        target_folder_paths: 目标文件夹路径列表
        dry_run: 试运行模式，True为只检查不删除
        log_session_name: 日志会话名称
        keep_oldest: 保留策略，True为保留最早的文件，False为保留最新的文件
    """
    try:
        transfer_log_manager = TransferLogManager()
        if not log_session_name:
            # 使用第一个文件夹的名称作为会话名
            first_folder_name = Path(target_folder_paths[0]).name if target_folder_paths else "unknown"
            session_name = f"dedup_{first_folder_name}_{os.getpid()}"
            log_session_name = transfer_log_manager.start_transfer_session(session_name)
        
        # 验证所有文件夹路径
        target_paths = []
        for folder_path in target_folder_paths:
            target_path = Path(folder_path)
            if not target_path.exists() or not target_path.is_dir():
                raise DuplicateCleanerError(f"目标文件夹不存在或不是有效目录: {folder_path}")
            target_paths.append(target_path)
        
        # 扫描所有文件夹中的文件
        all_files = []
        for target_path in target_paths:
            for file_path in target_path.rglob('*'):
                if file_path.is_file():
                    try:
                        file_size = file_path.stat().st_size
                        ctime = file_path.stat().st_ctime
                        # 使用相对于第一个文件夹的路径作为相对路径
                        relative_path = file_path.relative_to(target_paths[0]) if target_path == target_paths[0] else file_path
                        all_files.append({
                            'path': file_path,
                            'size': file_size,
                            'ctime': ctime,
                            'relative_path': relative_path,
                            'source_folder': str(target_path)
                        })
                    except Exception as e:
                        logging.warning(f"无法获取文件信息: {file_path}, 错误: {e}")
                        continue
        # 按文件大小分组
        file_groups = {}
        for file_info in all_files:
            key = file_info['size']
            if key not in file_groups:
                file_groups[key] = []
            file_groups[key].append(file_info)
        # 进一步用MD5分组
        duplicate_groups = []
        for filesize, group in file_groups.items():
            if len(group) < 2:
                continue
            hash_map = {}
            for file_info in group:
                try:
                    md5 = _calc_md5(file_info['path'])
                except Exception as e:
                    md5 = None
                    logging.warning(f"计算MD5失败: {file_info['path']}, 错误: {e}")
                if md5 not in hash_map:
                    hash_map[md5] = []
                hash_map[md5].append(file_info)
            for md5, files in hash_map.items():
                if md5 and len(files) > 1:
                    # 根据保留策略排序文件
                    if keep_oldest:
                        files.sort(key=lambda x: x['ctime'])  # 按创建时间升序，最早的在前
                    else:
                        files.sort(key=lambda x: x['ctime'], reverse=True)  # 按创建时间降序，最新的在前
                    duplicate_groups.append({
                        'size': filesize,
                        'md5': md5,
                        'files': files
                    })
        results = {
            'total_files_scanned': len(all_files),
            'duplicate_groups_found': len(duplicate_groups),
            'total_duplicates_found': sum(len(g['files'])-1 for g in duplicate_groups),
            'duplicate_groups': duplicate_groups,
            'files_to_delete': [],
            'files_deleted': [],
            'deletion_errors': [],
            'dry_run': dry_run,
            'log_session_name': log_session_name
        }
        for group in duplicate_groups:
            files = group['files']
            for idx, file_info in enumerate(files):
                file_info['keep'] = (idx == 0)
                if idx > 0:
                    results['files_to_delete'].append({
                        'path': str(file_info['path']),
                        'relative_path': str(file_info['relative_path']),
                        'size': group['size'],
                        'md5': group['md5'],
                        'ctime': file_info['ctime'],
                        'source_folder': file_info.get('source_folder', '')
                    })
                    if not dry_run:
                        try:
                            file_info['path'].unlink()
                            results['files_deleted'].append({
                                'path': str(file_info['path']),
                                'relative_path': str(file_info['relative_path']),
                                'size': group['size'],
                                'md5': group['md5'],
                                'ctime': file_info['ctime'],
                                'source_folder': file_info.get('source_folder', '')
                            })
                            transfer_log_manager.log_transfer_operation(
                                source_path=str(file_info['path']),
                                target_path="",
                                operation_type="delete_duplicate",
                                target_folder="",
                                success=True,
                                file_size=group['size'],
                                md5=group['md5'],
                                ctime=file_info['ctime']
                            )
                            logging.info(f"已删除重复文件: {file_info['relative_path']}")
                        except Exception as e:
                            error_msg = f"删除文件失败: {file_info['relative_path']}, 错误: {e}"
                            results['deletion_errors'].append({
                                'path': str(file_info['path']),
                                'relative_path': str(file_info['relative_path']),
                                'error': str(e),
                                'source_folder': file_info.get('source_folder', '')
                            })
                            logging.error(error_msg)
        if dry_run:
            logging.info(f"重复文件扫描完成 [试运行模式]: 扫描文件 {results['total_files_scanned']} 个, "
                       f"发现重复组 {results['duplicate_groups_found']} 个, "
                       f"待删除重复文件 {results['total_duplicates_found']} 个")
        else:
            logging.info(f"重复文件删除完成: 扫描文件 {results['total_files_scanned']} 个, "
                       f"发现重复组 {results['duplicate_groups_found']} 个, "
                       f"成功删除 {len(results['files_deleted'])} 个, "
                       f"删除失败 {len(results['deletion_errors'])} 个")
            transfer_log_manager.end_transfer_session()
        return results
    except Exception as e:
        raise DuplicateCleanerError(f"删除重复文件失败: {e}")

def undo_duplicate_delete(log_file_path: str, operation_ids: list = None, dry_run: bool = True) -> dict:
    """
    根据日志恢复被删除的重复文件（需配合日志和备份/回收站机制）
    """
    transfer_log_manager = TransferLogManager()
    return transfer_log_manager.restore_from_log(
        log_file_path=log_file_path,
        operation_ids=operation_ids,
        dry_run=dry_run
    ) 