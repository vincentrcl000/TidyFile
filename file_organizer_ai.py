#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能分类专用文件整理核心模块
"""
import os
import shutil
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import ollama
from transfer_log_manager import TransferLogManager
import PyPDF2
import docx
import time

class FileOrganizerError(Exception):
    pass

class OllamaClient:
    def __init__(self, model_name: str = None, host: str = "http://localhost:11434"):
        self.model_name = model_name
        self.host = host
        self.client = ollama.Client(host=host)
        self._validate_connection()
    def _validate_connection(self) -> None:
        try:
            models_response = self.client.list()
            if hasattr(models_response, 'models'):
                models_list = models_response.models
            elif isinstance(models_response, dict) and 'models' in models_response:
                models_list = models_response['models']
            else:
                models_list = models_response if isinstance(models_response, list) else []
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
        if max_retries is None:
            max_retries = len(self.available_models)
        last_error = None
        models_to_try = [self.model_name] + [m for m in self.available_models if m != self.model_name]
        for attempt, model_name in enumerate(models_to_try[:max_retries]):
            try:
                client = ollama.Client(host=self.host)
                response = client.chat(
                    model=model_name,
                    messages=messages
                )
                if model_name != self.model_name:
                    logging.info(f"模型切换: {self.model_name} -> {model_name}")
                    self.model_name = model_name
                return response['message']['content'].strip()
            except Exception as e:
                last_error = e
                logging.warning(f"模型 {model_name} 响应失败: {e}")
                if attempt < max_retries - 1:
                    continue
        raise FileOrganizerError(f"所有可用模型都响应失败，最后错误: {last_error}")

class FileOrganizer:
    def __init__(self, model_name: str = None, enable_transfer_log: bool = True):
        self.model_name = model_name
        self.ollama_client = None
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
    def initialize_ollama(self) -> None:
        try:
            self.ollama_client = OllamaClient(self.model_name)
            logging.info("Ollama 客户端初始化成功")
        except Exception as e:
            raise FileOrganizerError(f"初始化 Ollama 客户端失败: {e}")
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
    def get_directory_tree_structure(self, target_directory: str) -> str:
        try:
            target_path = Path(target_directory)
            if not target_path.exists():
                raise FileOrganizerError(f"目标目录不存在: {target_directory}")
            def build_tree(path: Path, prefix: str = "", is_last: bool = True) -> List[str]:
                lines = []
                if path != target_path:
                    connector = "└── " if is_last else "├── "
                    lines.append(f"{prefix}{connector}{path.name}")
                    prefix += "    " if is_last else "│   "
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
        try:
            if not self.ollama_client:
                self.initialize_ollama()
            file_name = Path(file_path).name
            prompt = self._build_classification_prompt(file_path, target_directory)
            logging.info(f"正在分类文件: {file_name}")
            classification_result = self.ollama_client.chat_with_retry([
                {
                    'role': 'user',
                    'content': prompt
                }
            ])
            logging.info(f"AI分类原始结果: {classification_result}")
            target_folders = self.scan_target_folders(target_directory)
            target_folder, match_reason = self._parse_classification_result(classification_result, target_folders)
            if target_folder and match_reason:
                logging.info(f"AI分类成功: {file_name} -> {target_folder}, 理由: {match_reason}")
                return target_folder, match_reason, True
            else:
                logging.warning(f"AI分类解析失败: {file_name}")
                return None, "所有分类方法均失败", False
        except Exception as e:
            logging.error(f"AI分类失败: {e}")
            return None, f"分类失败: {str(e)}", False
    def _build_classification_prompt(self, file_path: str, target_directory: str) -> str:
        file_name = Path(file_path).name
        file_extension = Path(file_path).suffix.lower()
        file_content = ""
        content_readable = False
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.read()[:2000]
                printable_ratio = sum(1 for c in file_content if c.isprintable() or c.isspace()) / len(file_content) if file_content else 0
                if printable_ratio > 0.7:
                    content_readable = True
                else:
                    file_content = "文件内容为二进制格式，无法读取"
        except Exception:
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
        directory_structure = self.get_directory_tree_structure(target_directory)
        prompt = f"""
你是一个专业的文件分类助手。请阅读原文件的前500个字，或者识别第一页内容，根据文件内容判断文件应该归类到下列哪个文件夹中，注意，每个文件根据文件内容只匹配一个文件夹，匹配原则是：

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
        try:
            result = result.strip()
            parts = result.split('|')
            if len(parts) != 3:
                logging.warning(f"分类结果格式不正确，期望3个部分，实际得到{len(parts)}个: {result}")
                return None, None
            original_filename = parts[0].strip()
            target_folder = parts[1].strip()
            match_reason = parts[2].strip()
            if target_folder in target_folders:
                return target_folder, match_reason
            else:
                for valid_folder in target_folders:
                    if target_folder in valid_folder or valid_folder in target_folder:
                        return valid_folder, f"{match_reason}（模糊匹配：{target_folder}）"
                logging.warning(f"目标文件夹 '{target_folder}' 不在有效列表中")
                return None, None
        except Exception as e:
            logging.warning(f"解析分类结果失败: {e}, 原始结果: {result}")
            return None, None
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
            for i, file_path in enumerate(source_files[:preview_count], 1):
                file_name = Path(file_path).name
                try:
                    logging.info(f"正在处理文件 {i}/{preview_count}: {file_name}")
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
    def organize_file(self, file_path: str, target_directory: str, target_folders: List[str]) -> Tuple[bool, str]:
        try:
            if not self.ollama_client:
                self.initialize_ollama()
            file_path_obj = Path(file_path)
            filename = file_path_obj.name
            recommended_folders = self.ollama_client.classify_file(filename, target_folders)
            if not recommended_folders:
                return False, "无法确定目标文件夹"
            target_folder = recommended_folders[0]
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
            logging.info(f"文件已复制: {file_path} -> {target_file_path}")
            return True, str(target_file_path)
        except Exception as e:
            error_msg = f"整理文件失败: {e}"
            logging.error(error_msg)
            return False, error_msg
    def organize_files(self, files=None, target_folders=None, target_base_dir=None, copy_mode=True, source_directory=None, target_directory=None, dry_run=False) -> Dict[str, any]:
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
            logging.info(f"开始安全文件整理，共 {len(files)} 个文件")
            for i, file_info in enumerate(files, 1):
                file_path = file_info['path']
                filename = file_info['name']
                try:
                    logging.info(f"正在处理文件 {i}/{len(files)}: {filename}")
                    target_folder, match_reason, success = self.classify_file(file_path, target_base_dir)
                    results['ai_responses'].append({
                        'file_name': filename,
                        'target_folder': target_folder,
                        'match_reason': match_reason,
                        'success': success
                    })
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
                        'classification_method': 'AI',
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