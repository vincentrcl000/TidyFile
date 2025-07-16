#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件整理器图形用户界面

本模块提供文件整理器的图形用户界面，包括：
1. 文件夹选择界面
2. 整理进度显示
3. 结果展示和确认
4. 错误处理和用户提示

作者: AI Assistant
创建时间: 2025-01-15
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime
from pathlib import Path

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from file_organizer import FileOrganizer, FileOrganizerError


class FileOrganizerGUI:
    """文件整理器图形用户界面类"""
    
    def __init__(self):
        """初始化 GUI 应用"""
        self.root = tk.Tk()
        self.root.title("智能文件整理器 v1.0")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 设置应用图标（如果有的话）
        try:
            # 可以在这里设置应用图标
            # self.root.iconbitmap('icon.ico')
            pass
        except:
            pass
            
        # 初始化变量
        self.source_directory = tk.StringVar()  # 源目录路径
        self.target_directory = tk.StringVar()  # 目标目录路径
        # 初始化文件整理器，启用转移日志功能
        self.organizer = FileOrganizer(enable_transfer_log=True)  # 文件整理器实例
        self.organize_results = None  # 整理结果
        
        # 创建界面
        self.create_widgets()
        
        # 居中显示窗口
        self.center_window()
        
    def center_window(self):
        """将窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
    def create_widgets(self):
        """创建界面组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(
            main_frame, 
            text="智能文件整理器", 
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 说明文字
        desc_label = ttk.Label(
            main_frame,
            text="使用 AI 智能分析文件内容，自动将文件分类到合适的文件夹中",
            font=('Arial', 10)
        )
        desc_label.grid(row=1, column=0, columnspan=3, pady=(0, 20))
        
        # 源目录选择
        ttk.Label(main_frame, text="待整理文件目录:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(
            main_frame, 
            textvariable=self.source_directory, 
            width=50
        ).grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=5)
        ttk.Button(
            main_frame, 
            text="浏览", 
            command=self.select_source_directory
        ).grid(row=2, column=2, pady=5)
        
        # 目标目录选择
        ttk.Label(main_frame, text="目标分类目录:").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Entry(
            main_frame, 
            textvariable=self.target_directory, 
            width=50
        ).grid(row=3, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=5)
        ttk.Button(
            main_frame, 
            text="浏览", 
            command=self.select_target_directory
        ).grid(row=3, column=2, pady=5)
        
        # 操作按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=20)
        
        # 开始整理按钮
        self.organize_button = ttk.Button(
            button_frame,
            text="开始智能整理",
            command=self.start_organize,
            style='Accent.TButton'
        )
        self.organize_button.pack(side=tk.LEFT, padx=5)
        
        # 预览按钮
        self.preview_button = ttk.Button(
            button_frame,
            text="预览分类结果",
            command=self.preview_classification
        )
        self.preview_button.pack(side=tk.LEFT, padx=5)
        
        # 转移日志按钮
        self.log_button = ttk.Button(
            button_frame,
            text="转移日志",
            command=self.show_transfer_logs
        )
        self.log_button.pack(side=tk.LEFT, padx=5)
        
        # 文件恢复按钮
        self.restore_button = ttk.Button(
            button_frame,
            text="文件恢复",
            command=self.show_restore_dialog
        )
        self.restore_button.pack(side=tk.LEFT, padx=5)
        
        # 重复文件删除按钮
        self.duplicate_button = ttk.Button(
            button_frame,
            text="删除重复文件",
            command=self.show_duplicate_removal_dialog
        )
        self.duplicate_button.pack(side=tk.LEFT, padx=5)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame,
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # 状态标签
        self.status_label = ttk.Label(main_frame, text="请选择源目录和目标目录")
        self.status_label.grid(row=6, column=0, columnspan=3, pady=5)
        
        # 日志显示区域
        log_frame = ttk.LabelFrame(main_frame, text="操作日志", padding="5")
        log_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=15,
            wrap=tk.WORD
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置主框架的行权重
        main_frame.rowconfigure(7, weight=1)
        
        # 初始化日志
        self.log_message("程序启动完成，请选择文件目录开始整理")
        
    def select_source_directory(self):
        """选择源目录"""
        directory = filedialog.askdirectory(
            title="选择待整理的文件目录",
            initialdir=os.path.expanduser("~")
        )
        if directory:
            self.source_directory.set(directory)
            self.log_message(f"已选择源目录: {directory}")
            self.update_status()
            
    def select_target_directory(self):
        """选择目标目录"""
        directory = filedialog.askdirectory(
            title="选择目标分类目录",
            initialdir=os.path.expanduser("~")
        )
        if directory:
            self.target_directory.set(directory)
            self.log_message(f"已选择目标目录: {directory}")
            self.update_status()
            
    def update_status(self):
        """更新状态显示"""
        source = self.source_directory.get()
        target = self.target_directory.get()
        
        if source and target:
            self.status_label.config(text="准备就绪，可以开始整理")
            self.organize_button.config(state='normal')
            self.preview_button.config(state='normal')
        elif source:
            self.status_label.config(text="请选择目标目录")
            self.organize_button.config(state='disabled')
            self.preview_button.config(state='disabled')
        elif target:
            self.status_label.config(text="请选择源目录")
            self.organize_button.config(state='disabled')
            self.preview_button.config(state='disabled')
        else:
            self.status_label.config(text="请选择源目录和目标目录")
            self.organize_button.config(state='disabled')
            self.preview_button.config(state='disabled')
            
    def log_message(self, message: str):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def preview_classification(self):
        """预览文件分类结果"""
        try:
            source = self.source_directory.get()
            target = self.target_directory.get()
            
            if not source or not target:
                messagebox.showerror("错误", "请先选择源目录和目标目录")
                return
                
            self.log_message("开始预览分类结果...")
            self.status_label.config(text="正在分析文件...")
            
            # 在新线程中执行预览
            threading.Thread(target=self._preview_worker, daemon=True).start()
            
        except Exception as e:
            self.log_message(f"预览失败: {e}")
            messagebox.showerror("错误", f"预览失败: {e}")
            
    def _preview_worker(self):
        """预览工作线程"""
        try:
            source = self.source_directory.get()
            target = self.target_directory.get()
            
            # 扫描文件和文件夹
            target_folders = self.organizer.scan_target_folders(target)
            source_files = self.organizer.scan_source_files(source)
            
            if not target_folders:
                self.root.after(0, lambda: messagebox.showerror("错误", "目标目录中没有子文件夹"))
                return
                
            if not source_files:
                self.root.after(0, lambda: messagebox.showerror("错误", "源目录中没有文件"))
                return
                
            # 初始化 Ollama
            self.organizer.initialize_ollama()
            
            # 预览前几个文件的分类结果
            preview_count = min(10, len(source_files))
            preview_results = []
            
            for i, file_path in enumerate(source_files[:preview_count]):
                filename = Path(file_path).name
                
                # 使用新的classify_file方法
                folder, reason, success = self.organizer.classify_file(file_path, target)
                
                preview_results.append({
                    'filename': filename,
                    'recommended_folder': folder if success else "无推荐",
                    'reason': reason,
                    'success': success
                })
                
                # 更新进度
                progress = (i + 1) / preview_count * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                
            # 显示预览结果
            self.root.after(0, lambda: self._show_preview_results(preview_results, len(source_files)))
            
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"预览失败: {e}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"预览失败: {e}"))
        finally:
            self.root.after(0, lambda: self.progress_var.set(0))
            self.root.after(0, lambda: self.status_label.config(text="预览完成"))
            
    def _show_preview_results(self, preview_results: list, total_files: int):
        """显示预览结果"""
        preview_window = tk.Toplevel(self.root)
        preview_window.title("分类预览结果")
        preview_window.geometry("700x500")
        preview_window.transient(self.root)
        preview_window.grab_set()
        
        # 创建预览内容
        frame = ttk.Frame(preview_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(
            frame,
            text=f"预览前 {len(preview_results)} 个文件的分类结果（共 {total_files} 个文件）:",
            font=('Arial', 12, 'bold')
        ).pack(pady=(0, 10))
        
        # 创建结果显示区域
        result_text = scrolledtext.ScrolledText(frame, height=18, wrap=tk.WORD)
        result_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 统计信息
        successful_count = sum(1 for result in preview_results if result['success'])
        failed_count = len(preview_results) - successful_count
        
        result_text.insert(tk.END, f"=== 分类预览统计 ===\n")
        result_text.insert(tk.END, f"成功推荐: {successful_count} 个文件\n")
        result_text.insert(tk.END, f"需要手动处理: {failed_count} 个文件\n\n")
        
        for i, result in enumerate(preview_results, 1):
            filename = result['filename']
            folder = result['recommended_folder']
            reason = result['reason']
            success = result['success']
            
            result_text.insert(tk.END, f"[{i}] 文件: {filename}\n")
            
            if success:
                result_text.insert(tk.END, f"✓ 推荐文件夹: {folder}\n")
                result_text.insert(tk.END, f"  {reason}\n")
            else:
                result_text.insert(tk.END, f"⚠ 分类结果: {reason}\n")
                if "建议创建新文件夹" in reason:
                    result_text.insert(tk.END, f"  建议操作：在目标目录中创建合适的文件夹后重新分类\n")
            
            result_text.insert(tk.END, "\n")
            
        result_text.config(state='disabled')
        
        # 按钮框架
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(
            button_frame,
            text="确定",
            command=preview_window.destroy
        ).pack(side=tk.RIGHT)
        
    def start_organize(self):
        """开始文件整理"""
        try:
            source = self.source_directory.get()
            target = self.target_directory.get()
            
            if not source or not target:
                messagebox.showerror("错误", "请先选择源目录和目标目录")
                return
                
            # 确认对话框
            if not messagebox.askyesno(
                "确认整理",
                f"即将开始整理文件:\n\n源目录: {source}\n目标目录: {target}\n\n确定要继续吗？"
            ):
                return
                
            self.log_message("开始文件整理...")
            self.status_label.config(text="正在整理文件...")
            self.organize_button.config(state='disabled')
            self.preview_button.config(state='disabled')
            
            # 在新线程中执行整理
            threading.Thread(target=self._organize_worker, daemon=True).start()
            
        except Exception as e:
            self.log_message(f"启动整理失败: {e}")
            messagebox.showerror("错误", f"启动整理失败: {e}")
            
    def _organize_worker(self):
        """文件整理工作线程"""
        try:
            source = self.source_directory.get()
            target = self.target_directory.get()
            
            # 执行文件整理，使用已有的文件整理器实例
            self.organize_results = self.organizer.organize_files(
                source_directory=source, 
                target_directory=target
            )
            
            # 更新进度
            self.root.after(0, lambda: self.progress_var.set(100))
            
            # 显示结果
            self.root.after(0, self._show_organize_results)
            
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"整理失败: {e}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"整理失败: {e}"))
        finally:
            self.root.after(0, lambda: self.organize_button.config(state='normal'))
            self.root.after(0, lambda: self.preview_button.config(state='normal'))
            self.root.after(0, lambda: self.progress_var.set(0))
            self.root.after(0, lambda: self.status_label.config(text="整理完成"))
            
    def _show_organize_results(self):
        """显示整理结果"""
        if not self.organize_results:
            return
            
        results = self.organize_results
        
        # 记录结果日志
        self.log_message(f"整理完成: 成功 {len(results['success'])}, 失败 {len(results['failed'])}")
        
        # 显示结果对话框
        result_message = f"""
文件整理完成！

总文件数: {results['total_files']}
成功整理: {len(results['success'])}
整理失败: {len(results['failed'])}

耗时: {(results['end_time'] - results['start_time']).total_seconds():.1f} 秒
"""
        
        if len(results['success']) > 0:
            # 询问是否删除原文件
            if messagebox.askyesno(
                "整理完成",
                result_message + "\n文件已成功复制到目标目录。\n\n是否删除原文件？"
            ):
                self._delete_source_files()
        else:
            messagebox.showinfo("整理完成", result_message)
            
    def _delete_source_files(self):
        """删除源文件"""
        try:
            if not self.organize_results or not self.organize_results['success']:
                return
                
            deleted_count = 0
            for file_info in self.organize_results['success']:
                source_path = file_info['source_path']
                try:
                    os.remove(source_path)
                    deleted_count += 1
                    self.log_message(f"已删除原文件: {source_path}")
                except Exception as e:
                    self.log_message(f"删除文件失败: {source_path}, 错误: {e}")
                    
            messagebox.showinfo(
                "删除完成",
                f"已删除 {deleted_count} 个原文件"
            )
            
        except Exception as e:
            self.log_message(f"删除原文件失败: {e}")
            messagebox.showerror("错误", f"删除原文件失败: {e}")
    
    def show_transfer_logs(self):
        """显示转移日志管理界面"""
        try:
            # 检查转移日志功能是否可用
            if not self.organizer.enable_transfer_log:
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
            self.log_message(f"显示转移日志失败: {e}")
            messagebox.showerror("错误", f"显示转移日志失败: {e}")
    
    def _load_transfer_logs(self, tree_widget):
        """加载转移日志到树形控件"""
        try:
            # 清空现有数据
            for item in tree_widget.get_children():
                tree_widget.delete(item)
            
            # 获取日志文件列表
            log_files = self.organizer.get_transfer_logs()
            
            for log_file in log_files:
                try:
                    # 获取日志摘要
                    summary = self.organizer.get_transfer_log_summary(log_file)
                    session_info = summary['session_info']
                    
                    # 解析时间
                    start_time = session_info.get('start_time', '')
                    if start_time:
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                            time_str = dt.strftime('%Y-%m-%d %H:%M')
                        except:
                            time_str = start_time[:16]  # 截取前16个字符
                    else:
                        time_str = '未知'
                    
                    # 插入数据
                    tree_widget.insert('', tk.END, values=(
                        time_str,
                        session_info.get('session_name', '未知'),
                        session_info.get('total_operations', 0),
                        session_info.get('successful_operations', 0),
                        session_info.get('failed_operations', 0),
                        log_file
                    ))
                    
                except Exception as e:
                    # 如果单个日志文件解析失败，跳过但记录错误
                    self.log_message(f"解析日志文件失败 {log_file}: {e}")
                    continue
            
        except Exception as e:
            self.log_message(f"加载转移日志失败: {e}")
            messagebox.showerror("错误", f"加载转移日志失败: {e}")
    
    def _show_log_details(self, tree_widget):
        """显示选中日志的详细信息"""
        try:
            selection = tree_widget.selection()
            if not selection:
                messagebox.showwarning("提示", "请先选择一个日志记录")
                return
            
            # 获取选中的日志文件路径
            item = tree_widget.item(selection[0])
            log_file_path = item['values'][5]  # 文件路径在第6列
            
            # 获取详细信息
            summary = self.organizer.get_transfer_log_summary(log_file_path)
            
            # 创建详情窗口
            detail_window = tk.Toplevel(self.root)
            detail_window.title("转移日志详情")
            detail_window.geometry("700x500")
            detail_window.transient(self.root)
            detail_window.grab_set()
            
            # 创建详情内容
            frame = ttk.Frame(detail_window, padding="10")
            frame.pack(fill=tk.BOTH, expand=True)
            
            # 会话信息
            session_info = summary['session_info']
            info_text = f"""会话信息:
会话名称: {session_info.get('session_name', '未知')}
开始时间: {session_info.get('start_time', '未知')}
结束时间: {session_info.get('end_time', '未知')}
总操作数: {session_info.get('total_operations', 0)}
成功操作: {session_info.get('successful_operations', 0)}
失败操作: {session_info.get('failed_operations', 0)}

操作类型统计:
"""
            
            for op_type, count in summary.get('operation_types', {}).items():
                info_text += f"{op_type}: {count}\n"
            
            info_text += "\n目标文件夹统计:\n"
            for folder, count in summary.get('target_folders', {}).items():
                info_text += f"{folder}: {count}\n"
            
            info_text += f"\n总文件大小: {summary.get('total_size_mb', 0)} MB"
            
            # 显示详情
            detail_text = scrolledtext.ScrolledText(frame, height=20, wrap=tk.WORD)
            detail_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            detail_text.insert(tk.END, info_text)
            detail_text.config(state='disabled')
            
            # 关闭按钮
            ttk.Button(
                frame,
                text="关闭",
                command=detail_window.destroy
            ).pack(side=tk.RIGHT)
            
        except Exception as e:
            self.log_message(f"显示日志详情失败: {e}")
            messagebox.showerror("错误", f"显示日志详情失败: {e}")
    
    def _restore_from_selected_log(self, tree_widget):
        """从选中的日志恢复文件"""
        try:
            selection = tree_widget.selection()
            if not selection:
                messagebox.showwarning("提示", "请先选择一个日志记录")
                return
            
            # 获取选中的日志文件路径
            item = tree_widget.item(selection[0])
            log_file_path = item['values'][5]  # 文件路径在第6列
            
            # 显示恢复确认对话框
            if not messagebox.askyesno(
                "确认恢复",
                "确定要从此日志恢复文件吗？\n\n注意：这将把文件从目标位置移动回原始位置。"
            ):
                return
            
            # 先进行试运行
            self.log_message("开始试运行恢复操作...")
            dry_run_results = self.organizer.restore_files_from_log(
                log_file_path=log_file_path,
                dry_run=True
            )
            
            # 显示试运行结果
            dry_run_message = f"""试运行结果:

可恢复文件: {dry_run_results['successful_restores']}
无法恢复: {dry_run_results['failed_restores']}
跳过文件: {dry_run_results['skipped_operations']}

确定要执行实际恢复操作吗？"""
            
            if not messagebox.askyesno("确认执行恢复", dry_run_message):
                return
            
            # 执行实际恢复
            self.log_message("开始执行文件恢复...")
            restore_results = self.organizer.restore_files_from_log(
                log_file_path=log_file_path,
                dry_run=False
            )
            
            # 显示恢复结果
            result_message = f"""文件恢复完成!

成功恢复: {restore_results['successful_restores']}
恢复失败: {restore_results['failed_restores']}
跳过文件: {restore_results['skipped_operations']}"""
            
            messagebox.showinfo("恢复完成", result_message)
            self.log_message(f"文件恢复完成: 成功 {restore_results['successful_restores']}, 失败 {restore_results['failed_restores']}")
            
        except Exception as e:
            self.log_message(f"文件恢复失败: {e}")
            messagebox.showerror("错误", f"文件恢复失败: {e}")
    
    def _cleanup_old_logs(self, tree_widget):
        """清理旧的转移日志"""
        try:
            # 询问保留天数
            days_dialog = tk.Toplevel(self.root)
            days_dialog.title("清理旧日志")
            days_dialog.geometry("300x150")
            days_dialog.transient(self.root)
            days_dialog.grab_set()
            
            frame = ttk.Frame(days_dialog, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(frame, text="保留最近多少天的日志？").pack(pady=(0, 10))
            
            days_var = tk.StringVar(value="30")
            ttk.Entry(frame, textvariable=days_var, width=10).pack(pady=(0, 10))
            
            result = {'confirmed': False, 'days': 30}
            
            def confirm():
                try:
                    result['days'] = int(days_var.get())
                    result['confirmed'] = True
                    days_dialog.destroy()
                except ValueError:
                    messagebox.showerror("错误", "请输入有效的天数")
            
            button_frame = ttk.Frame(frame)
            button_frame.pack(fill=tk.X)
            
            ttk.Button(button_frame, text="确定", command=confirm).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="取消", command=days_dialog.destroy).pack(side=tk.LEFT, padx=5)
            
            # 等待对话框关闭
            days_dialog.wait_window()
            
            if not result['confirmed']:
                return
            
            # 执行清理
            deleted_count = self.organizer.cleanup_old_transfer_logs(result['days'])
            
            messagebox.showinfo("清理完成", f"已删除 {deleted_count} 个旧日志文件")
            self.log_message(f"清理旧日志完成: 删除 {deleted_count} 个文件")
            
            # 刷新日志列表
            self._load_transfer_logs(tree_widget)
            
        except Exception as e:
            self.log_message(f"清理旧日志失败: {e}")
            messagebox.showerror("错误", f"清理旧日志失败: {e}")
    
    def show_restore_dialog(self):
        """显示文件恢复对话框"""
        try:
            # 检查转移日志功能是否可用
            if not self.organizer.enable_transfer_log:
                messagebox.showwarning("功能不可用", "转移日志功能未启用，无法进行文件恢复")
                return
            
            # 获取日志文件列表
            log_files = self.organizer.get_transfer_logs()
            
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
                    summary = self.organizer.get_transfer_log_summary(log_file)
                    session_info = summary['session_info']
                    
                    # 格式化显示文本
                    display_text = f"{session_info.get('session_name', '未知')} - {session_info.get('start_time', '未知')[:16]} (成功: {session_info.get('successful_operations', 0)})"
                    log_listbox.insert(tk.END, display_text)
                    log_data.append(log_file)
                    
                except Exception as e:
                    self.log_message(f"解析日志文件失败 {log_file}: {e}")
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
            self.log_message(f"显示恢复对话框失败: {e}")
            messagebox.showerror("错误", f"显示恢复对话框失败: {e}")
    
    def _execute_restore(self, log_file_path):
        """执行文件恢复操作"""
        try:
            # 确认恢复
            if not messagebox.askyesno(
                "确认恢复",
                "确定要恢复此日志中的所有文件吗？\n\n注意：这将把文件从目标位置移动回原始位置。"
            ):
                return
            
            self.log_message("开始文件恢复操作...")
            
            # 在新线程中执行恢复
            def restore_worker():
                try:
                    # 先试运行
                    dry_run_results = self.organizer.restore_files_from_log(
                        log_file_path=log_file_path,
                        dry_run=True
                    )
                    
                    # 在主线程中显示试运行结果
                    def show_dry_run_results():
                        dry_run_message = f"""试运行结果:

可恢复文件: {dry_run_results['successful_restores']}
无法恢复: {dry_run_results['failed_restores']}
跳过文件: {dry_run_results['skipped_operations']}

确定要执行实际恢复操作吗？"""
                        
                        if messagebox.askyesno("确认执行恢复", dry_run_message):
                            # 执行实际恢复
                            threading.Thread(target=actual_restore_worker, daemon=True).start()
                    
                    self.root.after(0, show_dry_run_results)
                    
                except Exception as e:
                    self.root.after(0, lambda: self.log_message(f"恢复试运行失败: {e}"))
                    self.root.after(0, lambda: messagebox.showerror("错误", f"恢复试运行失败: {e}"))
            
            def actual_restore_worker():
                try:
                    restore_results = self.organizer.restore_files_from_log(
                        log_file_path=log_file_path,
                        dry_run=False
                    )
                    
                    # 显示恢复结果
                    def show_results():
                        result_message = f"""文件恢复完成!

成功恢复: {restore_results['successful_restores']}
恢复失败: {restore_results['failed_restores']}
跳过文件: {restore_results['skipped_operations']}"""
                        
                        messagebox.showinfo("恢复完成", result_message)
                        self.log_message(f"文件恢复完成: 成功 {restore_results['successful_restores']}, 失败 {restore_results['failed_restores']}")
                    
                    self.root.after(0, show_results)
                    
                except Exception as e:
                    self.root.after(0, lambda: self.log_message(f"文件恢复失败: {e}"))
                    self.root.after(0, lambda: messagebox.showerror("错误", f"文件恢复失败: {e}"))
            
            # 启动试运行
            threading.Thread(target=restore_worker, daemon=True).start()
            
        except Exception as e:
            self.log_message(f"执行恢复失败: {e}")
            messagebox.showerror("错误", f"执行恢复失败: {e}")
    
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
                        results = self.organizer.remove_duplicate_files(
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
                            # 分组展示
                            if results.get('duplicate_groups'):
                                for idx, group in enumerate(results['duplicate_groups'], 1):
                                    name = group['name']
                                    size = group['size']
                                    md5 = group['md5']
                                    files = group['files']
                                    result_text.insert(tk.END, f"重复文件组{idx}: {name} ({size} bytes) [MD5: {md5}] 共{len(files)}个副本\n")
                                    for file_info in files:
                                        keep_flag = '【保留】' if file_info.get('keep') else '【待删】'
                                        result_text.insert(tk.END, f"  - {file_info['relative_path']} {keep_flag}\n")
                                    result_text.insert(tk.END, "\n")
                            else:
                                result_text.insert(tk.END, "未发现可删除的重复文件。\n")
                            result_text.config(state='normal')
                            # 添加确认删除按钮
                            if results['files_to_delete']:
                                def confirm_delete():
                                    if messagebox.askyesno(
                                        "确认删除", 
                                        f"确定要删除这 {len(results['files_to_delete'])} 个重复文件吗？\n\n此操作不可撤销！"
                                    ):
                                        # 执行实际删除
                                        result_text.delete(1.0, tk.END)
                                        result_text.insert(tk.END, "正在删除重复文件...\n")
                                        
                                        def delete_worker():
                                            try:
                                                delete_results = self.organizer.remove_duplicate_files(
                                                    target_folder_path=folder_path,
                                                    dry_run=False
                                                )
                                                
                                                def show_delete_results():
                                                    result_text.delete(1.0, tk.END)
                                                    result_text.insert(tk.END, f"删除完成！\n\n")
                                                    result_text.insert(tk.END, f"成功删除: {len(delete_results['files_deleted'])}\n")
                                                    result_text.insert(tk.END, f"删除失败: {len(delete_results['deletion_errors'])}\n\n")
                                                    
                                                    if delete_results['files_deleted']:
                                                        result_text.insert(tk.END, "已删除的文件:\n")
                                                        for file_info in delete_results['files_deleted']:
                                                            result_text.insert(tk.END, f"• {file_info['relative_path']}\n")
                                                    
                                                    if delete_results['deletion_errors']:
                                                        result_text.insert(tk.END, "\n删除失败的文件:\n")
                                                        for error_info in delete_results['deletion_errors']:
                                                            result_text.insert(tk.END, f"• {error_info['relative_path']}: {error_info['error']}\n")
                                                
                                                self.root.after(0, show_delete_results)
                                                
                                            except Exception as e:
                                                def show_error():
                                                    result_text.delete(1.0, tk.END)
                                                    result_text.insert(tk.END, f"删除失败: {e}")
                                                    messagebox.showerror("错误", f"删除失败: {e}")
                                                
                                                self.root.after(0, show_error)
                                        
                                        threading.Thread(target=delete_worker, daemon=True).start()
                                
                                # 添加确认删除按钮到按钮框架
                                confirm_button = ttk.Button(
                                    button_frame,
                                    text="确认删除",
                                    command=confirm_delete
                                )
                                confirm_button.pack(side=tk.LEFT, padx=5)
                            else:
                                result_text.insert(tk.END, f"成功删除: {len(results['files_deleted'])}\n")
                                result_text.insert(tk.END, f"删除失败: {len(results['deletion_errors'])}\n\n")
                                
                                if results['files_deleted']:
                                    result_text.insert(tk.END, "已删除的文件:\n")
                                    for file_info in results['files_deleted']:
                                        result_text.insert(tk.END, f"• {file_info['relative_path']}\n")
                                
                                if results['deletion_errors']:
                                    result_text.insert(tk.END, "\n删除失败的文件:\n")
                                    for error_info in results['deletion_errors']:
                                        result_text.insert(tk.END, f"• {error_info['relative_path']}: {error_info['error']}\n")
                            
                            # 记录日志
                            if dry_run:
                                self.log_message(f"重复文件扫描完成 [试运行]: 发现 {results['total_duplicates_found']} 个重复文件")
                            else:
                                self.log_message(f"重复文件删除完成: 删除 {len(results['files_deleted'])} 个文件")
                        
                        self.root.after(0, update_results)
                        
                    except Exception as e:
                        def show_error():
                            result_text.delete(1.0, tk.END)
                            result_text.insert(tk.END, f"扫描失败: {e}")
                            self.log_message(f"重复文件扫描失败: {e}")
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
            self.log_message(f"显示重复文件删除对话框失败: {e}")
            messagebox.showerror("错误", f"显示重复文件删除对话框失败: {e}")
            
    def run(self):
        """运行应用"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.log_message("程序被用户中断")
        except Exception as e:
            self.log_message(f"程序运行错误: {e}")
            messagebox.showerror("错误", f"程序运行错误: {e}")


def main():
    """主函数"""
    try:
        # 创建并运行 GUI 应用
        app = FileOrganizerGUI()
        app.run()
    except Exception as e:
        print(f"启动应用失败: {e}")
        messagebox.showerror("启动错误", f"启动应用失败: {e}")


if __name__ == "__main__":
    main()