import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import time
from typing import Dict, List, Optional
import ttkbootstrap as tb
from ttkbootstrap.constants import *

class AIModelConfigGUI:
    """AI模型配置管理GUI（所有操作通过AIClientManager）"""
    
    def __init__(self, parent_window):
        self.parent_window = parent_window
        # 通过AIClientManager统一管理
        from tidyfile.ai.client_manager import get_ai_manager, ModelConfig
        self.get_ai_manager = get_ai_manager
        self.ModelConfig = ModelConfig
        self.manager = self.get_ai_manager()
        self.config_file = self.manager.config_file
    
    def show_config_dialog(self):
        """显示AI模型配置对话框"""
        # 创建配置窗口
        config_window = tb.Toplevel(self.parent_window)
        config_window.title("AI模型配置")
        config_window.geometry("900x600")
        config_window.resizable(True, True)
        config_window.transient(self.parent_window)
        config_window.grab_set()
        
        # 创建主框架
        main_frame = tb.Frame(config_window, padding="10")
        main_frame.pack(fill=BOTH, expand=True)
        
        # 标题
        title_label = tb.Label(main_frame, text="AI模型服务配置", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # 说明
        info_label = tb.Label(main_frame, text="直接管理ai_models_config.json配置文件（通过AIClientManager）", font=('Arial', 10), foreground='gray')
        info_label.pack(pady=(0, 10))
        
        # 模型列表框架
        list_frame = tb.Frame(main_frame)
        list_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
        
        # 模型列表标题
        list_title = tb.Label(list_frame, text="已配置的模型服务:", font=('Arial', 10, 'bold'))
        list_title.pack(anchor=W, pady=(0, 5))
        
        # 模型列表（使用Treeview）
        columns = ('优先级', '模型名称', '模型类型', '服务地址', '模型名', '状态')
        model_tree = tb.Treeview(list_frame, columns=columns, show='headings', height=8)
        
        # 设置列标题和宽度
        column_widths = [60, 150, 80, 200, 120, 80]
        for i, col in enumerate(columns):
            model_tree.heading(col, text=col)
            model_tree.column(col, width=column_widths[i], minwidth=50)
        
        # 添加滚动条
        scrollbar = tb.Scrollbar(list_frame, orient=VERTICAL, command=model_tree.yview)
        model_tree.configure(yscrollcommand=scrollbar.set)
        
        model_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # 按钮框架
        button_frame = tb.Frame(main_frame)
        button_frame.pack(fill=X, pady=5)
        
        def refresh_model_list():
            try:
                self.manager.load_config()
                # 清空现有列表
                for item in model_tree.get_children():
                    model_tree.delete(item)
                # 按优先级排序
                sorted_models = sorted(self.manager.models, key=lambda x: x.priority)
                for model in sorted_models:
                    enabled_status = "✅ 启用" if model.enabled else "❌ 禁用"
                    model_tree.insert('', 'end', values=(
                        model.priority,
                        model.name,
                        model.model_type,
                        model.base_url,
                        model.model_name,
                        enabled_status
                    ))
            except Exception as e:
                messagebox.showerror("错误", f"刷新模型列表失败: {e}")
        
        def add_model():
            show_model_dialog()
        
        def edit_model():
            selected = model_tree.selection()
            if not selected:
                messagebox.showwarning("提示", "请先选择一个模型进行编辑")
                return
            item = model_tree.item(selected[0])
            values = item['values']
            model_name = values[1]
            # 查找对应的模型
            target_model = None
            for model in self.manager.models:
                if model.name == model_name:
                    target_model = model
                    break
            if not target_model:
                messagebox.showerror("错误", f"未找到模型 '{model_name}'")
                return
            show_model_dialog(is_edit=True, model_data=target_model)
        
        def delete_model():
            selected = model_tree.selection()
            if not selected:
                messagebox.showwarning("提示", "请先选择一个模型进行删除")
                return
            item = model_tree.item(selected[0])
            values = item['values']
            model_name = values[1]
            if messagebox.askyesno("确认删除", f"确定要删除模型 '{model_name}' 吗？"):
                try:
                    for model in self.manager.models:
                        if model.name == model_name:
                            self.manager.delete_model(model.id)
                            break
                    refresh_model_list()
                except Exception as e:
                    messagebox.showerror("错误", f"删除模型失败: {e}")
        
        def toggle_model_status():
            selected = model_tree.selection()
            if not selected:
                messagebox.showwarning("提示", "请先选择一个模型")
                return
            item = model_tree.item(selected[0])
            values = item['values']
            model_name = values[1]
            try:
                for model in self.manager.models:
                    if model.name == model_name:
                        model.enabled = not model.enabled
                        self.manager.save_config()
                        break
                refresh_model_list()
            except Exception as e:
                messagebox.showerror("错误", f"切换模型状态失败: {e}")
        
        def show_model_dialog(is_edit=False, model_data=None):
            dialog = tb.Toplevel(config_window)
            dialog.title("编辑模型配置" if is_edit else "添加模型配置")
            dialog.geometry("500x450")
            dialog.resizable(False, False)
            dialog.transient(config_window)
            dialog.grab_set()
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
            y = (dialog.winfo_screenheight() // 2) - (450 // 2)
            dialog.geometry(f"500x450+{x}+{y}")
            form_frame = tb.Frame(dialog, padding="20")
            form_frame.pack(fill=BOTH, expand=True)
            row = 0
            tb.Label(form_frame, text="优先级:", font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5)
            priority_var = tb.StringVar(value=str(model_data.priority) if model_data else "1")
            priority_combo = tb.Combobox(form_frame, textvariable=priority_var, values=[str(i) for i in range(1, 11)], width=37, state="readonly")
            priority_combo.grid(row=row, column=1, sticky=(W, E), pady=5, padx=(10, 0))
            row += 1
            tb.Label(form_frame, text="模型名称:", font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5)
            name_var = tb.StringVar(value=model_data.name if model_data else '')
            tb.Entry(form_frame, textvariable=name_var, width=40).grid(row=row, column=1, sticky=(W, E), pady=5, padx=(10, 0))
            row += 1
            tb.Label(form_frame, text="服务地址:", font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5)
            base_url_var = tb.StringVar(value=model_data.base_url if model_data else '')
            tb.Entry(form_frame, textvariable=base_url_var, width=40).grid(row=row, column=1, sticky=(W, E), pady=5, padx=(10, 0))
            row += 1
            tb.Label(form_frame, text="模型类型:", font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5)
            model_type_var = tb.StringVar(value=model_data.model_type if model_data else 'ollama')
            model_type_combo = tb.Combobox(form_frame, textvariable=model_type_var, values=["qwen_long", "ollama", "lm_studio", "openai_compatible"], width=37, state="readonly")
            model_type_combo.grid(row=row, column=1, sticky=(W, E), pady=5, padx=(10, 0))
            row += 1
            tb.Label(form_frame, text="模型名:", font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5)
            model_name_var = tb.StringVar(value=model_data.model_name if model_data else '')
            tb.Entry(form_frame, textvariable=model_name_var, width=40).grid(row=row, column=1, sticky=(W, E), pady=5, padx=(10, 0))
            row += 1
            tb.Label(form_frame, text="API密钥:", font=('Arial', 10)).grid(row=row, column=0, sticky=W, pady=5)
            api_key_var = tb.StringVar(value=model_data.api_key if model_data else '')
            tb.Entry(form_frame, textvariable=api_key_var, width=40, show="*").grid(row=row, column=1, sticky=(W, E), pady=5, padx=(10, 0))
            row += 1
            enabled_var = tk.BooleanVar(value=model_data.enabled if model_data else True)
            tb.Checkbutton(form_frame, text="启用此模型", variable=enabled_var).grid(row=row, column=0, columnspan=2, sticky=W, pady=10)
            row += 1
            button_frame2 = tb.Frame(form_frame)
            button_frame2.grid(row=row, column=0, columnspan=2, pady=20)
            def save_model():
                try:
                    if not name_var.get().strip():
                        messagebox.showwarning("输入错误", "请输入模型名称")
                        return
                    if not base_url_var.get().strip():
                        messagebox.showwarning("输入错误", "请输入服务地址")
                        return
                    if not model_name_var.get().strip():
                        messagebox.showwarning("输入错误", "请输入模型名")
                        return
                    new_priority = int(priority_var.get())
                    if new_priority < 1 or new_priority > 10:
                        messagebox.showwarning("输入错误", "优先级必须在1-10之间")
                        return
                    # 优先级冲突检查
                    for m in self.manager.models:
                        if (is_edit and model_data and m.id != model_data.id or not is_edit) and m.priority == new_priority:
                            if not messagebox.askyesno("优先级冲突", f"优先级 {new_priority} 已被其他模型使用，是否继续？"):
                                return
                            break
                    if is_edit and model_data:
                        self.manager.update_model(
                            model_data.id,
                            name=name_var.get().strip(),
                            base_url=base_url_var.get().strip(),
                            model_name=model_name_var.get().strip(),
                            model_type=model_type_var.get(),
                            api_key=api_key_var.get().strip(),
                            priority=new_priority,
                            enabled=enabled_var.get()
                        )
                        messagebox.showinfo("成功", f"模型 '{name_var.get().strip()}' 更新成功")
                    else:
                        new_model = self.ModelConfig(
                            id=f"model_{int(time.time())}",
                            name=name_var.get().strip(),
                            base_url=base_url_var.get().strip(),
                            model_name=model_name_var.get().strip(),
                            model_type=model_type_var.get(),
                            api_key=api_key_var.get().strip(),
                            priority=new_priority,
                            enabled=enabled_var.get()
                        )
                        self.manager.add_model(new_model)
                        messagebox.showinfo("成功", f"模型 '{new_model.name}' 添加成功")
                    dialog.destroy()
                    refresh_model_list()
                except Exception as e:
                    messagebox.showerror("错误", f"保存失败: {e}")
            def cancel():
                dialog.destroy()
            save_button_text = "更新" if is_edit else "保存"
            tb.Button(button_frame2, text=save_button_text, command=save_model, bootstyle=SUCCESS, width=15).pack(side=LEFT, padx=(0, 10))
            tb.Button(button_frame2, text="取消", command=cancel, bootstyle=SECONDARY, width=15).pack(side=LEFT)
            form_frame.columnconfigure(1, weight=1)
        # 按钮布局
        tb.Button(button_frame, text="添加模型", command=add_model, bootstyle=SUCCESS).grid(row=0, column=0, padx=2, pady=2, sticky=(W, E))
        tb.Button(button_frame, text="编辑模型", command=edit_model, bootstyle=INFO).grid(row=0, column=1, padx=2, pady=2, sticky=(W, E))
        tb.Button(button_frame, text="删除模型", command=delete_model, bootstyle=DANGER).grid(row=0, column=2, padx=2, pady=2, sticky=(W, E))
        tb.Button(button_frame, text="切换状态", command=toggle_model_status, bootstyle=WARNING).grid(row=0, column=3, padx=2, pady=2, sticky=(W, E))
        tb.Button(button_frame, text="刷新列表", command=refresh_model_list, bootstyle=SECONDARY).grid(row=1, column=0, columnspan=2, padx=2, pady=2, sticky=(W, E))
        tb.Button(button_frame, text="打开配置文件", command=lambda: os.startfile(self.config_file) if os.path.exists(self.config_file) else messagebox.showinfo("提示", "配置文件不存在"), bootstyle=PRIMARY).grid(row=1, column=2, columnspan=2, padx=2, pady=2, sticky=(W, E))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)
        button_frame.columnconfigure(3, weight=1)
        refresh_model_list() 