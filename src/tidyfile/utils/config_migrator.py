#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置迁移器

本模块提供配置文件迁移功能，包括：
1. 从项目根目录迁移配置文件到应用数据目录
2. 清理配置文件中的个人数据
3. 创建默认配置模板
4. 迁移状态检查和回滚

作者: AI Assistant
创建时间: 2025-08-05
"""

import json
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from tidyfile.utils.app_paths import AppPaths

logger = logging.getLogger(__name__)


class ConfigMigrator:
    """配置迁移器"""
    
    def __init__(self, app_paths: AppPaths):
        """
        初始化配置迁移器
        
        Args:
            app_paths: 应用路径管理器实例
        """
        self.app_paths = app_paths
        self.migration_log_file = app_paths.logs_dir / "migration.log"
        self._setup_logging()
    
    def _setup_logging(self):
        """设置迁移日志"""
        if not self.migration_log_file.parent.exists():
            self.migration_log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 添加文件处理器
        file_handler = logging.FileHandler(self.migration_log_file, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)
    
    def migrate_all_configs(self, force: bool = False) -> Dict[str, bool]:
        """
        迁移所有配置文件
        
        Args:
            force: 是否强制迁移（覆盖现有文件）
            
        Returns:
            迁移结果字典
        """
        logger.info("开始配置文件迁移")
        
        migrations = [
            ("AI模型配置", self._migrate_ai_config, force),
            ("分类规则配置", self._migrate_classification_rules, force),
            ("应用设置", self._create_default_app_settings, force),
            ("日志目录", self._migrate_logs, force),
            ("缓存目录", self._migrate_cache, force),
            ("结果文件", self._migrate_results, force)
        ]
        
        results = {}
        for name, migration_func, force_flag in migrations:
            try:
                success = migration_func(force_flag)
                results[name] = success
                status = "成功" if success else "跳过"
                logger.info(f"{name}迁移{status}")
            except Exception as e:
                logger.error(f"{name}迁移失败: {e}")
                results[name] = False
        
        # 记录迁移完成
        self._log_migration_completion(results)
        return results
    
    def _migrate_ai_config(self, force: bool = False) -> bool:
        """
        迁移AI模型配置
        
        Args:
            force: 是否强制迁移
            
        Returns:
            是否成功迁移
        """
        old_path = self.app_paths.old_ai_config_file
        new_path = self.app_paths.ai_config_file
        
        if not old_path.exists():
            logger.info("AI配置文件不存在，创建默认配置")
            return self._create_default_ai_config()
        
        if new_path.exists() and not force:
            logger.info("AI配置文件已存在，跳过迁移")
            return True
        
        try:
            # 加载并清理配置
            config_data = self._load_and_clean_ai_config(old_path)
            
            # 保存到新位置
            self._save_config(new_path, config_data)
            
            logger.info(f"AI配置已迁移到: {new_path}")
            return True
            
        except Exception as e:
            logger.error(f"AI配置迁移失败: {e}")
            return False
    
    def _migrate_classification_rules(self, force: bool = False) -> bool:
        """
        迁移分类规则配置
        
        Args:
            force: 是否强制迁移
            
        Returns:
            是否成功迁移
        """
        old_path = self.app_paths.old_classification_rules_file
        new_path = self.app_paths.classification_rules_file
        
        if not old_path.exists():
            logger.info("分类规则文件不存在，创建默认配置")
            return self._create_default_classification_rules()
        
        if new_path.exists() and not force:
            logger.info("分类规则文件已存在，跳过迁移")
            return True
        
        try:
            # 加载并清理配置
            config_data = self._load_and_clean_classification_rules(old_path)
            
            # 保存到新位置
            self._save_config(new_path, config_data)
            
            logger.info(f"分类规则已迁移到: {new_path}")
            return True
            
        except Exception as e:
            logger.error(f"分类规则迁移失败: {e}")
            return False
    
    def _create_default_app_settings(self, force: bool = False) -> bool:
        """
        创建默认应用设置
        
        Args:
            force: 是否强制创建
            
        Returns:
            是否成功创建
        """
        settings_path = self.app_paths.app_settings_file
        
        if settings_path.exists() and not force:
            logger.info("应用设置文件已存在，跳过创建")
            return True
        
        try:
            default_settings = {
                "app_info": {
                    "version": "1.0.0",
                    "last_updated": datetime.now().isoformat(),
                    "migration_version": "1.0"
                },
                "general": {
                    "portable_mode": self.app_paths.portable_mode,
                    "language": "zh-CN",
                    "theme": "default",
                    "auto_backup": True,
                    "backup_interval_days": 7,
                    "max_recent_files": 20
                },
                "ai": {
                    "default_model": "ollama-local",
                    "max_retries": 3,
                    "timeout_seconds": 300,
                    "batch_size": 10,
                    "preferred_models": ["qwen3", "deepseek"]
                },
                "file_processing": {
                    "max_file_size_mb": 100,
                    "supported_formats": [".pdf", ".docx", ".txt", ".md", ".html"],
                    "temp_file_cleanup": True,
                    "cleanup_interval_hours": 24,
                    "concurrent_processing": True,
                    "max_workers": 4
                },
                "logging": {
                    "level": "INFO",
                    "max_log_files": 10,
                    "max_log_size_mb": 10,
                    "log_to_file": True,
                    "log_to_console": True
                },
                "server": {
                    "port": 8080,
                    "host": "0.0.0.0",
                    "max_connections": 10,
                    "timeout_seconds": 300,
                    "enable_https": False,
                    "cert_file": "",
                    "key_file": ""
                },
                "ui": {
                    "window_size": "1200x800",
                    "auto_save_settings": True,
                    "show_tooltips": True,
                    "dark_mode": False
                }
            }
            
            self._save_config(settings_path, default_settings)
            logger.info(f"默认应用设置已创建: {settings_path}")
            return True
            
        except Exception as e:
            logger.error(f"创建应用设置失败: {e}")
            return False
    
    def _migrate_logs(self, force: bool = False) -> bool:
        """
        迁移日志目录
        
        Args:
            force: 是否强制迁移
            
        Returns:
            是否成功迁移
        """
        old_dir = self.app_paths.old_logs_dir
        new_dir = self.app_paths.logs_dir
        
        if not old_dir.exists():
            logger.info("旧日志目录不存在，跳过迁移")
            return True
        
        try:
            # 复制日志文件
            for log_file in old_dir.glob("*.log"):
                new_file = new_dir / log_file.name
                if not new_file.exists() or force:
                    shutil.copy2(log_file, new_file)
                    logger.debug(f"迁移日志文件: {log_file.name}")
            
            logger.info(f"日志目录已迁移到: {new_dir}")
            return True
            
        except Exception as e:
            logger.error(f"日志目录迁移失败: {e}")
            return False
    
    def _migrate_cache(self, force: bool = False) -> bool:
        """
        迁移缓存目录
        
        Args:
            force: 是否强制迁移
            
        Returns:
            是否成功迁移
        """
        old_dir = self.app_paths.old_cache_dir
        new_dir = self.app_paths.cache_dir
        
        if not old_dir.exists():
            logger.info("旧缓存目录不存在，跳过迁移")
            return True
        
        try:
            # 复制缓存文件
            for cache_file in old_dir.rglob("*"):
                if cache_file.is_file():
                    relative_path = cache_file.relative_to(old_dir)
                    new_file = new_dir / relative_path
                    
                    if not new_file.exists() or force:
                        new_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(cache_file, new_file)
                        logger.debug(f"迁移缓存文件: {relative_path}")
            
            logger.info(f"缓存目录已迁移到: {new_dir}")
            return True
            
        except Exception as e:
            logger.error(f"缓存目录迁移失败: {e}")
            return False
    
    def _migrate_results(self, force: bool = False) -> bool:
        """
        迁移结果文件
        
        Args:
            force: 是否强制迁移
            
        Returns:
            是否成功迁移
        """
        old_results_file = Path(__file__).parent / "ai_organize_result.json"
        new_results_file = self.app_paths.ai_results_file
        
        if not old_results_file.exists():
            logger.info("旧结果文件不存在，跳过迁移")
            return True
        
        try:
            if not new_results_file.exists() or force:
                shutil.copy2(old_results_file, new_results_file)
                logger.info(f"结果文件已迁移到: {new_results_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"结果文件迁移失败: {e}")
            return False
    
    def _load_and_clean_ai_config(self, file_path: Path) -> Dict[str, Any]:
        """
        加载并清理AI配置中的个人数据
        
        Args:
            file_path: 配置文件路径
            
        Returns:
            清理后的配置数据
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 清理API密钥等敏感信息
        for model in config.get('models', []):
            if 'api_key' in model:
                model['api_key'] = ''  # 清空API密钥
            if 'base_url' in model:
                # 保留本地模型配置，清理网络地址
                base_url = model['base_url'].lower()
                if not any(local in base_url for local in ['localhost', '127.0.0.1', '192.168.', '10.']):
                    model['base_url'] = ''
        
        return config
    
    def _load_and_clean_classification_rules(self, file_path: Path) -> Dict[str, Any]:
        """
        加载并清理分类规则中的个人数据
        
        Args:
            file_path: 配置文件路径
            
        Returns:
            清理后的规则数据
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            rules = json.load(f)
        
        # 保留规则结构，清理个人数据
        cleaned_rules = {}
        for rule_name, rule_data in rules.items():
            if isinstance(rule_data, dict):
                # 保留规则定义，清理时间戳等个人数据
                cleaned_rule = {
                    'description': rule_data.get('description', ''),
                    'keywords': rule_data.get('keywords', [])
                }
                cleaned_rules[rule_name] = cleaned_rule
        
        return cleaned_rules
    
    def _create_default_ai_config(self) -> bool:
        """
        创建默认AI配置
        
        Returns:
            是否成功创建
        """
        try:
            default_config = {
                "models": [
                    {
                        "id": "ollama-local",
                        "name": "本地Ollama模型",
                        "base_url": "http://localhost:11434",
                        "model_name": "qwen3:4b",
                        "model_type": "ollama",
                        "api_key": "",
                        "priority": 1,
                        "enabled": True
                    },
                    {
                        "id": "lm-studio-local",
                        "name": "本地LM Studio模型",
                        "base_url": "http://localhost:1234/v1",
                        "model_name": "qwen/qwen3-8b",
                        "model_type": "lm_studio",
                        "api_key": "",
                        "priority": 2,
                        "enabled": True
                    }
                ]
            }
            
            self._save_config(self.app_paths.ai_config_file, default_config)
            logger.info("默认AI配置已创建")
            return True
            
        except Exception as e:
            logger.error(f"创建默认AI配置失败: {e}")
            return False
    
    def _create_default_classification_rules(self) -> bool:
        """
        创建默认分类规则
        
        Returns:
            是否成功创建
        """
        try:
            default_rules = {
                "工作文档": {
                    "description": "工作相关的文档、报告、项目资料等",
                    "keywords": ["工作", "项目", "报告", "会议", "计划"]
                },
                "学习资料": {
                    "description": "学习、培训、教育相关的资料",
                    "keywords": ["学习", "培训", "教育", "课程", "教程"]
                },
                "个人文档": {
                    "description": "个人相关的文档、简历、证书等",
                    "keywords": ["个人", "简历", "证书", "身份证", "合同"]
                },
                "媒体文件": {
                    "description": "图片、视频、音频等媒体文件",
                    "keywords": ["图片", "视频", "音频", "照片", "音乐"]
                }
            }
            
            self._save_config(self.app_paths.classification_rules_file, default_rules)
            logger.info("默认分类规则已创建")
            return True
            
        except Exception as e:
            logger.error(f"创建默认分类规则失败: {e}")
            return False
    
    def _save_config(self, file_path: Path, data: Dict[str, Any]):
        """
        保存配置文件
        
        Args:
            file_path: 文件路径
            data: 配置数据
        """
        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存配置
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _log_migration_completion(self, results: Dict[str, bool]):
        """
        记录迁移完成状态
        
        Args:
            results: 迁移结果
        """
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        completion_log = {
            "timestamp": datetime.now().isoformat(),
            "total_migrations": total_count,
            "successful_migrations": success_count,
            "failed_migrations": total_count - success_count,
            "results": results
        }
        
        # 保存到迁移日志
        migration_status_file = self.app_paths.logs_dir / "migration_status.json"
        try:
            with open(migration_status_file, 'w', encoding='utf-8') as f:
                json.dump(completion_log, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存迁移状态失败: {e}")
    
    def check_migration_status(self) -> Dict[str, Any]:
        """
        检查迁移状态
        
        Returns:
            迁移状态信息
        """
        status = {
            "migration_completed": False,
            "config_files": {},
            "data_directories": {},
            "last_migration": None
        }
        
        # 检查配置文件
        config_files = {
            "ai_config": self.app_paths.ai_config_file,
            "classification_rules": self.app_paths.classification_rules_file,
            "app_settings": self.app_paths.app_settings_file
        }
        
        for name, file_path in config_files.items():
            status["config_files"][name] = {
                "exists": file_path.exists(),
                "path": str(file_path)
            }
        
        # 检查数据目录
        data_dirs = {
            "logs": self.app_paths.logs_dir,
            "cache": self.app_paths.cache_dir,
            "results": self.app_paths.results_dir,
            "transfer_logs": self.app_paths.transfer_logs_dir
        }
        
        for name, dir_path in data_dirs.items():
            status["data_directories"][name] = {
                "exists": dir_path.exists(),
                "path": str(dir_path)
            }
        
        # 检查迁移状态文件
        migration_status_file = self.app_paths.logs_dir / "migration_status.json"
        if migration_status_file.exists():
            try:
                with open(migration_status_file, 'r', encoding='utf-8') as f:
                    migration_data = json.load(f)
                status["last_migration"] = migration_data.get("timestamp")
                status["migration_completed"] = True
            except Exception:
                pass
        
        return status


if __name__ == "__main__":
    # 测试代码
    import argparse
    
    parser = argparse.ArgumentParser(description="配置迁移器测试")
    parser.add_argument("--migrate", action="store_true", help="执行迁移")
    parser.add_argument("--force", action="store_true", help="强制迁移")
    parser.add_argument("--status", action="store_true", help="检查迁移状态")
    args = parser.parse_args()
    
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建路径管理器和迁移器
    app_paths = AppPaths()
    migrator = ConfigMigrator(app_paths)
    
    if args.status:
        status = migrator.check_migration_status()
        print("迁移状态:")
        print(json.dumps(status, ensure_ascii=False, indent=2))
    elif args.migrate:
        results = migrator.migrate_all_configs(force=args.force)
        print("迁移结果:")
        for name, success in results.items():
            print(f"  {name}: {'成功' if success else '失败'}")
    else:
        print("请使用 --migrate 执行迁移或 --status 检查状态") 