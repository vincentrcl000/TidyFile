#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多任务文件解读管理器

支持同时启动多个文件解读任务，每个任务独立运行
可以同时处理多个不同的文件夹

单独执行使用方法:
    python multi_task_file_reader.py

功能说明:
    1. 图形界面管理多个文件解读任务
    2. 支持同时处理多个不同文件夹
    3. 实时显示任务进度和状态
    4. 支持任务启动、停止、重启、删除和统计
    5. 自动去重检测，避免重复处理
    6. 结果保存到 ai_organize_result.json

界面功能:
    - 创建任务: 选择文件夹，设置摘要长度
    - 任务管理: 启动、停止、重启、删除任务
    - 进度监控: 实时显示处理进度和当前文件
    - 统计信息: 查看成功/失败/跳过/路径更新的文件数量
    - 任务详情: 双击任务查看详细信息

支持的文件格式:
    - 文本文件: .txt, .md, .py, .js, .html, .css, .json, .xml, .csv
    - 文档文件: .pdf, .docx, .doc
    - 图片文件: .jpg, .jpeg, .png, .bmp, .gif, .tiff, .webp

作者: AI Assistant
创建时间: 2025-01-15
更新时间: 2025-08-05
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ttkbootstrap as tb
# 兼容新版本ttkbootstrap
try:
    from ttkbootstrap import Style, Window
except ImportError:
    pass
from ttkbootstrap.constants import *
import threading
import time
import json
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# 全局文件锁，防止多任务同时写入
_result_file_lock = threading.Lock()

