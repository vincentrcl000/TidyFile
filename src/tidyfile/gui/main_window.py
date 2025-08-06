#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文件整理器 - 分页版GUI应用
将智能分类和文件分类功能分离到不同的分页中
"""

import ttkbootstrap as tb
# 兼容新版本ttkbootstrap
try:
    from ttkbootstrap import Style, Window
except ImportError:
    pass
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import filedialog, messagebox, Listbox, ttk
from ttkbootstrap.scrolled import ScrolledText
import threading
import json
import os
import logging
from pathlib import Path
from datetime import datetime
import time
# from tidyfile.core.duplicate_cleaner import remove_duplicate_files  # 已迁移到独立模块
from tidyfile.core.file_reader import FileReader
from tidyfile.core.transfer_log_manager import TransferLogManager
from tidyfile.core.batch_add_chain_tags import ChainTagsBatchProcessor

# 导入国际化支持
try:
    from tidyfile.i18n.i18n_manager import get_i18n_manager, t
    from tidyfile.i18n.gui_language_updater import update_all_widgets, register_widget, register_tab_title, register_window_title
    I18N_AVAILABLE = True
except ImportError:
    I18N_AVAILABLE = False
    # 创建简单的翻译函数作为后备
    def t(key: str, section: str = "app", **kwargs) -> str:
        """简单的翻译函数后备"""
        return key
    
    # 创建空的更新函数作为后备
    def update_all_widgets():
        pass
    
    def register_widget(widget, text_key: str, section: str = "app", **kwargs):
        pass
    
    def register_tab_title(notebook, tab_id: str, text_key: str, section: str = "app"):
        pass
    
    def register_window_title(window, text_key: str, section: str = "app"):
        pass

class TagOptimizerGUI:
    """标签优化器GUI类"""
    
    def __init__(self, parent_frame, root_window):
        """初始化标签优化器"""
        self.parent_frame = parent_frame
        self.root_window = root_window
        self.processor = ChainTagsBatchProcessor()
        
        # 创建界面
        self.create_widgets()
        
        # 加载初始数据
        self.load_initial_data()
    
    def create_widgets(self):
        """创建界面组件"""
        # 创建主框架
        main_frame = tb.Frame(self.parent_frame)
        main_frame.pack(fill=BOTH, expand=True)
        
        # 标题
        title_label = tb.Label(main_frame, text=t("title", "tag_optimizer"), font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 15))
        register_widget(title_label, "title", "tag_optimizer")
        
        # 说明文字
        info_label = tb.Label(
            main_frame, 
            text=t("description", "tag_optimizer"),
            font=('Arial', 10),
            foreground="gray"
        )
        info_label.pack(pady=(0, 20))
        register_widget(info_label, "description", "tag_optimizer")
        
        # 创建功能按钮区域
        self.create_function_buttons(main_frame)
        
        # 创建结果显示区域
        self.create_result_area(main_frame)
    
    def create_function_buttons(self, parent):
        """创建功能按钮区域"""
        # 功能按钮框架
        button_frame = tb.LabelFrame(parent, text=t("function_selection", "tag_optimizer"), padding="10")
        button_frame.pack(fill=X, pady=(0, 15))
        register_widget(button_frame, "function_selection", "tag_optimizer")
        
        # 按钮配置
        buttons_config = [
            {
                "name": t("current_tag_analysis", "tag_optimizer"),
                "command": self.analyze_current_tags,
                "style": "info.TButton",
                "description": t("current_tag_analysis_desc", "tag_optimizer")
            },
            {
                "name": t("smart_tags", "tag_optimizer"),
                "command": self.smart_tags,
                "style": "success.TButton",
                "description": t("smart_tags_desc", "tag_optimizer")
            },
            {
                "name": t("tag_formatting", "tag_optimizer"),
                "command": self.format_tags,
                "style": "warning.TButton",
                "description": t("tag_formatting_desc", "tag_optimizer")
            }
        ]
        
        # 创建按钮网格
        for i, config in enumerate(buttons_config):
            row = i // 2
            col = i % 2
            
            # 按钮容器
            button_container = tb.Frame(button_frame)
            button_container.grid(row=row, column=col, sticky=(W, E, N, S), padx=10, pady=5)
            
            # 按钮
            button = tb.Button(
                button_container,
                text=config["name"],
                command=config["command"],
                style=config["style"],
                width=20
            )
            button.pack(pady=(0, 5))
            
            # 描述
            desc_label = tb.Label(
                button_container,
                text=config["description"],
                font=('Arial', 9),
                foreground="gray",
                wraplength=200,
                justify=CENTER
            )
            desc_label.pack()
        
        # 配置网格权重
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
    
    def create_result_area(self, parent):
        """创建结果显示区域"""
        # 结果框架
        result_frame = tb.LabelFrame(parent, text=t("operation_result", "tag_optimizer"), padding="10")
        result_frame.pack(fill=BOTH, expand=True)
        register_widget(result_frame, "operation_result", "tag_optimizer")
        
        # 创建文本区域
        self.result_text = ScrolledText(result_frame, height=15, font=('Consolas', 9))
        self.result_text.pack(fill=BOTH, expand=True)
        
        # 底部按钮框架
        bottom_frame = tb.Frame(result_frame)
        bottom_frame.pack(fill=X, pady=(10, 0))
        
        # 清空按钮
        clear_btn = tb.Button(bottom_frame, text=t("clear_result", "tag_optimizer"), command=self.clear_results, style="secondary.TButton")
        clear_btn.pack(side=LEFT)
        register_widget(clear_btn, "clear_result", "tag_optimizer")
        
        # 保存结果按钮
        save_btn = tb.Button(bottom_frame, text=t("save_result", "tag_optimizer"), command=self.save_results, style="info.TButton")
        save_btn.pack(side=LEFT, padx=(10, 0))
        register_widget(save_btn, "save_result", "tag_optimizer")
        
        # 刷新数据按钮
        refresh_btn = tb.Button(bottom_frame, text=t("refresh_data", "tag_optimizer"), command=self.refresh_data, style="warning.TButton")
        refresh_btn.pack(side=RIGHT)
        register_widget(refresh_btn, "refresh_data", "tag_optimizer")
    
    def load_initial_data(self):
        """加载初始数据"""
        try:
            data = self.processor.load_data()
            if data:
                self.log_message(f"✓ 成功加载 {len(data)} 条记录")
            else:
                self.log_message("✗ 无法加载数据")
        except Exception as e:
            self.log_message(f"✗ 加载数据失败: {e}")
    
    def log_message(self, message):
        """记录消息到结果区域"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.result_text.insert(END, f"[{timestamp}] {message}\n")
        self.result_text.see(END)
        self.root_window.update()
    
    def clear_results(self):
        """清空结果区域"""
        self.result_text.delete(1.0, END)
    
    def save_results(self):
        """保存结果到文件"""
        try:
            content = self.result_text.get(1.0, END)
            if not content.strip():
                messagebox.showwarning(t("warning", "messages"), t("no_content_to_save", "messages"))
                return
            
            filename = f"标签优化结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            messagebox.showinfo(t("success", "messages"), t("result_saved_to", "messages", filename=filename))
        except Exception as e:
            messagebox.showerror(t("error", "messages"), t("save_failed", "messages", e=str(e)))
    
    def refresh_data(self):
        """刷新数据"""
        self.log_message("正在刷新数据...")
        self.load_initial_data()
    
    def analyze_current_tags(self):
        """当前标签分析"""
        self.log_message("=" * 50)
        self.log_message("开始分析当前标签情况...")
        
        try:
            # 加载数据
            data = self.processor.load_data()
            if not data:
                self.log_message("✗ 无法加载数据")
                return
            
            # 执行扫描
            stats = self.processor.pre_scan_chain_tags(data)
            
            # 提取现有标签统计
            existing_tags = self.processor.extract_existing_tags(data)
            
            # 显示基本统计
            self.log_message(f"总记录数: {len(data)}")
            self.log_message(f"已有链式标签: {stats['existing_chain_tags']}")
            self.log_message(f"需要添加链式标签: {stats['need_chain_tags']}")
            self.log_message(f"无链式标签: {stats['no_level_tags']}")
            
            # 计算百分比
            total = len(data)
            if total > 0:
                existing_pct = (stats['existing_chain_tags'] / total) * 100
                need_pct = (stats['need_chain_tags'] / total) * 100
                no_level_pct = (stats['no_level_tags'] / total) * 100
                
                self.log_message(f"\n百分比统计:")
                self.log_message(f"  已有链式标签: {existing_pct:.1f}%")
                self.log_message(f"  需要添加链式标签: {need_pct:.1f}%")
                self.log_message(f"  无链式标签: {no_level_pct:.1f}%")
            
            # 显示各级标签数量统计
            self.log_message(f"\n各级标签数量统计:")
            self.log_message(f"  1级标签数量: {len(existing_tags[1])}")
            self.log_message(f"  2级标签数量: {len(existing_tags[2])}")
            self.log_message(f"  3级标签数量: {len(existing_tags[3])}")
            self.log_message(f"  4级标签数量: {len(existing_tags[4])}")
            self.log_message(f"  5级标签数量: {len(existing_tags[5])}")
            self.log_message(f"  3级及以上标签总数: {len(existing_tags[3] | existing_tags[4] | existing_tags[5])}")
            
            # 显示前10个1级标签示例
            if existing_tags[1]:
                self.log_message(f"\n1级标签示例 (前10个):")
                for i, tag in enumerate(sorted(list(existing_tags[1]))[:10], 1):
                    self.log_message(f"  {i}. {tag}")
                if len(existing_tags[1]) > 10:
                    self.log_message(f"  ... 还有 {len(existing_tags[1]) - 10} 个1级标签")
            
            self.log_message("✓ 标签分析完成")
            
        except Exception as e:
            self.log_message(f"✗ 标签分析失败: {e}")
    
    def smart_tags(self):
        """智能标签功能（增强版）"""
        self.log_message("=" * 50)
        self.log_message("开始智能标签处理（增强版）...")
        
        try:
            # 确认操作
            result = messagebox.askyesno(
                "确认操作", 
                "智能标签功能（增强版）将使用AI为以下记录推荐三级标签：\n" +
                "1. 链式标签为空的记录\n" +
                "2. 没有标签字段的记录（如在线文章）\n\n" +
                "确定要继续吗？"
            )
            if not result:
                self.log_message("操作已取消")
                return
            
            # 先统计需要处理的记录数量
            data = self.processor.load_data()
            if not data:
                self.log_message("✗ 无法加载数据")
                return
            
            empty_chain_tags_count = 0
            no_tags_field_count = 0
            
            for item in data:
                # 检查链式标签为空的情况
                current_chain_tag = ""
                if "标签" in item and isinstance(item["标签"], dict):
                    current_chain_tag = item["标签"].get("链式标签", "")
                
                if not current_chain_tag or not current_chain_tag.strip():
                    empty_chain_tags_count += 1
                
                # 检查没有标签字段的情况
                if "标签" not in item:
                    no_tags_field_count += 1
            
            total_need_process = empty_chain_tags_count + no_tags_field_count
            
            self.log_message(f"检测到需要处理的记录:")
            self.log_message(f"  链式标签为空的记录: {empty_chain_tags_count} 条")
            self.log_message(f"  没有标签字段的记录: {no_tags_field_count} 条")
            self.log_message(f"  总计需要处理: {total_need_process} 条")
            
            if total_need_process == 0:
                self.log_message("✓ 没有需要处理的记录")
                return
            
            # 执行智能标签处理
            success = self.processor._process_smart_tags(dry_run=False)
            
            if success:
                # 重新统计处理后的情况
                data_after = self.processor.load_data()
                if data_after:
                    empty_chain_tags_after = 0
                    no_tags_field_after = 0
                    
                    for item in data_after:
                        # 检查链式标签为空的情况
                        current_chain_tag = ""
                        if "标签" in item and isinstance(item["标签"], dict):
                            current_chain_tag = item["标签"].get("链式标签", "")
                        
                        if not current_chain_tag or not current_chain_tag.strip():
                            empty_chain_tags_after += 1
                        
                        # 检查没有标签字段的情况
                        if "标签" not in item:
                            no_tags_field_after += 1
                    
                    total_after = empty_chain_tags_after + no_tags_field_after
                    processed_count = total_need_process - total_after
                    
                    self.log_message(f"✓ 智能标签处理完成")
                    self.log_message(f"  处理前需要处理: {total_need_process} 条")
                    self.log_message(f"  处理后剩余: {total_after} 条")
                    self.log_message(f"  成功处理: {processed_count} 条")
                else:
                    self.log_message("✓ 智能标签处理完成")
            else:
                self.log_message("✗ 智能标签处理失败")
                
        except Exception as e:
            self.log_message(f"✗ 智能标签处理失败: {e}")
    
    def format_tags(self):
        """标签格式化功能"""
        self.log_message("=" * 50)
        self.log_message("开始标签格式化处理...")
        
        try:
            # 确认操作
            result = messagebox.askyesno(
                "确认操作", 
                "标签格式化功能将清理链式标签中的特殊字符和多余空格。\n\n确定要继续吗？"
            )
            if not result:
                self.log_message("操作已取消")
                return
            
            # 先统计需要格式化的标签数量
            data = self.processor.load_data()
            if not data:
                self.log_message("✗ 无法加载数据")
                return
            
            need_format_count = 0
            format_examples = []
            
            for item in data:
                if "标签" in item and isinstance(item["标签"], dict):
                    if "链式标签" in item["标签"]:
                        original_tag = item["标签"]["链式标签"]
                        if original_tag:
                            # 检查是否需要格式化
                            formatted_tag = self.processor._format_single_tag(original_tag)
                            if original_tag != formatted_tag:
                                need_format_count += 1
                                if len(format_examples) < 5:
                                    format_examples.append({
                                        'original': original_tag,
                                        'formatted': formatted_tag
                                    })
            
            self.log_message(f"检测到需要格式化的标签: {need_format_count} 个")
            
            if need_format_count == 0:
                self.log_message("✓ 没有需要格式化的标签")
                return
            
            # 显示格式化示例
            if format_examples:
                self.log_message(f"\n格式化示例:")
                for i, example in enumerate(format_examples, 1):
                    self.log_message(f"  {i}. 原标签: {example['original']}")
                    self.log_message(f"     格式化后: {example['formatted']}")
            
            # 执行标签格式化处理
            success = self.processor._process_format_tags(dry_run=False)
            
            if success:
                self.log_message(f"✓ 标签格式化处理完成")
                self.log_message(f"  格式化标签数量: {need_format_count} 个")
            else:
                self.log_message("✗ 标签格式化处理失败")
                
        except Exception as e:
            self.log_message(f"✗ 标签格式化处理失败: {e}")
    
