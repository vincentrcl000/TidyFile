#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
目录管理模块：递归扫描目标目录，生成JSON清单，支持后续AI匹配。
"""
import os
import json
from pathlib import Path
import logging

class DirectoryManager:
    def scan_and_build_json(self, target_directory: str, save_path: str = None) -> dict:
        """递归扫描目标目录，生成树状结构和JSON清单"""
        def build_tree(path: Path):
            node = {
                'name': path.name,
                'path': str(path),
                'children': []
            }
            logging.info(f"扫描目录: {path}")
            print(f"[DirectoryManager] 扫描目录: {path}")
            for child in sorted(path.iterdir()):
                if child.is_dir():
                    node['children'].append(build_tree(child))
            return node
        root = Path(target_directory)
        logging.info(f"开始递归扫描目标目录: {target_directory}")
        print(f"[DirectoryManager] 开始递归扫描目标目录: {target_directory}")
        tree = build_tree(root)
        if save_path:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(tree, f, ensure_ascii=False, indent=2)
            logging.info(f"目录清单已保存到: {save_path}")
            print(f"[DirectoryManager] 目录清单已保存到: {save_path}")
        return tree
    def load_json(self, json_path: str) -> dict:
        logging.info(f"加载目录清单: {json_path}")
        print(f"[DirectoryManager] 加载目录清单: {json_path}")
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f) 