class FileReadTask:
    """单个文件解读任务"""
    
    def __init__(self, task_id: str, folder_path: str, summary_length: int = 200):
        self.task_id = task_id
        self.folder_path = folder_path
        self.summary_length = summary_length
        self.status = "等待中"  # 等待中, 运行中, 已完成, 失败
        self.progress = 0.0
        self.current_file = ""
        self.total_files = 0
        self.processed_files = 0
        self.successful_reads = 0
        self.failed_reads = 0
        self.skipped_reads = 0  # 新增：跳过的文件数
        self.path_updated_reads = 0  # 新增：路径更新的文件数
        self.start_time = None
        self.end_time = None
        self.error_message = ""
        self.thread = None
        self.stop_flag = False
        
        # 设置日志
        self.setup_logging()
    
    def setup_logging(self):
        """设置日志记录"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
    
    def start(self):
        """启动任务"""
        # 如果任务已经在运行，先停止
        if self.status == "运行中":
            self.stop()
            time.sleep(0.5)  # 等待线程结束
        
        # 重置状态
        self.status = "运行中"
        self.start_time = datetime.now()
        self.stop_flag = False
        
        # 启动新线程
        self.thread = threading.Thread(target=self._run_task, daemon=True)
        self.thread.start()
    
    def stop(self):
        """停止任务"""
        self.stop_flag = True
        self.status = "已停止"
    
    def _safe_append_result(self, file_reader, result, folder_path):
        """安全地追加结果到文件，使用全局锁防止并发冲突"""
        with _result_file_lock:
            try:
                # 使用文件解读器的安全写入方法
                # 使用新的路径管理获取正确的文件路径
                from tidyfile.utils.app_paths import get_app_paths
                app_paths = get_app_paths()
                ai_result_file = str(app_paths.ai_results_file)
        
        file_reader.append_result_to_file(ai_result_file, result, folder_path)
                return True
            except Exception as e:
                logging.error(f"任务 {self.task_id}: 写入结果失败: {e}")
                return False
    
    def _run_task(self):
        """运行任务的具体实现"""
        try:
            from tidyfile.core.file_reader import FileReader
            from tidyfile.ai.client_manager import get_ai_manager
            
            # 确保AI客户端管理器正常工作
            ai_manager = get_ai_manager()
            if ai_manager.get_available_models_count() == 0:
                ai_manager.refresh_clients()
                if ai_manager.get_available_models_count() == 0:
                    self.status = "失败"
                    self.error_message = "没有可用的AI模型，请检查Ollama服务"
                    return
            
            # 初始化文件解读器
            file_reader = FileReader()
            file_reader.summary_length = self.summary_length
            
            # 扫描文件夹中的文件
            folder_path_obj = Path(self.folder_path)
            
            # 支持的文件扩展名（与file_reader.py保持一致）
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
            
            if not files:
                self.status = "失败"
                self.error_message = f"文件夹中没有找到可解读的文件: {self.folder_path}"
                return
            
            self.total_files = len(files)
            logging.info(f"任务 {self.task_id} 开始处理 {self.total_files} 个文件")
            
            for i, file_path in enumerate(files):
                if self.stop_flag:
                    break
                
                filename = Path(file_path).name
                self.current_file = filename
                self.processed_files = i + 1
                self.progress = (i + 1) / self.total_files * 100
                
                try:
                    # 解读单个文件（使用与file_reader.py相同的流程）
                    # 使用新的路径管理获取正确的文件路径
                    from tidyfile.utils.app_paths import get_app_paths
                    app_paths = get_app_paths()
                    ai_result_file = str(app_paths.ai_results_file)
        
        result = file_reader.generate_summary(file_path, self.summary_length, ai_result_file)
                    
                    # 检查处理状态
                    processing_status = result.get('processing_status', '')
                    
                    if processing_status == '已跳过':
                        # 完全重复的文件，跳过处理
                        self.skipped_reads += 1
                        logging.info(f"文件完全重复，跳过: {filename}")
                        continue
                    elif processing_status == '路径已更新':
                        # 同名但路径不同的文件，复用摘要并更新路径
                        self.path_updated_reads += 1
                        logging.info(f"文件路径已更新: {filename}")
                        # 使用安全写入方法
                        self._safe_append_result(file_reader, result, self.folder_path)
                        continue
                    
                    # 检查处理结果
                    if result['success']:
                        # 提取路径标签（如果不是路径更新情况）
                        if not result.get('tags'):
                            result['tags'] = file_reader.extract_path_tags(file_path, self.folder_path)
                        self.successful_reads += 1
                        
                        # 使用安全写入方法
                        if self._safe_append_result(file_reader, result, self.folder_path):
                            logging.info(f"文件解读成功: {filename}")
                        else:
                            logging.warning(f"文件解读成功但写入失败: {filename}")
                    else:
                        self.failed_reads += 1
                        logging.warning(f"文件解读失败: {filename} - {result.get('error', '未知错误')}")
                    
                except Exception as e:
                    self.failed_reads += 1
                    logging.error(f"文件解读异常: {filename} - {e}")
                
                # 稍微延迟，避免过于频繁的更新
                time.sleep(0.1)
            
            if not self.stop_flag:
                self.status = "已完成"
                logging.info(f"任务 {self.task_id} 完成: 成功 {self.successful_reads}, 失败 {self.failed_reads}, 跳过 {self.skipped_reads}, 路径更新 {self.path_updated_reads}")
            self.end_time = datetime.now()
            
        except Exception as e:
            self.status = "失败"
            self.error_message = str(e)
            self.end_time = datetime.now()
            logging.error(f"任务 {self.task_id} 执行失败: {e}")

class MultiTaskFileReaderGUI:
    """多任务文件解读GUI"""
    
    def __init__(self):
        self.root = tb.Window(themename="flatly")
        self.root.title("多任务文件解读管理器")
        self.root.geometry("1000x700")
        
        # 任务管理
        self.tasks: Dict[str, FileReadTask] = {}
        self.task_counter = 0
        
        # 创建界面
        self.create_widgets()
        
        # 启动状态更新线程
        self.update_thread = threading.Thread(target=self._update_status_loop, daemon=True)
        self.update_thread.start()
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = tb.Frame(self.root, padding="10")
        main_frame.pack(fill=BOTH, expand=True)
        
        # 标题
        title_label = tb.Label(
            main_frame,
            text="多任务文件解读管理器",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        # 说明文字
        desc_label = tb.Label(
            main_frame,
            text="可以同时启动多个文件解读任务，每个任务独立处理不同的文件夹",
            font=('Arial', 10)
        )
        desc_label.pack(pady=(0, 20))
        
        # 创建任务区域
        self.create_task_creation_area(main_frame)
        
        # 任务列表区域
        self.create_task_list_area(main_frame)
        
        # 控制按钮区域
        self.create_control_buttons(main_frame)
    
    def create_task_creation_area(self, parent):
        """创建任务创建区域"""
        creation_frame = tb.LabelFrame(parent, text="创建新任务", padding="10")
        creation_frame.pack(fill=X, pady=(0, 10))
        
        # 文件夹选择
        folder_frame = tb.Frame(creation_frame)
        folder_frame.pack(fill=X, pady=(0, 10))
        
        tb.Label(folder_frame, text="选择文件夹:", font=('Arial', 10)).pack(side=LEFT)
        
        self.folder_var = tb.StringVar()
        folder_entry = tb.Entry(folder_frame, textvariable=self.folder_var, width=50)
        folder_entry.pack(side=LEFT, padx=(10, 5), fill=X, expand=True)
        
        def select_folder():
            directory = filedialog.askdirectory(title="选择要解读的文件夹")
            if directory:
                self.folder_var.set(directory)
        
        tb.Button(
            folder_frame,
            text="浏览",
            command=select_folder,
            style='secondary.TButton'
        ).pack(side=LEFT, padx=(5, 0))
        
        # 参数设置
        params_frame = tb.Frame(creation_frame)
        params_frame.pack(fill=X, pady=(0, 10))
        
        tb.Label(params_frame, text="摘要长度:", font=('Arial', 10)).pack(side=LEFT)
        
        self.summary_length_var = tb.IntVar(value=200)
        summary_scale = tb.Scale(
            params_frame,
            from_=100,
            to=500,
            variable=self.summary_length_var,
            orient=HORIZONTAL,
            length=200
        )
        summary_scale.pack(side=LEFT, padx=(10, 5))
        
        self.summary_length_label = tb.Label(params_frame, text="200字符", font=('Arial', 9))
        self.summary_length_label.pack(side=LEFT, padx=(5, 0))
        
        # 绑定摘要长度变化事件
        def update_summary_label(*args):
            value = self.summary_length_var.get()
            self.summary_length_label.config(text=f"{value}字符")
        
        self.summary_length_var.trace_add('write', update_summary_label)
        
        # 创建任务按钮
        def create_task():
            folder_path = self.folder_var.get().strip()
            if not folder_path:
                messagebox.showwarning("提示", "请先选择要解读的文件夹")
                return
            
            if not os.path.exists(folder_path):
                messagebox.showerror("错误", "选择的文件夹不存在")
                return
            
            # 检查是否已有相同文件夹的任务
            for task in self.tasks.values():
                if task.folder_path == folder_path and task.status in ["等待中", "运行中"]:
                    messagebox.showwarning("提示", "该文件夹已有正在运行的任务")
                    return
            
            self.task_counter += 1
            task_id = f"Task_{self.task_counter}"
            
            # 创建新任务
            task = FileReadTask(
                task_id=task_id,
                folder_path=folder_path,
                summary_length=self.summary_length_var.get()
            )
            
            self.tasks[task_id] = task
            
            # 清空输入
            self.folder_var.set("")
            
            # 刷新任务列表
            self.refresh_task_list()
            
            # 自动启动任务
            task.start()
            
            messagebox.showinfo("成功", f"任务 {task_id} 已创建并开始运行")
        
        tb.Button(
            creation_frame,
            text="创建并启动任务",
            command=create_task,
            bootstyle=SUCCESS
        ).pack()
    
    def create_task_list_area(self, parent):
        """创建任务列表区域"""
        list_frame = tb.LabelFrame(parent, text="任务列表", padding="10")
        list_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
        
        # 创建Treeview，添加勾选列
        columns = ('选择', '任务ID', '文件夹', '状态', '进度', '当前文件', '成功/失败/跳过/更新', '开始时间')
        self.task_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        
        # 设置列标题
        for col in columns:
            self.task_tree.heading(col, text=col)
            self.task_tree.column(col, width=80)
        
        # 设置特定列的宽度
        self.task_tree.column('选择', width=60)
        self.task_tree.column('任务ID', width=100)
        self.task_tree.column('文件夹', width=200)
        self.task_tree.column('当前文件', width=150)
        self.task_tree.column('开始时间', width=150)
        self.task_tree.column('成功/失败/跳过/更新', width=180)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.task_tree.yview)
        self.task_tree.configure(yscrollcommand=scrollbar.set)
        
        self.task_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # 绑定点击事件处理勾选
        self.task_tree.bind('<Button-1>', self.on_tree_click)
        
        # 绑定双击事件查看详情
        self.task_tree.bind('<Double-1>', self.on_task_double_click)
        
        # 存储勾选状态
        self.checked_items = set()
    
    def on_tree_click(self, event):
        """处理树形控件的点击事件"""
        region = self.task_tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.task_tree.identify_column(event.x)
            item = self.task_tree.identify_row(event.y)
            
            # 如果点击的是第一列（选择列）
            if column == '#1' and item:
                self.toggle_checkbox(item)
    
    def toggle_checkbox(self, item):
        """切换勾选状态"""
        if item in self.checked_items:
            self.checked_items.remove(item)
            self.task_tree.set(item, '选择', '☐')
        else:
            self.checked_items.add(item)
            self.task_tree.set(item, '选择', '☑')
    
    def get_selected_tasks(self):
        """获取选中的任务ID列表"""
        return list(self.checked_items)
    
    def select_all_tasks(self):
        """全选所有任务"""
        for item in self.task_tree.get_children():
            self.checked_items.add(item)
            self.task_tree.set(item, '选择', '☑')
    
    def deselect_all_tasks(self):
        """取消全选"""
        for item in self.task_tree.get_children():
            self.checked_items.discard(item)
            self.task_tree.set(item, '选择', '☐')
    
    def create_control_buttons(self, parent):
        """创建控制按钮区域"""
        button_frame = tb.Frame(parent)
        button_frame.pack(fill=X, pady=(0, 10))
        
        def stop_selected_task():
            selected_tasks = self.get_selected_tasks()
            if not selected_tasks:
                messagebox.showwarning("提示", "请先勾选要停止的任务")
                return
            
            stopped_count = 0
            for task_id in selected_tasks:
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    if task.status == "运行中":
                        task.stop()
                        stopped_count += 1
            
            if stopped_count > 0:
                messagebox.showinfo("成功", f"已停止 {stopped_count} 个任务")
                # 取消勾选
                self.deselect_all_tasks()
            else:
                messagebox.showinfo("提示", "选中的任务都不在运行状态")
        
        def restart_selected_task():
            selected_tasks = self.get_selected_tasks()
            if not selected_tasks:
                messagebox.showwarning("提示", "请先勾选要重启的任务")
                return
            
            restart_count = 0
            for task_id in selected_tasks:
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    if task.status in ["已停止", "失败"]:
                        # 重置任务状态
                        task.status = "等待中"
                        task.progress = 0.0
                        task.current_file = ""
                        task.processed_files = 0
                        task.successful_reads = 0
                        task.failed_reads = 0
                        task.skipped_reads = 0
                        task.path_updated_reads = 0
                        task.start_time = None
                        task.end_time = None
                        task.error_message = ""
                        task.stop_flag = False
                        
                        # 重新启动任务
                        task.start()
                        restart_count += 1
            
            if restart_count > 0:
                messagebox.showinfo("成功", f"已重启 {restart_count} 个任务")
                # 取消勾选
                self.deselect_all_tasks()
            else:
                messagebox.showinfo("提示", "选中的任务都无法重启（只有已停止或失败的任务可以重启）")
        
        def remove_selected_task():
            selected_tasks = self.get_selected_tasks()
            if not selected_tasks:
                messagebox.showwarning("提示", "请先勾选要删除的任务")
                return
            
            # 检查是否有正在运行的任务
            running_tasks = []
            for task_id in selected_tasks:
                if task_id in self.tasks and self.tasks[task_id].status == "运行中":
                    running_tasks.append(task_id)
            
            if running_tasks:
                if not messagebox.askyesno("确认", f"有 {len(running_tasks)} 个任务正在运行，确定要删除吗？"):
                    return
            
            # 删除任务
            deleted_count = 0
            for task_id in selected_tasks:
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    if task.status == "运行中":
                        task.stop()
                    del self.tasks[task_id]
                    deleted_count += 1
            
            self.refresh_task_list()
            messagebox.showinfo("成功", f"已删除 {deleted_count} 个任务")
            # 取消勾选
            self.deselect_all_tasks()
        
        def clear_completed_tasks():
            completed_tasks = []
            for task_id, task in self.tasks.items():
                if task.status in ["已完成", "失败", "已停止"]:
                    completed_tasks.append(task_id)
            
            if not completed_tasks:
                messagebox.showinfo("提示", "没有已完成的任务")
                return
            
            if messagebox.askyesno("确认", f"确定要删除 {len(completed_tasks)} 个已完成的任务吗？"):
                for task_id in completed_tasks:
                    del self.tasks[task_id]
                self.refresh_task_list()
                messagebox.showinfo("成功", f"已删除 {len(completed_tasks)} 个已完成的任务")
        
        def show_statistics():
            total_tasks = len(self.tasks)
            running_tasks = sum(1 for task in self.tasks.values() if task.status == "运行中")
            completed_tasks = sum(1 for task in self.tasks.values() if task.status == "已完成")
            failed_tasks = sum(1 for task in self.tasks.values() if task.status == "失败")
            stopped_tasks = sum(1 for task in self.tasks.values() if task.status == "已停止")
            
            total_files = sum(task.total_files for task in self.tasks.values())
            total_successful = sum(task.successful_reads for task in self.tasks.values())
            total_failed = sum(task.failed_reads for task in self.tasks.values())
            total_skipped = sum(task.skipped_reads for task in self.tasks.values())
            total_path_updated = sum(task.path_updated_reads for task in self.tasks.values())
            
            stats_text = f"""
