#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文件整理器 - 分页版GUI应用
将智能分类和文件分类功能分离到不同的分页中
"""

import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
from ttkbootstrap.scrolled import ScrolledText
import threading
import json
import os
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
        self.root.title("智能文件管理器 v2.0 - 分页版")
        self.root.geometry("1200x1000")
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
            from file_organizer_ai import FileOrganizer as AIFileOrganizer
            from file_organizer_simple import FileOrganizer as SimpleFileOrganizer
            
            self.ai_organizer = AIFileOrganizer(enable_transfer_log=True)
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
            text="智能文件管理器 v2.0", 
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # 创建分页控件
        self.notebook = tb.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky=(W, E, N, S))
        
        # 创建文件解读页面
        self.create_file_reader_tab()
        
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
            height=8,
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
                import webbrowser
                import time
                import threading
                
                # 启动查看器服务器
                process = subprocess.Popen([sys.executable, "start_viewer_server.py"], 
                                         cwd=os.getcwd(), 
                                         creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
                
                # 存储进程引用以便后续管理
                if not hasattr(self, 'article_reader_processes'):
                    self.article_reader_processes = []
                self.article_reader_processes.append(process)
                
                # 延迟打开浏览器，确保服务器启动完成
                def open_browser():
                    time.sleep(2)  # 等待服务器启动
                    try:
                        webbrowser.open('http://localhost:8000/ai_result_viewer.html')
                    except Exception as e:
                        self.log_message(f"自动打开浏览器失败: {e}")
                
                threading.Thread(target=open_browser, daemon=True).start()
                
                self.log_message("已启动文章阅读助手服务器")
                messagebox.showinfo("提示", "文章阅读助手已启动！\n\n服务器正在启动中，浏览器将自动打开。\n关闭浏览器时服务器会自动停止。")
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
        
        # 预览按钮
        self.ai_preview_button = tb.Button(
            ai_button_frame,
            text="预览AI分类结果",
            command=self.ai_preview_classification
        )
        self.ai_preview_button.pack(side=LEFT, padx=5)
        
        # 开始整理按钮
        self.ai_organize_button = tb.Button(
            ai_button_frame,
            text="开始AI智能整理",
            command=self.ai_start_organize,
            bootstyle=SUCCESS
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
        
        # 预览按钮
        self.simple_preview_button = tb.Button(
            simple_button_frame,
            text="预览文件分类结果",
            command=self.simple_preview_classification
        )
        self.simple_preview_button.pack(side=LEFT, padx=5)
        
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
        
        # 重复文件删除按钮（第一个）
        self.duplicate_button = tb.Button(
            tools_button_frame,
            text="删除重复文件",
            command=self.show_duplicate_removal_dialog
        )
        self.duplicate_button.pack(side=LEFT, padx=5)
        
        # 文件恢复按钮（第二个）
        self.restore_button = tb.Button(
            tools_button_frame,
            text="文件恢复",
            command=self.show_restore_dialog
        )
        self.restore_button.pack(side=LEFT, padx=5)
        
        # 日志按钮（第三个，重命名为"日志"）
        self.log_button = tb.Button(
            tools_button_frame,
            text="日志",
            command=self.show_transfer_logs
        )
        self.log_button.pack(side=LEFT, padx=5)
        
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
        
    def ai_preview_classification(self):
        """AI预览分类结果"""
        source = self.source_directory.get()
        target = self.target_directory.get()
        
        if not source or not target:
            messagebox.showerror("错误", "请先选择源目录和目标目录")
            return
            
        self.log_message("开始AI预览分类...")
        self.ai_status_label.config(text="正在预览分类...")
        self.ai_preview_button.config(state='disabled')
        
        # 在新线程中执行预览
        threading.Thread(target=self._ai_preview_worker, daemon=True).start()
        
    def _ai_preview_worker(self):
        """AI预览工作线程"""
        try:
            source = self.source_directory.get()
            target = self.target_directory.get()
            
            # 应用AI参数设置
            self._apply_ai_parameters()
            
            # 获取文件列表
            source_files = self.ai_organizer.scan_files(source)
            if not source_files:
                self.root.after(0, lambda: messagebox.showinfo("提示", "源目录中没有找到文件"))
                return
                
            # 限制预览文件数量为5个
            max_preview_files = 5
            preview_files = source_files[:max_preview_files]
            preview_count = len(preview_files)
            preview_results = []
            ai_result_list = []
            ai_result_json_path = "preview_ai_result.json"
            
            self.root.after(0, lambda: self.log_message(f"将预览前{preview_count}个文件（共{len(source_files)}个文件）"))
            
            for i, file_info in enumerate(preview_files):
                file_path = str(file_info['path'])
                filename = str(file_info['name'])
                
                self.root.after(0, lambda f=filename: self.log_message(f"正在分析: {f}"))
                
                # 使用AI分析文件
                result = self.ai_organizer.analyze_and_classify_file(file_path, target)
                
                success = result.get('success', False)
                folder = result.get('recommended_folder', '')
                reason = result.get('match_reason', '')
                summary = result.get('content_summary', '')  # 修正字段名
                timing_info = result.get('timing_info', {})
                
                # 构建AI结果JSON条目
                ai_result_item = {
                    "源文件路径": file_path,
                    "文件摘要": summary,
                    "最匹配的目标目录": folder if success else "无推荐",
                    "匹配理由": reason if reason else ""
                }
                
                # 添加时间信息
                if timing_info:
                    ai_result_item["处理耗时信息"] = {
                        "总耗时(秒)": timing_info.get('total_processing_time', 0),
                        "内容提取耗时(秒)": timing_info.get('content_extraction_time', 0),
                        "摘要生成耗时(秒)": timing_info.get('summary_generation_time', 0),
                        "目录推荐耗时(秒)": timing_info.get('folder_recommendation_time', 0)
                    }
                    if 'ollama_init_time' in timing_info:
                        ai_result_item["处理耗时信息"]["Ollama初始化耗时(秒)"] = timing_info['ollama_init_time']
                
                ai_result_list.append(ai_result_item)
                
                preview_results.append({
                    'filename': filename,
                    'recommended_folder': folder if success else "无推荐",
                    'reason': reason,
                    'success': success,
                    'timing_info': timing_info
                })
                
                progress = (i + 1) / preview_count * 100
                self.root.after(0, lambda p=progress: self.ai_progress_var.set(p))
                
            # 保存AI结果到JSON文件
            with open(ai_result_json_path, 'w', encoding='utf-8') as f:
                json.dump(ai_result_list, f, ensure_ascii=False, indent=2)
                
            self.root.after(0, lambda: self._show_preview_results(preview_results, preview_count, "AI分类"))
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.log_message(f"AI预览失败: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"AI预览失败: {error_msg}"))
        finally:
            self.root.after(0, lambda: self.ai_progress_var.set(0))
            self.root.after(0, lambda: self.ai_status_label.config(text="预览完成"))
            self.root.after(0, lambda: self.ai_preview_button.config(state='normal'))
            
    def simple_preview_classification(self):
        """文件分类预览"""
        source = self.source_directory.get()
        target = self.target_directory.get()
        
        if not source or not target:
            messagebox.showerror("错误", "请先选择源目录和目标目录")
            return
            
        self.log_message("开始文件分类预览...")
        self.simple_status_label.config(text="正在预览分类...")
        self.simple_preview_button.config(state='disabled')
        
        # 在新线程中执行预览
        threading.Thread(target=self._simple_preview_worker, daemon=True).start()
        
    def _simple_preview_worker(self):
        """文件分类预览工作线程"""
        try:
            source = self.source_directory.get()
            target = self.target_directory.get()
            
            # 获取文件列表
            source_files = self.simple_organizer.scan_files(source)
            if not source_files:
                self.root.after(0, lambda: messagebox.showinfo("提示", "源目录中没有找到文件"))
                return
                
            # 预览所有文件，不限制数量
            preview_count = len(source_files)
            preview_results = []
            
            for i, file_info in enumerate(source_files):
                file_path = str(file_info['path'])
                filename = str(file_info['name'])
                
                self.root.after(0, lambda f=filename: self.log_message(f"正在分析: {f}"))
                
                # 使用简单分类
                folder, reason, success = self.simple_organizer.classify_file(file_path, target)
                
                preview_results.append({
                    'filename': filename,
                    'recommended_folder': folder if success else "无推荐",
                    'reason': reason,
                    'success': success,
                    'timing_info': {}
                })
                
                progress = (i + 1) / preview_count * 100
                self.root.after(0, lambda p=progress: self.simple_progress_var.set(p))
                
            self.root.after(0, lambda: self._show_preview_results(preview_results, len(source_files), "文件分类"))
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.log_message(f"文件分类预览失败: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"文件分类预览失败: {error_msg}"))
        finally:
            self.root.after(0, lambda: self.simple_progress_var.set(0))
            self.root.after(0, lambda: self.simple_status_label.config(text="预览完成"))
            self.root.after(0, lambda: self.simple_preview_button.config(state='normal'))
            
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
        # 这里需要修改AI文件整理器以支持动态参数设置
        # 暂时通过修改实例属性来实现
        if hasattr(self.ai_organizer, 'summary_length'):
            self.ai_organizer.summary_length = self.summary_length.get()
        if hasattr(self.ai_organizer, 'content_truncate'):
            self.ai_organizer.content_truncate = self.content_truncate.get()
            
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
        self.ai_preview_button.config(state='disabled')
        
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
            
            # 生成AI结果JSON文件
            self._generate_organize_result_json(self.organize_results, "ai_organize_result.json")
            
            # 更新进度
            self.root.after(0, lambda: self.ai_progress_var.set(100))
            
            # 显示结果
            self.root.after(0, lambda: self._show_organize_results("AI智能整理"))
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.log_message(f"AI整理失败: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"AI整理失败: {error_msg}"))
        finally:
            self.root.after(0, lambda: self.ai_organize_button.config(state='normal'))
            self.root.after(0, lambda: self.ai_preview_button.config(state='normal'))
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
        self.simple_preview_button.config(state='disabled')
        
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
            self.root.after(0, lambda: self.simple_preview_button.config(state='normal'))
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
            
    def _show_preview_results(self, preview_results, total_files, classification_type):
        """显示预览结果"""
        preview_window = tb.Toplevel(self.root)
        preview_window.title(f"{classification_type}预览结果")
        preview_window.geometry("700x500")
        preview_window.transient(self.root)
        preview_window.grab_set()
        
        # 创建预览内容
        frame = ttk.Frame(preview_window, padding="10")
        frame.pack(fill=BOTH, expand=True)
        
        ttk.Label(
            frame,
            text=f"预览前 {len(preview_results)} 个文件的{classification_type}结果（共 {total_files} 个文件）:",
            font=('Arial', 12, 'bold')
        ).pack(pady=(0, 10))
        
        # 创建结果显示区域
        result_text = scrolledtext.ScrolledText(frame, height=18, wrap=WORD)
        result_text.pack(fill=BOTH, expand=True, pady=(0, 10))
        
        # 统计信息
        successful_count = sum(1 for result in preview_results if result['success'])
        failed_count = len(preview_results) - successful_count
        
        result_text.insert(END, f"=== {classification_type}预览统计 ===\n")
        result_text.insert(END, f"成功推荐: {successful_count} 个文件\n")
        result_text.insert(END, f"需要手动处理: {failed_count} 个文件\n\n")
        
        for i, result in enumerate(preview_results, 1):
            filename = result['filename']
            folder = result['recommended_folder']
            reason = result['reason']
            success = result['success']
            timing_info = result.get('timing_info', {})
            
            result_text.insert(END, f"[{i}] 文件: {filename}\n")
            
            if success:
                result_text.insert(END, f"✓ 推荐文件夹: {folder}\n")
                result_text.insert(END, f"  {reason}\n")
            else:
                result_text.insert(END, f"⚠ 分类结果: {reason}\n")
                if "建议创建新文件夹" in reason:
                    result_text.insert(END, f"  建议操作：在目标目录中创建合适的文件夹后重新分类\n")
            
            # 显示时间信息（仅AI分类）
            if timing_info and classification_type == "AI分类":
                total_time = timing_info.get('total_processing_time', 0)
                extract_time = timing_info.get('content_extraction_time', 0)
                summary_time = timing_info.get('summary_generation_time', 0)
                recommend_time = timing_info.get('folder_recommendation_time', 0)
                
                result_text.insert(END, f"  ⏱ 处理耗时: 总计{total_time}秒 (提取{extract_time}s + 摘要{summary_time}s + 推荐{recommend_time}s)\n")
                
                if 'ollama_init_time' in timing_info:
                    init_time = timing_info['ollama_init_time']
                    result_text.insert(END, f"  🔧 Ollama初始化: {init_time}秒\n")
            
            result_text.insert(END, "\n")
            
        result_text.config(state='disabled')
        
        # 按钮框架
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=X)
        
        ttk.Button(
            button_frame,
            text="确定",
            command=preview_window.destroy
        ).pack(side=RIGHT)
        
    def _show_organize_results(self, operation_type):
        """显示整理结果"""
        if not self.organize_results:
            return
            
        results = self.organize_results
        
        # 创建结果窗口
        result_window = tb.Toplevel(self.root)
        result_window.title(f"{operation_type}结果")
        result_window.geometry("600x400")
        result_window.transient(self.root)
        result_window.grab_set()
        
        # 创建结果内容
        frame = ttk.Frame(result_window, padding="10")
        frame.pack(fill=BOTH, expand=True)
        
        ttk.Label(
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
        
        ttk.Label(frame, text=stats_text, font=('Arial', 10)).pack(pady=(0, 10))
        
        # 详细结果
        result_text = scrolledtext.ScrolledText(frame, height=15, wrap=WORD)
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
        
        result_text.config(state='disabled')
        
        # 按钮框架
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(
            button_frame,
            text="确定",
            command=result_window.destroy
        ).pack(side=tk.RIGHT)
        
    def show_transfer_logs(self):
        """显示转移日志管理界面"""
        try:
            # 检查转移日志功能是否可用
            if not self.ai_organizer.enable_transfer_log:
                messagebox.showwarning("功能不可用", "转移日志功能未启用")
                return
            
            # 创建转移日志窗口
            log_window = tk.Toplevel(self.root)
            log_window.title("转移日志管理")
            log_window.geometry("800x600")
            log_window.transient(self.root)
            log_window.grab_set()
            
            # 创建主框架
            main_frame = ttk.Frame(log_window, padding="10")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题
            ttk.Label(
                main_frame,
                text="转移日志管理",
                font=('Arial', 14, 'bold')
            ).pack(pady=(0, 10))
            
            # 日志列表框架
            list_frame = ttk.LabelFrame(main_frame, text="转移日志列表", padding="5")
            list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            # 创建日志列表
            columns = ('时间', '会话名称', '总文件数', '成功数', '失败数', '文件路径')
            log_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
            
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
            scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=log_tree.yview)
            log_tree.configure(yscrollcommand=scrollbar.set)
            
            log_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 加载日志数据
            self._load_transfer_logs(log_tree)
            
            # 按钮框架
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(10, 0))
            
            # 查看详情按钮
            ttk.Button(
                button_frame,
                text="查看详情",
                command=lambda: self._show_log_details(log_tree)
            ).pack(side=tk.LEFT, padx=5)
            
            # 恢复文件按钮
            ttk.Button(
                button_frame,
                text="恢复文件",
                command=lambda: self._restore_from_selected_log(log_tree)
            ).pack(side=tk.LEFT, padx=5)
            
            # 刷新按钮
            ttk.Button(
                button_frame,
                text="刷新",
                command=lambda: self._load_transfer_logs(log_tree)
            ).pack(side=tk.LEFT, padx=5)
            
            # 清理旧日志按钮
            ttk.Button(
                button_frame,
                text="清理旧日志",
                command=lambda: self._cleanup_old_logs(log_tree)
            ).pack(side=tk.LEFT, padx=5)
            
            # 关闭按钮
            ttk.Button(
                button_frame,
                text="关闭",
                command=log_window.destroy
            ).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.log_message(f"显示转移日志失败: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"显示转移日志失败: {error_msg}"))
        
    def show_restore_dialog(self):
        """显示文件恢复对话框"""
        try:
            # 检查转移日志功能是否可用
            if not self.ai_organizer.enable_transfer_log:
                messagebox.showwarning("功能不可用", "转移日志功能未启用，无法进行文件恢复")
                return
            
            # 获取日志文件列表
            log_files = self.ai_organizer.get_transfer_logs()
            
            if not log_files:
                messagebox.showinfo("提示", "没有找到转移日志文件")
                return
            
            # 创建恢复对话框
            restore_window = tk.Toplevel(self.root)
            restore_window.title("文件恢复")
            restore_window.geometry("600x400")
            restore_window.transient(self.root)
            restore_window.grab_set()
            
            # 创建主框架
            main_frame = ttk.Frame(restore_window, padding="10")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题
            ttk.Label(
                main_frame,
                text="选择要恢复的转移日志",
                font=('Arial', 12, 'bold')
            ).pack(pady=(0, 10))
            
            # 日志选择列表
            list_frame = ttk.Frame(main_frame)
            list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            # 创建列表框
            log_listbox = tk.Listbox(list_frame, height=15)
            log_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # 添加滚动条
            scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=log_listbox.yview)
            log_listbox.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 加载日志文件
            log_data = []
            for log_file in log_files:
                try:
                    summary = self.ai_organizer.get_transfer_log_summary(log_file)
                    session_info = summary['session_info']
                    
                    # 格式化显示文本
                    display_text = f"{session_info.get('session_name', '未知')} - {session_info.get('start_time', '未知')[:16]} (成功: {session_info.get('successful_operations', 0)})"
                    log_listbox.insert(tk.END, display_text)
                    log_data.append(log_file)
                    
                except Exception as e:
                    self.root.after(0, lambda err=e: self.log_message(f"解析日志文件失败 {log_file}: {err}"))
                    continue
            
            # 按钮框架
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X)
            
            def restore_selected():
                selection = log_listbox.curselection()
                if not selection:
                    messagebox.showwarning("提示", "请先选择一个日志记录")
                    return
                
                selected_log = log_data[selection[0]]
                restore_window.destroy()
                
                # 执行恢复
                self._execute_restore(selected_log)
            
            ttk.Button(
                button_frame,
                text="恢复选中的日志",
                command=restore_selected
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                button_frame,
                text="取消",
                command=restore_window.destroy
            ).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            self.root.after(0, lambda err=e: self.log_message(f"显示恢复对话框失败: {err}"))
            self.root.after(0, lambda err=e: messagebox.showerror("错误", f"显示恢复对话框失败: {err}"))
        
    def show_duplicate_removal_dialog(self):
        """显示重复文件删除对话框"""
        try:
            # 创建重复文件删除对话框
            duplicate_window = tk.Toplevel(self.root)
            duplicate_window.title("删除重复文件")
            duplicate_window.geometry("700x600")
            duplicate_window.transient(self.root)
            duplicate_window.grab_set()
            
            # 创建主框架
            main_frame = ttk.Frame(duplicate_window, padding="10")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题
            ttk.Label(
                main_frame,
                text="删除重复文件",
                font=('Arial', 12, 'bold')
            ).pack(pady=(0, 10))
            
            # 说明文字
            ttk.Label(
                main_frame,
                text="选择要检查重复文件的目标文件夹\n重复判断标准：文件名和文件大小完全一致",
                font=('Arial', 10)
            ).pack(pady=(0, 15))
            
            # 文件夹选择框架
            folder_frame = ttk.Frame(main_frame)
            folder_frame.pack(fill=tk.X, pady=(0, 15))
            
            ttk.Label(folder_frame, text="目标文件夹:").pack(anchor=tk.W)
            
            folder_var = tk.StringVar()
            folder_entry = ttk.Entry(folder_frame, textvariable=folder_var, width=50)
            folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
            
            def select_folder():
                directory = filedialog.askdirectory(
                    title="选择要检查重复文件的文件夹",
                    initialdir=self.target_directory.get() or os.path.expanduser("~")
                )
                if directory:
                    folder_var.set(directory)
            
            ttk.Button(folder_frame, text="浏览", command=select_folder).pack(side=tk.RIGHT)
            
            # 选项框架
            options_frame = ttk.LabelFrame(main_frame, text="选项", padding="5")
            options_frame.pack(fill=tk.X, pady=(0, 15))
            
            dry_run_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(
                options_frame,
                text="试运行模式（只检查不删除）",
                variable=dry_run_var
            ).pack(anchor=tk.W)
            
            # 结果显示区域
            result_frame = ttk.LabelFrame(main_frame, text="扫描结果", padding="5")
            result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
            
            result_text = scrolledtext.ScrolledText(
                result_frame,
                height=10,
                wrap=tk.WORD
            )
            result_text.pack(fill=tk.BOTH, expand=True)
            
            # 按钮框架（吸附底部，始终可见）
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
            
            def start_scan():
                folder_path = folder_var.get().strip()
                if not folder_path:
                    messagebox.showwarning("提示", "请先选择要检查的文件夹")
                    return
                
                if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
                    messagebox.showerror("错误", "选择的文件夹不存在或不是有效目录")
                    return
                
                # 清空结果显示
                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, "正在扫描重复文件...\n")
                
                # 在新线程中执行扫描
                def scan_worker():
                    try:
                        dry_run = dry_run_var.get()
                        results = remove_duplicate_files(
                            target_folder_path=folder_path,
                            dry_run=dry_run
                        )
                        # 分组展示所有重复文件
                        def update_results():
                            result_text.config(state='normal')
                            result_text.delete(1.0, tk.END)
                            result_text.insert(tk.END, f"扫描完成！\n\n")
                            result_text.insert(tk.END, f"总文件数: {results['total_files_scanned']}\n")
                            result_text.insert(tk.END, f"重复文件组: {results['duplicate_groups_found']}\n")
                            result_text.insert(tk.END, f"重复文件数: {results['total_duplicates_found']}\n\n")
                            if results.get('duplicate_groups'):
                                for idx, group in enumerate(results['duplicate_groups'], 1):
                                    size = group['size']
                                    md5 = group['md5']
                                    files = group['files']
                                    result_text.insert(tk.END, f"重复文件组{idx}: (大小: {size} bytes, MD5: {md5}) 共{len(files)}个副本\n")
                                    for file_info in files:
                                        keep_flag = '【保留】' if file_info.get('keep') else '【待删】'
                                        from datetime import datetime
                                        ctime_str = datetime.fromtimestamp(file_info['ctime']).strftime('%Y-%m-%d %H:%M:%S') if 'ctime' in file_info else ''
                                        result_text.insert(tk.END, f"  - {file_info['relative_path']} {keep_flag} 创建时间: {ctime_str}\n")
                                    result_text.insert(tk.END, "\n")
                                
                                # 如果是试运行模式且发现重复文件，添加删除按钮
                                if dry_run and results['total_duplicates_found'] > 0:
                                    # 清除现有的删除按钮（如果有）
                                    for widget in button_frame.winfo_children():
                                        if hasattr(widget, 'delete_button_flag'):
                                            widget.destroy()
                                    
                                    # 添加删除重复文件按钮
                                    def delete_duplicates():
                                        if messagebox.askyesno("确认删除", f"确定要删除 {results['total_duplicates_found']} 个重复文件吗？\n\n此操作不可撤销！"):
                                            result_text.delete(1.0, tk.END)
                                            result_text.insert(tk.END, "正在删除重复文件...\n")
                                            
                                            def delete_worker():
                                                try:
                                                    delete_results = remove_duplicate_files(
                                                        target_folder_path=folder_path,
                                                        dry_run=False
                                                    )
                                                    
                                                    def show_delete_results():
                                                        result_text.delete(1.0, tk.END)
                                                        result_text.insert(tk.END, f"删除完成！\n\n")
                                                        result_text.insert(tk.END, f"成功删除: {len(delete_results.get('files_deleted', []))} 个重复文件\n")
                                                        result_text.insert(tk.END, f"释放空间: {delete_results.get('space_freed', 0):,} 字节\n\n")
                                                        
                                                        if delete_results.get('files_deleted'):
                                                            result_text.insert(tk.END, "已删除的文件:\n")
                                                            for file_path in delete_results['files_deleted']:
                                                                result_text.insert(tk.END, f"  - {file_path}\n")
                                                        
                                                        self.root.after(0, lambda: self.log_message(f"重复文件删除完成: 删除 {len(delete_results.get('files_deleted', []))} 个文件"))
                                                    
                                                    duplicate_window.after(0, show_delete_results)
                                                    
                                                except Exception as e:
                                                    def show_delete_error():
                                                        result_text.delete(1.0, tk.END)
                                                        result_text.insert(tk.END, f"删除失败: {e}")
                                                        messagebox.showerror("错误", f"删除失败: {e}")
                                                    
                                                    duplicate_window.after(0, show_delete_error)
                                            
                                            threading.Thread(target=delete_worker, daemon=True).start()
                                    
                                    delete_btn = ttk.Button(
                                        button_frame,
                                        text=f"删除 {results['total_duplicates_found']} 个重复文件",
                                        command=delete_duplicates
                                    )
                                    delete_btn.delete_button_flag = True  # 标记为删除按钮
                                    delete_btn.pack(side=tk.LEFT, padx=5)
                            else:
                                result_text.insert(tk.END, "未发现可删除的重复文件。\n")
                            result_text.config(state='normal')
                            
                            # 记录日志
                            if dry_run:
                                self.root.after(0, lambda: self.log_message(f"重复文件扫描完成 [试运行]: 发现 {results['total_duplicates_found']} 个重复文件"))
                            else:
                                self.root.after(0, lambda: self.log_message(f"重复文件删除完成: 删除 {len(results.get('files_deleted', []))} 个文件"))
                        
                        self.root.after(0, update_results)
                        
                    except Exception as e:
                        def show_error():
                            result_text.delete(1.0, tk.END)
                            result_text.insert(tk.END, f"扫描失败: {e}")
                            self.root.after(0, lambda err=e: self.log_message(f"重复文件扫描失败: {err}"))
                            messagebox.showerror("错误", f"扫描失败: {e}")
                        
                        self.root.after(0, show_error)
                
                threading.Thread(target=scan_worker, daemon=True).start()
            
            ttk.Button(
                button_frame,
                text="开始扫描",
                command=start_scan
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                button_frame,
                text="关闭",
                command=duplicate_window.destroy
            ).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            self.root.after(0, lambda err=e: self.log_message(f"显示重复文件删除对话框失败: {err}"))
            self.root.after(0, lambda err=e: messagebox.showerror("错误", f"显示重复文件删除对话框失败: {err}"))
        

            
            # 摘要长度设置框架
            summary_frame = ttk.LabelFrame(main_frame, text="摘要参数设置", padding="10")
            summary_frame.pack(fill=tk.X, pady=(0, 15))
            
            # 摘要长度调节
            ttk.Label(summary_frame, text="文章摘要长度:").grid(row=0, column=0, sticky=tk.W, pady=5)
            summary_length_frame = ttk.Frame(summary_frame)
            summary_length_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
            summary_frame.columnconfigure(1, weight=1)
            summary_length_frame.columnconfigure(1, weight=1)
            
            # 创建摘要长度变量，默认200字
            summary_length_var = tk.IntVar(value=200)
            
            ttk.Label(summary_length_frame, text="100字").grid(row=0, column=0)
            summary_length_scale = ttk.Scale(
                summary_length_frame, 
                from_=100, 
                to=500, 
                variable=summary_length_var,
                orient=tk.HORIZONTAL
            )
            summary_length_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
            ttk.Label(summary_length_frame, text="500字").grid(row=0, column=2)
            
            # 显示当前值
            summary_value_label = ttk.Label(summary_length_frame, text=f"当前: {summary_length_var.get()}字")
            summary_value_label.grid(row=0, column=3, padx=(10, 0))
            
            # 更新显示值的回调函数
            def update_summary_label(*args):
                summary_value_label.config(text=f"当前: {int(summary_length_var.get())}字")
            
            summary_length_var.trace('w', update_summary_label)
            
            def select_folder():
                folder_path = filedialog.askdirectory(
                    title="选择要批量解读的文件夹",
                    initialdir=self.target_directory.get() or os.path.expanduser("~")
                )
                if folder_path:
                    folder_var.set(folder_path)
                    update_folder_info()
            
            # 开始批量解读按钮
            def start_batch_reading():
                folder_path = folder_var.get().strip()
                if not folder_path:
                    messagebox.showwarning("提示", "请先选择要解读的文件夹")
                    return
                
                if not os.path.exists(folder_path):
                    messagebox.showerror("错误", "选择的文件夹不存在")
                    return
                
                # 清空结果显示
                result_text.delete(1.0, tk.END)
                progress_var.set("正在扫描文件夹...")
                
                # 在新线程中执行批量文档解读
                def batch_read_worker():
                    try:
                        # 初始化AI文件整理器
                        progress_var.set("正在初始化AI整理器...")
                        print(f"\n=== 开始批量文档解读流程 ===")
                        print(f"目标文件夹: {folder_path}")
                        print(f"正在初始化FileOrganizer...")
                        
                        if not self.ai_organizer:
                            self.initialize_organizers()
                        
                        print(f"FileOrganizer初始化完成")
                        
                        # 定义进度回调函数
                        def progress_callback(current, total, filename):
                            progress_text = f"正在解读 ({current}/{total}): {filename}"
                            reader_window.after(0, lambda: progress_var.set(progress_text))
                        
                        # 调用批量文档解读方法
                        progress_var.set("开始批量解读...")
                        print(f"\n=== 开始批量文档解读 ===")
                        print(f"文件夹路径: {folder_path}")
                        
                        # 调用batch_read_documents方法，传递摘要长度参数
                        batch_results = self.ai_organizer.batch_read_documents(
                            folder_path=folder_path,
                            progress_callback=progress_callback,
                            summary_length=summary_length_var.get()
                        )
                        
                        print(f"批量解读结果: {batch_results}")
                        
                        # 显示批量解读结果
                        def show_batch_results():
                            result_text.delete(1.0, tk.END)
                            
                            # 显示统计信息
                            result_text.insert(tk.END, "=== 批量文档解读完成 ===\n\n")
                            result_text.insert(tk.END, f"总文件数: {batch_results['total_files']}\n")
                            result_text.insert(tk.END, f"成功解读: {batch_results['successful_reads']} 个\n")
                            result_text.insert(tk.END, f"解读失败: {batch_results['failed_reads']} 个\n")
                            
                            if batch_results['end_time'] and batch_results['start_time']:
                                duration = (batch_results['end_time'] - batch_results['start_time']).total_seconds()
                                result_text.insert(tk.END, f"总耗时: {duration:.1f} 秒\n")
                            
                            result_text.insert(tk.END, "\n结果已保存到: ai_organize_result.json\n")
                            result_text.insert(tk.END, "可通过 '查看AI结果' 功能查看详细解读结果\n")
                            
                            # 显示错误信息（如果有）
                            if batch_results.get('errors'):
                                result_text.insert(tk.END, "\n=== 错误信息 ===\n")
                                for error in batch_results['errors']:
                                    result_text.insert(tk.END, f"• {error}\n")
                            
                            progress_var.set("批量解读完成")
                            
                            # 记录日志
                            self.root.after(0, lambda: self.log_message(
                                f"批量文档解读完成: 成功 {batch_results['successful_reads']}, 失败 {batch_results['failed_reads']}"
                            ))
                        
                        reader_window.after(0, show_batch_results)
                        
                    except Exception as e:
                        error_exception = e  # 保存异常对象到局部变量
                        print(f"\n=== 批量文档解读过程中发生错误 ===")
                        print(f"错误类型: {type(error_exception).__name__}")
                        print(f"错误信息: {str(error_exception)}")
                        import traceback
                        print(f"详细错误堆栈:\n{traceback.format_exc()}")
                        print("=" * 50)
                        
                        def show_error():
                            progress_var.set("批量解读失败")
                            error_msg = f"批量文档解读失败: {error_exception}"
                            result_text.delete(1.0, tk.END)
                            result_text.insert(tk.END, error_msg)
                            self.root.after(0, lambda: self.log_message(f"批量文档解读失败: {error_exception}"))
                            messagebox.showerror("错误", error_msg)
                        
                        reader_window.after(0, show_error)
                
                threading.Thread(target=batch_read_worker, daemon=True).start()
            
            ttk.Button(folder_frame, text="开始批量解读", command=start_batch_reading).pack(side=tk.RIGHT, padx=(0, 5))
            ttk.Button(folder_frame, text="浏览", command=select_folder).pack(side=tk.RIGHT)
            
            # 文件夹信息显示
            info_frame = ttk.LabelFrame(main_frame, text="文件夹信息", padding="5")
            info_frame.pack(fill=tk.X, pady=(0, 15))
            
            info_text = tk.Text(info_frame, height=3, wrap=tk.WORD)
            info_text.pack(fill=tk.X)
            
            def update_folder_info():
                folder_path = folder_var.get()
                if folder_path and os.path.exists(folder_path):
                    try:
                        # 统计文件夹中的文档文件
                        from pathlib import Path
                        supported_extensions = {'.txt', '.pdf', '.docx', '.doc', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv'}
                        
                        folder_path_obj = Path(folder_path)
                        document_files = []
                        for file_path in folder_path_obj.rglob('*'):
                            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                                document_files.append(file_path)
                        
                        total_size = sum(f.stat().st_size for f in document_files if f.exists())
                        size_str = f"{total_size:,} 字节"
                        if total_size > 1024:
                            size_str += f" ({total_size/1024:.1f} KB)"
                        if total_size > 1024*1024:
                            size_str += f" ({total_size/(1024*1024):.1f} MB)"
                        
                        info_text.delete(1.0, tk.END)
                        info_text.insert(tk.END, f"文件夹: {os.path.basename(folder_path)}\n")
                        info_text.insert(tk.END, f"支持的文档文件: {len(document_files)} 个\n")
                        info_text.insert(tk.END, f"总大小: {size_str}")
                    except Exception as e:
                        info_text.delete(1.0, tk.END)
                        info_text.insert(tk.END, f"无法获取文件夹信息: {e}")
                else:
                    info_text.delete(1.0, tk.END)
            
            # 进度显示
            progress_frame = ttk.Frame(main_frame)
            progress_frame.pack(fill=tk.X, pady=(0, 15))
            
            progress_var = tk.StringVar(value="等待开始...")
            progress_label = ttk.Label(progress_frame, textvariable=progress_var)
            progress_label.pack()
            
            # 结果显示区域
            result_frame = ttk.LabelFrame(main_frame, text="批量解读结果", padding="5")
            result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
            
            # 结果文本显示
            result_text = scrolledtext.ScrolledText(
                result_frame,
                wrap=tk.WORD,
                height=15
            )
            result_text.pack(fill=tk.BOTH, expand=True)
            
            # 按钮框架
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
            
            # 进度条
            progress_var = tk.StringVar(value="")
            progress_label = ttk.Label(button_frame, textvariable=progress_var)
            progress_label.pack(side=tk.LEFT, padx=(0, 10))
            
            # 查看解读结果按钮
            def open_viewer():
                try:
                    import subprocess
                    import sys
                    # 启动查看器服务器
                    subprocess.Popen([sys.executable, "start_viewer_server.py"], 
                                   cwd=os.getcwd(), 
                                   creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
                    self.log_message("已启动文章阅读助手服务器")
                except Exception as e:
                    self.log_message(f"启动文章阅读助手失败: {e}")
                    messagebox.showerror("错误", f"启动文章阅读助手失败: {e}")
            
            ttk.Button(
                button_frame,
                text="查看解读结果",
                command=open_viewer
            ).pack(side=tk.RIGHT, padx=5)
            
            ttk.Button(
                button_frame,
                text="关闭",
                command=reader_window.destroy
            ).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            self.root.after(0, lambda err=e: self.log_message(f"显示文件解读对话框失败: {err}"))
            self.root.after(0, lambda err=e: messagebox.showerror("错误", f"显示文件解读对话框失败: {err}"))
    

    
    
    

    

    

    

    

    

    

    
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
            timestamp = item['values'][0]
            
            if timestamp == "暂无日志记录" or timestamp.startswith("加载失败"):
                return
            
            # 获取详细日志信息
            log_manager = TransferLogManager()
            logs = log_manager.get_all_logs()
            
            target_log = None
            for log in logs:
                if log.get('timestamp') == timestamp:
                    target_log = log
                    break
            
            if not target_log:
                messagebox.showerror("错误", "找不到对应的日志记录")
                return
            
            # 创建详情窗口
            detail_window = tk.Toplevel(self.root)
            detail_window.title(f"日志详情 - {timestamp}")
            detail_window.geometry("800x600")
            detail_window.transient(self.root)
            detail_window.grab_set()
            
            # 创建主框架
            main_frame = ttk.Frame(detail_window, padding="10")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 基本信息
            info_frame = ttk.LabelFrame(main_frame, text="基本信息", padding="5")
            info_frame.pack(fill=tk.X, pady=(0, 10))
            
            ttk.Label(info_frame, text=f"时间: {target_log.get('timestamp', 'N/A')}").pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"会话名称: {target_log.get('session_name', 'N/A')}").pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"源目录: {target_log.get('source_directory', 'N/A')}").pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"目标目录: {target_log.get('target_directory', 'N/A')}").pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"文件总数: {len(target_log.get('files', []))}").pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"状态: {'已完成' if target_log.get('completed', False) else '进行中'}").pack(anchor=tk.W)
            
            # 文件列表
            files_frame = ttk.LabelFrame(main_frame, text="文件列表", padding="5")
            files_frame.pack(fill=tk.BOTH, expand=True)
            
            # 创建文件列表树形视图
            files_tree = ttk.Treeview(
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
            files_scrollbar = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=files_tree.yview)
            files_tree.configure(yscrollcommand=files_scrollbar.set)
            
            files_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            files_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 填充文件数据
            for file_info in target_log.get('files', []):
                source_path = file_info.get('source_path', 'N/A')
                target_path = file_info.get('target_path', 'N/A')
                status = file_info.get('status', 'N/A')
                
                files_tree.insert("", "end", values=(source_path, target_path, status))
            
            # 关闭按钮
            ttk.Button(
                main_frame,
                text="关闭",
                command=detail_window.destroy
            ).pack(pady=(10, 0))
            
        except Exception as e:
            self.log_message(f"显示日志详情失败: {e}")
            messagebox.showerror("错误", f"显示日志详情失败: {e}")
    
    def _execute_restore(self, log_file, dry_run, progress_var, result_text, restore_window):
        """执行文件恢复操作"""
        try:
            # 获取日志管理器
            log_manager = TransferLogManager()
            
            if dry_run:
                progress_var.set("正在分析恢复操作...")
                result = log_manager.preview_restore(log_file)
                
                def update_preview():
                    result_text.delete(1.0, tk.END)
                    result_text.insert(tk.END, "=== 恢复预览 ===\n\n")
                    result_text.insert(tk.END, f"日志文件: {log_file}\n")
                    result_text.insert(tk.END, f"可恢复文件数: {result.get('restorable_count', 0)}\n")
                    result_text.insert(tk.END, f"无法恢复文件数: {result.get('non_restorable_count', 0)}\n\n")
                    
                    if result.get('restorable_files'):
                        result_text.insert(tk.END, "可恢复的文件:\n")
                        for file_info in result['restorable_files']:
                            result_text.insert(tk.END, f"  {file_info['target_path']} -> {file_info['source_path']}\n")
                        result_text.insert(tk.END, "\n")
                    
                    if result.get('non_restorable_files'):
                        result_text.insert(tk.END, "无法恢复的文件（目标文件不存在）:\n")
                        for file_info in result['non_restorable_files']:
                            result_text.insert(tk.END, f"  {file_info['target_path']}\n")
                    
                    progress_var.set("预览完成")
                
                restore_window.after(0, update_preview)
                
            else:
                progress_var.set("正在执行恢复操作...")
                result = log_manager.restore_files(log_file)
                
                def update_result():
                    result_text.delete(1.0, tk.END)
                    result_text.insert(tk.END, "=== 恢复结果 ===\n\n")
                    result_text.insert(tk.END, f"日志文件: {log_file}\n")
                    result_text.insert(tk.END, f"成功恢复: {result.get('restored_count', 0)} 个文件\n")
                    result_text.insert(tk.END, f"恢复失败: {result.get('failed_count', 0)} 个文件\n\n")
                    
                    if result.get('restored_files'):
                        result_text.insert(tk.END, "成功恢复的文件:\n")
                        for file_info in result['restored_files']:
                            result_text.insert(tk.END, f"  {file_info['target_path']} -> {file_info['source_path']}\n")
                        result_text.insert(tk.END, "\n")
                    
                    if result.get('failed_files'):
                        result_text.insert(tk.END, "恢复失败的文件:\n")
                        for file_info in result['failed_files']:
                            result_text.insert(tk.END, f"  {file_info['target_path']}: {file_info.get('error', '未知错误')}\n")
                    
                    progress_var.set("恢复完成")
                    
                    # 记录日志
                    self.root.after(0, lambda: self.log_message(f"文件恢复完成: 成功 {result.get('restored_count', 0)} 个，失败 {result.get('failed_count', 0)} 个"))
                
                restore_window.after(0, update_result)
                
        except Exception as e:
            def show_error():
                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, f"恢复操作失败: {e}")
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