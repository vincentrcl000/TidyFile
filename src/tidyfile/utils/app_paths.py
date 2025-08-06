#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用路径管理器

本模块提供跨平台的应用数据目录管理，支持：
1. 自动检测操作系统类型
2. 获取系统标准应用数据目录
3. 支持便携模式和安装模式
4. 自动创建必要的目录结构

作者: AI Assistant
创建时间: 2025-08-05
"""

import os
import sys
import platform
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class AppPaths:
    """应用路径管理器"""
    
    def __init__(self, portable_mode: bool = False, app_name: str = "TidyFile"):
        """
        初始化应用路径管理器
        
        Args:
            portable_mode: 是否为便携模式
            app_name: 应用名称
        """
        self.portable_mode = portable_mode
        self.app_name = app_name
        self._init_paths()
    
    def _init_paths(self):
        """初始化应用路径"""
        if self.portable_mode:
            # 便携模式：使用程序目录
            self.app_data_dir = Path(__file__).parent / "app_data"
            logger.info(f"便携模式：使用程序目录 {self.app_data_dir}")
        else:
            # 安装模式：使用系统标准目录
            self.app_data_dir = self._get_system_app_data_dir()
            logger.info(f"安装模式：使用系统目录 {self.app_data_dir}")
        
        # 确保目录存在
        self._ensure_directories()
    
    def _get_system_app_data_dir(self) -> Path:
        """
        获取系统标准应用数据目录
        
        Returns:
            系统标准应用数据目录路径
        """
        system = platform.system().lower()
        
        if system == "windows":
            # Windows: %APPDATA%/TidyFile/
            appdata = os.environ.get('APPDATA')
            if not appdata:
                # 备用方案：使用用户目录
                appdata = os.path.expanduser("~/AppData/Roaming")
            return Path(appdata) / self.app_name
            
        elif system == "darwin":  # macOS
            # macOS: ~/Library/Application Support/TidyFile/
            home = Path.home()
            return home / "Library" / "Application Support" / self.app_name
            
        else:  # Linux
            # Linux: ~/.config/TidyFile/
            home = Path.home()
            return home / ".config" / self.app_name
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            self.app_data_dir / "config",
            self.app_data_dir / "data" / "cache",
            self.app_data_dir / "data" / "logs",
            self.app_data_dir / "data" / "transfer_logs",
            self.app_data_dir / "data" / "results",
            self.app_data_dir / "data" / "results" / "weixin_articles",
            self.app_data_dir / "temp",
            self.app_data_dir / "user_data" / "templates",
            self.app_data_dir / "user_data" / "custom_rules",
            self.app_data_dir / "user_data" / "locales"
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.debug(f"确保目录存在: {directory}")
            except Exception as e:
                logger.error(f"创建目录失败 {directory}: {e}")
    
    # 配置文件路径
    @property
    def ai_config_file(self) -> Path:
        """AI模型配置文件路径"""
        return self.app_data_dir / "config" / "ai_models_config.json"
    
    @property
    def classification_rules_file(self) -> Path:
        """分类规则配置文件路径"""
        return self.app_data_dir / "config" / "classification_rules.json"
    
    @property
    def app_settings_file(self) -> Path:
        """应用设置文件路径"""
        return self.app_data_dir / "config" / "app_settings.json"
    
    # 数据文件路径
    @property
    def cache_dir(self) -> Path:
        """缓存目录路径"""
        return self.app_data_dir / "data" / "cache"
    
    @property
    def logs_dir(self) -> Path:
        """日志目录路径"""
        return self.app_data_dir / "data" / "logs"
    
    @property
    def transfer_logs_dir(self) -> Path:
        """转移日志目录路径"""
        return self.app_data_dir / "data" / "transfer_logs"
    
    @property
    def results_dir(self) -> Path:
        """结果目录路径"""
        return self.app_data_dir / "data" / "results"
    
    @property
    def ai_results_file(self) -> Path:
        """AI处理结果文件路径"""
        return self.results_dir / "ai_organize_result.json"
    
    @property
    def weixin_articles_dir(self) -> Path:
        """微信文章目录路径"""
        return self.results_dir / "weixin_articles"
    
    @property
    def temp_dir(self) -> Path:
        """临时文件目录路径"""
        return self.app_data_dir / "temp"
    
    @property
    def user_templates_dir(self) -> Path:
        """用户模板目录路径"""
        return self.app_data_dir / "user_data" / "templates"
    
    @property
    def user_custom_rules_dir(self) -> Path:
        """用户自定义规则目录路径"""
        return self.app_data_dir / "user_data" / "custom_rules"
    
    @property
    def user_data_dir(self) -> Path:
        """用户数据目录路径"""
        return self.app_data_dir / "user_data"
    
    # 旧路径兼容性（用于迁移）
    @property
    def old_ai_config_file(self) -> Path:
        """旧的AI配置文件路径（项目根目录）"""
        return Path(__file__).parent / "ai_models_config.json"
    
    @property
    def old_classification_rules_file(self) -> Path:
        """旧的分类规则文件路径（项目根目录）"""
        return Path(__file__).parent / "classification_rules.json"
    
    @property
    def old_logs_dir(self) -> Path:
        """旧的日志目录路径（项目根目录）"""
        return Path(__file__).parent / "logs"
    
    @property
    def old_transfer_logs_dir(self) -> Path:
        """旧的转移日志目录路径（项目根目录）"""
        return Path(__file__).parent / "transfer_logs"
    
    @property
    def old_cache_dir(self) -> Path:
        """旧的缓存目录路径（项目根目录）"""
        return Path(__file__).parent / "cache"
    
    def get_all_paths(self) -> Dict[str, Path]:
        """
        获取所有路径的字典
        
        Returns:
            包含所有路径的字典
        """
        return {
            'app_data_dir': self.app_data_dir,
            'ai_config_file': self.ai_config_file,
            'classification_rules_file': self.classification_rules_file,
            'app_settings_file': self.app_settings_file,
            'cache_dir': self.cache_dir,
            'logs_dir': self.logs_dir,
            'transfer_logs_dir': self.transfer_logs_dir,
            'results_dir': self.results_dir,
            'ai_results_file': self.ai_results_file,
            'weixin_articles_dir': self.weixin_articles_dir,
            'temp_dir': self.temp_dir,
            'user_templates_dir': self.user_templates_dir,
            'user_custom_rules_dir': self.user_custom_rules_dir
        }
    
    def print_paths(self):
        """打印所有路径信息（用于调试）"""
        print(f"应用数据目录: {self.app_data_dir}")
        print(f"便携模式: {self.portable_mode}")
        print(f"操作系统: {platform.system()} {platform.release()}")
        print("\n路径详情:")
        
        paths = self.get_all_paths()
        for name, path in paths.items():
            print(f"  {name}: {path}")
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """
        清理临时文件
        
        Args:
            max_age_hours: 文件最大保留时间（小时）
        """
        import time
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        try:
            for file_path in self.temp_dir.rglob("*"):
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_path.unlink()
                        logger.debug(f"清理临时文件: {file_path}")
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")


# 全局实例
_app_paths = None

def get_app_paths(portable_mode: bool = False) -> AppPaths:
    """
    获取应用路径管理器实例（单例模式）
    
    Args:
        portable_mode: 是否为便携模式
        
    Returns:
        AppPaths实例
    """
    global _app_paths
    if _app_paths is None:
        _app_paths = AppPaths(portable_mode=portable_mode)
    return _app_paths


def detect_portable_mode() -> bool:
    """
    检测是否为便携模式
    
    Returns:
        是否为便携模式
    """
    # 检查是否存在便携模式标记文件
    portable_marker = Path(__file__).parent / "portable_mode.txt"
    return portable_marker.exists()


if __name__ == "__main__":
    # 测试代码
    import argparse
    
    parser = argparse.ArgumentParser(description="应用路径管理器测试")
    parser.add_argument("--portable", action="store_true", help="便携模式")
    parser.add_argument("--cleanup", action="store_true", help="清理临时文件")
    args = parser.parse_args()
    
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建路径管理器
    app_paths = AppPaths(portable_mode=args.portable)
    
    if args.cleanup:
        app_paths.cleanup_temp_files()
        print("临时文件清理完成")
    else:
        app_paths.print_paths() 