任务统计:
- 总任务数: {total_tasks}
- 运行中: {running_tasks}
- 已完成: {completed_tasks}
- 失败: {failed_tasks}
- 已停止: {stopped_tasks}

文件统计:
- 总文件数: {total_files}
- 成功解读: {total_successful}
- 解读失败: {total_failed}
- 跳过文件: {total_skipped}
- 路径更新: {total_path_updated}
- 成功率: {total_successful/(total_files-total_skipped)*100:.1f}% (排除跳过的文件)
            """
            
            messagebox.showinfo("统计信息", stats_text)
        
        # 按钮布局
        tb.Button(
            button_frame,
            text="全选",
            command=self.select_all_tasks,
            style='secondary.TButton'
        ).pack(side=LEFT, padx=(0, 5))
        
        tb.Button(
            button_frame,
            text="取消全选",
            command=self.deselect_all_tasks,
            style='secondary.TButton'
        ).pack(side=LEFT, padx=(0, 10))
        
        tb.Button(
            button_frame,
            text="停止选中任务",
            command=stop_selected_task,
            bootstyle=WARNING
        ).pack(side=LEFT, padx=(0, 10))
        
        tb.Button(
            button_frame,
            text="重启选中任务",
            command=restart_selected_task,
            bootstyle=SUCCESS
        ).pack(side=LEFT, padx=(0, 10))
        
        tb.Button(
            button_frame,
            text="删除选中任务",
            command=remove_selected_task,
            bootstyle=DANGER
        ).pack(side=LEFT, padx=(0, 10))
        
        tb.Button(
            button_frame,
            text="清理已完成任务",
            command=clear_completed_tasks,
            style='secondary.TButton'
        ).pack(side=LEFT, padx=(0, 10))
        
        tb.Button(
            button_frame,
            text="查看统计信息",
            command=show_statistics,
            bootstyle=INFO
        ).pack(side=LEFT, padx=(0, 10))
    
    def refresh_task_list(self):
        """刷新任务列表"""
        # 保存当前勾选状态
        old_checked = self.checked_items.copy()
        
        # 清空现有项目
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        
        # 清空勾选状态
        self.checked_items.clear()
        
        # 添加任务
        for task_id, task in self.tasks.items():
            start_time_str = task.start_time.strftime("%H:%M:%S") if task.start_time else ""
            
            item = self.task_tree.insert('', 'end', task_id, values=(
                '☐',  # 勾选框
                task_id,
                os.path.basename(task.folder_path),
                task.status,
                f"{task.progress:.1f}%",
                task.current_file,
                f"{task.successful_reads}/{task.failed_reads}/{task.skipped_reads}/{task.path_updated_reads}",
                start_time_str
            ))
            
            # 恢复勾选状态
            if task_id in old_checked:
                self.checked_items.add(task_id)
                self.task_tree.set(task_id, '选择', '☑')
    
    def on_task_double_click(self, event):
        """双击任务显示详情（保留原有功能）"""
        region = self.task_tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.task_tree.identify_column(event.x)
            item = self.task_tree.identify_row(event.y)
            
            # 如果双击的不是第一列（选择列），显示详情
            if column != '#1' and item and item in self.tasks:
                task = self.tasks[item]
                self.show_task_details(task)
    
    def show_task_details(self, task):
        """显示任务详情"""
        details_window = tk.Toplevel(self.root)
        details_window.title(f"任务详情 - {task.task_id}")
        details_window.geometry("600x400")
        
        # 详情内容
        details_text = f"""
