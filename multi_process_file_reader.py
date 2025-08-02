#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多进程文件解读管理器

支持多任务多进程并行处理，充分利用大模型的并行处理能力
每个任务可以启动多个进程同时处理文件，大幅提升处理速度

单独执行使用方法:
    python multi_process_file_reader.py

功能说明:
    1. 图形界面管理多个文件解读任务
    2. 每个任务支持多进程并行处理
    3. 智能进程数量管理，避免资源冲突
    4. 实时显示任务进度和状态
    5. 支持任务启动、停止、重启、删除和统计
    6. 自动去重检测，避免重复处理
    7. 结果保存到 ai_organize_result.json

界面功能:
    - 创建任务: 选择文件夹，设置摘要长度和进程数
    - 任务管理: 启动、停止、重启、删除任务
    - 进度监控: 实时显示处理进度和当前文件
    - 统计信息: 查看成功/失败/跳过/路径更新的文件数量
    - 任务详情: 双击任务查看详细信息
    - 进程管理: 动态调整每个任务的进程数量

支持的文件格式:
    - 文本文件: .txt, .md, .py, .js, .html, .css, .json, .xml, .csv
    - 文档文件: .pdf, .docx, .doc
    - 图片文件: .jpg, .jpeg, .png, .bmp, .gif, .tiff, .webp

作者: AI Assistant
创建时间: 2025-01-15
更新时间: 2025-07-28
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
import multiprocessing
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import queue

# 可选导入psutil，如果不可用则使用备用方法
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("警告: psutil库未安装，将使用备用方法获取系统信息")

# 全局文件锁，防止多任务同时写入
_result_file_lock = threading.Lock()