class TagManagerGUI:
    """标签管理器GUI类"""
    
    def __init__(self, parent_frame, root_window):
        """初始化标签管理器"""
        self.parent_frame = parent_frame
        self.root_window = root_window
        self.json_file_path = "ai_organize_result.json"
        self.tags_data = []
        self.first_level_tags = set()
        
        # 创建界面
        self.create_widgets()
        
        # 加载数据
        self.load_tags_data()
    
    def create_widgets(self):
        """创建界面组件"""
        # 创建左右分栏框架
        content_frame = tb.Frame(self.parent_frame)
        content_frame.pack(fill=BOTH, expand=True)
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # 左侧：标签列表区域
        left_frame = tb.LabelFrame(content_frame, text=t("tag_list", "tag_manager"), padding="10")
        left_frame.grid(row=0, column=0, sticky=(W, E, N, S), padx=(0, 5))
        
        # 左侧顶部：统计信息
        self.stats_label = tb.Label(left_frame, text=t("loading", "tag_manager"), font=('Arial', 10))
        self.stats_label.pack(anchor=W, pady=(0, 10))
        
        # 左侧中间：标签列表
        list_frame = tb.Frame(left_frame)
        list_frame.pack(fill=BOTH, expand=True)
        
        # 创建标签列表（使用Treeview）
        columns = ('标签名称', '使用次数', '选择')
        self.tag_tree = tb.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # 设置列标题和宽度
        column_widths = [200, 80, 60]
        for i, col in enumerate(columns):
            self.tag_tree.heading(col, text=col)
            self.tag_tree.column(col, width=column_widths[i], minwidth=50)
        
        # 添加滚动条
        scrollbar = tb.Scrollbar(list_frame, orient=VERTICAL, command=self.tag_tree.yview)
        self.tag_tree.configure(yscrollcommand=scrollbar.set)
        
        self.tag_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # 绑定点击事件
        self.tag_tree.bind('<Button-1>', self.on_tag_click)
        
        # 左侧底部：操作按钮
        button_frame = tb.Frame(left_frame)
        button_frame.pack(fill=X, pady=(10, 0))
        
        tb.Button(button_frame, text=t("select_all", "tag_manager"), command=self.select_all_tags, bootstyle=INFO).pack(side=LEFT, padx=(0, 5))
        tb.Button(button_frame, text=t("deselect_all", "tag_manager"), command=self.deselect_all_tags, bootstyle=SECONDARY).pack(side=LEFT, padx=(0, 5))
        tb.Button(button_frame, text=t("refresh", "tag_manager"), command=self.refresh_tags, bootstyle=WARNING).pack(side=LEFT)
        
        # 右侧：预览和操作区域
        right_frame = tb.LabelFrame(content_frame, text=t("operation_preview", "tag_manager"), padding="10")
        right_frame.grid(row=0, column=1, sticky=(W, E, N, S), padx=(5, 0))
        
        # 右侧顶部：操作说明
        preview_label = tb.Label(right_frame, text=t("select_tags_to_delete", "tag_manager"), font=('Arial', 10))
        preview_label.pack(anchor=W, pady=(0, 10))
        
        # 右侧中间：预览文本区域
        preview_frame = tb.Frame(right_frame)
        preview_frame.pack(fill=BOTH, expand=True)
        
        self.preview_text = ScrolledText(preview_frame, height=15, width=50)
        self.preview_text.pack(fill=BOTH, expand=True)
        
        # 右侧底部：操作按钮
        action_frame = tb.Frame(right_frame)
        action_frame.pack(fill=X, pady=(10, 0))
        
        tb.Button(action_frame, text=t("preview_deletion", "tag_manager"), command=self.preview_deletion, bootstyle=INFO).pack(side=LEFT, padx=(0, 5))
        tb.Button(action_frame, text=t("execute_deletion", "tag_manager"), command=self.execute_deletion, bootstyle=DANGER).pack(side=LEFT, padx=(0, 5))
        tb.Button(action_frame, text=t("backup_file", "tag_manager"), command=self.backup_file, bootstyle=SUCCESS).pack(side=LEFT)
    
    def load_tags_data(self):
        """加载标签数据"""
        try:
            if not os.path.exists(self.json_file_path):
                messagebox.showerror(t("error", "messages"), t("file_not_exists", "messages", file_path=self.json_file_path))
                return
            
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                self.tags_data = json.load(f)
            
            # 提取一级标签
            self.first_level_tags = set()
            tag_counts = {}
            
            for item in self.tags_data:
                if isinstance(item, dict) and '标签' in item:
                    tags = item['标签']
                    if isinstance(tags, dict) and '链式标签' in tags:
                        chain_tag = tags['链式标签']
                        if isinstance(chain_tag, str):
                            # 处理包含"/"的多级标签
                            if '/' in chain_tag:
                                first_tag = chain_tag.split('/')[0]
                            else:
                                # 处理单级标签
                                first_tag = chain_tag
                            
                            self.first_level_tags.add(first_tag)
                            tag_counts[first_tag] = tag_counts.get(first_tag, 0) + 1
            
            # 更新统计信息
            self.stats_label.config(text=f"共找到 {len(self.first_level_tags)} 个一级标签，{len(self.tags_data)} 条记录")
            
            # 更新标签列表
            self.refresh_tag_list()
            
        except Exception as e:
            messagebox.showerror(t("error", "messages"), t("load_tag_data_failed", "messages", e=str(e)))
    
    def refresh_tag_list(self):
        """刷新标签列表"""
        # 清空现有项目
        for item in self.tag_tree.get_children():
            self.tag_tree.delete(item)
        
        # 重新计算标签使用次数（确保与load_tags_data中的逻辑一致）
        tag_counts = {}
        for item in self.tags_data:
            if isinstance(item, dict) and '标签' in item:
                tags = item['标签']
                if isinstance(tags, dict) and '链式标签' in tags:
                    chain_tag = tags['链式标签']
                    if isinstance(chain_tag, str):
                        # 处理包含"/"的多级标签
                        if '/' in chain_tag:
                            first_tag = chain_tag.split('/')[0]
                        else:
                            # 处理单级标签
                            first_tag = chain_tag
                        
                        tag_counts[first_tag] = tag_counts.get(first_tag, 0) + 1
        
        # 添加标签到列表（使用重新计算的数据）
        inserted_count = 0
        for tag in sorted(tag_counts.keys()):
            count = tag_counts[tag]
            self.tag_tree.insert('', 'end', values=(tag, count, '□'))
            inserted_count += 1
        
        # 更新统计信息以显示实际插入的项目数
        current_text = self.stats_label.cget("text")
        if "个一级标签" in current_text:
            # 更新标签数量信息
            self.stats_label.config(text=f"共找到 {len(tag_counts)} 个一级标签，{len(self.tags_data)} 条记录，界面显示 {inserted_count} 项")
    
    def select_all_tags(self):
        """全选标签"""
        for item in self.tag_tree.get_children():
            values = list(self.tag_tree.item(item)['values'])
            values[2] = '☑'
            self.tag_tree.item(item, values=values)
    
    def deselect_all_tags(self):
        """取消全选标签"""
        for item in self.tag_tree.get_children():
            values = list(self.tag_tree.item(item)['values'])
            values[2] = '□'
            self.tag_tree.item(item, values=values)
    
    def refresh_tags(self):
        """刷新标签数据"""
        self.load_tags_data()
    
    def get_selected_tags(self):
        """获取选中的标签"""
        selected_tags = []
        for item in self.tag_tree.get_children():
            values = self.tag_tree.item(item)['values']
            if values[2] == '☑':
                selected_tags.append(values[0])
        return selected_tags
    
    def on_tag_click(self, event):
        """处理标签点击事件"""
        region = self.tag_tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tag_tree.identify_column(event.x)
            if column == '#3':  # 选择列
                item = self.tag_tree.identify_row(event.y)
                if item:
                    values = list(self.tag_tree.item(item)['values'])
                    # 切换选择状态
                    values[2] = '☑' if values[2] == '□' else '□'
                    self.tag_tree.item(item, values=values)
    
    def preview_deletion(self):
        """预览删除效果"""
        selected_tags = self.get_selected_tags()
        if not selected_tags:
            messagebox.showwarning(t("warning", "messages"), t("please_select_tags_to_delete", "messages"))
            return
        
        self.preview_text.delete(1.0, END)
        preview_content = f"将要删除以下 {len(selected_tags)} 个一级标签：\n\n"
        
        for tag in selected_tags:
            preview_content += f"• {tag}\n"
        
        preview_content += f"\n影响范围：\n"
        
        # 统计影响
        affected_count = 0
        examples = []
        
        for item in self.tags_data:
            if isinstance(item, dict) and '标签' in item:
                tags = item['标签']
                if isinstance(tags, dict) and '链式标签' in tags:
                    chain_tag = tags['链式标签']
                    if isinstance(chain_tag, str):
                        # 处理包含"/"的多级标签
                        if '/' in chain_tag:
                            first_tag = chain_tag.split('/')[0]
                        else:
                            # 处理单级标签
                            first_tag = chain_tag
                        
                        if first_tag in selected_tags:
                            affected_count += 1
                            if len(examples) < 5:  # 只显示前5个例子
                                filename = item.get('文件名', '未知文件')
                                old_tag = chain_tag
                                # 如果是多级标签，删除第一级；如果是单级标签，删除整个标签
                                if '/' in chain_tag:
                                    new_tag = '/'.join(chain_tag.split('/')[1:]) if len(chain_tag.split('/')) > 1 else ''
                                else:
                                    new_tag = ''
                                examples.append(f"  {filename}\n    原标签: {old_tag}\n    新标签: {new_tag}\n")
        
        preview_content += f"将影响 {affected_count} 条记录\n\n"
        preview_content += "示例：\n" + ''.join(examples)
        
        if affected_count > 5:
            preview_content += f"\n... 还有 {affected_count - 5} 条记录\n"
        
        self.preview_text.insert(1.0, preview_content)
    
    def execute_deletion(self):
        """执行删除操作"""
        selected_tags = self.get_selected_tags()
        if not selected_tags:
            messagebox.showwarning(t("warning", "messages"), t("please_select_tags_to_delete", "messages"))
            return
        
        # 确认删除
        result = messagebox.askyesno(
            "确认删除", 
            f"确定要删除选中的 {len(selected_tags)} 个标签吗？\n此操作不可撤销！"
        )
        
        if not result:
            return
        
        try:
            # 执行删除
            modified_count = 0
            
            for item in self.tags_data:
                if isinstance(item, dict) and '标签' in item:
                    tags = item['标签']
                    if isinstance(tags, dict) and '链式标签' in tags:
                        chain_tag = tags['链式标签']
                        if isinstance(chain_tag, str):
                            # 处理包含"/"的多级标签
                            if '/' in chain_tag:
                                first_tag = chain_tag.split('/')[0]
                            else:
                                # 处理单级标签
                                first_tag = chain_tag
                            
                            if first_tag in selected_tags:
                                # 如果是多级标签，删除第一个标签段；如果是单级标签，删除整个标签
                                if '/' in chain_tag:
                                    new_chain_tag = '/'.join(chain_tag.split('/')[1:])
                                else:
                                    new_chain_tag = ''
                                tags['链式标签'] = new_chain_tag
                                modified_count += 1
            
            # 保存文件
            with open(self.json_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.tags_data, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo(t("success", "messages"), t("delete_operation_completed", "messages", count=modified_count))
            
            # 刷新数据
            self.load_tags_data()
            
        except Exception as e:
            messagebox.showerror(t("error", "messages"), t("execute_delete_failed", "messages", e=str(e)))
    
    def backup_file(self):
        """备份原文件"""
        try:
            import shutil
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.json_file_path}.backup_{timestamp}"
            
            shutil.copy2(self.json_file_path, backup_path)
            
            messagebox.showinfo(t("success", "messages"), t("file_backed_up_to", "messages", backup_path=backup_path))
            
        except Exception as e:
            messagebox.showerror(t("error", "messages"), t("backup_failed", "messages", e=str(e)))

