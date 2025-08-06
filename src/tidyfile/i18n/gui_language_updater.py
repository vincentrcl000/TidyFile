#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI语言更新管理器

本模块提供动态语言切换功能，包括：
1. 界面元素文本更新
2. 标签页标题更新
3. 按钮文本更新
4. 窗口标题更新

作者: AI Assistant
创建时间: 2025-08-05
"""

import tkinter as tk
from typing import Dict, List, Any, Callable
from tidyfile.i18n.i18n_manager import t


class GUILanguageUpdater:
    """GUI语言更新管理器"""
    
    def __init__(self):
        """初始化语言更新管理器"""
        self.widgets_to_update = {}  # 存储需要更新的组件
        self.tab_titles = {}  # 存储标签页标题
        self.window_titles = {}  # 存储窗口标题
        
    def register_widget(self, widget, text_key: str, section: str = "app", **kwargs):
        """
        注册需要更新的组件
        
        Args:
            widget: 要更新的组件
            text_key: 文本键
            section: 文本分类
            **kwargs: 格式化参数
        """
        widget_id = id(widget)
        self.widgets_to_update[widget_id] = {
            'widget': widget,
            'text_key': text_key,
            'section': section,
            'kwargs': kwargs
        }
    
    def register_tab_title(self, notebook, tab_id: str, text_key: str, section: str = "app"):
        """
        注册标签页标题
        
        Args:
            notebook: 标签页控件
            tab_id: 标签页标识
            text_key: 文本键
            section: 文本分类
        """
        self.tab_titles[tab_id] = {
            'notebook': notebook,
            'text_key': text_key,
            'section': section
        }
    
    def register_window_title(self, window, text_key: str, section: str = "app"):
        """
        注册窗口标题
        
        Args:
            window: 窗口对象
            text_key: 文本键
            section: 文本分类
        """
        window_id = id(window)
        self.window_titles[window_id] = {
            'window': window,
            'text_key': text_key,
            'section': section
        }
    
    def update_all_widgets(self):
        """更新所有注册的组件"""
        # 更新组件文本
        for widget_id, info in self.widgets_to_update.items():
            try:
                widget = info['widget']
                new_text = t(info['text_key'], info['section'], **info['kwargs'])
                
                # 根据组件类型更新文本
                if hasattr(widget, 'configure'):
                    # ttk组件
                    widget.configure(text=new_text)
                elif hasattr(widget, 'config'):
                    # tk组件
                    widget.config(text=new_text)
                elif hasattr(widget, 'set'):
                    # 变量组件
                    widget.set(new_text)
                    
            except Exception as e:
                print(f"更新组件失败 {widget_id}: {e}")
        
        # 更新标签页标题
        for tab_id, info in self.tab_titles.items():
            try:
                notebook = info['notebook']
                new_text = t(info['text_key'], info['section'])
                
                # 查找标签页索引
                for i in range(notebook.index('end')):
                    if notebook.tab(i, 'text') == tab_id or notebook.tab(i, 'text') in self._get_old_texts(info['text_key'], info['section']):
                        notebook.tab(i, text=new_text)
                        break
                        
            except Exception as e:
                print(f"更新标签页标题失败 {tab_id}: {e}")
        
        # 更新窗口标题
        for window_id, info in self.window_titles.items():
            try:
                window = info['window']
                new_text = t(info['text_key'], info['section'])
                window.title(new_text)
                
            except Exception as e:
                print(f"更新窗口标题失败 {window_id}: {e}")
    
    def _get_old_texts(self, text_key: str, section: str) -> List[str]:
        """获取可能的旧文本（用于标签页匹配）"""
        # 这里可以添加一些常见的文本映射
        text_mapping = {
            ('file_reader', 'app'): ['文件解读', 'File Reader'],
            ('article_reader', 'app'): ['文章阅读助手', 'Article Reader'],
            ('ai_classifier', 'app'): ['智能分类', 'AI Classifier'],
            ('tools', 'app'): ['工具', 'Tools'],
            ('weixin_manager', 'app'): ['微信文章管理', 'WeChat Manager']
        }
        
        key = (text_key, section)
        return text_mapping.get(key, [])
    
    def clear_registry(self):
        """清空注册表"""
        self.widgets_to_update.clear()
        self.tab_titles.clear()
        self.window_titles.clear()


# 全局实例
_global_updater = None

def get_global_updater() -> GUILanguageUpdater:
    """获取全局语言更新器实例"""
    global _global_updater
    if _global_updater is None:
        _global_updater = GUILanguageUpdater()
    return _global_updater

def register_widget(widget, text_key: str, section: str = "app", **kwargs):
    """注册组件（便捷函数）"""
    get_global_updater().register_widget(widget, text_key, section, **kwargs)

def register_tab_title(notebook, tab_id: str, text_key: str, section: str = "app"):
    """注册标签页标题（便捷函数）"""
    get_global_updater().register_tab_title(notebook, tab_id, text_key, section)

def register_window_title(window, text_key: str, section: str = "app"):
    """注册窗口标题（便捷函数）"""
    get_global_updater().register_window_title(window, text_key, section)

def update_all_widgets():
    """更新所有组件（便捷函数）"""
    get_global_updater().update_all_widgets() 