class ProcessFileReader:
    """进程级文件解读器，每个进程独立运行"""
    
    def __init__(self, process_id: int, model_name: str = None):
        self.process_id = process_id
        self.model_name = model_name
        self.setup_logging()
    
    def setup_logging(self):
        """设置日志记录"""
        logging.basicConfig(
            level=logging.INFO,
            format=f'%(asctime)s - Process-{self.process_id} - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
    
    def process_file(self, file_path: str, summary_length: int = 200) -> Dict[str, Any]:
        """处理单个文件"""
        try:
            from file_reader import FileReader
            
            # 初始化文件解读器
            file_reader = FileReader(model_name=self.model_name)
            file_reader.summary_length = summary_length
            
            # 生成摘要（确保指定结果文件路径以正确进行去重检查）
            result = file_reader.generate_summary(file_path, summary_length, "ai_organize_result.json")
            
            # 添加进程信息
            result['process_id'] = self.process_id
            result['processing_time'] = time.time()
            
            return result
            
        except Exception as e:
            logging.error(f"进程 {self.process_id} 处理文件失败: {file_path} - {e}")
            return {
                'file_path': file_path,
                'file_name': Path(file_path).name,
                'success': False,
                'extracted_text': '',
                'summary': '',
                'error': str(e),
                'model_used': self.model_name,
                'timestamp': datetime.now().isoformat(),
                'process_id': self.process_id,
                'processing_time': time.time()
            }

def process_file_worker(process_id: int, file_queue: multiprocessing.Queue, result_queue: multiprocessing.Queue, 
                       summary_length: int, model_name: str = None, working_dir: str = None):
    """进程工作函数"""
    try:
        # 确保子进程在正确的工作目录下运行
        if working_dir and os.path.exists(working_dir):
            os.chdir(working_dir)
            logging.info(f"进程 {process_id} 切换到工作目录: {working_dir}")
        
        # 初始化进程级文件解读器
        reader = ProcessFileReader(process_id, model_name)
        
        while True:
            try:
                # 从队列获取文件路径
                file_path = file_queue.get(timeout=1)
                
                # 检查是否为结束信号
                if file_path == "STOP":
                    break
                
                # 处理文件
                result = reader.process_file(file_path, summary_length)
                
                # 将结果放入结果队列
                result_queue.put(result)
                
            except queue.Empty:
                # 队列超时，继续等待
                continue
            except Exception as e:
                logging.error(f"进程 {process_id} 工作异常: {e}")
                # 即使出现异常也要继续处理下一个文件
                continue
                
    except Exception as e:
        logging.error(f"进程 {process_id} 初始化失败: {e}")
        # 发送错误结果到队列，确保主线程知道进程失败
        try:
            error_result = {
                'file_path': '',
                'file_name': '',
                'success': False,
                'extracted_text': '',
                'summary': '',
                'error': f'进程 {process_id} 初始化失败: {str(e)}',
                'model_used': model_name,
                'timestamp': datetime.now().isoformat(),
                'process_id': process_id,
                'processing_time': time.time()
            }
            result_queue.put(error_result)
        except:
            pass

class MultiProcessFileReadTask:
    """多进程文件解读任务"""
    
    def __init__(self, task_id: str, folder_path: str, summary_length: int = 200, max_processes: int = 4, gui_logger=None):
        self.task_id = task_id
        self.folder_path = folder_path
        self.summary_length = summary_length
        self.max_processes = max_processes
        self.gui_logger = gui_logger  # GUI日志记录器
        self.status = "等待中"  # 等待中, 运行中, 已完成, 失败
        self.progress = 0.0
        self.current_file = ""
        self.total_files = 0
        self.processed_files = 0
        self.successful_reads = 0
        self.failed_reads = 0
        self.skipped_reads = 0
        self.path_updated_reads = 0
        self.start_time = None
        self.end_time = None
        self.error_message = ""
        self.stop_flag = False
        
        # 多进程相关
        self.processes = []
        self.file_queue = None
        self.result_queue = None
        self.result_thread = None
        
        # 设置日志
        self.setup_logging()
    
    def gui_log(self, message: str, level: str = "INFO"):
        """向GUI发送日志消息"""
        if self.gui_logger:
            self.gui_logger(f"[{self.task_id}] {message}", level)
    
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
            time.sleep(1)  # 等待进程结束
        
        # 重置状态
        self.status = "运行中"
        self.start_time = datetime.now()
        self.stop_flag = False
        
        logging.info(f"任务 {self.task_id} 开始运行")
        self.gui_log("任务开始运行")
        
        # 启动新线程
        self.thread = threading.Thread(target=self._run_task, daemon=True)
        self.thread.start()
    
    def stop(self):
        """停止任务"""
        self.stop_flag = True
        self.status = "已停止"
        
        logging.info(f"任务 {self.task_id} 已停止")
        self.gui_log("任务已停止")
        
        # 停止所有进程
        self._stop_processes()
    
    def _stop_processes(self):
        """停止所有子进程"""
        try:
            # 发送停止信号到文件队列
            if self.file_queue:
                for _ in range(len(self.processes)):
                    self.file_queue.put("STOP")
            
            # 等待进程结束
            for process in self.processes:
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=5)
                    if process.is_alive():
                        process.kill()
            
            self.processes.clear()
            
        except Exception as e:
            logging.error(f"停止进程失败: {e}")
    
    def _safe_append_result(self, result):
        """安全地追加结果到文件，使用全局锁防止并发冲突"""
        with _result_file_lock:
            try:
                from file_reader import FileReader
                file_reader = FileReader()
                # 使用文件解读器的安全写入方法，确保与multi_task_file_reader.py一致
                file_reader.append_result_to_file("ai_organize_result.json", result, self.folder_path)
                return True
            except Exception as e:
                logging.error(f"任务 {self.task_id}: 写入结果失败: {e}")
                return False
    
    def _result_processor(self):
        """结果处理线程"""
        try:
            while not self.stop_flag:
                try:
                    # 从结果队列获取结果
                    result = self.result_queue.get(timeout=1)
                    
                    # 检查处理状态
                    processing_status = result.get('processing_status', '')
                    
                    if processing_status == '已跳过':
                        # 完全重复的文件，跳过处理
                        self.skipped_reads += 1
                        logging.info(f"文件完全重复，跳过: {result['file_name']}")
                        continue
                    elif processing_status == '路径已更新':
                        # 同名但路径不同的文件，复用摘要并更新路径
                        self.path_updated_reads += 1
                        logging.info(f"文件路径已更新: {result['file_name']}")
                        # 使用安全写入方法
                        self._safe_append_result(result)
                        continue
                    
                    # 检查处理结果
                    if result['success']:
                        # 提取路径标签（如果不是路径更新情况）
                        if not result.get('tags'):
                            from file_reader import FileReader
                            file_reader = FileReader()
                            result['tags'] = file_reader.extract_path_tags(result['file_path'], self.folder_path)
                        self.successful_reads += 1
                        
                        # 使用安全写入方法
                        if self._safe_append_result(result):
                            logging.info(f"文件解读成功: {result['file_name']} (进程: {result.get('process_id', 'N/A')})")
                        else:
                            logging.warning(f"文件解读成功但写入失败: {result['file_name']}")
                    else:
                        self.failed_reads += 1
                        logging.warning(f"文件解读失败: {result['file_name']} - {result.get('error', '未知错误')}")
                    
                    # 更新进度
                    self.processed_files += 1
                    if self.total_files > 0:
                        self.progress = (self.processed_files / self.total_files) * 100
                    
                except queue.Empty:
                    # 队列超时，继续等待
                    continue
                except Exception as e:
                    logging.error(f"结果处理异常: {e}")
                    # 即使出现异常也要更新进度，避免卡死
                    self.processed_files += 1
                    self.failed_reads += 1
                    if self.total_files > 0:
                        self.progress = (self.processed_files / self.total_files) * 100
                    continue
                    
        except Exception as e:
            logging.error(f"结果处理线程异常: {e}")
            # 确保任务状态正确更新
            if not self.stop_flag:
                self.status = "失败"
                self.error_message = f"结果处理线程异常: {str(e)}"
    
    def _run_task(self):
        """运行任务的具体实现"""
        try:
            from ai_client_manager import get_ai_manager
            
            # 确保AI客户端管理器正常工作
            ai_manager = get_ai_manager()
            if ai_manager.get_available_models_count() == 0:
                ai_manager.refresh_clients()
                if ai_manager.get_available_models_count() == 0:
                    self.status = "失败"
                    self.error_message = "没有可用的AI模型，请检查Ollama服务"
                    return
            
            # 获取可用模型信息
            available_models = ai_manager.get_enabled_models()
            if not available_models:
                self.status = "失败"
                self.error_message = "没有可用的AI模型"
                return
            
            # 选择模型（使用优先级最高的）
            selected_model = min(available_models, key=lambda x: x.priority)
            model_name = selected_model.model_name
            
            # 扫描文件夹中的文件
            folder_path_obj = Path(self.folder_path)
            
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
            
            if not files:
                self.status = "失败"
                self.error_message = f"文件夹中没有找到可解读的文件: {self.folder_path}"
                return
            
            self.total_files = len(files)
            logging.info(f"任务 {self.task_id} 开始处理 {self.total_files} 个文件，使用 {self.max_processes} 个进程")
            self.gui_log(f"开始处理 {self.total_files} 个文件，使用 {self.max_processes} 个进程")
            
            # 创建多进程队列
            self.file_queue = multiprocessing.Queue()
            self.result_queue = multiprocessing.Queue()
            
            # 启动结果处理线程
            self.result_thread = threading.Thread(target=self._result_processor, daemon=True)
            self.result_thread.start()
            
            # 启动工作进程
            for i in range(self.max_processes):
                process = multiprocessing.Process(
                    target=process_file_worker,
                    args=(i + 1, self.file_queue, self.result_queue, self.summary_length, model_name, os.getcwd())
                )
                process.start()
                self.processes.append(process)
                logging.info(f"启动进程 {i + 1}")
                self.gui_log(f"启动进程 {i + 1}")
            
            # 将文件路径放入队列
            for file_path in files:
                if self.stop_flag:
                    break
                self.file_queue.put(file_path)
            
            # 等待所有文件处理完成
            while self.processed_files < self.total_files and not self.stop_flag:
                time.sleep(0.1)
            
            # 发送停止信号
            for _ in range(len(self.processes)):
                self.file_queue.put("STOP")
            
            # 等待进程结束
            for process in self.processes:
                process.join(timeout=10)
            
            # 等待结果处理线程结束
            if self.result_thread and self.result_thread.is_alive():
                self.result_thread.join(timeout=5)
            
            if not self.stop_flag:
                self.status = "已完成"
                completion_msg = f"任务完成: 成功 {self.successful_reads}, 失败 {self.failed_reads}, 跳过 {self.skipped_reads}, 路径更新 {self.path_updated_reads}"
                logging.info(f"任务 {self.task_id} {completion_msg}")
                self.gui_log(completion_msg)
            self.end_time = datetime.now()
            
        except Exception as e:
            self.status = "失败"
            self.error_message = str(e)
            self.end_time = datetime.now()
            logging.error(f"任务 {self.task_id} 执行失败: {e}")
        finally:
            # 清理资源
            self._stop_processes()
            # 确保结果处理线程也结束
            if hasattr(self, 'result_thread') and self.result_thread and self.result_thread.is_alive():
                self.stop_flag = True
                self.result_thread.join(timeout=5)

