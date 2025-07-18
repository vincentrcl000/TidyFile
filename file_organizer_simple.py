#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件名匹配专用文件整理核心模块
"""
import os
import shutil
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from transfer_log_manager import TransferLogManager
import difflib
import PyPDF2
import docx
import time

class FileOrganizerError(Exception):
    pass

class FileOrganizer:
    def __init__(self, enable_transfer_log: bool = True):
        self.enable_transfer_log = enable_transfer_log
        self.transfer_log_manager = None
        if self.enable_transfer_log:
            try:
                self.transfer_log_manager = TransferLogManager()
                logging.info("转移日志管理器初始化成功")
            except Exception as e:
                logging.warning(f"转移日志管理器初始化失败: {e}")
                self.enable_transfer_log = False
        self.setup_logging()
    def setup_logging(self) -> None:
        log_filename = f"file_organizer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_path = os.path.join(os.path.dirname(__file__), "logs", log_filename)
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
    def scan_target_folders(self, target_directory: str) -> List[str]:
        try:
            target_path = Path(target_directory)
            if not target_path.exists():
                raise FileOrganizerError(f"目标目录不存在: {target_directory}")
            folders = []
            for item in target_path.rglob('*'):
                if item.is_dir():
                    relative_path = item.relative_to(target_path)
                    folders.append(str(relative_path))
            logging.info(f"扫描到 {len(folders)} 个目标文件夹（包含子目录）")
            return folders
        except Exception as e:
            raise FileOrganizerError(f"扫描目标文件夹失败: {e}")
    def _simple_classification(self, file_path: str, target_folders: List[str]) -> tuple:
        file_name = Path(file_path).name.lower()
        file_name_no_ext = Path(file_path).stem.lower()
        best_folder = None
        best_reason = ""
        for folder in target_folders:
            folder_lower = folder.lower()
            if file_name_no_ext == folder_lower:
                best_folder = folder
                best_reason = "文件名与文件夹名完全相等"
                break
            if folder_lower in file_name_no_ext:
                best_folder = folder
                best_reason = "文件名包含文件夹名"
                break
            if file_name_no_ext in folder_lower:
                best_folder = folder
                best_reason = "文件夹名包含文件名"
                break
        if best_folder:
            return (best_folder, best_reason, True)
        return (None, "无直接匹配的目标文件夹", False)
    def scan_source_files(self, source_directory: str) -> List[str]:
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
        return self.scan_target_folders(target_directory)
    def preview_classification(self, source_directory: str, target_directory: str) -> List[Dict[str, any]]:
        try:
            source_files = self.scan_source_files(source_directory)
            if not source_files:
                raise FileOrganizerError("源目录中没有找到文件")
            preview_results = []
            logging.info(f"开始预览分类，共 {len(source_files)} 个文件，仅分析前10个")
            preview_count = min(10, len(source_files))
            target_folders = self.scan_target_folders(target_directory)
            for i, file_path in enumerate(source_files[:preview_count], 1):
                file_name = Path(file_path).name
                try:
                    logging.info(f"正在处理文件 {i}/{preview_count}: {file_name}")
                    target_folder, match_reason, success = self._simple_classification(file_path, target_folders)
                    if success and target_folder:
                        preview_results.append({
                            'file_path': file_path,
                            'file_name': file_name,
                            'target_folder': target_folder,
                            'match_reason': match_reason,
                            'classification_method': 'Simple',
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
    def organize_file(self, file_path: str, target_directory: str, target_folders: List[str]) -> Tuple[bool, str]:
        try:
            file_path_obj = Path(file_path)
            filename = file_path_obj.name
            target_folder, match_reason, success = self._simple_classification(file_path, target_folders)
            if not success:
                return False, match_reason
            target_folder_path = Path(target_directory) / target_folder
            target_folder_path.mkdir(parents=True, exist_ok=True)
            target_file_path = target_folder_path / filename
            if target_file_path.exists():
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                name_parts = filename.rsplit('.', 1)
                if len(name_parts) == 2:
                    new_filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                else:
                    new_filename = f"{filename}_{timestamp}"
                target_file_path = target_folder_path / new_filename
            shutil.copy2(file_path, target_file_path)
            logging.info(f"[文件名匹配] 文件已复制: {file_path} -> {target_file_path}")
            return True, str(target_file_path)
        except Exception as e:
            error_msg = f"整理文件失败: {e}"
            logging.error(error_msg)
            return False, error_msg
    def organize_files(self, files=None, target_folders=None, target_base_dir=None, copy_mode=True, source_directory=None, target_directory=None, dry_run=False, progress_callback=None) -> Dict[str, any]:
        try:
            if source_directory and target_directory:
                target_folders = self.scan_target_folders(target_directory)
                files = self.scan_files(source_directory)
                target_base_dir = target_directory
                copy_mode = True
            if not files or not target_folders or not target_base_dir:
                raise FileOrganizerError("缺少必要参数")
            log_session_name = None
            if self.enable_transfer_log and self.transfer_log_manager and not dry_run:
                try:
                    session_name = f"organize_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    log_session_name = self.transfer_log_manager.start_transfer_session(session_name)
                    logging.info(f"开始转移日志会话: {session_name}")
                except Exception as e:
                    logging.warning(f"启动转移日志会话失败: {e}")
            if not target_folders:
                raise FileOrganizerError("目标目录中没有文件夹")
            if not files:
                raise FileOrganizerError("没有文件需要整理")
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
            # 输出整理开始信息到控制台
            print(f"\n=== 开始简单文件整理 ===")
            print(f"整理模式: {'复制' if copy_mode else '移动'}")
            print(f"源目录: {source_directory}")
            print(f"目标目录: {target_base_dir}")
            print(f"文件总数: {len(files)}")
            print(f"试运行: {'是' if dry_run else '否'}")
            print("=" * 50)
            
            logging.info(f"开始安全文件整理，共 {len(files)} 个文件")
            for i, file_info in enumerate(files, 1):
                file_path = file_info['path']
                filename = file_info['name']
                
                # 更新进度回调
                if progress_callback:
                    progress_percent = int((i / len(files)) * 100)
                    progress_callback(progress_percent, f"正在处理: {filename} ({i}/{len(files)})")
                
                # 控制台输出当前处理文件
                print(f"\n[{i}/{len(files)}] 正在处理: {filename}")
                
                try:
                    logging.info(f"正在处理文件 {i}/{len(files)}: {filename}")
                    print(f"  → 正在分析文件...")
                    target_folder, match_reason, success = self._simple_classification(file_path, target_folders)
                    results['ai_responses'].append({
                        'file_name': filename,
                        'target_folder': target_folder,
                        'match_reason': match_reason,
                        'success': success
                    })
                    
                    # 输出分类结果
                    if success and target_folder:
                        print(f"  ✓ 分类成功: {target_folder}")
                        print(f"  ✓ 匹配理由: {match_reason}")
                    else:
                        print(f"  ✗ 分类失败: {match_reason}")
                    
                    if not success or not target_folder:
                        error_msg = f"文件 {filename} 分类失败: {match_reason}，已跳过，未做任何处理"
                        logging.warning(error_msg)
                        results['errors'].append(error_msg)
                        results['skipped_files'] += 1
                        results['failed'].append({
                            'source_path': file_path,
                            'error': error_msg
                        })
                        continue
                    target_folder_path = Path(target_base_dir) / target_folder
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
                    original_target_path = target_folder_path / filename
                    target_file_path = original_target_path
                    if target_file_path.exists():
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        name_parts = filename.rsplit('.', 1)
                        if len(name_parts) == 2:
                            new_filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                        else:
                            new_filename = f"{filename}_{timestamp}"
                        target_file_path = target_folder_path / new_filename
                        logging.info(f"文件名冲突，重命名为: {target_file_path.name}")
                    if not dry_run:
                        try:
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
                            if copy_mode:
                                shutil.copy2(file_path, target_file_path)
                                operation = "copy"
                                operation_cn = "复制"
                            else:
                                shutil.move(file_path, target_file_path)
                                operation = "move"
                                operation_cn = "移动"
                            
                            print(f"  ✓ {operation_cn}操作完成: {target_file_path}")
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
                        'classification_method': 'Simple',
                        'renamed': str(target_file_path) != str(original_target_path),
                        'operation': operation
                    })
                except Exception as e:
                    error_msg = f"处理文件 {filename} 时出现异常: {e}"
                    logging.error(error_msg)
                    results['errors'].append(error_msg)
                    results['failed_moves'] += 1
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
            
            # 计算总耗时
            total_time = (results['end_time'] - results['start_time']).total_seconds()
            
            # 输出总结信息到控制台
            print(f"\n=== 简单文件整理完成 ===")
            print(f"总文件数: {results['total_files']}")
            print(f"成功处理: {results['successful_moves']}")
            print(f"处理失败: {results['failed_moves']}")
            print(f"跳过文件: {results['skipped_files']}")
            print(f"总耗时: {total_time:.2f} 秒")
            print("=" * 50)
            
            # 最终进度回调
            if progress_callback:
                progress_callback(100, f"整理完成! 成功: {results['successful_moves']}, 失败: {results['failed_moves']}")
            
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
        if not self.enable_transfer_log or not self.transfer_log_manager:
            raise FileOrganizerError("转移日志功能未启用")
        return self.transfer_log_manager.get_transfer_logs()
    def get_transfer_log_summary(self, log_file_path: str) -> Dict:
        if not self.enable_transfer_log or not self.transfer_log_manager:
            raise FileOrganizerError("转移日志功能未启用")
        return self.transfer_log_manager.get_session_summary(log_file_path)
    def restore_files_from_log(self, log_file_path: str, operation_ids: List[int] = None, dry_run: bool = True) -> Dict:
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
        if not self.enable_transfer_log or not self.transfer_log_manager:
            raise FileOrganizerError("转移日志功能未启用")
        return self.transfer_log_manager.cleanup_old_logs(days_to_keep)
    def multi_fuzzy_classification(self, file_path: str, target_folders: list, threshold: int = 60):
        file_name_no_ext = Path(file_path).stem.lower()
        results = []
        for folder in target_folders:
            folder_lower = folder.lower()
            # 完全相等
            if file_name_no_ext == folder_lower:
                results.append((folder, "完全相等", 100))
                continue
            # 包含关系
            if file_name_no_ext in folder_lower or folder_lower in file_name_no_ext:
                results.append((folder, "包含关系", 90))
                continue
            # difflib相似度
            ratio = difflib.SequenceMatcher(None, file_name_no_ext, folder_lower).ratio()
            if ratio > 0.8:
                results.append((folder, "模糊相似", int(ratio * 100)))
        # 按分数降序排序
        results = [r for r in results if r[2] >= threshold]
        results.sort(key=lambda x: -x[2])
        return results
    def classify_file(self, file_path: str, target_directory: str) -> tuple:
        target_folders = self.scan_target_folders(target_directory)
        fuzzy_results = self.multi_fuzzy_classification(file_path, target_folders)
        if fuzzy_results:
            best = fuzzy_results[0]
            return best[0], f"{best[1]}(分数:{best[2]})", True
        return None, "无匹配", False
    def get_file_summary(self, file_path: str, max_length: int = 50, max_pages: int = 2, max_seconds: int = 10) -> str:
        """
        自动适配 txt/pdf/docx 格式，返回前max_length字摘要，PDF/Word只取前max_pages页，单文件处理超时max_seconds秒。
        """
        ext = Path(file_path).suffix.lower()
        start_time = time.time()
        try:
            if ext == '.txt':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read(max_length)
            elif ext == '.pdf':
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ''
                    for i, page in enumerate(reader.pages):
                        if i >= max_pages or (time.time() - start_time) > max_seconds:
                            break
                        page_text = page.extract_text() or ''
                        text += page_text
                        if len(text) >= max_length:
                            break
                    if (time.time() - start_time) > max_seconds:
                        return '提取超时，已跳过'
                    return text[:max_length] if text else '未能提取正文'
            elif ext == '.docx':
                doc = docx.Document(file_path)
                text = ''
                for i, para in enumerate(doc.paragraphs):
                    if (time.time() - start_time) > max_seconds:
                        break
                    text += para.text
                    if len(text) >= max_length:
                        break
                if (time.time() - start_time) > max_seconds:
                    return '提取超时，已跳过'
                return text[:max_length] if text else '未能提取正文'
            else:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read(max_length)
        except Exception as e:
            if (time.time() - start_time) > max_seconds:
                return '提取超时，已跳过'
            return f'摘要获取失败: {e}'