class FileOrganizerTabGUI:
    """文件整理器分页图形用户界面类"""
    
    def __init__(self):
        """初始化 GUI 应用"""
        # 初始化配置迁移
        self._initialize_config_migration()
        
        # 初始化语言设置
        self._initialize_language()
        
        self.root = tb.Window(themename="flatly")
        self.root.title(t("title", "app"))
        
        # 响应式窗口大小设置
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 根据屏幕大小设置窗口尺寸
        if screen_width < 1366:  # 小屏幕
            window_width = min(1000, screen_width - 100)
            window_height = min(700, screen_height - 100)
        elif screen_width < 1920:  # 中等屏幕
            window_width = min(1200, screen_width - 100)
            window_height = min(800, screen_height - 100)
        else:  # 大屏幕
            window_width = min(1400, screen_width - 100)
            window_height = min(900, screen_height - 100)
        
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.resizable(True, True)
        
        # 设置最小窗口大小
        self.root.minsize(800, 600)
        
        # 初始化变量
        self.source_directory = tb.StringVar()  # 源目录路径
        self.target_directory = tb.StringVar()  # 目标目录路径
        
        # AI分类参数
        self.summary_length = tb.IntVar(value=200)  # 摘要长度，默认200字符
        self.content_truncate = tb.IntVar(value=2000)  # 内容截取，默认2000字符
        
        # 文件整理器实例
        self.ai_organizer = None
        self.simple_organizer = None
        self.organize_results = None
        
        # 创建界面
        self.create_widgets()
        
        # 居中显示窗口
        self.center_window()
        
        # 初始化文件整理器
        self.initialize_organizers()
    
    def _initialize_config_migration(self):
        """初始化配置迁移"""
        try:
            from tidyfile.utils.app_paths import get_app_paths
            from tidyfile.utils.config_migrator import ConfigMigrator
            
            # 获取应用路径
            app_paths = get_app_paths()
            
            # 创建迁移器
            migrator = ConfigMigrator(app_paths)
            
            # 检查迁移状态
            status = migrator.check_migration_status()
            
            if not status["migration_completed"]:
                # 执行迁移
                print("检测到首次运行，正在迁移配置文件...")
                results = migrator.migrate_all_configs()
                
                # 显示迁移结果
                success_count = sum(1 for success in results.values() if success)
                total_count = len(results)
                
                if success_count == total_count:
                    print(f"配置迁移完成，共迁移 {success_count} 项配置")
                else:
                    print(f"配置迁移部分完成，成功 {success_count}/{total_count} 项")
                    for name, success in results.items():
                        if not success:
                            print(f"  - {name}: 迁移失败")
            else:
                print("配置迁移已完成，跳过迁移步骤")
                
        except ImportError as e:
            print(f"配置迁移模块导入失败: {e}")
        except Exception as e:
            print(f"配置迁移初始化失败: {e}")
    
    def _initialize_language(self):
        """初始化语言设置"""
        if not I18N_AVAILABLE:
            print("国际化模块未加载，使用默认语言")
            return
        
        try:
            from tidyfile.utils.app_paths import get_app_paths
            app_paths = get_app_paths()
            settings_file = app_paths.app_settings_file
            
            if settings_file.exists():
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                saved_language = settings.get("general", {}).get("language")
                if saved_language:
                    i18n_manager = get_i18n_manager()
                    if i18n_manager.set_language(saved_language):
                        print(f"加载保存的语言设置: {saved_language}")
                    else:
                        print(f"保存的语言设置无效: {saved_language}")
                else:
                    # 检测系统语言
                    i18n_manager = get_i18n_manager()
                    system_language = i18n_manager.detect_system_language()
                    if system_language != i18n_manager.current_language:
                        i18n_manager.set_language(system_language)
                        print(f"检测到系统语言: {system_language}")
            else:
                # 首次运行，检测系统语言
                i18n_manager = get_i18n_manager()
                system_language = i18n_manager.detect_system_language()
                if system_language != i18n_manager.current_language:
                    i18n_manager.set_language(system_language)
                    print(f"首次运行，检测到系统语言: {system_language}")
                    
        except Exception as e:
            print(f"语言初始化失败: {e}")
    
    def center_window(self):
        """将窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_responsive_window(self, window, default_width, default_height, min_width=400, min_height=300):
        """设置响应式窗口大小"""
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        
        if screen_width < 1366:  # 小屏幕
            window_width = min(default_width - 100, screen_width - 100)
            window_height = min(default_height - 100, screen_height - 100)
        elif screen_width < 1920:  # 中等屏幕
            window_width = min(default_width, screen_width - 100)
            window_height = min(default_height, screen_height - 100)
        else:  # 大屏幕
            window_width = min(default_width + 100, screen_width - 100)
            window_height = min(default_height + 100, screen_height - 100)
        
        window.geometry(f"{window_width}x{window_height}")
        window.minsize(min_width, min_height)
        
        # 居中显示
        window.update_idletasks()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
    def initialize_organizers(self):
        """初始化文件整理器"""
        try:
            # 使用新的智能文件分类器
            from tidyfile.core.smart_file_classifier_adapter import SmartFileClassifierAdapter
            self.ai_organizer = SmartFileClassifierAdapter(model_name=None, enable_transfer_log=True)
            self.log_message(t("ai_classifier_init_complete", "app"))
            
            self.log_message(t("file_organizer_init_complete", "app"))
        except Exception as e:
            self.log_message(f"文件整理器初始化失败: {e}")
            messagebox.showerror(t("error", "messages"), t("file_organizer_init_failed", "messages", e=str(e)))
        
    def create_widgets(self):
        """创建界面组件"""
        # 创建主框架
        main_frame = tb.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky=(W, E, N, S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)  # 给日志区域更多空间
        
        # 标题
        title_label = tb.Label(
            main_frame, 
            text=t("title", "app"), 
            font=('Arial', 14, 'bold')
        )
        title_label.grid(row=0, column=0, pady=(0, 10))
        
        # 注册标题组件用于动态更新
        register_widget(title_label, "title", "app")
        register_window_title(self.root, "title", "app")
        
        # 创建分页控件
        self.notebook = tb.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky=(W, E, N, S))
        
        # 创建文件解读页面
        self.create_file_reader_tab()
        
        # 创建微信信息管理页面
        try:
            from tidyfile.gui.weixin_manager_gui import WeixinManagerTab
            self.weixin_manager_tab = WeixinManagerTab(self.notebook, log_callback=self.log_message)
        except Exception as e:
            print(f"微信信息管理模块加载失败: {e}")
        
        # 创建文章阅读助手页面
        self.create_article_reader_tab()
        
        # 创建智能分类页面
        self.create_ai_classification_tab()
        
        # 创建工具页面
        self.create_tools_tab()
        
        # 注册标签页标题用于动态更新
        register_tab_title(self.notebook, "file_reader", "file_reader", "app")
        register_tab_title(self.notebook, "article_reader", "article_reader", "app")
        register_tab_title(self.notebook, "ai_classifier", "ai_classifier", "app")
        register_tab_title(self.notebook, "tools", "tools", "app")
        register_tab_title(self.notebook, "weixin_manager", "weixin_manager", "app")
        
        # 日志显示区域
        log_frame = tb.LabelFrame(main_frame, text=t("operation_log", "app"), padding="5")
        log_frame.grid(row=2, column=0, sticky=(W, E, N, S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 日志控制按钮框架
        log_control_frame = tb.Frame(log_frame)
        log_control_frame.grid(row=0, column=0, sticky=(W, E), pady=(0, 5))
        log_control_frame.columnconfigure(1, weight=1)
        
        # 清空日志按钮
        tb.Button(
            log_control_frame,
            text=t("clear_log", "app"),
            command=self.clear_log,
            style='secondary.TButton',
            width=10
        ).grid(row=0, column=0, padx=(0, 10))
        
        # 日志级别选择
        tb.Label(log_control_frame, text=t("log_level", "app"), font=('Arial', 9)).grid(row=0, column=1, sticky=W, padx=(0, 5))
        self.log_level_var = tb.StringVar(value="INFO")
        log_level_combo = tb.Combobox(
            log_control_frame,
            textvariable=self.log_level_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            state="readonly",
            width=10
        )
        log_level_combo.grid(row=0, column=2, padx=(0, 10))
        
        # 日志文本框
        self.log_text = ScrolledText(
            log_frame,
            height=12,  # 增加高度
            wrap=WORD,
            font=('Consolas', 9)
        )
        self.log_text.grid(row=1, column=0, sticky=(W, E, N, S))
        
        # 配置主框架的行权重 - 给日志区域更多空间
        main_frame.rowconfigure(2, weight=1)
        
        # 初始化日志
        self.log_message(t("startup_message", "app"))
        
    def create_file_reader_tab(self):
        """创建文件解读页面"""
        reader_frame = tb.Frame(self.notebook, padding="5")
        self.notebook.add(reader_frame, text=t("file_reader", "app"))
        
        reader_frame.columnconfigure(1, weight=1)
        
        # 说明文字
        desc_label = tb.Label(
            reader_frame,
            text=t("description", "file_reader"),
            font=('Arial', 9)
        )
        desc_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        register_widget(desc_label, "description", "file_reader")
        
        # 文件夹选择
        folder_label = tb.Label(reader_frame, text=t("select_folder", "file_reader"), font=('Arial', 9))
        folder_label.grid(row=1, column=0, sticky=W, pady=3)
        register_widget(folder_label, "select_folder", "file_reader")
        self.reader_folder_var = tb.StringVar()
        tb.Entry(
            reader_frame, 
            textvariable=self.reader_folder_var, 
            width=40
        ).grid(row=1, column=1, sticky=(W, E), padx=(5, 5), pady=3)
        
        def select_reader_folder():
            directory = filedialog.askdirectory(title="选择要批量解读的文件夹")
            if directory:
                self.reader_folder_var.set(directory)
                self.log_message(f"选择文件解读目录: {directory}")
                
                # 扫描文件夹并显示文件数量
                try:
                    from pathlib import Path
                    folder_path = Path(directory)
                    supported_extensions = {'.txt', '.pdf', '.docx', '.doc', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv'}
                    document_files = []
                    for file_path in folder_path.rglob('*'):
                        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                            document_files.append(file_path)
                    file_count = len(document_files)
                    self.log_message(f"扫描到 {file_count} 个可解读文件")
                    self.reader_status_label.config(text=f"已选择文件夹，发现 {file_count} 个可解读文档")
                    self.log_message(f"已选择解读文件夹: {directory}，发现 {file_count} 个可解读文档")
                except Exception as e:
                    self.reader_status_label.config(text=t("folder_scan_failed", "article_reader"))
                    self.log_message(f"扫描文件夹失败: {e}")
        
        browse_btn = tb.Button(
            reader_frame, 
            text=t("browse", "file_reader"), 
            command=select_reader_folder,
            style='secondary.TButton'
        )
        browse_btn.grid(row=1, column=2, pady=3)
        register_widget(browse_btn, "browse", "file_reader")
        
        # 摘要参数设置
        params_frame = tb.LabelFrame(reader_frame, text=t("summary_params", "file_reader"), padding="5")
        params_frame.grid(row=2, column=0, columnspan=3, sticky=(W, E), pady=5)
        register_widget(params_frame, "summary_params", "file_reader")
        params_frame.columnconfigure(1, weight=1)
        
        # 摘要长度调节
        summary_length_label = tb.Label(params_frame, text=t("summary_length", "file_reader"), font=('Arial', 9))
        summary_length_label.grid(row=0, column=0, sticky=W, pady=3)
        register_widget(summary_length_label, "summary_length", "file_reader")
        summary_frame = tb.Frame(params_frame)
        summary_frame.grid(row=0, column=1, sticky=(W, E), padx=(5, 0), pady=3)
        summary_frame.columnconfigure(1, weight=1)
        
        self.reader_summary_length = tb.IntVar(value=200)
        
        min_label = tb.Label(summary_frame, text=t("characters_100", "file_reader"), font=('Arial', 8))
        min_label.grid(row=0, column=0)
        register_widget(min_label, "characters_100", "file_reader")
        
        reader_summary_scale = tb.Scale(
            summary_frame, 
            from_=100, 
            to=500, 
            variable=self.reader_summary_length,
            orient=HORIZONTAL
        )
        reader_summary_scale.grid(row=0, column=1, sticky=(W, E), padx=3)
        
        max_label = tb.Label(summary_frame, text=t("characters_500", "file_reader"), font=('Arial', 8))
        max_label.grid(row=0, column=2)
        register_widget(max_label, "characters_500", "file_reader")
        
        self.reader_summary_value_label = tb.Label(summary_frame, text=t("characters_200", "file_reader"), font=('Arial', 8))
        self.reader_summary_value_label.grid(row=0, column=3, padx=(5, 0))
        register_widget(self.reader_summary_value_label, "characters_200", "file_reader")
        
        # 绑定摘要长度变化事件
        def update_reader_summary_label(*args):
            value = self.reader_summary_length.get()
            self.reader_summary_value_label.config(text=f"{int(value)}{t('characters', 'file_organizer')}")
        
        self.reader_summary_length.trace_add('write', update_reader_summary_label)
        
        # 操作按钮
        button_frame = tb.Frame(reader_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=10)
        
        def start_batch_reading():
            folder_path = self.reader_folder_var.get().strip()
            if not folder_path:
                messagebox.showwarning(t("info", "messages"), t("please_select_folder_to_read", "messages"))
                self.log_message("文件解读失败：未选择文件夹", "WARNING")
                return
            
            if not os.path.exists(folder_path):
                messagebox.showerror(t("error", "messages"), t("selected_folder_not_exists", "messages"))
                self.log_message(f"文件解读失败：文件夹不存在 - {folder_path}", "ERROR")
                return
            
            self.log_message(f"开始批量文件解读，目录: {folder_path}")
            self.log_message(f"摘要长度设置: {self.reader_summary_length.get()} 字符")
            self.reader_status_label.config(text=t("reading_documents", "file_reader"))
            self.reader_start_button.config(state='disabled')
            
            # 在新线程中执行批量解读
            threading.Thread(target=self._batch_read_worker, args=(folder_path,), daemon=True).start()
        
        self.reader_start_button = tb.Button(
            button_frame,
            text=t("start_batch_reading", "file_reader"),
            command=start_batch_reading,
            bootstyle=SUCCESS
        )
        self.reader_start_button.pack(side=LEFT, padx=3)
        register_widget(self.reader_start_button, "start_batch_reading", "file_reader")
        
        # 进度条
        self.reader_progress_var = tb.DoubleVar()
        self.reader_progress_bar = tb.Progressbar(
            reader_frame,
            variable=self.reader_progress_var,
            maximum=100
        )
        self.reader_progress_bar.grid(row=4, column=0, columnspan=3, sticky=(W, E), pady=5)
        
        # 状态标签
        self.reader_status_label = tb.Label(reader_frame, text=t("please_select_folder", "file_reader"), font=('Arial', 9))
        self.reader_status_label.grid(row=5, column=0, columnspan=3, pady=3)
        register_widget(self.reader_status_label, "please_select_folder", "file_reader")
        
    def create_article_reader_tab(self):
        """创建文章阅读助手页面"""
        article_frame = tb.Frame(self.notebook, padding="5")
        self.notebook.add(article_frame, text=t("article_reader", "app"))
        
        # 说明文字
        desc_label = tb.Label(
            article_frame,
            text=t("description", "article_reader"),
            font=('Arial', 9)
        )
        desc_label.pack(pady=(0, 10))
        register_widget(desc_label, "description", "article_reader")
        
        # 功能说明
        features_frame = tb.LabelFrame(article_frame, text=t("features", "article_reader"), padding="5")
        features_frame.pack(fill=X, pady=(0, 10))
        register_widget(features_frame, "features", "article_reader")
        
        features_text = [
            t("feature_view_results", "article_reader"),
            t("feature_open_files", "article_reader"),
            t("feature_refresh_records", "article_reader"),
            t("feature_web_interface", "article_reader")
        ]
        
        for i, feature in enumerate(features_text):
            feature_label = tb.Label(features_frame, text=feature, font=('Arial', 8))
            feature_label.pack(anchor=W, pady=1)
            # 注册每个功能特性标签
            if i == 0:
                register_widget(feature_label, "feature_view_results", "article_reader")
            elif i == 1:
                register_widget(feature_label, "feature_open_files", "article_reader")
            elif i == 2:
                register_widget(feature_label, "feature_refresh_records", "article_reader")
            elif i == 3:
                register_widget(feature_label, "feature_web_interface", "article_reader")
        
        # 操作按钮
        button_frame = tb.Frame(article_frame)
        button_frame.pack(pady=10)
        
        def start_article_reader():
            try:
                import subprocess
                import socket
                
                self.log_message(t("server_starting", "article_reader"))
                
                # 检查是否已经有服务器在运行
                def check_port(port):
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.settimeout(1)
                            result = s.connect_ex(('localhost', port))
                            return result == 0
                    except:
                        return False
                
                # 检查80和8000端口
                if check_port(80) or check_port(8000):
                    # 获取本机IP地址
                    try:
                        import socket
                        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        s.connect(("8.8.8.8", 80))
                        local_ip = s.getsockname()[0]
                        s.close()
                        lan_url = f"http://{local_ip}/viewer.html"
                    except:
                        lan_url = "http://[本机IP]/viewer.html"
                    
                    self.log_message(f"{t('server_detected', 'article_reader')}:\n本机: http://localhost/viewer.html\n局域网: {lan_url}")
                    
                    # 创建可复制的链接对话框
                    self._show_article_reader_urls("http://localhost/viewer.html", lan_url, t("server_running", "article_reader"))
                    return
                
                # 直接调用VBS脚本启动服务器
                vbs_script = "启动文章阅读助手_增强版.vbs"
                if os.path.exists(vbs_script):
                    subprocess.Popen(["cscript", "//nologo", vbs_script], 
                                   cwd=os.getcwd(), 
                                   creationflags=subprocess.CREATE_NO_WINDOW)
                    
                    self.log_message(t("server_started", "article_reader"))
                    
                    # 获取本机IP地址并显示URL对话框
                    try:
                        import socket
                        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        s.connect(("8.8.8.8", 80))
                        local_ip = s.getsockname()[0]
                        s.close()
                        lan_url = f"http://{local_ip}/viewer.html"
                    except:
                        lan_url = "http://[本机IP]/viewer.html"
                    
                    # 显示URL对话框
                    self._show_article_reader_urls("http://localhost/viewer.html", lan_url, t("startup_success", "article_reader"))
                else:
                    messagebox.showerror(t("error", "messages"), t("startup_script_not_found", "messages", script=vbs_script))
                
            except Exception as e:
                self.log_message(f"启动文章阅读助手失败: {e}")
                messagebox.showerror(t("error", "messages"), t("start_article_reader_failed", "messages", e=str(e)))
        
        start_btn = tb.Button(
            button_frame,
            text=t("start_article_reader", "article_reader"),
            command=start_article_reader,
            bootstyle=SUCCESS
        )
        start_btn.pack()
        register_widget(start_btn, "start_article_reader", "article_reader")
        
        # 状态信息
        status_frame = tb.LabelFrame(article_frame, text=t("usage_instructions", "article_reader"), padding="10")
        status_frame.pack(fill=X, pady=(20, 0))
        register_widget(status_frame, "usage_instructions", "article_reader")
        
        instructions = [
            t("instruction_1", "article_reader"),
            t("instruction_2", "article_reader"),
            t("instruction_3", "article_reader"),
            t("instruction_4", "article_reader"),
            t("instruction_5", "article_reader")
        ]
        
        instruction_labels = []
        for i, instruction in enumerate(instructions):
            label = tb.Label(status_frame, text=instruction, font=('Arial', 9))
            label.pack(anchor=W, pady=2)
            instruction_labels.append(label)
            # 注册每个说明标签用于动态更新
            register_widget(label, f"instruction_{i+1}", "article_reader")
    
    def _show_article_reader_urls(self, local_url, lan_url, status):
        """显示文章阅读助手URL对话框"""
        # 创建自定义对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("文章阅读助手 - " + status)
        dialog.geometry("600x450")
        dialog.resizable(True, True)
        dialog.minsize(500, 350)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (dialog.winfo_screenheight() // 2) - (450 // 2)
        dialog.geometry(f"600x450+{x}+{y}")
        
        # 主框架
        main_frame = tb.Frame(dialog, padding="20")
        main_frame.pack(fill=BOTH, expand=True)
        
        # 配置主框架的网格权重
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)  # 让说明文字区域可以扩展
        
        # 标题
        title_label = tb.Label(main_frame, text=t("article_reader_started", "article_reader"), font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 20), sticky=W)
        
        # 链接框架
        links_frame = tb.Frame(main_frame)
        links_frame.grid(row=1, column=0, sticky=EW, pady=(0, 20))
        links_frame.columnconfigure(0, weight=1)
        
        # 本机访问
        local_frame = tb.LabelFrame(links_frame, text=t("local_access", "article_reader"), padding="10")
        local_frame.grid(row=0, column=0, sticky=EW, pady=(0, 10))
        local_frame.columnconfigure(0, weight=1)
        
        local_entry = tb.Entry(local_frame, font=('Arial', 11), width=60)
        local_entry.grid(row=0, column=0, sticky=EW, padx=(0, 10))
        local_entry.insert(0, local_url)
        local_entry.config(state='readonly')
        
        def copy_local():
            dialog.clipboard_clear()
            dialog.clipboard_append(local_url)
            dialog.update()
            # 显示复制成功提示
            copy_btn.config(text=t("copied", "article_reader"))
            dialog.after(1000, lambda: copy_btn.config(text=t("copy", "article_reader")))
        
        copy_btn = tb.Button(local_frame, text=t("copy", "article_reader"), command=copy_local, bootstyle=INFO)
        copy_btn.grid(row=0, column=1)
        
        # 局域网访问
        lan_frame = tb.LabelFrame(links_frame, text=t("lan_access", "article_reader"), padding="10")
        lan_frame.grid(row=1, column=0, sticky=EW, pady=(0, 10))
        lan_frame.columnconfigure(0, weight=1)
        
        lan_entry = tb.Entry(lan_frame, font=('Arial', 11), width=60)
        lan_entry.grid(row=0, column=0, sticky=EW, padx=(0, 10))
        lan_entry.insert(0, lan_url)
        lan_entry.config(state='readonly')
        
        def copy_lan():
            dialog.clipboard_clear()
            dialog.clipboard_append(lan_url)
            dialog.update()
            # 显示复制成功提示
            copy_lan_btn.config(text=t("copied", "article_reader"))
            dialog.after(1000, lambda: copy_lan_btn.config(text=t("copy", "article_reader")))
        
        copy_lan_btn = tb.Button(lan_frame, text=t("copy", "article_reader"), command=copy_lan, bootstyle=INFO)
        copy_lan_btn.grid(row=0, column=1)
        
        # 说明文字框架（可滚动）
        info_frame = tb.LabelFrame(main_frame, text=t("usage_instructions", "article_reader"), padding="10")
        info_frame.grid(row=2, column=0, sticky=NSEW, pady=(0, 20))
        info_frame.columnconfigure(0, weight=1)
        info_frame.rowconfigure(0, weight=1)
        
        # 创建文本框用于显示说明文字
        info_text = tk.Text(info_frame, font=('Arial', 10), wrap=tk.WORD, height=8, 
                           relief=tk.FLAT, fg='black')
        info_text.grid(row=0, column=0, sticky=NSEW)
        
        # 添加滚动条
        scrollbar = tk.Scrollbar(info_frame, orient=tk.VERTICAL, command=info_text.yview)
        scrollbar.grid(row=0, column=1, sticky=NS)
        info_text.config(yscrollcommand=scrollbar.set)
        
        # 插入说明文字
        instructions = [
            "📋 使用说明：",
            "",
            "• 点击复制按钮可复制链接到剪贴板",
            "• 在浏览器中粘贴链接即可访问",
            "• 局域网内其他设备可通过局域网链接访问",
            "• 关闭浏览器时服务器会自动停止",
            "",
            "🔧 功能特性：",
            "",
            "• 查看AI分析结果和文件摘要",
            "• 直接打开文件进行查看",
            "• 重复解读后点击刷新删除重复记录",
            "• 友好的Web界面，支持搜索和筛选",
            "",
            "💡 提示：",
            "",
            "• 如果本机访问失败，请尝试局域网访问",
            "• 确保防火墙允许程序访问网络",
            "• 服务器启动后会自动打开浏览器"
        ]
        
        for instruction in instructions:
            info_text.insert(tk.END, instruction + "\n")
        
        info_text.config(state=tk.DISABLED)  # 设置为只读
        
        # 按钮框架
        button_frame = tb.Frame(main_frame)
        button_frame.grid(row=3, column=0, pady=(0, 10))
        
        def open_local():
            import webbrowser
            webbrowser.open(local_url)
        
        def open_lan():
            import webbrowser
            webbrowser.open(lan_url)
        
        def close_dialog():
            dialog.destroy()
        
        tb.Button(button_frame, text=t("open_local", "article_reader"), command=open_local, bootstyle=SUCCESS).pack(side=LEFT, padx=(0, 10))
        tb.Button(button_frame, text=t("open_lan", "article_reader"), command=open_lan, bootstyle=WARNING).pack(side=LEFT, padx=(0, 10))
        tb.Button(button_frame, text=t("close", "article_reader"), command=close_dialog, bootstyle=SECONDARY).pack(side=LEFT)
        
    def create_ai_classification_tab(self):
        """创建智能分类页面"""
        ai_frame = tb.Frame(self.notebook, padding="5")
        self.notebook.add(ai_frame, text=t("ai_classifier", "app"))
        
        ai_frame.columnconfigure(1, weight=1)
        
        # 说明文字
        desc_label = tb.Label(
            ai_frame,
            text=t("description", "ai_classifier"),
            font=('Arial', 9)
        )
        desc_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        register_widget(desc_label, "description", "ai_classifier")
        
        # 源目录选择
        source_label = tb.Label(ai_frame, text=t("source_directory", "ai_classifier"), font=('Arial', 9))
        source_label.grid(row=1, column=0, sticky=W, pady=3)
        register_widget(source_label, "source_directory", "ai_classifier")
        tb.Entry(
            ai_frame, 
            textvariable=self.source_directory, 
            width=40
        ).grid(row=1, column=1, sticky=(W, E), padx=(5, 5), pady=3)
        source_browse_btn = tb.Button(
            ai_frame, 
            text=t("browse", "ai_classifier"), 
            command=self.select_source_directory,
            style='secondary.TButton'
        )
        source_browse_btn.grid(row=1, column=2, pady=3)
        register_widget(source_browse_btn, "browse", "ai_classifier")
        
        # 目标目录选择
        target_label = tb.Label(ai_frame, text=t("target_directory", "ai_classifier"), font=('Arial', 9))
        target_label.grid(row=2, column=0, sticky=W, pady=3)
        register_widget(target_label, "target_directory", "ai_classifier")
        tb.Entry(
            ai_frame, 
            textvariable=self.target_directory, 
            width=40
        ).grid(row=2, column=1, sticky=(W, E), padx=(5, 5), pady=3)
        target_browse_btn = tb.Button(
            ai_frame, 
            text=t("browse", "ai_classifier"), 
            command=self.select_target_directory,
            style='secondary.TButton'
        )
        target_browse_btn.grid(row=2, column=2, pady=3)
        register_widget(target_browse_btn, "browse", "ai_classifier")
        
        # AI参数调节区域
        params_frame = tb.LabelFrame(ai_frame, text=t("ai_params", "ai_classifier"), padding="5")
        params_frame.grid(row=3, column=0, columnspan=3, sticky=(W, E), pady=5)
        register_widget(params_frame, "ai_params", "ai_classifier")
        params_frame.columnconfigure(1, weight=1)
        
        # 摘要长度调节
        summary_length_label = tb.Label(params_frame, text=t("summary_length", "ai_classifier"), font=('Arial', 9))
        summary_length_label.grid(row=0, column=0, sticky=W, pady=3)
        register_widget(summary_length_label, "summary_length", "ai_classifier")
        summary_frame = tb.Frame(params_frame)
        summary_frame.grid(row=0, column=1, sticky=(W, E), padx=(5, 0), pady=3)
        summary_frame.columnconfigure(1, weight=1)
        
        tb.Label(summary_frame, text="100", font=('Arial', 8)).grid(row=0, column=0)
        self.summary_scale = tb.Scale(
            summary_frame, 
            from_=100, 
            to=500, 
            variable=self.summary_length,
            orient=HORIZONTAL
        )
        self.summary_scale.grid(row=0, column=1, sticky=(W, E), padx=3)
        tb.Label(summary_frame, text="500", font=('Arial', 8)).grid(row=0, column=2)
        self.summary_value_label = tb.Label(summary_frame, text="200" + t("characters", "ai_classifier"), font=('Arial', 8))
        self.summary_value_label.grid(row=0, column=3, padx=(5, 0))
        
        # 绑定摘要长度变化事件
        self.summary_length.trace_add('write', self.update_summary_label)
        
        # 字符截取调节
        content_truncate_label = tb.Label(params_frame, text=t("content_truncate", "ai_classifier"), font=('Arial', 9))
        content_truncate_label.grid(row=1, column=0, sticky=W, pady=3)
        register_widget(content_truncate_label, "content_truncate", "ai_classifier")
        truncate_frame = tb.Frame(params_frame)
        truncate_frame.grid(row=1, column=1, sticky=(W, E), padx=(5, 0), pady=3)
        truncate_frame.columnconfigure(1, weight=1)
        
        tb.Label(truncate_frame, text="1000", font=('Arial', 8)).grid(row=0, column=0)
        self.truncate_scale = tb.Scale(
            truncate_frame, 
            from_=1000, 
            to=5000, 
            variable=self.content_truncate,
            orient=HORIZONTAL
        )
        self.truncate_scale.grid(row=0, column=1, sticky=(W, E), padx=3)
        tb.Label(truncate_frame, text="5000", font=('Arial', 8)).grid(row=0, column=2)
        self.truncate_value_label = tb.Label(truncate_frame, text="2000" + t("characters", "ai_classifier"), font=('Arial', 8))
        self.truncate_value_label.grid(row=0, column=3, padx=(5, 0))
        
        # 绑定字符截取变化事件
        self.content_truncate.trace_add('write', self.update_truncate_label)
        
        # 操作按钮框架
        ai_button_frame = tb.Frame(ai_frame)
        ai_button_frame.grid(row=4, column=0, columnspan=3, pady=10)
        

        
        # 开始整理按钮
        self.ai_organize_button = tb.Button(
            ai_button_frame,
            text=t("start_ai_organize", "ai_classifier"),
            command=self.ai_start_organize
        )
        self.ai_organize_button.pack(side=LEFT, padx=5)
        register_widget(self.ai_organize_button, "start_ai_organize", "ai_classifier")
        
        # 进度条
        self.ai_progress_var = tb.DoubleVar()
        self.ai_progress_bar = tb.Progressbar(
            ai_frame,
            variable=self.ai_progress_var,
            maximum=100
        )
        self.ai_progress_bar.grid(row=5, column=0, columnspan=3, sticky=(W, E), pady=10)
        
        # 状态标签
        self.ai_status_label = tb.Label(ai_frame, text=t("please_select_directories", "ai_classifier"))
        self.ai_status_label.grid(row=6, column=0, columnspan=3, pady=5)
        register_widget(self.ai_status_label, "please_select_directories", "ai_classifier")
        
    # 文件分类页面已删除
        
    def create_tools_tab(self):
        """创建工具页面"""
        tools_frame = tb.Frame(self.notebook, padding="10")
        self.notebook.add(tools_frame, text=t("tools", "app"))
        
        # 标题
        title_label = tb.Label(tools_frame, text=t("title", "tools"), font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        register_widget(title_label, "title", "tools")
        
        # 工具按钮框架 - 使用垂直布局
        tools_button_frame = tb.Frame(tools_frame)
        tools_button_frame.pack(fill=X, padx=20)
        
        # 工具配置 - 按要求的顺序排列
        tools_config = [
            {
                "name": t("language_settings", "tools"),
                "command": self.show_language_settings,
                "style": "info.TButton",
                "description": t("language_settings_desc", "tools")
            },
            {
                "name": t("duplicate_remover", "tools"),
                "command": self.show_duplicate_removal_dialog,
                "style": "warning.TButton",
                "description": t("duplicate_remover_desc", "tools")
            },
            {
                "name": t("classification_rules", "tools"),
                "command": self.show_classification_rules_manager,
                "style": "info.TButton",
                "description": t("classification_rules_desc", "tools")
            },
            {
                "name": t("ai_model_config", "tools"),
                "command": self.show_ai_model_config,
                "style": "info.TButton",
                "description": t("ai_model_config_desc", "tools")
            },
            {
                "name": t("tag_manager", "tools"),
                "command": self.show_tag_manager,
                "style": "info.TButton",
                "description": t("tag_manager_desc", "tools")
            },
            {
                "name": t("tag_optimizer", "tools"),
                "command": self.show_tag_optimizer,
                "style": "success.TButton",
                "description": t("tag_optimizer_desc", "tools")
            },
            {
                "name": t("multi_task_reader", "tools"),
                "command": self.show_multi_task_file_reader,
                "style": "info.TButton",
                "description": t("multi_task_reader_desc", "tools")
            },
            {
                "name": t("multi_process_reader", "tools"),
                "command": self.show_multi_process_file_reader,
                "style": "info.TButton",
                "description": t("multi_process_reader_desc", "tools")
            },
            {
                "name": t("transfer_logs", "tools"),
                "command": self.show_transfer_logs,
                "style": "secondary.TButton",
                "description": t("transfer_logs_desc", "tools")
            }
        ]
        
        # 创建工具按钮和描述
        for i, tool in enumerate(tools_config):
            # 工具行框架
            tool_row = tb.Frame(tools_button_frame)
            tool_row.pack(fill=X, pady=8)
            
            # 按钮
            button = tb.Button(
                tool_row,
                text=tool["name"],
                command=tool["command"],
                style=tool["style"],
                width=15
            )
            button.pack(side=LEFT, padx=(0, 15))
            
            # 描述标签
            desc_label = tb.Label(
                tool_row,
                text=tool["description"],
                font=("Arial", 10),
                foreground="gray",
                anchor=W
            )
            desc_label.pack(side=LEFT, fill=X, expand=True)
            
            # 注册描述标签用于动态更新
            if tool["name"] == t("language_settings", "tools"):
                register_widget(desc_label, "language_settings_desc", "tools")
            elif tool["name"] == t("duplicate_remover", "tools"):
                register_widget(desc_label, "duplicate_remover_desc", "tools")
            elif tool["name"] == t("classification_rules", "tools"):
                register_widget(desc_label, "classification_rules_desc", "tools")
            elif tool["name"] == t("ai_model_config", "tools"):
                register_widget(desc_label, "ai_model_config_desc", "tools")
            elif tool["name"] == t("tag_manager", "tools"):
                register_widget(desc_label, "tag_manager_desc", "tools")
            elif tool["name"] == t("tag_optimizer", "tools"):
                register_widget(desc_label, "tag_optimizer_desc", "tools")
            elif tool["name"] == t("multi_task_reader", "tools"):
                register_widget(desc_label, "multi_task_reader_desc", "tools")
            elif tool["name"] == t("multi_process_reader", "tools"):
                register_widget(desc_label, "multi_process_reader_desc", "tools")
            elif tool["name"] == t("transfer_logs", "tools"):
                register_widget(desc_label, "transfer_logs_desc", "tools")
            
            # 保存按钮引用（如果需要）
            if tool["name"] == "删除重复文件":
                self.duplicate_button = button
            elif tool["name"] == "分类规则管理":
                self.classification_rules_button = button
            elif tool["name"] == "AI模型配置":
                self.ai_model_config_button = button
            elif tool["name"] == "标签管理":
                self.tag_manager_button = button
            elif tool["name"] == "标签优化":
                self.tag_optimizer_button = button
            elif tool["name"] == "多任务文件解读":
                self.multi_task_file_reader_button = button
            elif tool["name"] == "高并发文件解读":
                self.multi_process_file_reader_button = button
            elif tool["name"] == "日志":
                self.log_button = button
        
        # 文件目录智能整理功能暂时隐藏，保留代码
        # self.directory_organize_button = tb.Button(
        #     tools_button_frame,
        #     text="文件目录智能整理",
        #     command=self.show_directory_organize_dialog,
        #     style='info.TButton'
        # )
        # self.directory_organize_button.pack(pady=5)
        
    def update_summary_label(self, *args):
        """更新摘要长度标签"""
        value = self.summary_length.get()
        self.summary_value_label.config(text=f"{value}字符")
        
    def update_truncate_label(self, *args):
        """更新字符截取标签"""
        value = self.content_truncate.get()
        if value >= 2000:
            self.truncate_value_label.config(text=t("full_text", "ai_classifier"))
        else:
            self.truncate_value_label.config(text=f"{value}{t('characters', 'ai_classifier')}")
        
    def select_source_directory(self):
        """选择源目录"""
        directory = filedialog.askdirectory(title="选择待整理的文件目录")
        if directory:
            self.source_directory.set(directory)
            self.log_message(f"已选择源目录: {directory}")
            
    def select_target_directory(self):
        """选择目标目录"""
        directory = filedialog.askdirectory(title="选择目标分类目录")
        if directory:
            self.target_directory.set(directory)
            self.log_message(f"已选择目标目录: {directory}")
            
    def log_message(self, message, level="INFO"):
        """记录日志消息"""
        # 检查日志级别
        current_level = self.log_level_var.get()
        level_order = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
        
        if level_order.get(level, 1) < level_order.get(current_level, 1):
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        # 在主线程中更新UI
        self.root.after(0, lambda: self._append_log_message(log_entry))
    
    def _append_log_message(self, log_entry):
        """在主线程中追加日志消息"""
        try:
            self.log_text.insert(END, log_entry)
            self.log_text.see(END)
            
            # 限制日志行数，避免内存占用过大
            lines = self.log_text.get(1.0, END).split('\n')
            if len(lines) > 1000:  # 保留最近1000行
                self.log_text.delete(1.0, f"{len(lines) - 500}.0")
        except:
            pass
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, END)
        self.log_message("日志已清空")
        

            

            
    def _batch_read_worker(self, folder_path):
        """批量解读工作线程"""
        try:
            self.log_message("初始化文件解读器...")
            
            # 初始化AI文件整理器
            if not self.ai_organizer:
                self.initialize_organizers()
            
            # 定义进度回调函数
            def progress_callback(current, total, filename):
                progress = (current / total) * 100 if total > 0 else 0
                self.root.after(0, lambda: self.reader_progress_var.set(progress))
                self.root.after(0, lambda: self.reader_status_label.config(text=f"正在解读 ({current}/{total}): {filename}"))
                # 每处理10个文件记录一次日志
                if current % 10 == 0 or current == total:
                    self.log_message(f"处理进度: {current}/{total} ({progress:.1f}%) - 当前文件: {filename}")
            
            # 直接使用FileReader进行批量文档解读
            from tidyfile.core.file_reader import FileReader
            
            # 初始化文件解读器
            file_reader = FileReader()
            file_reader.summary_length = self.reader_summary_length.get()
            
            # 扫描文件夹中的文件
            from pathlib import Path
            folder_path_obj = Path(folder_path)
            
            self.log_message("开始扫描文件夹中的可解读文件...")
            
            # 支持的文件扩展名
            supported_extensions = [
                '.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv',
                '.pdf', '.docx', '.doc',
                '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'
            ]
            
            # 收集所有支持的文件
            files = []
            for file_path in folder_path_obj.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    files.append(str(file_path))
            
            self.log_message(f"扫描完成，发现 {len(files)} 个可解读文件")
            
            if not files:
                batch_results = {
                    'success': False,
                    'message': f'文件夹中没有找到可解读的文件: {folder_path}',
                    'results': [],
                    'total_files': 0,
                    'successful_reads': 0,
                    'failed_reads': 0
                }
            else:
                total_files = len(files)
                successful_reads = 0
                failed_reads = 0
                results = []
                
                for i, file_path in enumerate(files):
                    filename = Path(file_path).name
                    
                    # 更新进度
                    progress_callback(i + 1, total_files, filename)
                    
                    try:
                        # 解读单个文件
                        self.log_message(f"开始解读文件: {filename}", "DEBUG")
                        result = file_reader.generate_summary(file_path, self.reader_summary_length.get())
                        
                        # 提取路径标签
                        if result['success']:
                            result['tags'] = file_reader.extract_path_tags(file_path, folder_path)
                            successful_reads += 1
                            logging.info(f"文件解读成功: {filename}")
                            self.log_message(f"文件解读成功: {filename}")
                            
                            # 写入结果到ai_organize_result.json
                            file_reader.append_result_to_file("ai_organize_result.json", result, folder_path)
                        else:
                            failed_reads += 1
                            error_msg = result.get('error', '未知错误')
                            logging.warning(f"文件解读失败: {filename} - {error_msg}")
                            self.log_message(f"文件解读失败: {filename} - {error_msg}", "WARNING")
                        
                        results.append(result)
                        
                    except Exception as e:
                        failed_reads += 1
                        error_msg = str(e)
                        self.log_message(f"文件解读异常: {filename} - {error_msg}", "ERROR")
                        error_result = {
                            'file_path': file_path,
                            'file_name': filename,
                            'success': False,
                            'extracted_text': '',
                            'summary': '',
                            'error': error_msg,
                            'model_used': 'unknown',
                            'timestamp': datetime.now().isoformat()
                        }
                        results.append(error_result)
                
                # 批量解读结果已通过file_reader.append_result_to_file写入ai_organize_result.json
                # 不再需要单独的batch_read_results.json文件
                
                completion_msg = f"批量解读完成，共处理 {total_files} 个文件，成功 {successful_reads} 个，失败 {failed_reads} 个"
                self.log_message(completion_msg)
                
                batch_results = {
                    'success': True,
                    'folder_path': folder_path,
                    'total_files': total_files,
                    'successful_reads': successful_reads,
                    'failed_reads': failed_reads,
                    'results': results
                }
            
            # 显示结果
            def show_results():
                self.reader_status_label.config(text=t("batch_reading_completed", "file_reader"))
                self.log_message(f"批量文档解读完成: 成功 {batch_results['successful_reads']}, 失败 {batch_results['failed_reads']}")
                messagebox.showinfo(t("success", "messages"), t("batch_reading_completed", "messages", success=batch_results['successful_reads'], failed=batch_results['failed_reads']))
            
            self.root.after(0, show_results)
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.log_message(f"批量文档解读失败: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror(t("error", "messages"), t("batch_document_reading_failed", "messages", error=error_msg)))
            self.root.after(0, lambda: self.reader_status_label.config(text=t("reading_failed", "file_reader")))
        finally:
            self.root.after(0, lambda: self.reader_progress_var.set(0))
            self.root.after(0, lambda: self.reader_start_button.config(state='normal'))
            
    def _apply_ai_parameters(self):
        """应用AI参数设置"""
        try:
            # 获取当前参数值
            summary_len = self.summary_length.get()
            content_len = self.content_truncate.get()
            
            # 设置新分类器的参数
            if hasattr(self.ai_organizer, 'set_parameters'):
                # 新分类器适配器
                self.ai_organizer.set_parameters(
                    content_extraction_length=content_len,
                    summary_length=summary_len
                )
            elif hasattr(self.ai_organizer, 'summary_length'):
                # 旧分类器
                self.ai_organizer.summary_length = summary_len
                self.ai_organizer.content_truncate = content_len
            
            self.log_message(f"AI参数已更新: 摘要长度={summary_len}, 内容截取={content_len}")
            
        except Exception as e:
            self.log_message(f"设置AI参数失败: {e}")
            
    def ai_start_organize(self):
        """开始AI智能整理"""
        source = self.source_directory.get()
        target = self.target_directory.get()
        
        if not source or not target:
            messagebox.showerror(t("error", "messages"), t("please_select_directories", "messages"))
            self.log_message("AI智能整理失败：未选择源目录或目标目录", "WARNING")
            return
            
        # 确认对话框
        if not messagebox.askyesno(
            "确认整理",
            f"即将开始AI智能整理:\n\n源目录: {source}\n目标目录: {target}\n\n确定要继续吗？"
        ):
            self.log_message("AI智能整理操作已取消", "INFO")
            return
            
        self.log_message(f"开始AI智能整理，源目录: {source}")
        self.log_message(f"目标目录: {target}")
        self.ai_status_label.config(text=t("organizing_files", "ai_classifier"))
        self.ai_organize_button.config(state='disabled')
        
        # 在新线程中执行整理
        threading.Thread(target=self._ai_organize_worker, daemon=True).start()
        
    def _ai_organize_worker(self):
        """AI整理工作线程"""
        try:
            source = self.source_directory.get()
            target = self.target_directory.get()
            
            self.log_message("初始化AI智能整理器...")
            
            # 应用AI参数设置
            self._apply_ai_parameters()
            
            # 定义进度回调函数
            def progress_callback(current, total, filename):
                progress_percent = int((current / total) * 100)
                status_text = f"正在处理 {current}/{total}: {filename[:30]}{'...' if len(filename) > 30 else ''}"
                
                # 更新GUI进度条和状态
                self.root.after(0, lambda: self.ai_progress_var.set(progress_percent))
                self.root.after(0, lambda: self.ai_status_label.config(text=status_text))
                
                # 每处理10个文件记录一次日志
                if current % 10 == 0 or current == total:
                    self.root.after(0, lambda: self.log_message(f"AI整理进度: {current}/{total} ({progress_percent}%) - 当前文件: {filename}"))
            
            # 执行文件整理
            self.organize_results = self.ai_organizer.organize_files(
                source_directory=source, 
                target_directory=target,
                progress_callback=progress_callback
            )
            
            # AI结果已在处理过程中实时写入，不再需要重新生成
            # self._generate_organize_result_json(self.organize_results, "ai_organize_result.json")
            
            # 更新进度
            self.root.after(0, lambda: self.ai_progress_var.set(100))
            
            # 显示结果
            self.root.after(0, lambda: self._show_organize_results("AI智能整理"))
            
            # 如果AI智能整理成功且有文件被处理，询问是否删除源文件
            if (self.organize_results and 
                self.organize_results.get('successful_moves', 0) > 0 and 
                self.organize_results.get('success') and 
                len(self.organize_results.get('success', [])) > 0):
                
                self.root.after(1000, lambda: self._ask_delete_source_files_after_organize())
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.log_message(f"AI整理失败: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror(t("error", "messages"), t("ai_organize_failed", "messages", error=error_msg)))
        finally:
            self.root.after(0, lambda: self.ai_organize_button.config(state='normal'))
            self.root.after(0, lambda: self.ai_progress_var.set(0))
            self.root.after(0, lambda: self.ai_status_label.config(text=t("organize_completed", "ai_classifier")))
            
    # 简单分类相关方法已删除
            
    def _generate_organize_result_json(self, results, filename):
        """生成整理结果JSON文件"""
        try:
            if not results:
                return
                
            # 构建结果JSON
            result_json = []
            
            # 从ai_responses中获取详细信息
            ai_responses = results.get('ai_responses', [])
            move_details = results.get('move_details', [])
            
            for i, response in enumerate(ai_responses):
                detail = move_details[i] if i < len(move_details) else {}
                
                result_item = {
                    "源文件路径": detail.get('source_file', response.get('file_name', '')),
                    "文件摘要": response.get('summary', ''),  # 如果有摘要信息
                    "最匹配的目标目录": response.get('target_folder', ''),
                    "匹配理由": response.get('match_reason', ''),
                    "处理结果": {
                        "成功": response.get('success', False),
                        "目标路径": detail.get('target_path', ''),
                        "操作类型": detail.get('operation', ''),
                        "是否重命名": detail.get('renamed', False)
                    }
                }
                
                result_json.append(result_item)
                
            # 保存到文件
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result_json, f, ensure_ascii=False, indent=2)
                
            self.log_message(f"整理结果已保存到: {filename}")
            
        except Exception as e:
            self.log_message(f"保存整理结果失败: {e}")
            

        
    def _show_organize_results(self, operation_type):
        """显示整理结果"""
        try:
            if not self.organize_results:
                self.log_message("警告: 没有整理结果可显示")
                return
                
            results = self.organize_results
            
            # 创建结果窗口
            result_window = tb.Toplevel(self.root)
            result_window.title(f"{operation_type}结果")
            result_window.geometry("600x400")
            result_window.transient(self.root)
            result_window.grab_set()
            
            # 创建结果内容
            frame = tb.Frame(result_window, padding="10")
            frame.pack(fill=BOTH, expand=True)
            
            tb.Label(
                frame,
                text=f"{operation_type}完成",
                font=('Arial', 14, 'bold')
            ).pack(pady=(0, 10))
            
            # 统计信息
            stats_text = f"""总文件数: {results['total_files']}