class MultiProcessFileReaderGUI:
    """多进程文件解读GUI"""
    
    def __init__(self):
        self.root = tb.Window(themename="flatly")
        self.root.title("多进程文件解读管理器")
        self.root.geometry("1200x900")
        
        # 任务管理
        self.tasks: Dict[str, MultiProcessFileReadTask] = {}
        self.task_counter = 0
        
        # 日志管理
        self.log_queue = queue.Queue()
        self.log_lock = threading.Lock()
        
        # 创建界面
        self.create_widgets()
        
        # 启动状态更新线程
        self.update_thread = threading.Thread(target=self._update_status_loop, daemon=True)
        self.update_thread.start()
        
        # 启动日志更新线程
        self.log_thread = threading.Thread(target=self._update_log_loop, daemon=True)
        self.log_thread.start()
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = tb.Frame(self.root, padding="10")
        main_frame.pack(fill=BOTH, expand=True)
        
        # 标题
        title_label = tb.Label(
            main_frame,
            text="多进程文件解读管理器",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 10))
        
        # 说明文字
        desc_label = tb.Label(
            main_frame,
            text="支持多任务多进程并行处理，充分利用大模型的并行处理能力",
            font=('Arial', 10)
        )
        desc_label.pack(pady=(0, 20))
        
        # 创建任务区域
        self.create_task_creation_area(main_frame)
        
        # 任务列表区域
        self.create_task_list_area(main_frame)
        
        # 控制按钮区域
        self.create_control_buttons(main_frame)
        
        # 操作日志区域
        self.create_log_area(main_frame)
    
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
        
        # 摘要长度设置
        tb.Label(params_frame, text="摘要长度:", font=('Arial', 10)).pack(side=LEFT)
        
        self.summary_length_var = tb.IntVar(value=200)
        summary_scale = tb.Scale(
            params_frame,
            from_=100,
            to=500,
            variable=self.summary_length_var,
            orient=HORIZONTAL,
            length=150
        )
        summary_scale.pack(side=LEFT, padx=(10, 5))
        
        self.summary_length_label = tb.Label(params_frame, text="200字符", font=('Arial', 9))
        self.summary_length_label.pack(side=LEFT, padx=(5, 20))
        
        # 进程数设置
        tb.Label(params_frame, text="进程数:", font=('Arial', 10)).pack(side=LEFT)
        
        # 获取CPU核心数
        cpu_count = multiprocessing.cpu_count()
        recommended_processes = min(cpu_count, 8)  # 建议不超过8个进程
        
        self.process_count_var = tb.IntVar(value=recommended_processes)
        process_scale = tb.Scale(
            params_frame,
            from_=1,
            to=min(cpu_count * 2, 16),  # 最大不超过CPU核心数的2倍，且不超过16
            variable=self.process_count_var,
            orient=HORIZONTAL,
            length=150
        )
        process_scale.pack(side=LEFT, padx=(10, 5))
        
        self.process_count_label = tb.Label(params_frame, text=f"{recommended_processes}个", font=('Arial', 9))
        self.process_count_label.pack(side=LEFT, padx=(5, 0))
        
        # 绑定参数变化事件
        def update_summary_label(*args):
            value = self.summary_length_var.get()
            self.summary_length_label.config(text=f"{value}字符")
        
        def update_process_label(*args):
            value = self.process_count_var.get()
            self.process_count_label.config(text=f"{value}个")
        
        self.summary_length_var.trace_add('write', update_summary_label)
        self.process_count_var.trace_add('write', update_process_label)
        
        # 创建任务按钮
        def create_task():
            folder_path = self.folder_var.get().strip()
            if not folder_path:
                messagebox.showwarning("提示", "请先选择要解读的文件夹")
                self.log_message("创建任务失败：未选择文件夹", "WARNING")
                return
            
            if not os.path.exists(folder_path):
                messagebox.showerror("错误", "选择的文件夹不存在")
                self.log_message(f"创建任务失败：文件夹不存在 - {folder_path}", "ERROR")
                return
            
            # 检查是否已有相同文件夹的任务
            for task in self.tasks.values():
                if task.folder_path == folder_path and task.status in ["等待中", "运行中"]:
                    messagebox.showwarning("提示", "该文件夹已有正在运行的任务")
                    self.log_message(f"创建任务失败：文件夹已有运行中的任务 - {folder_path}", "WARNING")
                    return
            
            self.task_counter += 1
            task_id = f"Task_{self.task_counter}"
            
            # 创建新任务
            task = MultiProcessFileReadTask(
                task_id=task_id,
                folder_path=folder_path,
                summary_length=self.summary_length_var.get(),
                max_processes=self.process_count_var.get(),
                gui_logger=self.log_message
            )
            
            self.tasks[task_id] = task
            
            # 清空输入
            self.folder_var.set("")
            
            # 刷新任务列表
            self.refresh_task_list()
            
            # 记录日志
            self.log_message(f"创建任务 {task_id}：文件夹={os.path.basename(folder_path)}，进程数={self.process_count_var.get()}，摘要长度={self.summary_length_var.get()}")
            
            # 自动启动任务
            task.start()
            
            self.log_message(f"任务 {task_id} 已开始运行")
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
        columns = ('选择', '任务ID', '文件夹', '状态', '进度', '进程数', '成功/失败/跳过/更新/总数', '开始时间')
        self.task_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        
        # 设置列标题
        for col in columns:
            self.task_tree.heading(col, text=col)
            self.task_tree.column(col, width=80)
        
        # 设置特定列的宽度
        self.task_tree.column('选择', width=60)
        self.task_tree.column('任务ID', width=100)
        self.task_tree.column('文件夹', width=200)
        self.task_tree.column('进程数', width=80)
        self.task_tree.column('开始时间', width=150)
        self.task_tree.column('成功/失败/跳过/更新/总数', width=200)
        
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
    
    def create_log_area(self, parent):
        """创建操作日志区域"""
        log_frame = tb.LabelFrame(parent, text="操作日志", padding="10")
        log_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
        
        # 创建日志文本框
        self.log_text = tk.Text(
            log_frame,
            wrap=tk.WORD,
            height=8,
            font=('Consolas', 9),
            bg='#f8f9fa',
            fg='#212529'
        )
        
        # 添加滚动条
        log_scrollbar = ttk.Scrollbar(log_frame, orient=VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side=LEFT, fill=BOTH, expand=True)
        log_scrollbar.pack(side=RIGHT, fill=Y)
        
        # 初始日志
        self.log_message("系统启动完成，等待用户操作...")
    
    def log_message(self, message: str, level: str = "INFO"):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        # 将日志放入队列，由日志更新线程处理
        self.log_queue.put(log_entry)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("日志已清空")
    
    def _update_log_loop(self):
        """日志更新循环"""
        while True:
            try:
                # 从队列获取日志消息
                log_message = self.log_queue.get(timeout=1)
                
                # 在主线程中更新UI
                self.root.after(0, self._append_log_message, log_message)
                
            except queue.Empty:
                continue
            except:
                break
    
    def _append_log_message(self, message: str):
        """在主线程中追加日志消息"""
        try:
            self.log_text.insert(tk.END, message)
            self.log_text.see(tk.END)  # 自动滚动到底部
            
            # 限制日志行数，避免内存占用过大
            lines = self.log_text.get(1.0, tk.END).split('\n')
            if len(lines) > 1000:  # 保留最近1000行
                self.log_text.delete(1.0, f"{len(lines) - 500}.0")
        except:
            pass
    
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
                self.log_message("停止任务失败：未选择任务", "WARNING")
                return
            
            stopped_count = 0
            for task_id in selected_tasks:
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    if task.status == "运行中":
                        task.stop()
                        stopped_count += 1
                        self.log_message(f"已停止任务：{task_id}")
            
            if stopped_count > 0:
                messagebox.showinfo("成功", f"已停止 {stopped_count} 个任务")
                self.log_message(f"成功停止 {stopped_count} 个任务")
                # 取消勾选
                self.deselect_all_tasks()
            else:
                messagebox.showinfo("提示", "选中的任务都不在运行状态")
                self.log_message("停止任务失败：选中的任务都不在运行状态", "WARNING")
        
        def restart_selected_task():
            selected_tasks = self.get_selected_tasks()
            if not selected_tasks:
                messagebox.showwarning("提示", "请先勾选要重启的任务")
                self.log_message("重启任务失败：未选择任务", "WARNING")
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
                        self.log_message(f"已重启任务：{task_id}")
            
            if restart_count > 0:
                messagebox.showinfo("成功", f"已重启 {restart_count} 个任务")
                self.log_message(f"成功重启 {restart_count} 个任务")
                # 取消勾选
                self.deselect_all_tasks()
            else:
                messagebox.showinfo("提示", "选中的任务都无法重启（只有已停止或失败的任务可以重启）")
                self.log_message("重启任务失败：选中的任务都无法重启", "WARNING")
        
        def remove_selected_task():
            selected_tasks = self.get_selected_tasks()
            if not selected_tasks:
                messagebox.showwarning("提示", "请先勾选要删除的任务")
                self.log_message("删除任务失败：未选择任务", "WARNING")
                return
            
            # 检查是否有正在运行的任务
            running_tasks = []
            for task_id in selected_tasks:
                if task_id in self.tasks and self.tasks[task_id].status == "运行中":
                    running_tasks.append(task_id)
            
            if running_tasks:
                if not messagebox.askyesno("确认", f"有 {len(running_tasks)} 个任务正在运行，确定要删除吗？"):
                    self.log_message("删除任务操作已取消", "INFO")
                    return
            
            # 删除任务
            deleted_count = 0
            for task_id in selected_tasks:
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    if task.status == "运行中":
                        task.stop()
                        self.log_message(f"停止运行中的任务：{task_id}")
                    del self.tasks[task_id]
                    deleted_count += 1
                    self.log_message(f"已删除任务：{task_id}")
            
            self.refresh_task_list()
            messagebox.showinfo("成功", f"已删除 {deleted_count} 个任务")
            self.log_message(f"成功删除 {deleted_count} 个任务")
            # 取消勾选
            self.deselect_all_tasks()
        
        def clear_completed_tasks():
            completed_tasks = []
            for task_id, task in self.tasks.items():
                if task.status in ["已完成", "失败", "已停止"]:
                    completed_tasks.append(task_id)
            
            if not completed_tasks:
                messagebox.showinfo("提示", "没有已完成的任务")
                self.log_message("清理任务：没有已完成的任务", "INFO")
                return
            
            if messagebox.askyesno("确认", f"确定要删除 {len(completed_tasks)} 个已完成的任务吗？"):
                for task_id in completed_tasks:
                    del self.tasks[task_id]
                    self.log_message(f"清理已完成任务：{task_id}")
                self.refresh_task_list()
                messagebox.showinfo("成功", f"已删除 {len(completed_tasks)} 个已完成的任务")
                self.log_message(f"成功清理 {len(completed_tasks)} 个已完成的任务")
            else:
                messagebox.showinfo("提示", "操作已取消")
                self.log_message("清理任务操作已取消", "INFO")
        
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
            
            # 计算总进程数
            total_processes = sum(task.max_processes for task in self.tasks.values() if task.status == "运行中")
            
            # 获取系统信息
            cpu_count = multiprocessing.cpu_count()
            if PSUTIL_AVAILABLE:
                memory_usage = psutil.virtual_memory().percent
            else:
                memory_usage = "未知"
            
            stats_text = f"""
任务统计:
- 总任务数: {total_tasks}
- 运行中: {running_tasks}
- 已完成: {completed_tasks}
- 失败: {failed_tasks}
- 已停止: {stopped_tasks}
- 当前总进程数: {total_processes}

文件统计:
- 总文件数: {total_files}
- 成功解读: {total_successful} / {total_files}
- 解读失败: {total_failed} / {total_files}
- 跳过文件: {total_skipped} / {total_files}
- 路径更新: {total_path_updated} / {total_files}
- 成功率: {total_successful/(total_files-total_skipped)*100:.1f}% (排除跳过的文件)

系统信息:
- CPU核心数: {cpu_count}
- 内存使用: {memory_usage}{'%' if isinstance(memory_usage, (int, float)) else ''}
            """
            
            messagebox.showinfo("统计信息", stats_text)
            self.log_message("查看统计信息")
        
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
        
        tb.Button(
            button_frame,
            text="清空日志",
            command=self.clear_log,
            style='secondary.TButton'
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
                f"{task.max_processes}个",
                f"{task.successful_reads}/{task.failed_reads}/{task.skipped_reads}/{task.path_updated_reads}/{task.total_files}",
                start_time_str
            ))
            
            # 恢复勾选状态
            if task_id in old_checked:
                self.checked_items.add(task_id)
                self.task_tree.set(task_id, '选择', '☑')
    
    def on_task_double_click(self, event):
        """双击任务显示详情"""
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
        details_window.geometry("700x500")
        
        # 详情内容
        details_text = f"""
任务ID: {task.task_id}
文件夹路径: {task.folder_path}
状态: {task.status}
进度: {task.progress:.1f}%
总文件数: {task.total_files}
已处理: {task.processed_files}
成功解读: {task.successful_reads} / {task.total_files}
解读失败: {task.failed_reads} / {task.total_files}
跳过文件: {task.skipped_reads} / {task.total_files}
路径更新: {task.path_updated_reads} / {task.total_files}
进程数: {task.max_processes}
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
    app = MultiProcessFileReaderGUI()
    app.run()

if __name__ == "__main__":
    main() 