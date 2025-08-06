import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
# 兼容新版本ttkbootstrap
try:
    from ttkbootstrap import Style, Window
except ImportError:
    pass
from ttkbootstrap.scrolled import ScrolledText
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DuplicateFileRemoverGUI:
    """删除重复文件GUI界面"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.window = None
        self.folder_listbox = None
        self.result_text = None
        self.dry_run_var = None
        self.keep_strategy_var = None
        
    def show_dialog(self):
        """显示删除重复文件对话框"""
        try:
            # 创建新窗口
            self.window = tb.Toplevel(self.parent)
            self.window.title("删除重复文件")
            self.window.resizable(True, True)
            
            # 设置窗口大小和位置
            self._setup_window_size()
            
            # 创建界面
            self._create_widgets()
            
            # 设置窗口模态
            self.window.transient(self.parent)
            self.window.grab_set()
            self.window.focus_set()
            
            # 等待窗口关闭
            self.window.wait_window()
            
        except Exception as e:
            logger.error(f"显示删除重复文件对话框失败: {e}")
            messagebox.showerror("错误", f"显示删除重复文件对话框失败: {e}")
    
    def _setup_window_size(self):
        """设置响应式窗口大小"""
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        if screen_width < 1366:  # 小屏幕
            window_width = min(700, screen_width - 100)
            window_height = min(600, screen_height - 100)
        elif screen_width < 1920:  # 中等屏幕
            window_width = min(800, screen_width - 100)
            window_height = min(700, screen_height - 100)
        else:  # 大屏幕
            window_width = min(900, screen_width - 100)
            window_height = min(800, screen_height - 100)
        
        self.window.geometry(f"{window_width}x{window_height}")
        self.window.minsize(500, 400)
        
        # 居中显示
        self.window.update_idletasks()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = tb.Frame(self.window, padding="5")
        main_frame.pack(fill=tb.BOTH, expand=True)
        
        # 标题
        title_label = tb.Label(
            main_frame, 
            text="删除重复文件", 
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # 说明文字
        desc_text = "选择要检查重复文件的目标文件夹\n重复判断标准：文件大小+MD5哈希值完全一致"
        desc_label = tb.Label(main_frame, text=desc_text, justify=tk.CENTER)
        desc_label.pack(pady=(0, 15))
        
        # 文件夹选择区域
        folder_frame = tb.LabelFrame(main_frame, text="目标文件夹", padding="5")
        folder_frame.pack(fill=tb.BOTH, expand=True, pady=(0, 10))
        
        # 文件夹列表
        list_frame = tb.Frame(folder_frame)
        list_frame.pack(fill=tb.BOTH, expand=True, pady=(3, 0))
        
        self.folder_listbox = tk.Listbox(
            list_frame,
            height=3,
            selectmode=tk.EXTENDED
        )
        self.folder_listbox.pack(side=tk.LEFT, fill=tb.BOTH, expand=True)
        
        # 滚动条
        scrollbar = tb.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.folder_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.folder_listbox.config(yscrollcommand=scrollbar.set)
        
        # 文件夹操作按钮
        button_frame = tb.Frame(folder_frame)
        button_frame.pack(fill=tk.X, pady=(3, 0))
        
        def select_folder():
            directory = filedialog.askdirectory(title="选择要检查的文件夹")
            if directory:
                # 检查是否已存在
                existing_folders = list(self.folder_listbox.get(0, tk.END))
                if directory not in existing_folders:
                    self.folder_listbox.insert(tk.END, directory)
        
        def remove_selected_folder():
            selected_indices = self.folder_listbox.curselection()
            if selected_indices:
                # 从后往前删除，避免索引变化
                for index in reversed(selected_indices):
                    self.folder_listbox.delete(index)
        
        def clear_all_folders():
            self.folder_listbox.delete(0, tk.END)
        
        tb.Button(
            button_frame, 
            text="添加文件夹", 
            command=select_folder,
            style='info.TButton'
        ).pack(side=tk.LEFT, padx=(0, 3))
        
        tb.Button(
            button_frame, 
            text="移除选中", 
            command=remove_selected_folder,
            style='warning.TButton'
        ).pack(side=tk.LEFT, padx=3)
        
        tb.Button(
            button_frame, 
            text="清空列表", 
            command=clear_all_folders,
            style='danger.TButton'
        ).pack(side=tk.LEFT, padx=3)
        
        # 选项设置区域
        options_frame = tb.LabelFrame(main_frame, text="扫描选项", padding="3")
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 试运行选项
        self.dry_run_var = tk.BooleanVar(value=True)
        tb.Checkbutton(
            options_frame,
            text="试运行模式（不实际删除文件）",
            variable=self.dry_run_var
        ).pack(anchor=tk.W, pady=2)
        
        # 保留策略
        strategy_frame = tb.Frame(options_frame)
        strategy_frame.pack(fill=tk.X, pady=(5, 0))
        
        tb.Label(strategy_frame, text="保留策略:").pack(side=tk.LEFT)
        
        self.keep_strategy_var = tk.StringVar(value="newest")
        tb.Radiobutton(
            strategy_frame,
            text="保留最新的文件",
            variable=self.keep_strategy_var,
            value="newest"
        ).pack(side=tk.LEFT, padx=(10, 20))
        
        tb.Radiobutton(
            strategy_frame,
            text="保留最旧的文件",
            variable=self.keep_strategy_var,
            value="oldest"
        ).pack(side=tk.LEFT)
        
        # 结果显示区域
        result_frame = tb.LabelFrame(main_frame, text="扫描结果", padding="3")
        result_frame.pack(fill=tb.BOTH, expand=True, pady=(0, 5))
        
        self.result_text = ScrolledText(
            result_frame,
            height=8,
            wrap=tk.WORD
        )
        self.result_text.pack(fill=tb.BOTH, expand=True)
        
        # 操作按钮框架
        action_frame = tb.Frame(main_frame)
        action_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        
        def start_scan():
            selected_folders = list(self.folder_listbox.get(0, tk.END))
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
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "正在扫描重复文件...\n")
            
            # 在新线程中执行扫描
            def scan_worker():
                try:
                    dry_run = self.dry_run_var.get()
                    keep_oldest = self.keep_strategy_var.get() == "oldest"
                    logger.info(f"开始扫描: 文件夹={selected_folders}, 试运行={dry_run}, 保留最旧={keep_oldest}")
                    results = self._remove_duplicate_files(
                        target_folder_paths=selected_folders,
                        dry_run=dry_run,
                        keep_oldest=keep_oldest
                    )
                    logger.info(f"扫描完成: 结果={results}")
                    
                    # 在主线程中更新结果
                    self.window.after(0, lambda: self._update_results(results))
                    
                except Exception as e:
                    logger.error(f"扫描重复文件失败: {e}")
                    self.window.after(0, lambda: self._show_error(str(e)))
            
            threading.Thread(target=scan_worker, daemon=True).start()
        
        def close_dialog():
            self.window.destroy()
        
        tb.Button(
            action_frame, 
            text="开始扫描", 
            command=start_scan,
            style='success.TButton'
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        tb.Button(
            action_frame, 
            text="关闭", 
            command=close_dialog,
            style='secondary.TButton'
        ).pack(side=tk.RIGHT)
    
    def _update_results(self, results):
        """更新扫描结果"""
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"扫描完成！\n\n")
        self.result_text.insert(tk.END, f"扫描文件夹: {len(results.get('target_folders', []))} 个\n")
        self.result_text.insert(tk.END, f"总文件数: {results['total_files_scanned']}\n")
        self.result_text.insert(tk.END, f"重复文件组: {results['duplicate_groups_found']}\n")
        self.result_text.insert(tk.END, f"重复文件数: {results['total_duplicates_found']}\n\n")
        
        if results.get('duplicate_groups'):
            for idx, group in enumerate(results['duplicate_groups'], 1):
                size = group['size']
                md5 = group['md5']
                files = group['files']
                self.result_text.insert(tk.END, f"重复文件组{idx}: (大小: {size} bytes, MD5: {md5}) 共{len(files)}个副本\n")
                for file_info in files:
                    keep_flag = '【保留】' if file_info.get('keep') else '【待删】'
                    ctime_str = datetime.fromtimestamp(file_info['ctime']).strftime('%Y-%m-%d %H:%M:%S') if 'ctime' in file_info else ''
                    source_folder = file_info.get('source_folder', '')
                    relative_path = file_info.get('relative_path', str(file_info.get('path', '')))
                    self.result_text.insert(tk.END, f"  - {relative_path} {keep_flag} 来源: {source_folder} 创建时间: {ctime_str}\n")
                self.result_text.insert(tk.END, "\n")
            
            # 如果是试运行模式且发现重复文件，添加删除按钮
            if results.get('dry_run') and results['total_duplicates_found'] > 0:
                self._add_delete_button(results)
        else:
            self.result_text.insert(tk.END, "未发现可删除的重复文件。\n")
    
    def _add_delete_button(self, scan_results):
        """添加删除按钮"""
        # 查找现有的删除按钮并移除
        for widget in self.window.winfo_children():
            if hasattr(widget, '_delete_button_flag'):
                widget.destroy()
        
        # 查找操作按钮框架
        action_frame = None
        for widget in self.window.winfo_children():
            if isinstance(widget, tb.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, tb.Frame):
                        # 检查这个框架是否包含扫描按钮
                        for grandchild in child.winfo_children():
                            if isinstance(grandchild, tb.Button) and grandchild.cget('text') == "开始扫描":
                                action_frame = child
                                break
                        if action_frame:
                            break
                if action_frame:
                    break
        
        if not action_frame:
            # 如果找不到操作框架，就在窗口底部创建
            action_frame = self.window
        
        # 创建删除按钮
        def delete_duplicates():
            if messagebox.askyesno("确认删除", f"确定要删除 {scan_results['total_duplicates_found']} 个重复文件吗？\n\n此操作不可撤销！"):
                self.result_text.delete(1.0, tk.END)
                self.result_text.insert(tk.END, "正在删除重复文件...\n")
                
                def delete_worker():
                    try:
                        keep_oldest = self.keep_strategy_var.get() == "oldest"
                        # 获取当前选择的文件夹列表
                        selected_folders = list(self.folder_listbox.get(0, tk.END))
                        delete_results = self._remove_duplicate_files(
                            target_folder_paths=selected_folders,
                            dry_run=False,
                            keep_oldest=keep_oldest
                        )
                        
                        self.window.after(0, lambda: self._show_delete_results(delete_results))
                        
                    except Exception as e:
                        logger.error(f"删除重复文件失败: {e}")
                        self.window.after(0, lambda: self._show_error(str(e)))
                
                threading.Thread(target=delete_worker, daemon=True).start()
        
        delete_button = tb.Button(
            action_frame,
            text=f"删除 {scan_results['total_duplicates_found']} 个重复文件",
            command=delete_duplicates,
            style='danger.TButton'
        )
        delete_button._delete_button_flag = True
        delete_button.pack(side=tk.LEFT, padx=(5, 0))
    
    def _show_delete_results(self, results):
        """显示删除结果"""
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"删除完成！\n\n")
        self.result_text.insert(tk.END, f"成功删除: {len(results.get('files_deleted', []))} 个文件\n")
        self.result_text.insert(tk.END, f"删除失败: {len(results.get('deletion_errors', []))} 个文件\n")
        
        # 计算释放的空间
        space_freed = sum(file_info.get('size', 0) for file_info in results.get('files_deleted', []))
        self.result_text.insert(tk.END, f"释放空间: {space_freed:,} bytes\n\n")
        
        if results.get('files_deleted'):
            self.result_text.insert(tk.END, "已删除的文件:\n")
            for file_info in results['files_deleted']:
                relative_path = file_info.get('relative_path', file_info.get('path', ''))
                self.result_text.insert(tk.END, f"  - {relative_path}\n")
        
        if results.get('deletion_errors'):
            self.result_text.insert(tk.END, "\n删除失败的文件:\n")
            for file_info in results['deletion_errors']:
                relative_path = file_info.get('relative_path', file_info.get('path', ''))
                error_msg = file_info.get('error', '未知错误')
                self.result_text.insert(tk.END, f"  - {relative_path}: {error_msg}\n")
    
    def _show_error(self, error_message):
        """显示错误信息"""
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"扫描失败:\n{error_message}")
    
    def _remove_duplicate_files(self, target_folder_paths, dry_run=True, keep_oldest=False):
        """删除重复文件的核心逻辑"""
        try:
            from tidyfile.core.duplicate_cleaner import remove_duplicate_files
            logger.info(f"开始调用删除重复文件函数: 文件夹={target_folder_paths}, 试运行={dry_run}, 保留最旧={keep_oldest}")
            result = remove_duplicate_files(
                target_folder_paths=target_folder_paths,
                dry_run=dry_run,
                keep_oldest=keep_oldest
            )
            logger.info(f"删除重复文件函数调用完成: 扫描文件={result.get('total_files_scanned', 0)}, 重复组={result.get('duplicate_groups_found', 0)}")
            return result
        except Exception as e:
            logger.error(f"调用删除重复文件函数失败: {e}")
            raise


def show_duplicate_remover_dialog(parent=None):
    """显示删除重复文件对话框的便捷函数"""
    dialog = DuplicateFileRemoverGUI(parent)
    dialog.show_dialog()


 