处理文件数: {results['processed_files']}
成功移动: {results['successful_moves']}
失败移动: {results['failed_moves']}
跳过文件: {results['skipped_files']}"""
            
            tb.Label(frame, text=stats_text, font=('Arial', 10)).pack(pady=(0, 10))
            
            # 详细结果
            result_text = ScrolledText(frame, height=15, wrap=WORD)
            result_text.pack(fill=BOTH, expand=True, pady=(0, 10))
            
            # 显示成功的移动
            if results['success']:
                result_text.insert(END, "=== 成功移动的文件 ===\n")
                for item in results['success']:
                    result_text.insert(END, f"✓ {Path(item['source_path']).name} -> {item['target_folder']}\n")
                result_text.insert(END, "\n")
            
            # 显示失败的移动
            if results['failed']:
                result_text.insert(END, "=== 失败的文件 ===\n")
                for item in results['failed']:
                    result_text.insert(END, f"✗ {Path(item['source_path']).name}: {item['error']}\n")
                result_text.insert(END, "\n")
            
            # 显示错误信息
            if results['errors']:
                result_text.insert(END, "=== 错误信息 ===\n")
                for error in results['errors']:
                    result_text.insert(END, f"⚠ {error}\n")
            
            # result_text.config(state='disabled')  # ttkbootstrap ScrolledText不支持state配置
            
            # 按钮框架
            button_frame = tb.Frame(frame)
            button_frame.pack(fill=tb.X)
            
            # 确定按钮
            confirm_button = tb.Button(
                button_frame,
                text=t("confirm", "directory_organizer"),
                command=result_window.destroy
            )
            confirm_button.pack(side=tb.RIGHT)
            
            # 删除源文件按钮（仅在AI智能整理且有成功移动时显示）
            if (operation_type == "AI智能整理" and 
                results.get('successful_moves', 0) > 0 and 
                results.get('success') is not None and 
                len(results.get('success', [])) > 0):
                
                def delete_source_files():
                    """删除源文件"""
                    try:
                        # 获取成功移动的文件列表
                        successful_files = results['success']
                        
                        # 确认删除
                        delete_count = len(successful_files)
                        if not messagebox.askyesno(
                            "确认删除源文件", 
                            f"确定要删除 {delete_count} 个源文件吗？\n\n此操作不可撤销！"
                        ):
                            return
                        
                        # 执行删除
                        deleted_count = 0
                        failed_count = 0
                        failed_files = []
                        
                        for file_info in successful_files:
                            source_path = file_info['source_path']
                            try:
                                if os.path.exists(source_path):
                                    os.remove(source_path)
                                    deleted_count += 1
                                else:
                                    failed_count += 1
                                    failed_files.append(f"{os.path.basename(source_path)} (文件不存在)")
                            except Exception as e:
                                failed_count += 1
                                failed_files.append(f"{os.path.basename(source_path)} ({str(e)})")
                        
                        # 显示删除结果
                        result_msg = f"源文件删除完成:\n\n成功删除: {deleted_count} 个\n删除失败: {failed_count} 个"
                        
                        if failed_files:
                            result_msg += f"\n\n失败的文件:\n" + "\n".join(failed_files[:10])  # 只显示前10个
                            if len(failed_files) > 10:
                                result_msg += f"\n... 还有 {len(failed_files) - 10} 个失败文件"
                        
                        messagebox.showinfo(t("delete_completed", "messages"), result_msg)
                        
                    except Exception as e:
                        messagebox.showerror(t("delete_failed", "messages"), t("delete_source_files_error", "messages", error=str(e)))
                
                # 删除源文件按钮
                delete_button = tb.Button(
                    button_frame,
                    text=t("delete_source_files", "directory_organizer"),
                    command=delete_source_files
                )
                delete_button.pack(side=tb.RIGHT, padx=(0, 10))
                
        except Exception as e:
            error_msg = f"显示整理结果时出错: {str(e)}"
            self.log_message(error_msg)
            messagebox.showerror("错误", error_msg)
    
    def _ask_delete_source_files_after_organize(self):
        """迁移完成后询问是否删除源文件"""
        try:
            if not self.organize_results:
                return
                
            results = self.organize_results
            successful_files = results.get('success', [])
            
            if not successful_files:
                return
                
            delete_count = len(successful_files)
            
            # 弹出选择对话框
            message = f"AI智能整理已完成，成功处理了 {delete_count} 个文件。\n\n"
            message += f"是否要删除源文件？\n\n"
            message += f"• 选择'是'：删除源文件（不可撤销）\n"
            message += f"• 选择'否'：保留源文件\n"
            message += f"• 选择'取消'：稍后决定"
            
            choice = messagebox.askyesnocancel("文件迁移完成", message)
            
            if choice is True:  # 用户选择"是"
                self._delete_source_files_from_results(successful_files)
            elif choice is False:  # 用户选择"否"
                self.log_message("用户选择保留源文件")
            # choice is None 表示用户选择"取消"，不做任何操作
                
        except Exception as e:
            error_msg = f"询问删除源文件时出错: {str(e)}"
            self.log_message(error_msg)
            messagebox.showerror("错误", error_msg)
    
    def _delete_source_files_from_results(self, successful_files):
        """从结果中删除源文件"""
        try:
            deleted_count = 0
            failed_count = 0
            failed_files = []
            
            for file_info in successful_files:
                source_path = file_info['source_path']
                try:
                    if os.path.exists(source_path):
                        os.remove(source_path)
                        deleted_count += 1
                        self.log_message(f"已删除源文件: {os.path.basename(source_path)}")
                    else:
                        failed_count += 1
                        failed_files.append(f"{os.path.basename(source_path)} (文件不存在)")
                except Exception as e:
                    failed_count += 1
                    failed_files.append(f"{os.path.basename(source_path)} ({str(e)})")
            
            # 显示删除结果
            result_msg = f"源文件删除完成:\n\n成功删除: {deleted_count} 个\n删除失败: {failed_count} 个"
            
            if failed_files:
                result_msg += f"\n\n失败的文件:\n" + "\n".join(failed_files[:10])  # 只显示前10个
                if len(failed_files) > 10:
                    result_msg += f"\n... 还有 {len(failed_files) - 10} 个失败文件"
            
            messagebox.showinfo(t("delete_completed", "messages"), result_msg)
            self.log_message(f"源文件删除完成: 成功 {deleted_count} 个，失败 {failed_count} 个")
            
        except Exception as e:
            error_msg = f"删除源文件时出错: {str(e)}"
            self.log_message(error_msg)
            messagebox.showerror(t("delete_failed", "messages"), error_msg)
    
    def show_transfer_logs(self):
        """显示转移日志管理界面"""
        try:
            # 检查转移日志功能是否可用
            if not self.ai_organizer.enable_transfer_log:
                messagebox.showwarning(t("warning", "messages"), t("transfer_logs_not_enabled", "messages"))
                return
            
            # 创建转移日志窗口
            log_window = tb.Toplevel(self.root)
            log_window.title("转移日志管理")
            log_window.geometry("800x600")
            log_window.transient(self.root)
            log_window.grab_set()
            
            # 创建主框架
            main_frame = tb.Frame(log_window, padding="10")
            main_frame.pack(fill=tb.BOTH, expand=True)
            
            # 标题
            tb.Label(
                main_frame,
                text=t("title", "transfer_logs"),
                font=('Arial', 14, 'bold')
            ).pack(pady=(0, 10))
            
            # 日志列表框架
            list_frame = tb.LabelFrame(main_frame, text=t("log_list", "transfer_logs"), padding="5")
            list_frame.pack(fill=tb.BOTH, expand=True, pady=(0, 10))
            
            # 创建日志列表
            columns = ('时间', '会话名称', '总文件数', '成功数', '失败数', '文件路径')
            log_tree = tb.Treeview(list_frame, columns=columns, show='headings', height=15)
            
            # 设置列标题和宽度
            log_tree.heading('时间', text='时间')
            log_tree.heading('会话名称', text='会话名称')
            log_tree.heading('总文件数', text='总文件数')
            log_tree.heading('成功数', text='成功数')
            log_tree.heading('失败数', text='失败数')
            log_tree.heading('文件路径', text='文件路径')
            
            log_tree.column('时间', width=120)
            log_tree.column('会话名称', width=150)
            log_tree.column('总文件数', width=80)
            log_tree.column('成功数', width=80)
            log_tree.column('失败数', width=80)
            log_tree.column('文件路径', width=250)
            
            # 添加滚动条
            scrollbar = tb.Scrollbar(list_frame, orient=tb.VERTICAL, command=log_tree.yview)
            log_tree.configure(yscrollcommand=scrollbar.set)
            
            log_tree.pack(side=tb.LEFT, fill=tb.BOTH, expand=True)
            scrollbar.pack(side=tb.RIGHT, fill=tb.Y)
            
            # 加载日志数据
            self._load_transfer_logs(log_tree)
            
            # 按钮框架
            button_frame = tb.Frame(main_frame)
            button_frame.pack(fill=tb.X, pady=(10, 0))
            
            # 查看详情按钮
            tb.Button(
                button_frame,
                text=t("view_details", "transfer_logs"),
                command=lambda: self._show_log_details(log_tree)
            ).pack(side=tb.LEFT, padx=5)
            
            # 恢复文件按钮
            tb.Button(
                button_frame,
                text=t("restore_files", "transfer_logs"),
                command=lambda: self._restore_from_selected_log(log_tree)
            ).pack(side=tb.LEFT, padx=5)
            
            # 刷新按钮
            tb.Button(
                button_frame,
                text=t("refresh", "transfer_logs"),
                command=lambda: self._load_transfer_logs(log_tree)
            ).pack(side=tb.LEFT, padx=5)
            
            # 清理旧日志按钮
            tb.Button(
                button_frame,
                text=t("clean_old_logs", "transfer_logs"),
                command=lambda: self._cleanup_old_logs(log_tree)
            ).pack(side=tb.LEFT, padx=5)
            
            # 关闭按钮
            tb.Button(
                button_frame,
                text=t("close", "transfer_logs"),
                command=log_window.destroy
            ).pack(side=tb.RIGHT, padx=5)
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.log_message(f"显示转移日志失败: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror(t("error", "messages"), t("show_transfer_logs_failed", "messages", error=error_msg)))
        

    def show_duplicate_removal_dialog(self):
        """显示删除重复文件对话框"""
        try:
            from tidyfile.gui.duplicate_file_remover_gui import show_duplicate_remover_dialog
            show_duplicate_remover_dialog(self.root)
        except Exception as e:
            self.log_message(f"显示重复文件删除对话框失败: {e}")
            messagebox.showerror(t("error", "messages"), t("show_duplicate_remover_failed", "messages", e=str(e)))
        
    def show_classification_rules_manager(self):
        """显示分类规则管理器"""
        try:
            from tidyfile.gui.classification_rules_gui import ClassificationRulesGUI
            import tkinter as tk
            
            # 创建新窗口
            rules_window = tk.Toplevel(self.root)
            rules_window.title("分类规则管理器")
            
            # 设置响应式窗口
            self.setup_responsive_window(rules_window, 800, 600, 600, 400)
            rules_window.transient(self.root)  # 设置为主窗口的临时窗口
            rules_window.grab_set()  # 模态窗口
            
            # 创建分类规则管理器GUI
            rules_gui = ClassificationRulesGUI(rules_window)
            
            self.log_message("分类规则管理器已打开")
            
        except Exception as e:
            self.log_message(f"打开分类规则管理器失败: {e}")
            messagebox.showerror(t("error", "messages"), t("open_classification_rules_failed", "messages", e=str(e)))
    
    def show_ai_model_config(self):
        """显示AI模型配置"""
        try:
            from tidyfile.gui.ai_model_config_gui import AIModelConfigGUI
            config_gui = AIModelConfigGUI(self.root)
            config_gui.show_config_dialog()
        except Exception as e:
            self.log_message(f"显示AI模型配置失败: {e}")
            messagebox.showerror(t("error", "messages"), t("show_ai_model_config_failed", "messages", e=str(e)))
    
    def show_tag_manager(self):
        """显示标签管理器"""
        try:
            # 创建标签管理窗口
            tag_window = tb.Toplevel(self.root)
            tag_window.title("标签管理器")
            
            # 设置响应式窗口
            self.setup_responsive_window(tag_window, 900, 700, 700, 500)
            tag_window.resizable(True, True)
            tag_window.transient(self.root)
            tag_window.grab_set()
            
            # 创建主框架
            main_frame = tb.Frame(tag_window, padding="10")
            main_frame.pack(fill=BOTH, expand=True)
            
            # 标题
            title_label = tb.Label(main_frame, text=t("title", "tag_manager"), font=('Arial', 14, 'bold'))
            title_label.pack(pady=(0, 15))
            
            # 说明文字
            info_label = tb.Label(
                main_frame, 
                text=t("description", "tag_manager"),
                font=('Arial', 10),
                foreground="gray"
            )
            info_label.pack(pady=(0, 15))
            
            # 创建标签管理器GUI
            tag_manager = TagManagerGUI(main_frame, self.root)
            
            self.log_message("标签管理器已打开")
            
        except Exception as e:
            self.log_message(f"打开标签管理器失败: {e}")
            messagebox.showerror(t("error", "messages"), t("open_tag_manager_failed", "messages", e=str(e)))
    
    def show_tag_optimizer(self):
        """显示标签优化器"""
        try:
            # 创建标签优化窗口
            optimizer_window = tb.Toplevel(self.root)
            optimizer_window.title("标签优化工具")
            
            # 设置响应式窗口
            self.setup_responsive_window(optimizer_window, 1000, 800, 800, 600)
            optimizer_window.resizable(True, True)
            optimizer_window.transient(self.root)
            optimizer_window.grab_set()
            
            # 创建主框架
            main_frame = tb.Frame(optimizer_window, padding="10")
            main_frame.pack(fill=BOTH, expand=True)
            
            # 创建标签优化器GUI
            tag_optimizer = TagOptimizerGUI(main_frame, self.root)
            
            self.log_message("标签优化工具已打开")
            
        except Exception as e:
            self.log_message(f"打开标签优化工具失败: {e}")
            messagebox.showerror(t("error", "messages"), t("open_tag_optimizer_failed", "messages", e=str(e)))
    
    def show_multi_task_file_reader(self):
        """显示多任务文件解读管理器"""
        try:
            import subprocess
            import sys
            
            # 启动多任务文件解读管理器
            script_path = os.path.join(os.path.dirname(__file__), "multi_task_file_reader.py")
            subprocess.Popen([sys.executable, script_path])
            
            self.log_message("多任务文件解读管理器已启动")
            
        except Exception as e:
            self.log_message(f"启动多任务文件解读管理器失败: {e}")
            messagebox.showerror(t("error", "messages"), t("start_multi_task_reader_failed", "messages", e=str(e)))
    
    def show_multi_process_file_reader(self):
        """显示高并发文件解读管理器"""
        try:
            import subprocess
            import sys
            
            # 启动高并发文件解读管理器
            script_path = os.path.join(os.path.dirname(__file__), "multi_process_file_reader.py")
            subprocess.Popen([sys.executable, script_path])
            
            self.log_message("高并发文件解读管理器已启动")
            
        except Exception as e:
            self.log_message(f"启动高并发文件解读管理器失败: {e}")
            messagebox.showerror(t("error", "messages"), t("start_multi_process_reader_failed", "messages", e=str(e)))
    
    def show_language_settings(self):
        """显示语言设置对话框"""
        if not I18N_AVAILABLE:
            messagebox.showwarning(t("warning", "messages"), t("i18n_module_not_loaded", "messages"))
            return
        
        # 创建语言设置对话框
        language_window = tb.Toplevel(self.root)
        language_window.title(t("language_settings", "settings"))
        language_window.geometry("600x500")
        language_window.resizable(True, True)
        language_window.transient(self.root)
        language_window.grab_set()
        
        # 设置最小窗口大小
        language_window.minsize(550, 450)
        
        # 居中显示
        language_window.update_idletasks()
        x = (language_window.winfo_screenwidth() // 2) - (600 // 2)
        y = (language_window.winfo_screenheight() // 2) - (500 // 2)
        language_window.geometry(f"600x500+{x}+{y}")
        
        # 主框架
        main_frame = tb.Frame(language_window, padding="20")
        main_frame.pack(fill=BOTH, expand=True)
        
        # 配置主框架的网格权重
        language_window.columnconfigure(0, weight=1)
        language_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # 标题
        title_label = tb.Label(main_frame, text=t("language_settings", "settings"), font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 当前语言显示
        current_lang_frame = tb.LabelFrame(main_frame, text=t("current_language", "settings"), padding="10")
        current_lang_frame.pack(fill=X, pady=(0, 20))
        
        i18n_manager = get_i18n_manager()
        current_lang_info = i18n_manager.get_language_info(i18n_manager.current_language)
        current_lang_label = tb.Label(current_lang_frame, text=current_lang_info["name"], font=("Arial", 12))
        current_lang_label.pack()
        
        # 语言选择
        lang_select_frame = tb.LabelFrame(main_frame, text=t("select_language", "settings"), padding="10")
        lang_select_frame.pack(fill=BOTH, expand=True, pady=(0, 20))
        
        # 语言选择变量
        selected_language = tk.StringVar(value=i18n_manager.current_language)
        
        # 创建语言选项
        available_languages = i18n_manager.get_available_languages()
        
        for lang_code in available_languages:
            lang_info = i18n_manager.get_language_info(lang_code)
            lang_radio = tk.Radiobutton(
                lang_select_frame,
                text=lang_info["name"],
                variable=selected_language,
                value=lang_code,
                font=("Arial", 11),
                anchor=W
            )
            lang_radio.pack(anchor=W, pady=8, padx=10)
        
        # 按钮框架
        button_frame = tb.Frame(main_frame)
        button_frame.pack(fill=X, pady=(20, 0))
        button_frame.columnconfigure(1, weight=1)  # 让中间空间可扩展
        
        def apply_language():
            """应用语言设置"""
            new_language = selected_language.get()
            if i18n_manager.set_language(new_language):
                # 更新应用设置
                try:
                    from tidyfile.utils.app_paths import get_app_paths
                    app_paths = get_app_paths()
                    settings_file = app_paths.app_settings_file
                    
                    if settings_file.exists():
                        with open(settings_file, 'r', encoding='utf-8') as f:
                            settings = json.load(f)
                    else:
                        settings = {"app_info": {}, "general": {}}
                    
                    settings["general"]["language"] = new_language
                    
                    with open(settings_file, 'w', encoding='utf-8') as f:
                        json.dump(settings, f, ensure_ascii=False, indent=2)
                    
                    messagebox.showinfo(t("success", "messages"), t("language_changed", "settings"))
                    language_window.destroy()
                    
                    # 立即更新界面
                    try:
                        update_all_widgets()
                        print("界面语言已更新")
                    except Exception as e:
                        print(f"界面更新失败: {e}")
                    
                    # 提示重启应用（可选）
                    if messagebox.askyesno(t("restart_required", "settings"), t("restart_message", "settings")):
                        # 重启应用程序
                        self.root.after(100, self._restart_application)
                except Exception as e:
                    messagebox.showerror(t("error", "messages"), f"{t('save_settings_failed', 'settings')}: {e}")
            else:
                messagebox.showerror(t("error", "messages"), t("language_change_failed", "settings"))
        
        def cancel_settings():
            """取消设置"""
            language_window.destroy()
        
        # 应用按钮
        apply_button = tb.Button(
            button_frame,
            text=t("apply", "settings"),
            command=apply_language,
            style="success.TButton",
            width=12
        )
        apply_button.grid(row=0, column=0, padx=(0, 10))
        
        # 取消按钮
        cancel_button = tb.Button(
            button_frame,
            text=t("cancel", "settings"),
            command=cancel_settings,
            style="secondary.TButton",
            width=12
        )
        cancel_button.grid(row=0, column=2)
    
    def _restart_application(self):
        """重启应用程序"""
        try:
            import sys
            import subprocess
            import os
            
            # 获取当前脚本路径
            script_path = sys.argv[0]
            
            # 关闭当前窗口
            self.root.destroy()
            
            # 启动新的进程
            subprocess.Popen([sys.executable, script_path])
            
            # 退出当前进程
            sys.exit(0)
        except Exception as e:
            print(f"重启应用程序失败: {e}")
            # 如果重启失败，至少关闭窗口
            self.root.destroy()
    
    def show_directory_organize_dialog(self):
        """显示文件目录智能整理对话框"""
        try:
            # 创建目录整理对话框
            organize_window = tb.Toplevel(self.root)
            organize_window.title("文件目录智能整理")
            organize_window.geometry("1400x800")
            organize_window.transient(self.root)
            organize_window.grab_set()
            
            # 创建主框架
            main_frame = tb.Frame(organize_window, padding="10")
            main_frame.pack(fill=tb.BOTH, expand=True)
            
            # 标题
            tb.Label(
                main_frame,
                text=t("title", "directory_organizer"),
                font=('Arial', 14, 'bold')
            ).pack(pady=(0, 10))
            
            # 说明文字
            tb.Label(
                main_frame,
                text=t("description", "directory_organizer"),
                font=('Arial', 10)
            ).pack(pady=(0, 15))
            
            # 创建左右分栏框架
            content_frame = tb.Frame(main_frame)
            content_frame.pack(fill=tb.BOTH, expand=True)
            content_frame.columnconfigure(0, weight=1)
            content_frame.columnconfigure(1, weight=1)
            content_frame.rowconfigure(0, weight=1)
            
            # 左侧：目录选择区域
            left_frame = tb.LabelFrame(content_frame, text=t("select_directories", "directory_organizer"), padding="10")
            left_frame.grid(row=0, column=0, sticky=(tb.W, tb.E, tb.N, tb.S), padx=(0, 5))
            
            # 左侧顶部：刷新按钮
            refresh_frame = tb.Frame(left_frame)
            refresh_frame.pack(fill=tb.X, pady=(0, 10))
            
            tb.Button(
                refresh_frame,
                text=t("refresh_system_directories", "directory_organizer"),
                command=lambda: refresh_drives()
            ).pack(side=tb.LEFT)
            
            # 左侧中间：目录树
            tree_frame = tb.Frame(left_frame)
            tree_frame.pack(fill=tb.BOTH, expand=True)
            
            # 创建目录树
            drive_tree = ttk.Treeview(tree_frame, show="tree", height=20)
            drive_tree.pack(side=tb.LEFT, fill=tb.BOTH, expand=True)
            
            # 添加滚动条
            tree_scrollbar = tb.Scrollbar(tree_frame, orient=tb.VERTICAL, command=drive_tree.yview)
            drive_tree.configure(yscrollcommand=tree_scrollbar.set)
            tree_scrollbar.pack(side=tb.RIGHT, fill=tb.Y)
            
            # 左侧底部：已选择目录列表
            selected_frame = tb.LabelFrame(left_frame, text=t("selected_directories", "directory_organizer"), padding="5")
            selected_frame.pack(fill=tb.X, pady=(10, 0))
            
            selected_listbox = Listbox(selected_frame, height=4)
            selected_listbox.pack(side=tb.LEFT, fill=tb.BOTH, expand=True)
            
            selected_scrollbar = tb.Scrollbar(selected_frame, orient=tb.VERTICAL, command=selected_listbox.yview)
            selected_listbox.configure(yscrollcommand=selected_scrollbar.set)
            selected_scrollbar.pack(side=tb.RIGHT, fill=tb.Y)
            
            # 右侧：推荐结果区域
            right_frame = tb.LabelFrame(content_frame, text=t("ai_recommendation", "directory_organizer"), padding="10")
            right_frame.grid(row=0, column=1, sticky=(tb.W, tb.E, tb.N, tb.S), padx=(5, 0))
            
            # 右侧顶部：目标目录选择
            target_frame = tb.Frame(right_frame)
            target_frame.pack(fill=tb.X, pady=(0, 10))
            
            tb.Label(target_frame, text=t("new_directory_location", "directory_organizer")).pack(anchor=tb.W)
            
            target_var = tb.StringVar()
            target_entry = tb.Entry(target_frame, textvariable=target_var, width=40)
            target_entry.pack(side=tb.LEFT, fill=tb.X, expand=True, padx=(0, 5))
            
            def select_target_folder():
                folder_path = filedialog.askdirectory(title="选择新建目录的位置")
                if folder_path:
                    target_var.set(folder_path)
            
            tb.Button(
                target_frame,
                text=t("select", "directory_organizer"),
                command=select_target_folder
            ).pack(side=tb.RIGHT)
            
            # 右侧中间：推荐结果显示
            result_frame = tb.Frame(right_frame)
            result_frame.pack(fill=tb.BOTH, expand=True, pady=(0, 10))
            
            result_text = ScrolledText(result_frame, wrap=tb.WORD)
            result_text.pack(fill=tb.BOTH, expand=True)
            
            # 右侧底部：操作按钮
            button_frame = tb.Frame(right_frame)
            button_frame.pack(fill=tb.X)
            
            # 存储选中的目录和复选框状态
            selected_directories = []
            checkbox_states = {}  # 存储复选框状态
            
            def refresh_drives():
                """刷新系统盘符"""
                try:
                    # 清空现有树
                    for item in drive_tree.get_children():
                        drive_tree.delete(item)
                    
                    # 导入目录整理器
                    from tidyfile.core.directory_organizer import DirectoryOrganizer
                    organizer = DirectoryOrganizer(model_name=None)  # 自动选择模型，优先qwen3系列
                    drives = organizer.get_system_drives()
                    
                    # 添加盘符到树，使用统一的展开/折叠样式
                    for drive in drives:
                        drive_tree.insert("", "end", text=f"☐ {drive}", values=(drive,), open=False)
                    
                    try:
                        result_text.delete(1.0, tb.END)
                        result_text.insert(tb.END, f"已加载 {len(drives)} 个系统盘符\n")
                    except Exception as e:
                        pass
                    
                except Exception as e:
                    messagebox.showerror(t("error", "messages"), t("refresh_drives_failed", "messages", e=str(e)))
            
            def on_tree_select(event):
                """处理目录选择"""
                selection = drive_tree.selection()
                if selection:
                    item = drive_tree.item(selection[0])
                    path = item['values'][0] if item['values'] else ""
                    item_text = item['text']
                    
                    # 检查是否是复选框点击
                    if item_text.startswith('☐') or item_text.startswith('☑'):
                        # 切换复选框状态
                        if item_text.startswith('☐'):
                            # 选中
                            drive_tree.item(selection[0], text=f"☑ {item_text[2:]}")
                            if path and path not in selected_directories:
                                selected_directories.append(path)
                                selected_listbox.insert(tb.END, path)
                                checkbox_states[path] = True
                                
                                # 自动选中所有子目录
                                select_all_children(selection[0])
                        else:
                            # 取消选中
                            drive_tree.item(selection[0], text=f"☐ {item_text[2:]}")
                            if path and path in selected_directories:
                                selected_directories.remove(path)
                                # 从列表中移除
                                for i in range(selected_listbox.size()):
                                    if selected_listbox.get(i) == path:
                                        selected_listbox.delete(i)
                                        break
                                checkbox_states[path] = False
                                
                                # 自动取消选中所有子目录
                                unselect_all_children(selection[0])
            
            def select_all_children(parent_item):
                """选中所有子目录"""
                for child in drive_tree.get_children(parent_item):
                    child_text = drive_tree.item(child)['text']
                    child_path = drive_tree.item(child)['values'][0] if drive_tree.item(child)['values'] else ""
                    
                    if child_text.startswith('☐') and child_path:
                        drive_tree.item(child, text=f"☑ {child_text[2:]}")
                        if child_path not in selected_directories:
                            selected_directories.append(child_path)
                            selected_listbox.insert(tb.END, child_path)
                            checkbox_states[child_path] = True
                        
                        # 递归选中子目录
                        select_all_children(child)
            
            def unselect_all_children(parent_item):
                """取消选中所有子目录"""
                for child in drive_tree.get_children(parent_item):
                    child_text = drive_tree.item(child)['text']
                    child_path = drive_tree.item(child)['values'][0] if drive_tree.item(child)['values'] else ""
                    
                    if child_text.startswith('☑') and child_path:
                        drive_tree.item(child, text=f"☐ {child_text[2:]}")
                        if child_path in selected_directories:
                            selected_directories.remove(child_path)
                            # 从列表中移除
                            for i in range(selected_listbox.size()):
                                if selected_listbox.get(i) == child_path:
                                    selected_listbox.delete(i)
                                    break
                            checkbox_states[child_path] = False
                        
                        # 递归取消选中子目录
                        unselect_all_children(child)
            
            def expand_drive(drive_path, parent_item):
                """展开盘符下的目录"""
                try:
                    from tidyfile.core.directory_organizer import DirectoryOrganizer
                    organizer = DirectoryOrganizer(model_name=None)  # 自动选择模型，优先qwen3系列
                    directories = organizer.scan_drive_structure(drive_path, max_depth=1)
                    
                    for dir_info in directories:
                        dir_path = dir_info['path']
                        dir_name = dir_info['name']
                        
                        # 添加到树中，前面加上复选框
                        child_item = drive_tree.insert(
                            parent_item, "end", 
                            text=f"☐ {dir_name}", 
                            values=(dir_path,),
                            open=False
                        )
                        
                        # 如果有子目录，添加占位符
                        if dir_info['has_children']:
                            drive_tree.insert(child_item, "end", text="...", values=("",))
                            
                except Exception as e:
                    logging.warning(f"展开盘符失败 {drive_path}: {e}")
            
            def on_tree_double_click(event):
                """处理双击展开"""
                selection = drive_tree.selection()
                if selection:
                    item = drive_tree.item(selection[0])
                    path = item['values'][0] if item['values'] else ""
                    item_text = item['text']
                    
                    if path and (path.endswith(':\\') or path == '/'):
                        # 展开盘符
                        expand_drive(path, selection[0])
                        # 更新图标为展开状态
                        drive_tree.item(selection[0], text=f"☑ {item_text[2:]}")
                    elif path and (item_text.startswith('☐') or item_text.startswith('☑')):
                        # 展开目录
                        expand_directory(path, selection[0])
            
            def expand_directory(dir_path, parent_item):
                """展开目录"""
                try:
                    path = Path(dir_path)
                    if not path.exists() or not path.is_dir():
                        return
                    
                    # 清空占位符
                    for child in drive_tree.get_children(parent_item):
                        if drive_tree.item(child)['text'] == '...':
                            drive_tree.delete(child)
                    
                    # 添加子目录
                    for item in path.iterdir():
                        if item.is_dir():
                            try:
                                # 检查是否有访问权限
                                list(item.iterdir())
                                
                                # 过滤掉$开头的目录
                                if item.name.startswith('$'):
                                    continue
                                
                                child_item = drive_tree.insert(
                                    parent_item, "end",
                                    text=f"☐ {item.name}",
                                    values=(str(item),),
                                    open=False
                                )
                                
                                # 如果有子目录，添加占位符
                                if any(item.iterdir()):
                                    drive_tree.insert(child_item, "end", text="...", values=("",))
                                    
                            except PermissionError:
                                continue
                            except Exception as e:
                                continue
                    
                    # 更新父目录图标为展开状态
                    parent_text = drive_tree.item(parent_item)['text']
                    if parent_text.startswith('☐') or parent_text.startswith('☑'):
                        drive_tree.item(parent_item, text=f"☑ {parent_text[2:]}")
                    
                except Exception as e:
                    logging.warning(f"展开目录失败 {dir_path}: {e}")
            
            def remove_selected_directory():
                """移除选中的目录"""
                selection = selected_listbox.curselection()
                if selection:
                    index = selection[0]
                    path = selected_listbox.get(index)
                    selected_directories.remove(path)
                    selected_listbox.delete(index)
                    
                    # 更新树中的复选框状态
                    update_tree_checkbox(path, False)
            
            def clear_selected_directories():
                """清空已选择的目录"""
                selected_directories.clear()
                selected_listbox.delete(0, tb.END)
                
                # 重置所有复选框状态
                reset_all_checkboxes()
            
            def update_tree_checkbox(path, checked):
                """更新树中指定路径的复选框状态"""
                def update_recursive(items):
                    for item in items:
                        item_path = drive_tree.item(item)['values'][0] if drive_tree.item(item)['values'] else ""
                        if item_path == path:
                            item_text = drive_tree.item(item)['text']
                            if checked and item_text.startswith('☐'):
                                drive_tree.item(item, text=f"☑ {item_text[2:]}")
                            elif not checked and item_text.startswith('☑'):
                                drive_tree.item(item, text=f"☐ {item_text[2:]}")
                            break
                        # 递归检查子项
                        update_recursive(drive_tree.get_children(item))
                
                update_recursive(drive_tree.get_children())
            
            def reset_all_checkboxes():
                """重置所有复选框状态"""
                def reset_recursive(items):
                    for item in items:
                        item_text = drive_tree.item(item)['text']
                        if item_text.startswith('☑'):
                            drive_tree.item(item, text=f"☐ {item_text[2:]}")
                        # 递归重置子项
                        reset_recursive(drive_tree.get_children(item))
                
                reset_recursive(drive_tree.get_children())
            
            def generate_recommendation():
                """生成AI推荐"""
                if not selected_directories:
                    messagebox.showwarning(t("info", "messages"), t("please_select_directories_to_organize", "messages"))
                    return
                
                if not target_var.get():
                    messagebox.showwarning(t("info", "messages"), t("please_select_new_directory_location", "messages"))
                    return
                
                # 禁用按钮
                recommend_btn.config(state='disabled')
                create_btn.config(state='disabled')
                
                # 在新线程中执行推荐
                def recommendation_worker():
                    try:
                        from tidyfile.core.directory_organizer import DirectoryOrganizer
                        organizer = DirectoryOrganizer(model_name=None)  # 自动选择模型，优先qwen3系列
                        
                        # 直接传递用户选择的目录列表
                        recommendation_result = organizer.generate_directory_recommendation(selected_directories)
                        
                        # 显示结果
                        def show_recommendation():
                            result_text.delete(1.0, tb.END)
                            
                            recommended_structure = recommendation_result['recommended_structure']
                            
                            result_text.insert(tb.END, "=== AI推荐目录结构 ===\n\n")
                            
                            # 显示推荐结构
                            self._display_recommended_structure(result_text, recommended_structure.get('recommended_structure', []))
                            
                            # 显示整理原则
                            principles = recommended_structure.get('organization_principles', [])
                            if principles:
                                result_text.insert(tb.END, "\n=== 整理原则 ===\n")
                                for i, principle in enumerate(principles, 1):
                                    result_text.insert(tb.END, f"{i}. {principle}\n")
                            
                            # 显示总结
                            summary = recommended_structure.get('summary', '')
                            if summary:
                                result_text.insert(tb.END, f"\n=== 整理总结 ===\n{summary}\n")
                            
                            # 启用创建按钮和重新推荐按钮
                            create_btn.config(state='normal')
                            re_recommend_btn.config(state='normal')
                            
                            # 存储推荐结果
                            organize_window.recommendation_result = recommendation_result
                        
                        organize_window.after(0, show_recommendation)
                        
                    except Exception as worker_error:
                        def show_error():
                            result_text.delete(1.0, tb.END)
                            result_text.insert(tb.END, f"生成推荐失败: {worker_error}")
                            recommend_btn.config(state='normal')
                        
                        organize_window.after(0, show_error)
                
                threading.Thread(target=recommendation_worker, daemon=True).start()
            
            def create_recommended_structure():
                """创建推荐的目录结构"""
                if not hasattr(organize_window, 'recommendation_result'):
                    messagebox.showwarning(t("info", "messages"), t("please_generate_ai_recommendation", "messages"))
                    return
                
                try:
                    from tidyfile.core.directory_organizer import DirectoryOrganizer
                    organizer = DirectoryOrganizer(model_name="deepseek-r1:8b")
                    
                    target_dir = target_var.get()
                    recommended_structure = organize_window.recommendation_result['recommended_structure']
                    
                    # 创建目录结构
                    create_result = organizer.create_recommended_structure(target_dir, recommended_structure)
                    
                    # 显示结果
                    result_text.delete(1.0, tb.END)
                    result_text.insert(tb.END, "=== 目录创建结果 ===\n\n")
                    result_text.insert(tb.END, f"目标目录: {target_dir}\n")
                    result_text.insert(tb.END, f"成功创建: {create_result['total_created']} 个目录\n")
                    result_text.insert(tb.END, f"创建失败: {create_result['total_failed']} 个目录\n\n")
                    
                    if create_result['created_directories']:
                        result_text.insert(tb.END, "已创建的目录:\n")
                        for dir_path in create_result['created_directories']:
                            result_text.insert(tb.END, f"  ✓ {dir_path}\n")
                    
                    if create_result['failed_directories']:
                        result_text.insert(tb.END, "\n创建失败的目录:\n")
                        for failed in create_result['failed_directories']:
                            result_text.insert(tb.END, f"  ✗ {failed['path']}: {failed['error']}\n")
                    
                    result_text.insert(tb.END, "\n=== 操作完成 ===\n")
                    result_text.insert(tb.END, "已成功创建新的目录结构，请使用智能分类或文件分类功能将原文件迁移到新的目录中。\n")
                    
                    messagebox.showinfo(t("success", "messages"), t("directory_structure_created", "messages"))
                    
                except Exception as e:
                    messagebox.showerror(t("error", "messages"), t("create_directory_structure_failed", "messages", e=str(e)))
            
            def re_generate_recommendation():
                """重新生成AI推荐"""
                if not selected_directories:
                    messagebox.showwarning(t("info", "messages"), t("please_select_directories_to_organize", "messages"))
                    return
                
                if not target_var.get():
                    messagebox.showwarning(t("info", "messages"), t("please_select_new_directory_location", "messages"))
                    return
                
                # 禁用按钮
                recommend_btn.config(state='disabled')
                re_recommend_btn.config(state='disabled')
                create_btn.config(state='disabled')
                
                # 在新线程中执行重新推荐
                def re_recommendation_worker():
                    try:
                        from tidyfile.core.directory_organizer import DirectoryOrganizer
                        organizer = DirectoryOrganizer(model_name=None)  # 自动选择模型，优先qwen3系列
                        
                        # 直接传递用户选择的目录列表
                        recommendation_result = organizer.generate_directory_recommendation(selected_directories)
                        
                        # 显示结果
                        def show_recommendation():
                            result_text.delete(1.0, tb.END)
                            
                            recommended_structure = recommendation_result['recommended_structure']
                            
                            result_text.insert(tb.END, "=== AI重新推荐目录结构 ===\n\n")
                            
                            # 显示推荐结构
                            self._display_recommended_structure(result_text, recommended_structure.get('recommended_structure', []))
                            
                            # 显示整理原则
                            principles = recommended_structure.get('organization_principles', [])
                            if principles:
                                result_text.insert(tb.END, "\n=== 整理原则 ===\n")
                                for i, principle in enumerate(principles, 1):
                                    result_text.insert(tb.END, f"{i}. {principle}\n")
                            
                            # 显示总结
                            summary = recommended_structure.get('summary', '')
                            if summary:
                                result_text.insert(tb.END, f"\n=== 整理总结 ===\n{summary}\n")
                            
                            # 启用创建按钮和重新推荐按钮
                            create_btn.config(state='normal')
                            re_recommend_btn.config(state='normal')
                            
                            # 存储推荐结果
                            organize_window.recommendation_result = recommendation_result
                        
                        organize_window.after(0, show_recommendation)
                        
                    except Exception as worker_error:
                        def show_error():
                            result_text.delete(1.0, tb.END)
                            result_text.insert(tb.END, f"重新生成推荐失败: {worker_error}")
                            recommend_btn.config(state='normal')
                            re_recommend_btn.config(state='normal')
                        
                        organize_window.after(0, show_error)
                
                threading.Thread(target=re_recommendation_worker, daemon=True).start()
            
            # 绑定事件
            drive_tree.bind('<<TreeviewSelect>>', on_tree_select)
            drive_tree.bind('<Double-1>', on_tree_double_click)
            
            # 左侧底部按钮
            left_button_frame = tb.Frame(left_frame)
            left_button_frame.pack(fill=tb.X, pady=(10, 0))
            
            tb.Button(
                left_button_frame,
                text=t("remove_selected", "directory_organizer"),
                command=remove_selected_directory
            ).pack(side=tb.LEFT, padx=5)
            
            tb.Button(
                left_button_frame,
                text=t("clear_list", "directory_organizer"),
                command=clear_selected_directories
            ).pack(side=tb.LEFT, padx=5)
            
            # 右侧按钮
            recommend_btn = tb.Button(
                button_frame,
                text=t("smart_recommendation", "directory_organizer"),
                command=generate_recommendation
            )
            recommend_btn.pack(side=tb.LEFT, padx=5)
            
            re_recommend_btn = tb.Button(
                button_frame,
                text=t("re_recommendation", "directory_organizer"),
                command=re_generate_recommendation,
                state='disabled'
            )
            re_recommend_btn.pack(side=tb.LEFT, padx=5)
            
            create_btn = tb.Button(
                button_frame,
                text=t("use_this_recommendation", "directory_organizer"),
                command=create_recommended_structure,
                state='disabled'
            )
            create_btn.pack(side=tb.LEFT, padx=5)
            
            tb.Button(
                button_frame,
                text=t("close", "directory_organizer"),
                command=organize_window.destroy
            ).pack(side=tb.RIGHT, padx=5)
            
            # 初始化加载盘符
            refresh_drives()
            
        except Exception as e:
            self.root.after(0, lambda err=e: self.log_message(f"显示目录整理对话框失败: {err}"))
            self.root.after(0, lambda err=e: messagebox.showerror(t("error", "messages"), t("show_restore_dialog_failed", "messages", e=str(err))))
    
    def _display_recommended_structure(self, text_widget, recommended_structure, level=0):
        """显示推荐的目录结构"""
        if isinstance(recommended_structure, list):
            # 路径列表格式
            text_widget.insert(tb.END, "=== AI推荐目录结构 ===\n\n")
            if recommended_structure:
                text_widget.insert(tb.END, "推荐目录结构：\n")
                for i, path in enumerate(recommended_structure, 1):
                    text_widget.insert(tb.END, f"{i}. {path}\n")
            else:
                text_widget.insert(tb.END, "暂无推荐目录结构\n")
        else:
            # 旧格式兼容
            text_widget.insert(tb.END, "=== AI推荐目录结构 ===\n\n")
            for item in recommended_structure:
                indent = "  " * level
                name = item.get('name', '')
                description = item.get('description', '')
                directories = item.get('directories', [])
                
                text_widget.insert(tb.END, f"{indent}📁 {name}")
                if description:
                    text_widget.insert(tb.END, f" - {description}")
                text_widget.insert(tb.END, "\n")
                
                # 显示目录列表
                if directories:
                    for dir_name in directories:
                        text_widget.insert(tb.END, f"{indent}  ├─ {dir_name}\n")
                
                # 递归显示子目录
                sub_dirs = item.get('sub_directories', [])
                if sub_dirs:
                    self._display_recommended_structure(text_widget, sub_dirs, level + 1)
    
    def _load_transfer_logs(self, tree):
        """加载转移日志数据"""
        try:
            # 清空现有数据
            for item in tree.get_children():
                tree.delete(item)
            
            # 获取日志管理器
            log_manager = TransferLogManager()
            log_files = log_manager.get_transfer_logs()
            
            if not log_files:
                tree.insert("", "end", values=("暂无日志记录", "", "", "", "", ""))
                return
            
            # 加载每个日志文件的信息
            for log_file_path in log_files:
                try:
                    log_data = log_manager.load_transfer_log(log_file_path)
                    session_info = log_data.get('session_info', {})
                    
                    # 提取信息
                    start_time = session_info.get('start_time', 'N/A')
                    if start_time != 'N/A':
                        # 格式化时间显示
                        from datetime import datetime
                        try:
                            dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                            start_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            pass
                    
                    session_name = session_info.get('session_name', 'N/A')
                    total_ops = session_info.get('total_operations', 0)
                    success_ops = session_info.get('successful_operations', 0)
                    failed_ops = session_info.get('failed_operations', 0)
                    
                    tree.insert("", "end", values=(
                        start_time, session_name, total_ops, success_ops, failed_ops, log_file_path
                    ))
                    
                except Exception as file_error:
                    # 如果单个文件加载失败，显示错误信息
                    tree.insert("", "end", values=(
                        "文件损坏", os.path.basename(log_file_path), "0", "0", "0", log_file_path
                    ))
                
        except Exception as e:
            self.log_message(f"加载转移日志失败: {e}")
            tree.insert("", "end", values=(f"加载失败: {e}", "", "", "", "", ""))
    
    def _show_log_details(self, tree):
        """显示选中日志的详细信息"""
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个日志记录")
            return
        
        try:
            # 获取选中项的数据
            item = tree.item(selection[0])
            values = item['values'] if item['values'] else []
            
            if not values or len(values) < 6:
                messagebox.showwarning(t("info", "messages"), t("please_select_valid_log_record", "messages"))
                return
            
            timestamp = values[0]
            log_file_path = values[5]  # 第6个字段是完整的文件路径
            
            if timestamp == "暂无日志记录" or timestamp.startswith("加载失败") or timestamp.startswith("文件损坏"):
                return
            
            # 直接使用存储的文件路径加载日志数据
            log_manager = TransferLogManager()
            try:
                target_log = log_manager.load_transfer_log(log_file_path)
            except Exception as e:
                messagebox.showerror(t("error", "messages"), t("cannot_load_log_file", "messages", filename=os.path.basename(log_file_path)))
                return
            
            # 创建详情窗口
            detail_window = tb.Toplevel(self.root)
            detail_window.title(f"日志详情 - {timestamp}")
            detail_window.geometry("800x600")
            detail_window.transient(self.root)
            detail_window.grab_set()
            
            # 创建主框架
            main_frame = tb.Frame(detail_window, padding="10")
            main_frame.pack(fill=tb.BOTH, expand=True)
            
            # 基本信息
            info_frame = tb.LabelFrame(main_frame, text=t("basic_info", "transfer_logs"), padding="5")
            info_frame.pack(fill=tb.X, pady=(0, 10))
            
            session_info = target_log.get('session_info', {})
            tb.Label(info_frame, text=f"时间: {session_info.get('start_time', 'N/A')}").pack(anchor=tb.W)
            tb.Label(info_frame, text=f"会话名称: {session_info.get('session_name', 'N/A')}").pack(anchor=tb.W)
            tb.Label(info_frame, text=f"总操作数: {session_info.get('total_operations', 0)}").pack(anchor=tb.W)
            tb.Label(info_frame, text=f"成功操作: {session_info.get('successful_operations', 0)}").pack(anchor=tb.W)
            tb.Label(info_frame, text=f"失败操作: {session_info.get('failed_operations', 0)}").pack(anchor=tb.W)
            tb.Label(info_frame, text=f"状态: {'已完成' if session_info.get('end_time') else '进行中'}").pack(anchor=tb.W)
            
            # 文件列表
            files_frame = tb.LabelFrame(main_frame, text=t("file_list", "transfer_logs"), padding="5")
            files_frame.pack(fill=tb.BOTH, expand=True)
            
            # 创建文件列表树形视图
            files_tree = tb.Treeview(
                files_frame,
                columns=("source", "target", "status"),
                show="headings",
                height=15
            )
            
            files_tree.heading("source", text=t("source_file", "transfer_logs"))
            files_tree.heading("target", text=t("target_file", "transfer_logs"))
            files_tree.heading("status", text=t("status", "transfer_logs"))
            
            files_tree.column("source", width=300)
            files_tree.column("target", width=300)
            files_tree.column("status", width=100)
            
            # 添加滚动条
            files_scrollbar = tb.Scrollbar(files_frame, orient=tb.VERTICAL, command=files_tree.yview)
            files_tree.configure(yscrollcommand=files_scrollbar.set)
            
            files_tree.pack(side=tb.LEFT, fill=tb.BOTH, expand=True)
            files_scrollbar.pack(side=tb.RIGHT, fill=tb.Y)
            
            # 填充文件数据
            for operation in target_log.get('operations', []):
                source_path = operation.get('source_path', 'N/A')
                target_path = operation.get('target_path', 'N/A')
                status = '成功' if operation.get('success', False) else '失败'
                
                files_tree.insert("", "end", values=(source_path, target_path, status))
            
            # 关闭按钮
            tb.Button(
                main_frame,
                text=t("close", "transfer_logs"),
                command=detail_window.destroy
            ).pack(pady=(10, 0))
            
        except Exception as e:
            self.log_message(f"显示日志详情失败: {e}")
            messagebox.showerror(t("error", "messages"), t("show_log_details_failed", "messages", e=str(e)))
    
    def _restore_from_selected_log(self, log_tree):
        """从选中的日志记录恢复文件"""
        try:
            # 获取选中的项目
            selection = log_tree.selection()
            if not selection:
                messagebox.showwarning(t("info", "messages"), t("please_select_log_record", "messages"))
                return
            
            # 获取选中项目的数据
            item = log_tree.item(selection[0])
            values = item['values'] if item['values'] else []
            
            if not values or len(values) < 6:
                messagebox.showwarning(t("info", "messages"), t("please_select_valid_log_record", "messages"))
                return
            
            timestamp = values[0]
            log_file_path = values[5]  # 第6个字段是完整的文件路径
            
            if not timestamp or timestamp == "暂无日志记录" or timestamp.startswith("加载失败") or timestamp.startswith("文件损坏"):
                messagebox.showwarning(t("info", "messages"), t("please_select_valid_log_record", "messages"))
                return
            
            # 直接使用存储的文件路径
            target_log_file = log_file_path
            
            # 验证文件是否存在
            if not os.path.exists(target_log_file):
                messagebox.showerror(t("error", "messages"), t("log_file_not_exists", "messages", filename=os.path.basename(target_log_file)))
                return
            
            # 创建恢复对话框
            restore_window = tb.Toplevel(self.root)
            restore_window.title("文件恢复")
            restore_window.geometry("600x500")
            restore_window.transient(self.root)
            restore_window.grab_set()
            
            # 创建主框架
            main_frame = tb.Frame(restore_window, padding="10")
            main_frame.pack(fill=tb.BOTH, expand=True)
            
            # 标题
            tb.Label(
                main_frame,
                text=t("file_restore", "transfer_logs"),
                font=('Arial', 12, 'bold')
            ).pack(pady=(0, 10))
            
            # 日志文件信息
            tb.Label(main_frame, text=f"日志文件: {Path(target_log_file).name}").pack(anchor=tb.W)
            tb.Label(main_frame, text=f"时间戳: {timestamp}").pack(anchor=tb.W)
            
            # 操作模式选择
            mode_frame = tb.LabelFrame(main_frame, text=t("operation_mode", "transfer_logs"), padding="5")
            mode_frame.pack(fill=tb.X, pady=(10, 10))
            
            dry_run_var = tb.BooleanVar(value=True)
            tb.Radiobutton(
                mode_frame,
                text=t("preview_mode", "transfer_logs"),
                variable=dry_run_var,
                value=True
            ).pack(anchor=tb.W)
            tb.Radiobutton(
                mode_frame,
                text=t("execute_mode", "transfer_logs"),
                variable=dry_run_var,
                value=False
            ).pack(anchor=tb.W)
            
            # 进度条
            progress_var = tb.StringVar(value="准备就绪")
            progress_label = tb.Label(main_frame, textvariable=progress_var)
            progress_label.pack(anchor=tb.W, pady=(0, 5))
            
            # 结果显示区域
            result_text = ScrolledText(main_frame, height=15, wrap=tb.WORD)
            result_text.pack(fill=tb.BOTH, expand=True, pady=(0, 10))
            
            # 按钮框架
            button_frame = tb.Frame(main_frame)
            button_frame.pack(fill=tb.X)
            
            def start_restore():
                # 禁用按钮
                restore_btn.config(state='disabled')
                cancel_btn.config(state='disabled')
                
                # 执行恢复操作
                self._execute_restore(target_log_file, dry_run_var.get(), progress_var, result_text, restore_window)
                
                # 重新启用按钮
                restore_btn.config(state='normal')
                cancel_btn.config(state='normal')
            
            restore_btn = tb.Button(
                button_frame,
                text=t("start_restore", "directory_organizer"),
                command=start_restore
            )
            restore_btn.pack(side=tb.LEFT, padx=5)
            
            cancel_btn = tb.Button(
                button_frame,
                text=t("cancel", "directory_organizer"),
                command=restore_window.destroy
            )
            cancel_btn.pack(side=tb.RIGHT, padx=5)
            
        except Exception as e:
            self.log_message(f"显示恢复对话框失败: {e}")
            messagebox.showerror(t("error", "messages"), t("show_restore_dialog_failed", "messages", e=str(e)))
    
    def _execute_restore(self, log_file, dry_run, progress_var, result_text, restore_window):
        """执行文件恢复操作"""
        try:
            # 获取日志管理器
            log_manager = TransferLogManager()
            
            if dry_run:
                progress_var.set("正在分析恢复操作...")
                result = log_manager.restore_from_log(log_file, dry_run=True)
                
                def update_preview():
                    result_text.delete(1.0, tb.END)
                    result_text.insert(tb.END, "=== 恢复预览 ===\n\n")
                    result_text.insert(tb.END, f"日志文件: {os.path.basename(log_file)}\n")
                    result_text.insert(tb.END, f"总操作数: {result.get('total_operations', 0)}\n")
                    result_text.insert(tb.END, f"可恢复操作: {result.get('successful_restores', 0)}\n")
                    result_text.insert(tb.END, f"跳过操作: {result.get('skipped_operations', 0)}\n\n")
                    
                    if result.get('restore_details'):
                        result_text.insert(tb.END, "恢复详情:\n")
                        for detail in result['restore_details']:
                            status = "✓" if detail.get('restore_success') else "⚠"
                            result_text.insert(tb.END, f"  {status} {detail['target_path']} -> {detail['source_path']}\n")
                            result_text.insert(tb.END, f"      {detail.get('restore_message', '')}\n")
                    else:
                        result_text.insert(tb.END, "没有找到可恢复的操作\n")
                    
                    progress_var.set("预览完成")
                
                restore_window.after(0, update_preview)
                
            else:
                progress_var.set("正在执行恢复操作...")
                result = log_manager.restore_from_log(log_file, dry_run=False)
                
                def update_result():
                    result_text.delete(1.0, tb.END)
                    result_text.insert(tb.END, "=== 恢复结果 ===\n\n")
                    result_text.insert(tb.END, f"日志文件: {os.path.basename(log_file)}\n")
                    result_text.insert(tb.END, f"成功恢复: {result.get('successful_restores', 0)} 个文件\n")
                    result_text.insert(tb.END, f"恢复失败: {result.get('failed_restores', 0)} 个文件\n")
                    result_text.insert(tb.END, f"跳过操作: {result.get('skipped_operations', 0)} 个\n\n")
                    
                    if result.get('restore_details'):
                        result_text.insert(tb.END, "恢复详情:\n")
                        for detail in result['restore_details']:
                            status = "✓" if detail.get('restore_success') else "✗"
                            result_text.insert(tb.END, f"  {status} {detail['target_path']} -> {detail['source_path']}\n")
                            result_text.insert(tb.END, f"      {detail.get('restore_message', '')}\n")
                    else:
                        result_text.insert(tb.END, "没有找到可恢复的操作\n")
                    
                    progress_var.set("恢复完成")
                    
                    # 记录日志
                    self.root.after(0, lambda: self.log_message(f"文件恢复完成: 成功 {result.get('successful_restores', 0)} 个，失败 {result.get('failed_restores', 0)} 个"))
                
                restore_window.after(0, update_result)
                
        except Exception as e:
            def show_error():
                result_text.delete(1.0, tb.END)
                result_text.insert(tb.END, f"恢复操作失败: {e}\n")
                result_text.insert(tb.END, f"请检查日志文件是否完整: {os.path.basename(log_file)}")
                progress_var.set("恢复失败")
                self.root.after(0, lambda err=e: self.log_message(f"文件恢复失败: {err}"))
            
            restore_window.after(0, show_error)
        
    def run(self):
        """运行应用"""
        self.root.mainloop()

def main():
    """主函数"""
    app = FileOrganizerTabGUI()
    app.run()

if __name__ == "__main__":
    main()