任务ID: {task.task_id}
文件夹路径: {task.folder_path}
状态: {task.status}
进度: {task.progress:.1f}%
当前文件: {task.current_file}
总文件数: {task.total_files}
已处理: {task.processed_files}
成功解读: {task.successful_reads}
解读失败: {task.failed_reads}
跳过文件: {task.skipped_reads}
路径更新: {task.path_updated_reads}
开始时间: {task.start_time.strftime("%Y-%m-%d %H:%M:%S") if task.start_time else "未开始"}
结束时间: {task.end_time.strftime("%Y-%m-%d %H:%M:%S") if task.end_time else "未结束"}
摘要长度: {task.summary_length}字符
        """
        
        if task.error_message:
            details_text += f"\n错误信息: {task.error_message}"
        
        # 计算运行时间
        if task.start_time and task.end_time:
            duration = task.end_time - task.start_time
            details_text += f"\n运行时间: {duration}"
        elif task.start_time:
            duration = datetime.now() - task.start_time
            details_text += f"\n运行时间: {duration}"
        
        # 显示详情
        text_widget = tk.Text(details_window, wrap=tk.WORD, padx=10, pady=10)
        text_widget.pack(fill=BOTH, expand=True)
        text_widget.insert('1.0', details_text)
        text_widget.config(state=tk.DISABLED)
    
    def _update_status_loop(self):
        """状态更新循环"""
        while True:
            try:
                # 在主线程中更新UI
                self.root.after(0, self.refresh_task_list)
                time.sleep(1)  # 每秒更新一次
            except:
                break
    
    def run(self):
        """运行GUI"""
        self.root.mainloop()

def main():
    """主函数"""
    app = MultiTaskFileReaderGUI()
    app.run()

if __name__ == "__main__":
    main() 