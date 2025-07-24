#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文件整理器 - 分页版GUI应用
将智能分类和文件分类功能分离到不同的分页中
"""

import ttkbootstrap as tb
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
from file_duplicate_cleaner import remove_duplicate_files
from file_reader import FileReader
from transfer_log_manager import TransferLogManager

class FileOrganizerTabGUI:
    """文件整理器分页图形用户界面类"""
    
    def __init__(self):
        """初始化 GUI 应用"""
        self.root = tb.Window(themename="flatly")
        self.root.title("智能文件管理系统")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        # 初始化变量
        self.source_directory = tb.StringVar()  # 源目录路径
        self.target_directory = tb.StringVar()  # 目标目录路径
        
        # AI分类参数
        self.summary_length = tb.IntVar(value=100)  # 摘要长度，默认100字符
        self.content_truncate = tb.IntVar(value=500)  # 内容截取，默认500字符
        
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
        
    def center_window(self):
        """将窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
    def initialize_organizers(self):
        """初始化文件整理器"""
        try:
            # 优先使用新的智能文件分类器
            try:
                from smart_file_classifier_adapter import SmartFileClassifierAdapter
                self.ai_organizer = SmartFileClassifierAdapter(model_name=None, enable_transfer_log=True)
                self.log_message("新的智能文件分类器初始化完成")
            except ImportError:
                # 如果新分类器不可用，回退到旧分类器
                from file_organizer_ai import FileOrganizer as AIFileOrganizer
                self.ai_organizer = AIFileOrganizer(model_name=None, enable_transfer_log=True)
                self.log_message("使用旧版AI文件整理器（新分类器不可用）")
            
            from file_organizer_simple import FileOrganizer as SimpleFileOrganizer
            self.simple_organizer = SimpleFileOrganizer(enable_transfer_log=True)
            
            self.log_message("文件整理器初始化完成")
        except Exception as e:
            self.log_message(f"文件整理器初始化失败: {e}")
            messagebox.showerror("错误", f"文件整理器初始化失败: {e}")
        
    def create_widgets(self):
        """创建界面组件"""
        # 创建主框架
        main_frame = tb.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(W, E, N, S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 标题
        title_label = tb.Label(
            main_frame, 
            text="智能文件管理系统", 
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # 创建分页控件
        self.notebook = tb.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky=(W, E, N, S))
        
        # 创建文件解读页面
        self.create_file_reader_tab()
        
        # 创建微信信息管理页面
        try:
            from weixin_manager_gui import WeixinManagerTab
            self.weixin_manager_tab = WeixinManagerTab(self.notebook, log_callback=self.log_message)
        except Exception as e:
            print(f"微信信息管理模块加载失败: {e}")
        
        # 创建文章阅读助手页面
        self.create_article_reader_tab()
        
        # 创建智能分类页面
        self.create_ai_classification_tab()
        
        # 创建文件分类页面
        self.create_simple_classification_tab()
        
        # 创建工具页面
        self.create_tools_tab()
        
        # 日志显示区域
        log_frame = tb.LabelFrame(main_frame, text="操作日志", padding="5")
        log_frame.grid(row=2, column=0, sticky=(W, E, N, S), pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = ScrolledText(
            log_frame,
            height=6,
            wrap=WORD
        )
        self.log_text.grid(row=0, column=0, sticky=(W, E, N, S))
        
        # 配置主框架的行权重
        main_frame.rowconfigure(2, weight=0)
        
        # 初始化日志
        self.log_message("程序启动完成，请选择文件目录开始整理")
        
    def create_file_reader_tab(self):
        """创建文件解读页面"""
        reader_frame = tb.Frame(self.notebook, padding="10")
        self.notebook.add(reader_frame, text="文件解读")
        
        reader_frame.columnconfigure(1, weight=1)
        
        # 说明文字
        desc_label = tb.Label(
            reader_frame,
            text="选择文件夹，批量解读其中的所有文档，生成摘要并保存到AI结果文件",
            font=('Arial', 10)
        )
        desc_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 文件夹选择
        tb.Label(reader_frame, text="选择文件夹:").grid(row=1, column=0, sticky=W, pady=5)
        self.reader_folder_var = tb.StringVar()
        tb.Entry(
            reader_frame, 
            textvariable=self.reader_folder_var, 
            width=50
        ).grid(row=1, column=1, sticky=(W, E), padx=(10, 5), pady=5)
        
        def select_reader_folder():
            directory = filedialog.askdirectory(title="选择要批量解读的文件夹")
            if directory:
                self.reader_folder_var.set(directory)
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
                    self.reader_status_label.config(text=f"已选择文件夹，发现 {file_count} 个可解读文档")
                    self.log_message(f"已选择解读文件夹: {directory}，发现 {file_count} 个可解读文档")
                except Exception as e:
                    self.reader_status_label.config(text="文件夹扫描失败")
                    self.log_message(f"扫描文件夹失败: {e}")
        
        tb.Button(
            reader_frame, 
            text="浏览", 
            command=select_reader_folder
        ).grid(row=1, column=2, pady=5)
        
        # 摘要参数设置
        params_frame = tb.LabelFrame(reader_frame, text="摘要参数设置", padding="10")
        params_frame.grid(row=2, column=0, columnspan=3, sticky=(W, E), pady=10)
        params_frame.columnconfigure(1, weight=1)
        
        # 摘要长度调节
        tb.Label(params_frame, text="文章摘要长度:").grid(row=0, column=0, sticky=W, pady=5)
        summary_frame = tb.Frame(params_frame)
        summary_frame.grid(row=0, column=1, sticky=(W, E), padx=(10, 0), pady=5)
        summary_frame.columnconfigure(1, weight=1)
        
        self.reader_summary_length = tb.IntVar(value=200)
        
        tb.Label(summary_frame, text="100字").grid(row=0, column=0)
        reader_summary_scale = tb.Scale(
            summary_frame, 
            from_=100, 
            to=500, 
            variable=self.reader_summary_length,
            orient=HORIZONTAL
        )
        reader_summary_scale.grid(row=0, column=1, sticky=(W, E), padx=5)
        tb.Label(summary_frame, text="500字").grid(row=0, column=2)
        self.reader_summary_value_label = tb.Label(summary_frame, text="200字符")
        self.reader_summary_value_label.grid(row=0, column=3, padx=(10, 0))
        
        # 绑定摘要长度变化事件
        def update_reader_summary_label(*args):
            value = self.reader_summary_length.get()
            self.reader_summary_value_label.config(text=f"{int(value)}字符")
        
        self.reader_summary_length.trace_add('write', update_reader_summary_label)
        
        # 操作按钮
        button_frame = tb.Frame(reader_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=20)
        
        def start_batch_reading():
            folder_path = self.reader_folder_var.get().strip()
            if not folder_path:
                messagebox.showwarning("提示", "请先选择要解读的文件夹")
                return
            
            if not os.path.exists(folder_path):
                messagebox.showerror("错误", "选择的文件夹不存在")
                return
            
            self.log_message("开始批量文档解读...")
            self.reader_status_label.config(text="正在解读文档...")
            self.reader_start_button.config(state='disabled')
            
            # 在新线程中执行批量解读
            threading.Thread(target=self._batch_read_worker, args=(folder_path,), daemon=True).start()
        
        self.reader_start_button = tb.Button(
            button_frame,
            text="开始批量解读",
            command=start_batch_reading,
            bootstyle=SUCCESS
        )
        self.reader_start_button.pack(side=LEFT, padx=5)
        
        # 进度条
        self.reader_progress_var = tb.DoubleVar()
        self.reader_progress_bar = tb.Progressbar(
            reader_frame,
            variable=self.reader_progress_var,
            maximum=100
        )
        self.reader_progress_bar.grid(row=4, column=0, columnspan=3, sticky=(W, E), pady=10)
        
        # 状态标签
        self.reader_status_label = tb.Label(reader_frame, text="请选择要解读的文件夹")
        self.reader_status_label.grid(row=5, column=0, columnspan=3, pady=5)
        
    def create_article_reader_tab(self):
        """创建文章阅读助手页面"""
        article_frame = tb.Frame(self.notebook, padding="10")
        self.notebook.add(article_frame, text="文章阅读助手")
        
        # 说明文字
        desc_label = tb.Label(
            article_frame,
            text="启动文章阅读助手服务器，在浏览器中查看和管理AI分析结果",
            font=('Arial', 10)
        )
        desc_label.pack(pady=(0, 20))
        
        # 功能说明
        features_frame = tb.LabelFrame(article_frame, text="功能特性", padding="10")
        features_frame.pack(fill=X, pady=(0, 20))
        
        features_text = [
            "• 查看AI分析结果和文件摘要",
            "• 直接打开文件进行查看",
            "• 重复解读后点击刷新删除重复记录",
            "• 友好的Web界面"
        ]
        
        for feature in features_text:
            tb.Label(features_frame, text=feature, font=('Arial', 9)).pack(anchor=W, pady=2)
        
        # 操作按钮
        button_frame = tb.Frame(article_frame)
        button_frame.pack(pady=20)
        
        def start_article_reader():
            try:
                import subprocess
                import sys
                import socket
                
                # 检查是否已经有服务器在运行
                def check_port(port):
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.settimeout(1)
                            result = s.connect_ex(('localhost', port))
                            return result == 0
                    except:
                        return False
                
                # 检查8000和8001端口
                if check_port(8000) or check_port(8001):
                    self.log_message("检测到已有服务器运行，请直接在浏览器访问 http://localhost:8000/ai_result_viewer.html 或 http://localhost:8001/ai_result_viewer.html")
                    messagebox.showinfo("提示", "检测到文章阅读助手已在运行！\n请在浏览器访问 http://localhost:8000/ai_result_viewer.html 或 http://localhost:8001/ai_result_viewer.html")
                    return
                
                # 启动查看器服务器
                process = subprocess.Popen([sys.executable, "start_viewer_server.py"], 
                                         cwd=os.getcwd(), 
                                         creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
                
                # 存储进程引用以便后续管理
                if not hasattr(self, 'article_reader_processes'):
                    self.article_reader_processes = []
                self.article_reader_processes.append(process)
                
                self.log_message("已启动文章阅读助手服务器")
                messagebox.showinfo("提示", "文章阅读助手已启动！\n\n服务器正在启动中，请稍后在浏览器访问：\nhttp://localhost:8000/ai_result_viewer.html 或 http://localhost:8001/ai_result_viewer.html\n关闭浏览器时服务器会自动停止。")
            except Exception as e:
                self.log_message(f"启动文章阅读助手失败: {e}")
                messagebox.showerror("错误", f"启动文章阅读助手失败: {e}")
        
        tb.Button(
            button_frame,
            text="启动文章阅读助手",
            command=start_article_reader,
            bootstyle=SUCCESS
        ).pack()
        
        # 状态信息
        status_frame = tb.LabelFrame(article_frame, text="使用说明", padding="10")
        status_frame.pack(fill=X, pady=(20, 0))
        
        instructions = [
            "1. 点击上方按钮启动文章阅读助手",
            "2. 服务器将在新的控制台窗口中运行",
            "3. 浏览器会自动打开AI结果查看页面",
            "4. 使用完毕后，直接关闭浏览器即可自动停止服务器"
        ]
        
        for instruction in instructions:
            tb.Label(status_frame, text=instruction, font=('Arial', 9)).pack(anchor=W, pady=2)
        
    def create_ai_classification_tab(self):
        """创建智能分类页面"""
        ai_frame = tb.Frame(self.notebook, padding="10")
        self.notebook.add(ai_frame, text="智能分类")
        
        ai_frame.columnconfigure(1, weight=1)
        
        # 说明文字
        desc_label = tb.Label(
            ai_frame,
            text="使用 AI 智能分析文件内容，自动将文件分类到合适的文件夹中",
            font=('Arial', 10)
        )
        desc_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 源目录选择
        tb.Label(ai_frame, text="待整理文件目录:").grid(row=1, column=0, sticky=W, pady=5)
        tb.Entry(
            ai_frame, 
            textvariable=self.source_directory, 
            width=50
        ).grid(row=1, column=1, sticky=(W, E), padx=(10, 5), pady=5)
        tb.Button(
            ai_frame, 
            text="浏览", 
            command=self.select_source_directory
        ).grid(row=1, column=2, pady=5)
        
        # 目标目录选择
        tb.Label(ai_frame, text="目标分类目录:").grid(row=2, column=0, sticky=W, pady=5)
        tb.Entry(
            ai_frame, 
            textvariable=self.target_directory, 
            width=50
        ).grid(row=2, column=1, sticky=(W, E), padx=(10, 5), pady=5)
        tb.Button(
            ai_frame, 
            text="浏览", 
            command=self.select_target_directory
        ).grid(row=2, column=2, pady=5)
        
        # AI参数调节区域
        params_frame = tb.LabelFrame(ai_frame, text="AI参数设置", padding="10")
        params_frame.grid(row=3, column=0, columnspan=3, sticky=(W, E), pady=10)
        params_frame.columnconfigure(1, weight=1)
        
        # 摘要长度调节
        tb.Label(params_frame, text="摘要长度:").grid(row=0, column=0, sticky=W, pady=5)
        summary_frame = tb.Frame(params_frame)
        summary_frame.grid(row=0, column=1, sticky=(W, E), padx=(10, 0), pady=5)
        summary_frame.columnconfigure(1, weight=1)
        
        tb.Label(summary_frame, text="50").grid(row=0, column=0)
        self.summary_scale = tb.Scale(
            summary_frame, 
            from_=50, 
            to=200, 
            variable=self.summary_length,
            orient=HORIZONTAL
        )
        self.summary_scale.grid(row=0, column=1, sticky=(W, E), padx=5)
        tb.Label(summary_frame, text="200").grid(row=0, column=2)
        self.summary_value_label = tb.Label(summary_frame, text="100字符")
        self.summary_value_label.grid(row=0, column=3, padx=(10, 0))
        
        # 绑定摘要长度变化事件
        self.summary_length.trace_add('write', self.update_summary_label)
        
        # 字符截取调节
        tb.Label(params_frame, text="内容截取:").grid(row=1, column=0, sticky=W, pady=5)
        truncate_frame = tb.Frame(params_frame)
        truncate_frame.grid(row=1, column=1, sticky=(W, E), padx=(10, 0), pady=5)
        truncate_frame.columnconfigure(1, weight=1)
        
        tb.Label(truncate_frame, text="200").grid(row=0, column=0)
        self.truncate_scale = tb.Scale(
            truncate_frame, 
            from_=200, 
            to=2000, 
            variable=self.content_truncate,
            orient=HORIZONTAL
        )
        self.truncate_scale.grid(row=0, column=1, sticky=(W, E), padx=5)
        tb.Label(truncate_frame, text="全文").grid(row=0, column=2)
        self.truncate_value_label = tb.Label(truncate_frame, text="500字符")
        self.truncate_value_label.grid(row=0, column=3, padx=(10, 0))
        
        # 绑定字符截取变化事件
        self.content_truncate.trace_add('write', self.update_truncate_label)
        
        # 操作按钮框架
        ai_button_frame = tb.Frame(ai_frame)
        ai_button_frame.grid(row=4, column=0, columnspan=3, pady=20)
        

        
        # 开始整理按钮
        self.ai_organize_button = tb.Button(
            ai_button_frame,
            text="开始AI智能整理",
            command=self.ai_start_organize
        )
        self.ai_organize_button.pack(side=LEFT, padx=5)
        
        # 进度条
        self.ai_progress_var = tb.DoubleVar()
        self.ai_progress_bar = tb.Progressbar(
            ai_frame,
            variable=self.ai_progress_var,
            maximum=100
        )
        self.ai_progress_bar.grid(row=5, column=0, columnspan=3, sticky=(W, E), pady=10)
        
        # 状态标签
        self.ai_status_label = tb.Label(ai_frame, text="请选择源目录和目标目录")
        self.ai_status_label.grid(row=6, column=0, columnspan=3, pady=5)
        
    def create_simple_classification_tab(self):
        """创建文件分类页面"""
        simple_frame = tb.Frame(self.notebook, padding="10")
        self.notebook.add(simple_frame, text="文件分类")
        
        simple_frame.columnconfigure(1, weight=1)
        
        # 说明文字
        desc_label = tb.Label(
            simple_frame,
            text="基于文件名和扩展名进行快速分类，适合简单的文件整理需求",
            font=('Arial', 10)
        )
        desc_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 源目录选择
        tb.Label(simple_frame, text="待整理文件目录:").grid(row=1, column=0, sticky=W, pady=5)
        tb.Entry(
            simple_frame, 
            textvariable=self.source_directory, 
            width=50
        ).grid(row=1, column=1, sticky=(W, E), padx=(10, 5), pady=5)
        tb.Button(
            simple_frame, 
            text="浏览", 
            command=self.select_source_directory
        ).grid(row=1, column=2, pady=5)
        
        # 目标目录选择
        tb.Label(simple_frame, text="目标分类目录:").grid(row=2, column=0, sticky=W, pady=5)
        tb.Entry(
            simple_frame, 
            textvariable=self.target_directory, 
            width=50
        ).grid(row=2, column=1, sticky=(W, E), padx=(10, 5), pady=5)
        tb.Button(
            simple_frame, 
            text="浏览", 
            command=self.select_target_directory
        ).grid(row=2, column=2, pady=5)
        
        # 操作按钮框架
        simple_button_frame = tb.Frame(simple_frame)
        simple_button_frame.grid(row=3, column=0, columnspan=3, pady=20)
        

        
        # 开始整理按钮
        self.simple_organize_button = tb.Button(
            simple_button_frame,
            text="开始文件分类整理",
            command=self.simple_start_organize,
            bootstyle=SUCCESS
        )
        self.simple_organize_button.pack(side=LEFT, padx=5)
        
        # 进度条
        self.simple_progress_var = tb.DoubleVar()
        self.simple_progress_bar = tb.Progressbar(
            simple_frame,
            variable=self.simple_progress_var,
            maximum=100
        )
        self.simple_progress_bar.grid(row=4, column=0, columnspan=3, sticky=(W, E), pady=10)
        
        # 状态标签
        self.simple_status_label = tb.Label(simple_frame, text="请选择源目录和目标目录")
        self.simple_status_label.grid(row=5, column=0, columnspan=3, pady=5)
        
    def create_tools_tab(self):
        """创建工具页面"""
        tools_frame = tb.Frame(self.notebook, padding="10")
        self.notebook.add(tools_frame, text="工具")
        
        # 工具按钮框架
        tools_button_frame = tb.Frame(tools_frame)
        tools_button_frame.grid(row=0, column=0, pady=20)
        
        # 文件目录智能整理按钮（第一个）
        self.directory_organize_button = tb.Button(
            tools_button_frame,
            text="文件目录智能整理",
            command=self.show_directory_organize_dialog
        )
        self.directory_organize_button.pack(side=LEFT, padx=5)
        
        # 重复文件删除按钮（第二个）
        self.duplicate_button = tb.Button(
            tools_button_frame,
            text="删除重复文件",
            command=self.show_duplicate_removal_dialog
        )
        self.duplicate_button.pack(side=LEFT, padx=5)
        

        
        # 日志按钮（第二个）
        self.log_button = tb.Button(
            tools_button_frame,
            text="日志",
            command=self.show_transfer_logs
        )
        self.log_button.pack(side=LEFT, padx=5)
        
        # 分类规则管理按钮
        self.classification_rules_button = tb.Button(
            tools_button_frame,
            text="分类规则管理",
            command=self.show_classification_rules_manager
        )
        self.classification_rules_button.pack(side=LEFT, padx=5)
        
        # AI模型配置按钮
        self.ai_model_config_button = tb.Button(
            tools_button_frame,
            text="AI模型配置",
            command=self.show_ai_model_config
        )
        self.ai_model_config_button.pack(side=LEFT, padx=5)
        
    def update_summary_label(self, *args):
        """更新摘要长度标签"""
        value = self.summary_length.get()
        self.summary_value_label.config(text=f"{value}字符")
        
    def update_truncate_label(self, *args):
        """更新字符截取标签"""
        value = self.content_truncate.get()
        if value >= 2000:
            self.truncate_value_label.config(text="全文")
        else:
            self.truncate_value_label.config(text=f"{value}字符")
        
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
            
    def log_message(self, message):
        """记录日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(END, log_entry)
        self.log_text.see(END)
        

            

            
    def _batch_read_worker(self, folder_path):
        """批量解读工作线程"""
        try:
            # 初始化AI文件整理器
            if not self.ai_organizer:
                self.initialize_organizers()
            
            # 定义进度回调函数
            def progress_callback(current, total, filename):
                progress = (current / total) * 100 if total > 0 else 0
                self.root.after(0, lambda: self.reader_progress_var.set(progress))
                self.root.after(0, lambda: self.reader_status_label.config(text=f"正在解读 ({current}/{total}): {filename}"))
            
            # 调用批量文档解读方法
            batch_results = self.ai_organizer.batch_read_documents(
                folder_path=folder_path,
                progress_callback=progress_callback,
                summary_length=self.reader_summary_length.get()
            )
            
            # 显示结果
            def show_results():
                self.reader_status_label.config(text="批量解读完成")
                self.log_message(f"批量文档解读完成: 成功 {batch_results['successful_reads']}, 失败 {batch_results['failed_reads']}")
                messagebox.showinfo("完成", f"批量解读完成！\n\n成功解读: {batch_results['successful_reads']} 个\n解读失败: {batch_results['failed_reads']} 个\n\n结果已保存到: ai_organize_result.json")
            
            self.root.after(0, show_results)
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.log_message(f"批量文档解读失败: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"批量文档解读失败: {error_msg}"))
            self.root.after(0, lambda: self.reader_status_label.config(text="解读失败"))
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
            messagebox.showerror("错误", "请先选择源目录和目标目录")
            return
            
        # 确认对话框
        if not messagebox.askyesno(
            "确认整理",
            f"即将开始AI智能整理:\n\n源目录: {source}\n目标目录: {target}\n\n确定要继续吗？"
        ):
            return
            
        self.log_message("开始AI智能整理...")
        self.ai_status_label.config(text="正在整理文件...")
        self.ai_organize_button.config(state='disabled')
        
        # 在新线程中执行整理
        threading.Thread(target=self._ai_organize_worker, daemon=True).start()
        
    def _ai_organize_worker(self):
        """AI整理工作线程"""
        try:
            source = self.source_directory.get()
            target = self.target_directory.get()
            
            # 应用AI参数设置
            self._apply_ai_parameters()
            
            # 定义进度回调函数
            def progress_callback(current, total, filename):
                progress_percent = int((current / total) * 100)
                status_text = f"正在处理 {current}/{total}: {filename[:30]}{'...' if len(filename) > 30 else ''}"
                
                # 更新GUI进度条和状态
                self.root.after(0, lambda: self.ai_progress_var.set(progress_percent))
                self.root.after(0, lambda: self.ai_status_label.config(text=status_text))
                self.root.after(0, lambda: self.log_message(f"[{current}/{total}] 处理: {filename}"))
            
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
            self.root.after(0, lambda: messagebox.showerror("错误", f"AI整理失败: {error_msg}"))
        finally:
            self.root.after(0, lambda: self.ai_organize_button.config(state='normal'))
            self.root.after(0, lambda: self.ai_progress_var.set(0))
            self.root.after(0, lambda: self.ai_status_label.config(text="整理完成"))
            
    def simple_start_organize(self):
        """开始文件分类整理"""
        source = self.source_directory.get()
        target = self.target_directory.get()
        
        if not source or not target:
            messagebox.showerror("错误", "请先选择源目录和目标目录")
            return
            
        # 确认对话框
        if not messagebox.askyesno(
            "确认整理",
            f"即将开始文件分类整理:\n\n源目录: {source}\n目标目录: {target}\n\n确定要继续吗？"
        ):
            return
            
        self.log_message("开始文件分类整理...")
        self.simple_status_label.config(text="正在整理文件...")
        self.simple_organize_button.config(state='disabled')
        
        # 在新线程中执行整理
        threading.Thread(target=self._simple_organize_worker, daemon=True).start()
        
    def _simple_organize_worker(self):
        """文件分类整理工作线程"""
        try:
            source = self.source_directory.get()
            target = self.target_directory.get()
            
            # 定义进度回调函数
            def progress_callback(percent, status_text):
                self.root.after(0, lambda: self.simple_progress_var.set(percent))
                self.root.after(0, lambda: self.simple_status_label.config(text=status_text))
                self.root.after(0, lambda: self.log_message(f"[简单分类] {status_text}"))
            
            # 执行文件整理
            self.organize_results = self.simple_organizer.organize_files(
                source_directory=source, 
                target_directory=target,
                progress_callback=progress_callback
            )
            
            # 生成结果JSON文件
            self._generate_organize_result_json(self.organize_results, "simple_organize_result.json")
            
            # 更新进度
            self.root.after(0, lambda: self.simple_progress_var.set(100))
            
            # 显示结果
            self.root.after(0, lambda: self._show_organize_results("文件分类整理"))
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.log_message(f"文件分类整理失败: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"文件分类整理失败: {error_msg}"))
        finally:
            self.root.after(0, lambda: self.simple_organize_button.config(state='normal'))
            self.root.after(0, lambda: self.simple_progress_var.set(0))
            self.root.after(0, lambda: self.simple_status_label.config(text="整理完成"))
            
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
                text="确定",
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
                        
                        messagebox.showinfo("删除完成", result_msg)
                        
                    except Exception as e:
                        messagebox.showerror("删除失败", f"删除源文件时出错: {str(e)}")
                
                # 删除源文件按钮
                delete_button = tb.Button(
                    button_frame,
                    text="删除源文件",
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
            
            messagebox.showinfo("删除完成", result_msg)
            self.log_message(f"源文件删除完成: 成功 {deleted_count} 个，失败 {failed_count} 个")
            
        except Exception as e:
            error_msg = f"删除源文件时出错: {str(e)}"
            self.log_message(error_msg)
            messagebox.showerror("删除失败", error_msg)
    
    def show_transfer_logs(self):
        """显示转移日志管理界面"""
        try:
            # 检查转移日志功能是否可用
            if not self.ai_organizer.enable_transfer_log:
                messagebox.showwarning("功能不可用", "转移日志功能未启用")
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
                text="转移日志管理",
                font=('Arial', 14, 'bold')
            ).pack(pady=(0, 10))
            
            # 日志列表框架
            list_frame = tb.LabelFrame(main_frame, text="转移日志列表", padding="5")
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
                text="查看详情",
                command=lambda: self._show_log_details(log_tree)
            ).pack(side=tb.LEFT, padx=5)
            
            # 恢复文件按钮
            tb.Button(
                button_frame,
                text="恢复文件",
                command=lambda: self._restore_from_selected_log(log_tree)
            ).pack(side=tb.LEFT, padx=5)
            
            # 刷新按钮
            tb.Button(
                button_frame,
                text="刷新",
                command=lambda: self._load_transfer_logs(log_tree)
            ).pack(side=tb.LEFT, padx=5)
            
            # 清理旧日志按钮
            tb.Button(
                button_frame,
                text="清理旧日志",
                command=lambda: self._cleanup_old_logs(log_tree)
            ).pack(side=tb.LEFT, padx=5)
            
            # 关闭按钮
            tb.Button(
                button_frame,
                text="关闭",
                command=log_window.destroy
            ).pack(side=tb.RIGHT, padx=5)
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.log_message(f"显示转移日志失败: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"显示转移日志失败: {error_msg}"))
        

    def show_duplicate_removal_dialog(self):
        """显示重复文件删除对话框"""
        try:
            # 创建重复文件删除对话框
            duplicate_window = tb.Toplevel(self.root)
            duplicate_window.title("删除重复文件")
            duplicate_window.geometry("700x600")
            duplicate_window.transient(self.root)
            duplicate_window.grab_set()
            
            # 创建主框架
            main_frame = tb.Frame(duplicate_window, padding="10")
            main_frame.pack(fill=tb.BOTH, expand=True)
            
            # 标题
            tb.Label(
                main_frame,
                text="删除重复文件",
                font=('Arial', 12, 'bold')
            ).pack(pady=(0, 10))
            
            # 说明文字
            tb.Label(
                main_frame,
                text="选择要检查重复文件的目标文件夹\n重复判断标准：文件大小+MD5哈希值完全一致",
                font=('Arial', 10)
            ).pack(pady=(0, 15))
            
            # 文件夹选择框架
            folder_frame = tb.Frame(main_frame)
            folder_frame.pack(fill=tb.X, pady=(0, 15))
            
            tb.Label(folder_frame, text="目标文件夹:").pack(anchor=tb.W)
            
            # 文件夹列表框架
            folder_list_frame = tb.Frame(folder_frame)
            folder_list_frame.pack(fill=tb.X, pady=(5, 0))
            
            # 文件夹列表
            folder_listbox = tk.Listbox(folder_list_frame, height=4, selectmode=tk.EXTENDED)
            folder_listbox.pack(side=tb.LEFT, fill=tb.X, expand=True, padx=(0, 5))
            
            # 滚动条
            folder_scrollbar = ttk.Scrollbar(folder_list_frame, orient="vertical", command=folder_listbox.yview)
            folder_listbox.configure(yscrollcommand=folder_scrollbar.set)
            folder_scrollbar.pack(side=tb.RIGHT, fill=tb.Y)
            
            # 按钮框架
            folder_button_frame = tb.Frame(folder_frame)
            folder_button_frame.pack(fill=tb.X, pady=(5, 0))
            
            def select_folder():
                directory = filedialog.askdirectory(
                    title="选择要检查重复文件的文件夹",
                    initialdir=self.target_directory.get() or os.path.expanduser("~")
                )
                if directory:
                    # 检查是否已经添加过
                    if directory not in folder_listbox.get(0, tk.END):
                        folder_listbox.insert(tk.END, directory)
            
            def remove_selected_folder():
                selected_indices = folder_listbox.curselection()
                # 从后往前删除，避免索引变化
                for index in reversed(selected_indices):
                    folder_listbox.delete(index)
            
            def clear_all_folders():
                folder_listbox.delete(0, tk.END)
            
            tb.Button(folder_button_frame, text="添加文件夹", command=select_folder).pack(side=tb.LEFT, padx=(0, 5))
            tb.Button(folder_button_frame, text="移除选中", command=remove_selected_folder).pack(side=tb.LEFT, padx=(0, 5))
            tb.Button(folder_button_frame, text="清空列表", command=clear_all_folders).pack(side=tb.LEFT)
            
            # 选项框架
            options_frame = tb.LabelFrame(main_frame, text="选项", padding="5")
            options_frame.pack(fill=tb.X, pady=(0, 15))
            
            dry_run_var = tb.BooleanVar(value=True)
            tb.Checkbutton(
                options_frame,
                text="试运行模式（只检查不删除）",
                variable=dry_run_var
            ).pack(anchor=tb.W)
            
            # 保留策略选择
            keep_strategy_var = tb.StringVar(value="oldest")
            strategy_frame = tb.Frame(options_frame)
            strategy_frame.pack(fill=tb.X, pady=(5, 0))
            
            tb.Label(strategy_frame, text="保留策略:").pack(side=tb.LEFT)
            tb.Radiobutton(
                strategy_frame,
                text="保留最早的文件（默认）",
                variable=keep_strategy_var,
                value="oldest"
            ).pack(side=tb.LEFT, padx=(10, 20))
            tb.Radiobutton(
                strategy_frame,
                text="保留最新的文件",
                variable=keep_strategy_var,
                value="newest"
            ).pack(side=tb.LEFT)
            
            # 结果显示区域
            result_frame = tb.LabelFrame(main_frame, text="扫描结果", padding="5")
            result_frame.pack(fill=tb.BOTH, expand=True, pady=(0, 15))
            
            result_text = ScrolledText(
                result_frame,
                height=10,
                wrap=tb.WORD
            )
            result_text.pack(fill=tb.BOTH, expand=True)
            
            # 按钮框架（吸附底部，始终可见）
            button_frame = tb.Frame(main_frame)
            button_frame.pack(side=tb.BOTTOM, fill=tb.X, pady=(10, 0))
            
            def start_scan():
                selected_folders = list(folder_listbox.get(0, tk.END))
                if not selected_folders:
                    messagebox.showwarning("提示", "请先选择要检查的文件夹")
                    return
                
                # 验证所有文件夹
                invalid_folders = []
                for folder_path in selected_folders:
                    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
                        invalid_folders.append(folder_path)
                
                if invalid_folders:
                    messagebox.showerror("错误", f"以下文件夹不存在或不是有效目录:\n{chr(10).join(invalid_folders)}")
                    return
                
                # 清空结果显示
                result_text.delete(1.0, tb.END)
                result_text.insert(tb.END, "正在扫描重复文件...\n")
                
                # 在新线程中执行扫描
                def scan_worker():
                    try:
                        dry_run = dry_run_var.get()
                        keep_oldest = keep_strategy_var.get() == "oldest"
                        results = remove_duplicate_files(
                            target_folder_paths=selected_folders,
                            dry_run=dry_run,
                            keep_oldest=keep_oldest
                        )
                        # 分组展示所有重复文件
                        def update_results():
                            # result_text.config(state='normal')  # ttkbootstrap ScrolledText不支持state配置
                            result_text.delete(1.0, tb.END)
                            result_text.insert(tb.END, f"扫描完成！\n\n")
                            result_text.insert(tb.END, f"扫描文件夹: {len(selected_folders)} 个\n")
                            result_text.insert(tb.END, f"总文件数: {results['total_files_scanned']}\n")
                            result_text.insert(tb.END, f"重复文件组: {results['duplicate_groups_found']}\n")
                            result_text.insert(tb.END, f"重复文件数: {results['total_duplicates_found']}\n\n")
                            if results.get('duplicate_groups'):
                                for idx, group in enumerate(results['duplicate_groups'], 1):
                                    size = group['size']
                                    md5 = group['md5']
                                    files = group['files']
                                    result_text.insert(tb.END, f"重复文件组{idx}: (大小: {size} bytes, MD5: {md5}) 共{len(files)}个副本\n")
                                    for file_info in files:
                                        keep_flag = '【保留】' if file_info.get('keep') else '【待删】'
                                        from datetime import datetime
                                        ctime_str = datetime.fromtimestamp(file_info['ctime']).strftime('%Y-%m-%d %H:%M:%S') if 'ctime' in file_info else ''
                                        source_folder = file_info.get('source_folder', '')
                                        result_text.insert(tb.END, f"  - {file_info['relative_path']} {keep_flag} 来源: {source_folder} 创建时间: {ctime_str}\n")
                                    result_text.insert(tb.END, "\n")
                                
                                # 如果是试运行模式且发现重复文件，添加删除按钮
                                if dry_run and results['total_duplicates_found'] > 0:
                                    # 清除现有的删除按钮（如果有）
                                    for widget in button_frame.winfo_children():
                                        if hasattr(widget, 'delete_button_flag'):
                                            widget.destroy()
                                    
                                    # 添加删除重复文件按钮
                                    def delete_duplicates():
                                        if messagebox.askyesno("确认删除", f"确定要删除 {results['total_duplicates_found']} 个重复文件吗？\n\n此操作不可撤销！"):
                                            result_text.delete(1.0, tb.END)
                                            result_text.insert(tb.END, "正在删除重复文件...\n")
                                            
                                            def delete_worker():
                                                try:
                                                    keep_oldest = keep_strategy_var.get() == "oldest"
                                                    delete_results = remove_duplicate_files(
                                                        target_folder_paths=selected_folders,
                                                        dry_run=False,
                                                        keep_oldest=keep_oldest
                                                    )
                                                    
                                                    # 记录删除操作到转移日志
                                                    if self.ai_organizer and self.ai_organizer.enable_transfer_log and self.ai_organizer.transfer_log_manager:
                                                        try:
                                                            session_name = f"duplicate_removal_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                                                            log_session = self.ai_organizer.transfer_log_manager.start_transfer_session(session_name)
                                                            
                                                            for file_info in delete_results.get('files_deleted', []):
                                                                try:
                                                                    # file_info 是一个字典，包含 path, relative_path, size, md5, ctime 等字段
                                                                    file_path = file_info.get('path', '')
                                                                    file_size = file_info.get('size', 0)
                                                                    md5 = file_info.get('md5', '')
                                                                    ctime = file_info.get('ctime', 0)
                                                                    
                                                                    self.ai_organizer.transfer_log_manager.log_transfer_operation(
                                                                        source_path=file_path,
                                                                        target_path="",  # 删除操作没有目标路径
                                                                        operation_type="delete_duplicate",
                                                                        target_folder="重复文件删除",
                                                                        success=True,
                                                                        file_size=file_size,
                                                                        md5=md5,
                                                                        ctime=ctime
                                                                    )
                                                                except Exception as e:
                                                                    print(f"记录删除日志失败: {e}")
                                                            
                                                            self.ai_organizer.transfer_log_manager.end_transfer_session()
                                                        except Exception as e:
                                                            print(f"创建删除日志会话失败: {e}")
                                                    
                                                    def show_delete_results():
                                                        result_text.delete(1.0, tb.END)
                                                        result_text.insert(tb.END, f"删除完成！\n\n")
                                                        result_text.insert(tb.END, f"成功删除: {len(delete_results.get('files_deleted', []))} 个重复文件\n")
                                                        result_text.insert(tb.END, f"释放空间: {delete_results.get('space_freed', 0):,} 字节\n\n")
                                                        
                                                        if delete_results.get('files_deleted'):
                                                            result_text.insert(tb.END, "已删除的文件:\n")
                                                            for file_info in delete_results['files_deleted']:
                                                                file_path = file_info.get('path', '')
                                                                relative_path = file_info.get('relative_path', '')
                                                                source_folder = file_info.get('source_folder', '')
                                                                result_text.insert(tb.END, f"  - {relative_path} (来源: {source_folder})\n")
                                                        
                                                        self.root.after(0, lambda: self.log_message(f"重复文件删除完成: 删除 {len(delete_results.get('files_deleted', []))} 个文件"))
                                                    
                                                    duplicate_window.after(0, show_delete_results)
                                                    
                                                except Exception as e:
                                                    def show_delete_error():
                                                        result_text.delete(1.0, tb.END)
                                                        result_text.insert(tb.END, f"删除失败: {e}")
                                                        messagebox.showerror("错误", f"删除失败: {e}")
                                                    
                                                    duplicate_window.after(0, show_delete_error)
                                            
                                            threading.Thread(target=delete_worker, daemon=True).start()
                                    
                                    delete_btn = tb.Button(
                                        button_frame,
                                        text=f"删除 {results['total_duplicates_found']} 个重复文件",
                                        command=delete_duplicates
                                    )
                                    delete_btn.delete_button_flag = True  # 标记为删除按钮
                                    delete_btn.pack(side=tb.LEFT, padx=5)
                            else:
                                result_text.insert(tb.END, "未发现可删除的重复文件。\n")
                            # result_text.config(state='normal')  # ttkbootstrap ScrolledText不支持state配置
                            
                            # 记录日志
                            if dry_run:
                                self.root.after(0, lambda: self.log_message(f"重复文件扫描完成 [试运行]: 发现 {results['total_duplicates_found']} 个重复文件"))
                            else:
                                self.root.after(0, lambda: self.log_message(f"重复文件删除完成: 删除 {len(results.get('files_deleted', []))} 个文件"))
                        
                        self.root.after(0, update_results)
                        
                    except Exception as e:
                        def show_error():
                            result_text.delete(1.0, tb.END)
                            result_text.insert(tb.END, f"扫描失败: {e}")
                            self.root.after(0, lambda err=e: self.log_message(f"重复文件扫描失败: {err}"))
                            messagebox.showerror("错误", f"扫描失败: {e}")
                        
                        self.root.after(0, show_error)
                
                threading.Thread(target=scan_worker, daemon=True).start()
            
            tb.Button(
                button_frame,
                text="开始扫描",
                command=start_scan
            ).pack(side=tb.LEFT, padx=5)
            
            tb.Button(
                button_frame,
                text="关闭",
                command=duplicate_window.destroy
            ).pack(side=tb.RIGHT, padx=5)
            
        except Exception as e:
            self.root.after(0, lambda err=e: self.log_message(f"显示重复文件删除对话框失败: {err}"))
            self.root.after(0, lambda err=e: messagebox.showerror("错误", f"显示重复文件删除对话框失败: {err}"))
        
    def show_classification_rules_manager(self):
        """显示分类规则管理器"""
        try:
            from classification_rules_gui import ClassificationRulesGUI
            import tkinter as tk
            
            # 创建新窗口
            rules_window = tk.Toplevel(self.root)
            rules_window.title("分类规则管理器")
            rules_window.geometry("800x600")
            rules_window.transient(self.root)  # 设置为主窗口的临时窗口
            rules_window.grab_set()  # 模态窗口
            
            # 创建分类规则管理器GUI
            rules_gui = ClassificationRulesGUI(rules_window)
            
            # 居中显示窗口
            rules_window.update_idletasks()
            width = rules_window.winfo_width()
            height = rules_window.winfo_height()
            x = (rules_window.winfo_screenwidth() // 2) - (width // 2)
            y = (rules_window.winfo_screenheight() // 2) - (height // 2)
            rules_window.geometry(f"{width}x{height}+{x}+{y}")
            
            self.log_message("分类规则管理器已打开")
            
        except Exception as e:
            self.log_message(f"打开分类规则管理器失败: {e}")
            messagebox.showerror("错误", f"打开分类规则管理器失败: {e}")
    
    def show_ai_model_config(self):
        """显示AI模型配置"""
        try:
            # 创建AI模型配置窗口
            config_window = tb.Toplevel(self.root)
            config_window.title("AI模型配置")
            config_window.geometry("800x600")
            config_window.resizable(True, True)
            config_window.transient(self.root)
            config_window.grab_set()
            
            # 居中显示
            config_window.update_idletasks()
            x = (config_window.winfo_screenwidth() // 2) - (800 // 2)
            y = (config_window.winfo_screenheight() // 2) - (600 // 2)
            config_window.geometry(f"800x600+{x}+{y}")
            
            # 创建主框架
            main_frame = tb.Frame(config_window, padding="10")
            main_frame.pack(fill=BOTH, expand=True)
            
            # 标题
            title_label = tb.Label(main_frame, text="AI模型服务配置", font=('Arial', 14, 'bold'))
            title_label.pack(pady=(0, 20))
            
            # 模型列表框架
            list_frame = tb.Frame(main_frame)
            list_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
            
            # 模型列表标题
            list_title = tb.Label(list_frame, text="已配置的模型服务:", font=('Arial', 11, 'bold'))
            list_title.pack(anchor=W, pady=(0, 10))
            
            # 模型列表（使用Treeview）
            columns = ('优先级', '模型名称', '模型类型', '服务地址', '模型名', '状态')
            model_tree = tb.Treeview(list_frame, columns=columns, show='headings', height=8)
            
            # 设置列标题
            for col in columns:
                model_tree.heading(col, text=col)
                model_tree.column(col, width=120)
            
            # 添加滚动条
            scrollbar = tb.Scrollbar(list_frame, orient=VERTICAL, command=model_tree.yview)
            model_tree.configure(yscrollcommand=scrollbar.set)
            
            model_tree.pack(side=LEFT, fill=BOTH, expand=True)
            scrollbar.pack(side=RIGHT, fill=Y)
            
            # 按钮框架
            button_frame = tb.Frame(main_frame)
            button_frame.pack(fill=X, pady=10)
            
            def refresh_model_list():
                """刷新模型列表"""
                try:
                    # 清空现有列表
                    for item in model_tree.get_children():
                        model_tree.delete(item)
                    
                    # 从AI管理器获取模型可用性信息
                    from ai_client_manager import get_model_availability_info
                    model_info = get_model_availability_info()
                    
                    # 添加到列表
                    for info in model_info:
                        # 状态显示：启用状态 + 连接状态 + 可用性
                        enabled_status = "✅ 启用" if info['enabled'] else "❌ 禁用"
                        connection_status = "✅ 已连接" if info['client_initialized'] else "❌ 未连接"
                        availability_status = "✅ 可用" if info['available'] else "❌ 不可用"
                        
                        model_tree.insert('', 'end', values=(
                            info['priority'],
                            info['name'],
                            info.get('model_type', 'unknown'),
                            info['base_url'],
                            info['model_name'],
                            f"{enabled_status} | {connection_status} | {availability_status}"
                        ))
                    
                    self.log_message(f"模型列表刷新完成，共 {len(model_info)} 个模型")
                    
                except Exception as e:
                    self.log_message(f"刷新模型列表失败: {e}")
                    messagebox.showerror("错误", f"刷新模型列表失败: {e}")
            
            def add_model():
                """添加模型"""
                show_model_dialog()
            
            def edit_model():
                """编辑模型"""
                selected = model_tree.selection()
                if not selected:
                    messagebox.showwarning("提示", "请先选择一个模型进行编辑")
                    return
                
                # 获取选中的模型信息
                item = model_tree.item(selected[0])
                values = item['values']
                
                # 显示编辑对话框
                show_model_dialog(
                    priority=values[0],
                    name=values[1],
                    base_url=values[3],  # 调整索引
                    model_name=values[4]  # 调整索引
                )
            
            def delete_model():
                """删除模型"""
                selected = model_tree.selection()
                if not selected:
                    messagebox.showwarning("提示", "请先选择一个模型进行删除")
                    return
                
                # 获取选中的模型信息
                item = model_tree.item(selected[0])
                values = item['values']
                model_name = values[1]  # 模型名称
                
                if messagebox.askyesno("确认删除", f"确定要删除模型 '{model_name}' 吗？"):
                    try:
                        from ai_client_manager import get_ai_manager
                        manager = get_ai_manager()
                        
                        # 根据模型名称查找并删除
                        for model in manager.models:
                            if model.name == model_name:
                                manager.delete_model(model.id)
                                self.log_message(f"模型 '{model_name}' 删除成功")
                                messagebox.showinfo("成功", f"模型 '{model_name}' 删除成功")
                                refresh_model_list()  # 刷新列表
                                return
                        
                        messagebox.showerror("错误", f"未找到模型 '{model_name}'")
                        
                    except Exception as e:
                        self.log_message(f"删除模型失败: {e}")
                        messagebox.showerror("错误", f"删除模型失败: {e}")
            
            def enable_selected_model():
                """启用选中的模型"""
                selected = model_tree.selection()
                if not selected:
                    messagebox.showwarning("提示", "请先选择一个模型进行启用")
                    return
                
                # 获取选中的模型信息
                item = model_tree.item(selected[0])
                values = item['values']
                model_name = values[1]  # 模型名称在第二列
                
                try:
                    from ai_client_manager import get_ai_manager
                    manager = get_ai_manager()
                    
                    # 根据模型名称查找并启用
                    for model in manager.models:
                        if model.name == model_name:
                            if manager.enable_model(model.id):
                                self.log_message(f"模型 '{model_name}' 启用成功")
                                messagebox.showinfo("成功", f"模型 '{model_name}' 启用成功")
                            else:
                                self.log_message(f"模型 '{model_name}' 启用失败")
                                messagebox.showerror("错误", f"模型 '{model_name}' 启用失败，请检查连接")
                            refresh_model_list()  # 刷新列表
                            return
                    
                    messagebox.showerror("错误", f"未找到模型 '{model_name}'")
                    
                except Exception as e:
                    self.log_message(f"启用模型失败: {e}")
                    messagebox.showerror("错误", f"启用模型失败: {e}")
            
            def disable_selected_model():
                """禁用选中的模型"""
                selected = model_tree.selection()
                if not selected:
                    messagebox.showwarning("提示", "请先选择一个模型进行禁用")
                    return
                
                # 获取选中的模型信息
                item = model_tree.item(selected[0])
                values = item['values']
                model_name = values[1]  # 模型名称在第二列
                
                if messagebox.askyesno("确认禁用", f"确定要禁用模型 '{model_name}' 吗？"):
                    try:
                        from ai_client_manager import get_ai_manager
                        manager = get_ai_manager()
                        
                        # 根据模型名称查找并禁用
                        for model in manager.models:
                            if model.name == model_name:
                                model.enabled = False
                                if model.id in manager.clients:
                                    del manager.clients[model.id]
                                manager.save_config()
                                self.log_message(f"模型 '{model_name}' 禁用成功")
                                messagebox.showinfo("成功", f"模型 '{model_name}' 禁用成功")
                                refresh_model_list()  # 刷新列表
                                return
                        
                        messagebox.showerror("错误", f"未找到模型 '{model_name}'")
                        
                    except Exception as e:
                        self.log_message(f"禁用模型失败: {e}")
                        messagebox.showerror("错误", f"禁用模型失败: {e}")
            
            def show_model_details():
                """显示模型详细信息"""
                selected = model_tree.selection()
                if not selected:
                    messagebox.showwarning("提示", "请先选择一个模型查看详情")
                    return
                
                try:
                    from ai_client_manager import get_model_availability_info
                    model_info_list = get_model_availability_info()
                    
                    # 获取选中的模型信息
                    item = model_tree.item(selected[0])
                    values = item['values']
                    model_name = values[1]  # 模型名称在第二列
                    
                    # 找到对应的模型信息
                    model_info = None
                    for info in model_info_list:
                        if info['name'] == model_name:
                            model_info = info
                            break
                    
                    if not model_info:
                        messagebox.showerror("错误", "未找到模型信息")
                        return
                    
                    # 显示详细信息
                    detail_text = f"模型详细信息: {model_name}\n"
                    detail_text += "=" * 50 + "\n\n"
                    detail_text += f"模型ID: {model_info['id']}\n"
                    detail_text += f"显示名称: {model_info['name']}\n"
                    detail_text += f"服务地址: {model_info['base_url']}\n"
                    detail_text += f"模型名称: {model_info['model_name']}\n"
                    if model_info.get('mapped_model_name') and model_info['mapped_model_name'] != model_info['model_name']:
                        detail_text += f"映射后模型名称: {model_info['mapped_model_name']}\n"
                    detail_text += f"优先级: {model_info['priority']}\n"
                    detail_text += f"客户端初始化: {'是' if model_info['client_initialized'] else '否'}\n"
                    detail_text += f"模型可用: {'是' if model_info['available'] else '否'}\n"
                    
                    if not model_info['available']:
                        detail_text += f"\n错误信息: {model_info['error']}\n"
                        
                        if model_info['available_models']:
                            detail_text += f"\n可用模型: {', '.join(model_info['available_models'])}\n"
                        
                        if model_info['suggestions']:
                            detail_text += f"\n解决建议:\n"
                            for i, suggestion in enumerate(model_info['suggestions'], 1):
                                detail_text += f"{i}. {suggestion}\n"
                    
                    # 创建详细信息窗口
                    detail_window = tb.Toplevel(config_window)
                    detail_window.title(f"模型详情 - {model_name}")
                    detail_window.geometry("600x500")
                    detail_window.transient(config_window)
                    detail_window.grab_set()
                    
                    # 创建文本显示区域
                    text_frame = tb.Frame(detail_window, padding="10")
                    text_frame.pack(fill=BOTH, expand=True)
                    
                    text_widget = tk.Text(text_frame, wrap=tk.WORD, padx=10, pady=10)
                    text_widget.pack(fill=BOTH, expand=True)
                    text_widget.insert(tk.END, detail_text)
                    text_widget.config(state=tk.DISABLED)
                    
                except Exception as e:
                    self.log_message(f"获取模型详情失败: {e}")
                    messagebox.showerror("错误", f"获取模型详情失败: {e}")
            
            def test_connections():
                """测试所有模型连接"""
                try:
                    from ai_client_manager import test_ai_connections
                    self.log_message("开始测试模型连接...")
                    
                    # 在新线程中执行测试
                    def test_worker():
                        try:
                            results = test_ai_connections()
                            
                            # 显示测试结果
                            result_text = "连接测试结果:\n\n"
                            for name, result in results.items():
                                if result.get('success'):
                                    result_text += f"✅ {name}: 连接成功"
                                    if result.get('response_time'):
                                        result_text += f" (响应时间: {result['response_time']}s)"
                                else:
                                    result_text += f"❌ {name}: 连接失败"
                                    if result.get('error'):
                                        result_text += f" - {result['error']}"
                                result_text += "\n"
                            
                            self.log_message(result_text)
                            messagebox.showinfo("测试完成", result_text)
                            
                        except Exception as e:
                            self.log_message(f"测试连接失败: {e}")
                            messagebox.showerror("错误", f"测试连接失败: {e}")
                    
                    threading.Thread(target=test_worker, daemon=True).start()
                    
                except Exception as e:
                    self.log_message(f"启动连接测试失败: {e}")
                    messagebox.showerror("错误", f"启动连接测试失败: {e}")
            
            def show_model_dialog(priority=None, name="", base_url="", model_name="", api_key=""):
                """显示模型配置对话框"""
                # 创建对话框
                dialog = tb.Toplevel(config_window)
                dialog.title("模型配置")
                dialog.geometry("500x450")
                dialog.resizable(False, False)
                dialog.transient(config_window)
                dialog.grab_set()
                
                # 居中显示
                dialog.update_idletasks()
                x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
                y = (dialog.winfo_screenheight() // 2) - (450 // 2)
                dialog.geometry(f"500x450+{x}+{y}")
                
                # 创建表单
                form_frame = tb.Frame(dialog, padding="20")
                form_frame.pack(fill=BOTH, expand=True)
                
                row = 0
                
                # 优先级（下拉菜单）
                tb.Label(form_frame, text="优先级:", font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5)
                priority_var = tb.StringVar(value=str(priority) if priority else "1")
                priority_combo = tb.Combobox(form_frame, textvariable=priority_var, values=["1", "2", "3", "4", "5"], width=37, state="readonly")
                priority_combo.grid(row=row, column=1, sticky=(W, E), pady=5, padx=(10, 0))
                row += 1
                
                # 模型名称
                tb.Label(form_frame, text="模型名称:", font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5)
                name_var = tb.StringVar(value=name)
                tb.Entry(form_frame, textvariable=name_var, width=40).grid(row=row, column=1, sticky=(W, E), pady=5, padx=(10, 0))
                row += 1
                
                # 服务地址
                tb.Label(form_frame, text="服务地址:", font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5)
                base_url_var = tb.StringVar(value=base_url)
                tb.Entry(form_frame, textvariable=base_url_var, width=40).grid(row=row, column=1, sticky=(W, E), pady=5, padx=(10, 0))
                row += 1
                
                # 模型类型
                tb.Label(form_frame, text="模型类型:", font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5)
                model_type_var = tb.StringVar(value="ollama")
                model_type_combo = tb.Combobox(form_frame, textvariable=model_type_var, values=["qwen_long", "ollama", "lm_studio", "openai_compatible"], width=37, state="readonly")
                model_type_combo.grid(row=row, column=1, sticky=(W, E), pady=5, padx=(10, 0))
                row += 1
                
                # 模型名
                tb.Label(form_frame, text="模型名:", font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5)
                model_name_var = tb.StringVar(value=model_name)
                tb.Entry(form_frame, textvariable=model_name_var, width=40).grid(row=row, column=1, sticky=(W, E), pady=5, padx=(10, 0))
                row += 1
                
                # API密钥
                tb.Label(form_frame, text="API密钥:", font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5)
                api_key_var = tb.StringVar(value=api_key)
                tb.Entry(form_frame, textvariable=api_key_var, width=40, show="*").grid(row=row, column=1, sticky=(W, E), pady=5, padx=(10, 0))
                row += 1
                
                # 启用状态
                enabled_var = tb.BooleanVar(value=True)
                tb.Checkbutton(form_frame, text="启用此模型", variable=enabled_var).grid(row=row, column=0, columnspan=2, sticky=W, pady=10)
                row += 1
                
                # 按钮框架
                button_frame = tb.Frame(form_frame)
                button_frame.grid(row=row, column=0, columnspan=2, pady=20)
                
                def save_model():
                    try:
                        # 验证输入
                        if not name_var.get().strip():
                            messagebox.showwarning("输入错误", "请输入模型名称")
                            return
                        if not base_url_var.get().strip():
                            messagebox.showwarning("输入错误", "请输入服务地址")
                            return
                        if not model_name_var.get().strip():
                            messagebox.showwarning("输入错误", "请输入模型名")
                            return
                        
                        # 获取AI管理器
                        from ai_client_manager import get_ai_manager, ModelConfig
                        manager = get_ai_manager()
                        
                        # 创建模型配置
                        model_id = f"model_{int(time.time())}"  # 生成唯一ID
                        new_model = ModelConfig(
                            id=model_id,
                            name=name_var.get().strip(),
                            base_url=base_url_var.get().strip(),
                            model_name=model_name_var.get().strip(),
                            model_type=model_type_var.get(),
                            api_key=api_key_var.get().strip(),
                            priority=int(priority_var.get()),
                            enabled=enabled_var.get()
                        )
                        
                        # 添加模型
                        manager.add_model(new_model)
                        
                        self.log_message(f"模型 '{new_model.name}' 保存成功")
                        messagebox.showinfo("成功", f"模型 '{new_model.name}' 保存成功")
                        dialog.destroy()
                        refresh_model_list()  # 刷新列表
                        
                    except Exception as e:
                        self.log_message(f"保存模型失败: {e}")
                        messagebox.showerror("错误", f"保存失败: {e}")
                
                def cancel():
                    dialog.destroy()
                
                # 保存和取消按钮
                tb.Button(button_frame, text="保存", command=save_model, bootstyle=SUCCESS, width=15).pack(side=LEFT, padx=(0, 10))
                tb.Button(button_frame, text="取消", command=cancel, bootstyle=SECONDARY, width=15).pack(side=LEFT)
                
                # 设置列权重
                form_frame.columnconfigure(1, weight=1)
            
            # 添加按钮
            tb.Button(button_frame, text="添加模型", command=add_model, bootstyle=SUCCESS).pack(side=LEFT, padx=5)
            tb.Button(button_frame, text="编辑模型", command=edit_model, bootstyle=INFO).pack(side=LEFT, padx=5)
            tb.Button(button_frame, text="删除模型", command=delete_model, bootstyle=DANGER).pack(side=LEFT, padx=5)
            tb.Button(button_frame, text="测试连接", command=test_connections, bootstyle=WARNING).pack(side=LEFT, padx=5)
            tb.Button(button_frame, text="刷新列表", command=refresh_model_list, bootstyle=SECONDARY).pack(side=LEFT, padx=5)
            tb.Button(button_frame, text="查看详情", command=show_model_details, bootstyle=PRIMARY).pack(side=LEFT, padx=5)
            tb.Button(button_frame, text="启用模型", command=enable_selected_model, bootstyle=SUCCESS).pack(side=LEFT, padx=5)
            tb.Button(button_frame, text="禁用模型", command=disable_selected_model, bootstyle=WARNING).pack(side=LEFT, padx=5)
            
            # 初始化模型列表
            refresh_model_list()
            
        except Exception as e:
            self.log_message(f"打开AI模型配置失败: {e}")
            messagebox.showerror("错误", f"打开AI模型配置失败: {e}")
    
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
                text="文件目录智能整理",
                font=('Arial', 14, 'bold')
            ).pack(pady=(0, 10))
            
            # 说明文字
            tb.Label(
                main_frame,
                text="选择要整理的目录，AI将智能分析并推荐优化的目录结构",
                font=('Arial', 10)
            ).pack(pady=(0, 15))
            
            # 创建左右分栏框架
            content_frame = tb.Frame(main_frame)
            content_frame.pack(fill=tb.BOTH, expand=True)
            content_frame.columnconfigure(0, weight=1)
            content_frame.columnconfigure(1, weight=1)
            content_frame.rowconfigure(0, weight=1)
            
            # 左侧：目录选择区域
            left_frame = tb.LabelFrame(content_frame, text="选择要整理的目录", padding="10")
            left_frame.grid(row=0, column=0, sticky=(tb.W, tb.E, tb.N, tb.S), padx=(0, 5))
            
            # 左侧顶部：刷新按钮
            refresh_frame = tb.Frame(left_frame)
            refresh_frame.pack(fill=tb.X, pady=(0, 10))
            
            tb.Button(
                refresh_frame,
                text="刷新系统目录",
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
            selected_frame = tb.LabelFrame(left_frame, text="已选择的目录", padding="5")
            selected_frame.pack(fill=tb.X, pady=(10, 0))
            
            selected_listbox = Listbox(selected_frame, height=4)
            selected_listbox.pack(side=tb.LEFT, fill=tb.BOTH, expand=True)
            
            selected_scrollbar = tb.Scrollbar(selected_frame, orient=tb.VERTICAL, command=selected_listbox.yview)
            selected_listbox.configure(yscrollcommand=selected_scrollbar.set)
            selected_scrollbar.pack(side=tb.RIGHT, fill=tb.Y)
            
            # 右侧：推荐结果区域
            right_frame = tb.LabelFrame(content_frame, text="AI推荐结果", padding="10")
            right_frame.grid(row=0, column=1, sticky=(tb.W, tb.E, tb.N, tb.S), padx=(5, 0))
            
            # 右侧顶部：目标目录选择
            target_frame = tb.Frame(right_frame)
            target_frame.pack(fill=tb.X, pady=(0, 10))
            
            tb.Label(target_frame, text="新建目录位置:").pack(anchor=tb.W)
            
            target_var = tb.StringVar()
            target_entry = tb.Entry(target_frame, textvariable=target_var, width=40)
            target_entry.pack(side=tb.LEFT, fill=tb.X, expand=True, padx=(0, 5))
            
            def select_target_folder():
                folder_path = filedialog.askdirectory(title="选择新建目录的位置")
                if folder_path:
                    target_var.set(folder_path)
            
            tb.Button(
                target_frame,
                text="选择",
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
                    from directory_organizer import DirectoryOrganizer
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
                    messagebox.showerror("错误", f"刷新盘符失败: {e}")
            
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
                    from directory_organizer import DirectoryOrganizer
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
                    messagebox.showwarning("提示", "请先选择要整理的目录")
                    return
                
                if not target_var.get():
                    messagebox.showwarning("提示", "请先选择新建目录的位置")
                    return
                
                # 禁用按钮
                recommend_btn.config(state='disabled')
                create_btn.config(state='disabled')
                
                # 在新线程中执行推荐
                def recommendation_worker():
                    try:
                        from directory_organizer import DirectoryOrganizer
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
                    messagebox.showwarning("提示", "请先生成AI推荐")
                    return
                
                try:
                    from directory_organizer import DirectoryOrganizer
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
                    
                    messagebox.showinfo("完成", "目录结构创建完成！\n\n请使用智能分类或文件分类功能将原文件迁移到新的目录中。")
                    
                except Exception as e:
                    messagebox.showerror("错误", f"创建目录结构失败: {e}")
            
            def re_generate_recommendation():
                """重新生成AI推荐"""
                if not selected_directories:
                    messagebox.showwarning("提示", "请先选择要整理的目录")
                    return
                
                if not target_var.get():
                    messagebox.showwarning("提示", "请先选择新建目录的位置")
                    return
                
                # 禁用按钮
                recommend_btn.config(state='disabled')
                re_recommend_btn.config(state='disabled')
                create_btn.config(state='disabled')
                
                # 在新线程中执行重新推荐
                def re_recommendation_worker():
                    try:
                        from directory_organizer import DirectoryOrganizer
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
                text="移除选中",
                command=remove_selected_directory
            ).pack(side=tb.LEFT, padx=5)
            
            tb.Button(
                left_button_frame,
                text="清空列表",
                command=clear_selected_directories
            ).pack(side=tb.LEFT, padx=5)
            
            # 右侧按钮
            recommend_btn = tb.Button(
                button_frame,
                text="智能推荐",
                command=generate_recommendation
            )
            recommend_btn.pack(side=tb.LEFT, padx=5)
            
            re_recommend_btn = tb.Button(
                button_frame,
                text="重新推荐",
                command=re_generate_recommendation,
                state='disabled'
            )
            re_recommend_btn.pack(side=tb.LEFT, padx=5)
            
            create_btn = tb.Button(
                button_frame,
                text="使用此推荐目录",
                command=create_recommended_structure,
                state='disabled'
            )
            create_btn.pack(side=tb.LEFT, padx=5)
            
            tb.Button(
                button_frame,
                text="关闭",
                command=organize_window.destroy
            ).pack(side=tb.RIGHT, padx=5)
            
            # 初始化加载盘符
            refresh_drives()
            
        except Exception as e:
            self.root.after(0, lambda err=e: self.log_message(f"显示目录整理对话框失败: {err}"))
            self.root.after(0, lambda err=e: messagebox.showerror("错误", f"显示目录整理对话框失败: {err}"))
    
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
                messagebox.showwarning("提示", "请先选择一个有效的日志记录")
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
                messagebox.showerror("错误", f"无法加载日志文件: {os.path.basename(log_file_path)}")
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
            info_frame = tb.LabelFrame(main_frame, text="基本信息", padding="5")
            info_frame.pack(fill=tb.X, pady=(0, 10))
            
            session_info = target_log.get('session_info', {})
            tb.Label(info_frame, text=f"时间: {session_info.get('start_time', 'N/A')}").pack(anchor=tb.W)
            tb.Label(info_frame, text=f"会话名称: {session_info.get('session_name', 'N/A')}").pack(anchor=tb.W)
            tb.Label(info_frame, text=f"总操作数: {session_info.get('total_operations', 0)}").pack(anchor=tb.W)
            tb.Label(info_frame, text=f"成功操作: {session_info.get('successful_operations', 0)}").pack(anchor=tb.W)
            tb.Label(info_frame, text=f"失败操作: {session_info.get('failed_operations', 0)}").pack(anchor=tb.W)
            tb.Label(info_frame, text=f"状态: {'已完成' if session_info.get('end_time') else '进行中'}").pack(anchor=tb.W)
            
            # 文件列表
            files_frame = tb.LabelFrame(main_frame, text="文件列表", padding="5")
            files_frame.pack(fill=tb.BOTH, expand=True)
            
            # 创建文件列表树形视图
            files_tree = tb.Treeview(
                files_frame,
                columns=("source", "target", "status"),
                show="headings",
                height=15
            )
            
            files_tree.heading("source", text="源文件")
            files_tree.heading("target", text="目标文件")
            files_tree.heading("status", text="状态")
            
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
                text="关闭",
                command=detail_window.destroy
            ).pack(pady=(10, 0))
            
        except Exception as e:
            self.log_message(f"显示日志详情失败: {e}")
            messagebox.showerror("错误", f"显示日志详情失败: {e}")
    
    def _restore_from_selected_log(self, log_tree):
        """从选中的日志记录恢复文件"""
        try:
            # 获取选中的项目
            selection = log_tree.selection()
            if not selection:
                messagebox.showwarning("提示", "请先选择一个日志记录")
                return
            
            # 获取选中项目的数据
            item = log_tree.item(selection[0])
            values = item['values'] if item['values'] else []
            
            if not values or len(values) < 6:
                messagebox.showwarning("提示", "请先选择一个有效的日志记录")
                return
            
            timestamp = values[0]
            log_file_path = values[5]  # 第6个字段是完整的文件路径
            
            if not timestamp or timestamp == "暂无日志记录" or timestamp.startswith("加载失败") or timestamp.startswith("文件损坏"):
                messagebox.showwarning("提示", "请先选择一个有效的日志记录")
                return
            
            # 直接使用存储的文件路径
            target_log_file = log_file_path
            
            # 验证文件是否存在
            if not os.path.exists(target_log_file):
                messagebox.showerror("错误", f"日志文件不存在: {os.path.basename(target_log_file)}")
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
                text="文件恢复操作",
                font=('Arial', 12, 'bold')
            ).pack(pady=(0, 10))
            
            # 日志文件信息
            tb.Label(main_frame, text=f"日志文件: {Path(target_log_file).name}").pack(anchor=tb.W)
            tb.Label(main_frame, text=f"时间戳: {timestamp}").pack(anchor=tb.W)
            
            # 操作模式选择
            mode_frame = tb.LabelFrame(main_frame, text="操作模式", padding="5")
            mode_frame.pack(fill=tb.X, pady=(10, 10))
            
            dry_run_var = tb.BooleanVar(value=True)
            tb.Radiobutton(
                mode_frame,
                text="预览模式（仅显示将要恢复的文件，不实际执行）",
                variable=dry_run_var,
                value=True
            ).pack(anchor=tb.W)
            tb.Radiobutton(
                mode_frame,
                text="执行模式（实际恢复文件）",
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
                text="开始恢复",
                command=start_restore
            )
            restore_btn.pack(side=tb.LEFT, padx=5)
            
            cancel_btn = tb.Button(
                button_frame,
                text="取消",
                command=restore_window.destroy
            )
            cancel_btn.pack(side=tb.RIGHT, padx=5)
            
        except Exception as e:
            self.log_message(f"显示恢复对话框失败: {e}")
            messagebox.showerror("错误", f"显示恢复对话框失败: {e}")
    
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