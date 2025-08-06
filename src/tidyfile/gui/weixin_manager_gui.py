import ttkbootstrap as tb
# 兼容新版本ttkbootstrap
try:
    from ttkbootstrap import Style, Window
except ImportError:
    pass
from ttkbootstrap.constants import *
from tkinter import messagebox
import threading
from datetime import datetime
import os
import sys
from tidyfile.core.weixin_manager_logic import WeixinManagerLogic
import subprocess

# 导入国际化支持
try:
    from tidyfile.i18n.i18n_manager import t
except ImportError:
    # 如果国际化模块不可用，使用默认函数
    def t(key, section="app", **kwargs):
        return key

class WeixinManagerTab:
    """微信信息管理Tab"""
    def __init__(self, notebook, log_callback=None):
        self.notebook = notebook
        self.logic = WeixinManagerLogic()
        self.log_callback = log_callback  # 主GUI日志输出方法
        self.frame = tb.Frame(notebook, padding="10")
        notebook.add(self.frame, text=t("weixin_manager", "app"))
        self.create_widgets()

    def create_widgets(self):
        self.tab_control = tb.Notebook(self.frame)
        self.tab_control.pack(fill=BOTH, expand=True)
        self.create_favorites_tab()

    def create_favorites_tab(self):
        fav_frame = tb.Frame(self.tab_control, padding="10")
        self.tab_control.add(fav_frame, text=t("favorites_organize", "weixin_manager"))
        fav_frame.columnconfigure(1, weight=1)
        row = 0
        tb.Label(fav_frame, text=t("account", "weixin_manager"), font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5, padx=(0, 10))
        self.talker_var = tb.StringVar()
        tb.Entry(fav_frame, textvariable=self.talker_var, width=30).grid(row=row, column=1, sticky=(W, E), pady=5)
        row += 1
        tb.Label(fav_frame, text=t("start_date", "weixin_manager"), font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5, padx=(0, 10))
        self.start_date_var = tb.StringVar()
        tb.Entry(fav_frame, textvariable=self.start_date_var, width=30).grid(row=row, column=1, sticky=(W, E), pady=5)
        self.start_date_var.set(datetime.now().strftime('%Y-%m-%d'))
        row += 1
        tb.Label(fav_frame, text=t("end_date", "weixin_manager"), font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5, padx=(0, 10))
        self.end_date_var = tb.StringVar()
        tb.Entry(fav_frame, textvariable=self.end_date_var, width=30).grid(row=row, column=1, sticky=(W, E), pady=5)
        self.end_date_var.set(datetime.now().strftime('%Y-%m-%d'))
        row += 1
        # 超时设置
        tb.Label(fav_frame, text="超时时间(秒)", font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5, padx=(0, 10))
        self.timeout_var = tb.IntVar(value=60)
        timeout_frame = tb.Frame(fav_frame)
        timeout_frame.grid(row=row, column=1, sticky=(W, E), pady=5)
        tb.Label(timeout_frame, text="30秒").pack(side=LEFT)
        self.timeout_scale = tb.Scale(timeout_frame, from_=30, to=300, variable=self.timeout_var, orient=HORIZONTAL, length=180)
        self.timeout_scale.pack(side=LEFT, padx=5)
        self.timeout_value_label = tb.Label(timeout_frame, text="60秒")
        self.timeout_value_label.pack(side=LEFT, padx=(10, 0))
        self.timeout_var.trace_add('write', self.update_timeout_label)
        row += 1
        # 摘要长度调节
        tb.Label(fav_frame, text=t("summary_length", "weixin_manager"), font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5, padx=(0, 10))
        self.summary_length = tb.IntVar(value=200)
        summary_frame = tb.Frame(fav_frame)
        summary_frame.grid(row=row, column=1, sticky=(W, E), pady=5)
        tb.Label(summary_frame, text="100" + t("characters", "weixin_manager")).pack(side=LEFT)
        self.summary_scale = tb.Scale(summary_frame, from_=100, to=500, variable=self.summary_length, orient=HORIZONTAL, length=180)
        self.summary_scale.pack(side=LEFT, padx=5)
        self.summary_value_label = tb.Label(summary_frame, text="200" + t("characters", "weixin_manager"))
        self.summary_value_label.pack(side=LEFT, padx=(10, 0))
        self.summary_length.trace_add('write', self.update_summary_label)
        row += 1
        button_frame = tb.Frame(fav_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=15)
        self.backup_btn = tb.Button(button_frame, text=t("backup_articles", "weixin_manager"), command=self.start_backup, bootstyle=SUCCESS, width=18)
        self.backup_btn.pack(side=LEFT, padx=(0, 10))
        self.analyze_btn = tb.Button(button_frame, text=t("analyze_backup", "weixin_manager"), command=self.analyze_backup, bootstyle=INFO, width=18)
        self.analyze_btn.pack(side=LEFT)


    


    def log_message(self, message):
        if self.log_callback:
            self.log_callback(message)

    def update_summary_label(self, *args):
        value = self.summary_length.get()
        self.summary_value_label.config(text=f"{value}{t('characters', 'weixin_manager')}")

    def update_timeout_label(self, *args):
        value = self.timeout_var.get()
        self.timeout_value_label.config(text=f"{value}秒")

    def validate_input(self):
        talker = self.talker_var.get().strip()
        start_date = self.start_date_var.get().strip()
        end_date = self.end_date_var.get().strip()
        if not talker:
            messagebox.showwarning(t("input_error", "weixin_manager"), t("please_enter_account", "weixin_manager"))
            return None
        if not start_date or not end_date:
            messagebox.showwarning(t("input_error", "weixin_manager"), t("please_enter_dates", "weixin_manager"))
            return None
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            messagebox.showwarning(t("input_error", "weixin_manager"), t("date_format_error", "weixin_manager"))
            return None
        if start_date > end_date:
            messagebox.showwarning(t("input_error", "weixin_manager"), t("start_date_after_end", "weixin_manager"))
            return None
        return talker, start_date, end_date

    def start_backup(self):
        result = self.validate_input()
        if result is None:
            self.log_message("收藏文章备份失败：输入参数验证失败")
            return
        talker, start_date, end_date = result
        timeout = self.timeout_var.get()
        self.backup_btn.config(state='disabled')
        self.log_message(f"开始备份微信收藏文章")
        self.log_message(f"收藏账号: {talker}")
        self.log_message(f"时间范围: {start_date} ~ {end_date}")
        self.log_message(f"超时设置: {timeout}秒")
        self.log_message("正在连接微信接口...")
        thread = threading.Thread(target=self._backup_worker, args=(talker, start_date, end_date, timeout), daemon=True)
        thread.start()

    def _backup_worker(self, talker, start_date, end_date, timeout):
        try:
            # 重定向print输出到GUI日志
            import sys
            from io import StringIO
            
            # 创建字符串缓冲区来捕获print输出
            output_buffer = StringIO()
            original_stdout = sys.stdout
            sys.stdout = output_buffer
            
            try:
                self.log_message("正在拉取微信收藏文章数据...")
                count, save_path = self.logic.backup_wechat_favorites(talker, start_date, end_date, timeout)
                
                # 获取捕获的输出并发送到GUI日志
                captured_output = output_buffer.getvalue()
                if captured_output:
                    # 按行分割并发送到GUI
                    lines = captured_output.strip().split('\n')
                    for line in lines:
                        if line.strip():
                            self.frame.after(0, lambda line=line: self.log_message(line.strip()))
                
                self.frame.after(0, lambda: self._backup_completed(count, save_path))
                
            finally:
                # 恢复原始stdout
                sys.stdout = original_stdout
                output_buffer.close()
                
        except Exception as e:
            error_msg = str(e)
            self.log_message(f"收藏文章备份异常: {error_msg}")
            self.frame.after(0, lambda: self._backup_failed(error_msg))

    def _backup_completed(self, count, save_path):
        self.log_message(f"收藏文章备份完成！共保存 {count} 篇文章")
        self.log_message(f"保存路径: {save_path}")
        if count > 0:
            messagebox.showinfo("备份成功", f"成功备份 {count} 篇文章到:\n{save_path}")
        else:
            messagebox.showinfo("备份完成", "未找到符合条件的文章")
        self.backup_btn.config(state='normal')

    def _backup_failed(self, error_msg):
        self.log_message(f"收藏文章备份失败: {error_msg}")
        messagebox.showerror("备份失败", f"备份过程中发生错误:\n{error_msg}")
        self.backup_btn.config(state='normal')

    def analyze_backup(self):
        summary_len = self.summary_length.get()
        self.log_message(f"开始批量解读微信收藏文章")
        self.log_message(f"摘要长度设置: {summary_len} 字符")
        self.log_message("正在检查备份文件...")
        thread = threading.Thread(target=self._analyze_worker, args=(summary_len,), daemon=True)
        thread.start()

    def _analyze_worker(self, summary_len):
        try:
            self.log_message("正在启动微信文章AI解读脚本...")
            
            # 使用当前Python解释器的完整路径
            python_executable = sys.executable
            # 获取脚本的正确路径
            script_dir = os.path.dirname(os.path.abspath(__file__))
            script_path = os.path.join(script_dir, "..", "core", "wechat_article_ai_summary.py")
            
            # 如果找不到脚本，尝试备用路径
            if not os.path.exists(script_path):
                script_path = os.path.join(os.path.dirname(script_dir), "core", "wechat_article_ai_summary.py")
            
            if not os.path.exists(script_path):
                raise FileNotFoundError(f"找不到微信文章AI解读脚本: {script_path}")
            
            # 直接运行脚本文件，但设置正确的环境
            cmd = [
                python_executable, script_path,
                "--summary_length", str(summary_len)
            ]
            
            self.log_message(f"执行命令: {' '.join(cmd)}")
            
            # 设置工作目录为项目根目录，确保模块导入正常
            # 从当前文件位置计算项目根目录：当前文件在 src/tidyfile/gui/，需要向上3级到项目根目录
            current_file_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.normpath(os.path.join(current_file_dir, '..', '..', '..'))
            
            # 设置环境变量，添加src目录到Python路径
            env = os.environ.copy()
            src_path = os.path.join(project_root, 'src')
            
            # 确保PYTHONPATH包含src目录
            if 'PYTHONPATH' in env:
                if src_path not in env['PYTHONPATH']:
                    env['PYTHONPATH'] = src_path + os.pathsep + env['PYTHONPATH']
            else:
                env['PYTHONPATH'] = src_path
            
            # 添加当前工作目录到Python路径
            if 'PYTHONPATH' in env:
                env['PYTHONPATH'] = project_root + os.pathsep + env['PYTHONPATH']
            else:
                env['PYTHONPATH'] = project_root
            
            # 使用Popen实时捕获输出
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 将stderr重定向到stdout
                text=True,
                bufsize=1,  # 行缓冲
                universal_newlines=True,
                cwd=project_root,  # 设置工作目录为项目根目录
                env=env  # 设置环境变量
            )
            
            # 实时读取输出
            while True:
                output_line = process.stdout.readline()
                if output_line == '' and process.poll() is not None:
                    break
                if output_line:
                    # 去除行尾的换行符并记录日志
                    line = output_line.rstrip()
                    if line.strip():
                        self.frame.after(0, lambda line=line: self.log_message(line.strip()))
            
            # 等待进程完成并获取返回码
            return_code = process.wait()
            
            # 根据返回码判断是否成功
            if return_code != 0:
                error_message = self._analyze_error_type("进程返回非零退出码")
                self.log_message(f"备份文章解读失败: {error_message}")
                messagebox.showerror("解读失败", error_message)
            else:
                self.log_message("微信文章批量解读已完成，摘要已写入ai_organize_result.json")
                messagebox.showinfo("解读完成", "微信文章批量解读已完成，摘要已写入ai_organize_result.json")
                
        except Exception as e:
            error_msg = str(e)
            self.log_message(f"备份文章解读异常: {error_msg}")
            self.frame.after(0, lambda: self.log_message(f"解读失败: {error_msg}"))
            messagebox.showerror("解读失败", f"解读过程中发生错误:\n{error_msg}")
    
    def _analyze_error_type(self, output):
        """根据输出内容分析错误类型并返回相应的错误提示"""
        output_lower = output.lower()
        
        # 依赖包缺失错误
        if any(keyword in output_lower for keyword in ["modulenotfounderror", "import error", "no module named"]) or "依赖缺失" in output:
            return "依赖包缺失，请先安装以下依赖包：\n\npip install beautifulsoup4 html2text fake-useragent requests markdown\n\n如果已安装但仍报错，请检查Python环境或重新安装依赖包。"
        
        # AI服务连接失败错误
        elif any(keyword in output_lower for keyword in ["failed to connect", "connection refused"]) or \
             ("ollama" in output_lower and "connect" in output_lower) or \
             "ai服务连接失败" in output:
            return "AI服务连接失败\n\n请确保：\n1. Ollama服务已启动\n2. 服务地址正确（默认：http://localhost:11434）\n3. 网络连接正常\n\n启动Ollama命令：ollama serve"
        
        # 文件不存在错误
        elif any(keyword in output_lower for keyword in ["file not found", "file does not exist"]) or \
             ("未找到" in output and "weixin_article.json" in output):
            return "文件不存在\n\n请先执行'收藏文章备份'功能，生成weixin_article.json文件。"
        
        # 网络连接错误
        elif any(keyword in output_lower for keyword in ["timeout", "connection error"]) or "网络错误" in output:
            return "网络连接错误\n\n请检查：\n1. 网络连接是否正常\n2. 防火墙设置\n3. 代理设置"
        
        # 权限错误
        elif any(keyword in output_lower for keyword in ["permission denied", "access denied"]):
            return "权限不足\n\n请以管理员身份运行程序，或检查文件/目录的访问权限。"
        
        # 内存不足错误
        elif any(keyword in output_lower for keyword in ["out of memory"]) or \
             ("memory" in output_lower and "error" in output_lower):
            return "内存不足\n\n请关闭其他程序释放内存，或减少处理的文章数量。"
        
        # 进程返回非零退出码
        elif "进程返回非零退出码" in output:
            return "微信文章批量解读失败\n\n请检查操作日志获取详细错误信息，或联系技术支持。"
        
        # 其他未知错误
        else:
            return "微信文章批量解读失败\n\n请检查操作日志获取详细错误信息，或联系技术支持。"
    
 