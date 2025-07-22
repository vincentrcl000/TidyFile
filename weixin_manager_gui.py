import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox
import threading
from datetime import datetime
import os
import sys
from weixin_manager_logic import WeixinManagerLogic
import subprocess

class WeixinManagerTab:
    """微信信息管理Tab"""
    def __init__(self, notebook, log_callback=None):
        self.notebook = notebook
        self.logic = WeixinManagerLogic()
        self.log_callback = log_callback  # 主GUI日志输出方法
        self.frame = tb.Frame(notebook, padding="10")
        notebook.add(self.frame, text="微信信息管理")
        self.create_widgets()

    def create_widgets(self):
        self.tab_control = tb.Notebook(self.frame)
        self.tab_control.pack(fill=BOTH, expand=True)
        self.create_favorites_tab()
        self.create_empty_tab("聊天记录总结")
        self.create_empty_tab("群聊话题汇总")
        self.create_empty_tab("公众号文章分析")

    def create_favorites_tab(self):
        fav_frame = tb.Frame(self.tab_control, padding="10")
        self.tab_control.add(fav_frame, text="收藏文章整理")
        fav_frame.columnconfigure(1, weight=1)
        row = 0
        tb.Label(fav_frame, text="收藏账号:", font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5, padx=(0, 10))
        self.talker_var = tb.StringVar()
        tb.Entry(fav_frame, textvariable=self.talker_var, width=30, font=('Arial', 10)).grid(row=row, column=1, sticky=(W, E), pady=5)
        row += 1
        tb.Label(fav_frame, text="起始日期:", font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5, padx=(0, 10))
        self.start_date_var = tb.StringVar()
        tb.Entry(fav_frame, textvariable=self.start_date_var, width=30, font=('Arial', 10)).grid(row=row, column=1, sticky=(W, E), pady=5)
        self.start_date_var.set(datetime.now().strftime('%Y-%m-%d'))
        row += 1
        tb.Label(fav_frame, text="结束日期:", font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5, padx=(0, 10))
        self.end_date_var = tb.StringVar()
        tb.Entry(fav_frame, textvariable=self.end_date_var, width=30, font=('Arial', 10)).grid(row=row, column=1, sticky=(W, E), pady=5)
        self.end_date_var.set(datetime.now().strftime('%Y-%m-%d'))
        row += 1
        # 摘要长度调节
        tb.Label(fav_frame, text="摘要长度:", font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5, padx=(0, 10))
        self.summary_length = tb.IntVar(value=200)
        summary_frame = tb.Frame(fav_frame)
        summary_frame.grid(row=row, column=1, sticky=(W, E), pady=5)
        tb.Label(summary_frame, text="100字").pack(side=LEFT)
        self.summary_scale = tb.Scale(summary_frame, from_=100, to=500, variable=self.summary_length, orient=HORIZONTAL, length=180)
        self.summary_scale.pack(side=LEFT, padx=5)
        self.summary_value_label = tb.Label(summary_frame, text="200字符")
        self.summary_value_label.pack(side=LEFT, padx=(10, 0))
        self.summary_length.trace_add('write', self.update_summary_label)
        row += 1
        button_frame = tb.Frame(fav_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=15)
        self.backup_btn = tb.Button(button_frame, text="收藏文章备份", command=self.start_backup, bootstyle=SUCCESS, width=18)
        self.backup_btn.pack(side=LEFT, padx=(0, 10))
        self.analyze_btn = tb.Button(button_frame, text="备份文章解读", command=self.analyze_backup, bootstyle=INFO, width=18)
        self.analyze_btn.pack(side=LEFT)

    def create_empty_tab(self, name):
        frame = tb.Frame(self.tab_control, padding="20")
        self.tab_control.add(frame, text=name)
        tb.Label(frame, text=f"{name}功能暂未实现", font=('Arial', 12)).pack(pady=50)
        tb.Label(frame, text="敬请期待后续版本", font=('Arial', 10), foreground='gray').pack()

    def log_message(self, message):
        if self.log_callback:
            self.log_callback(message)

    def update_summary_label(self, *args):
        value = self.summary_length.get()
        self.summary_value_label.config(text=f"{value}字符")

    def validate_input(self):
        talker = self.talker_var.get().strip()
        start_date = self.start_date_var.get().strip()
        end_date = self.end_date_var.get().strip()
        if not talker:
            messagebox.showwarning("输入错误", "请输入收藏账号")
            return None
        if not start_date or not end_date:
            messagebox.showwarning("输入错误", "请输入起始和结束日期")
            return None
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            messagebox.showwarning("输入错误", "日期格式错误，请使用 YYYY-MM-DD 格式")
            return None
        if start_date > end_date:
            messagebox.showwarning("输入错误", "起始日期不能晚于结束日期")
            return None
        return talker, start_date, end_date

    def start_backup(self):
        result = self.validate_input()
        if result is None:
            return
        talker, start_date, end_date = result
        self.backup_btn.config(state='disabled')
        self.log_message(f"开始备份微信收藏文章")
        self.log_message(f"收藏账号: {talker}")
        self.log_message(f"时间范围: {start_date} ~ {end_date}")
        thread = threading.Thread(target=self._backup_worker, args=(talker, start_date, end_date), daemon=True)
        thread.start()

    def _backup_worker(self, talker, start_date, end_date):
        try:
            count, save_path = self.logic.backup_wechat_favorites(talker, start_date, end_date)
            self.frame.after(0, lambda: self._backup_completed(count, save_path))
        except Exception as e:
            self.frame.after(0, lambda: self._backup_failed(str(e)))

    def _backup_completed(self, count, save_path):
        self.log_message(f"备份完成！共保存 {count} 篇文章")
        self.log_message(f"保存路径: {save_path}")
        if count > 0:
            messagebox.showinfo("备份成功", f"成功备份 {count} 篇文章到:\n{save_path}")
        else:
            messagebox.showinfo("备份完成", "未找到符合条件的文章")
        self.backup_btn.config(state='normal')

    def _backup_failed(self, error_msg):
        self.log_message(f"备份失败: {error_msg}")
        messagebox.showerror("备份失败", f"备份过程中发生错误:\n{error_msg}")
        self.backup_btn.config(state='normal')

    def analyze_backup(self):
        summary_len = self.summary_length.get()
        self.log_message(f"开始批量解读微信收藏文章，摘要长度：{summary_len}")
        thread = threading.Thread(target=self._analyze_worker, args=(summary_len,), daemon=True)
        thread.start()

    def _analyze_worker(self, summary_len):
        try:
            # 使用当前Python解释器的完整路径
            python_executable = sys.executable
            # 调用独立脚本，传递摘要长度参数
            cmd = [
                python_executable, "wechat_article_ai_summary.py",
                "--summary_length", str(summary_len)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            output = result.stdout + "\n" + result.stderr
            self.frame.after(0, lambda: self.log_message(output.strip()))
            # 判断是否有异常
            if ("Traceback" in output or "ModuleNotFoundError" in output or "依赖缺失" in output or result.returncode != 0):
                messagebox.showerror("解读失败", "微信文章批量解读失败，请检查操作日志和依赖包！\n如有依赖缺失，请先安装依赖：\npip install beautifulsoup4 html2text fake-useragent requests")
            else:
                messagebox.showinfo("解读完成", "微信文章批量解读已完成，摘要已写入ai_organize_result.json")
        except Exception as e:
            self.frame.after(0, lambda: self.log_message(f"解读失败: {e}"))
            messagebox.showerror("解读失败", f"解读过程中发生错误:\n{e}") 