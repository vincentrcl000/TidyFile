#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迁移执行与日志模块：执行迁移命令，写入迁移日志，支持回滚。
"""
import shutil
from pathlib import Path
from transfer_log_manager import TransferLogManager
import os
import logging

class MigrationExecutor:
    def __init__(self):
        self.log_manager = TransferLogManager()
    def execute_plan(self, plan, dry_run=False):
        session_name = f"ai_migrate_{os.getpid()}"
        log_session = self.log_manager.start_transfer_session(session_name)
        results = []
        logging.info(f"开始执行迁移计划，共{len(plan)}条")
        print(f"[MigrationExecutor] 开始执行迁移计划，共{len(plan)}条")
        for item in plan:
            src = item.get('source') or 'unknown'
            tgt_dir = item.get('target_dir') or 'unknown'
            op = item.get('operation') or 'unknown'
            print(f"[MigrationExecutor] 迁移计划: {src} -> {tgt_dir} [{op}]")
            logging.info(f"迁移计划: {src} -> {tgt_dir} [{op}]")
            if not tgt_dir or not item['operation']:
                results.append({'source': src, 'target': None, 'success': False, 'error': '无目标目录'})
                logging.warning(f"跳过: {src}，无目标目录")
                print(f"[MigrationExecutor] 跳过: {src}，无目标目录")
                continue
            tgt_path = Path(tgt_dir) / Path(src).name
            try:
                if not dry_run:
                    Path(tgt_dir).mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, tgt_path)
                self.log_manager.log_transfer_operation(
                    source_path=src,
                    target_path=str(tgt_path),
                    operation_type=op,
                    target_folder=tgt_dir,
                    success=True
                )
                print(f"[MigrationExecutor] 日志写入: {src} -> {tgt_path}")
                logging.info(f"日志写入: {src} -> {tgt_path}")
                results.append({'source': src, 'target': str(tgt_path), 'success': True})
                logging.info(f"迁移成功: {src} -> {tgt_path}")
                print(f"[MigrationExecutor] 迁移成功: {src} -> {tgt_path}")
            except Exception as e:
                self.log_manager.log_transfer_operation(
                    source_path=src,
                    target_path=str(tgt_path),
                    operation_type=op,
                    target_folder=tgt_dir,
                    success=False,
                    error_message=str(e)
                )
                print(f"[MigrationExecutor] 日志写入(失败): {src} -> {tgt_path}, 错误: {e}")
                logging.error(f"日志写入(失败): {src} -> {tgt_path}, 错误: {e}")
                results.append({'source': src, 'target': str(tgt_path), 'success': False, 'error': str(e)})
                logging.error(f"迁移失败: {src} -> {tgt_path}, 错误: {e}")
                print(f"[MigrationExecutor] 迁移失败: {src} -> {tgt_path}, 错误: {e}")
        self.log_manager.end_transfer_session()
        logging.info(f"迁移执行完成，总{len(results)}条")
        print(f"[MigrationExecutor] 迁移执行完成，总{len(results)}条")
        return results
    def undo(self, log_file_path, operation_ids=None, dry_run=True):
        logging.info(f"开始回滚迁移，日志: {log_file_path}")
        print(f"[MigrationExecutor] 开始回滚迁移，日志: {log_file_path}")
        return self.log_manager.restore_from_log(log_file_path, operation_ids, dry_run) 