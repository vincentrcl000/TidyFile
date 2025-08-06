#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分类规则管理GUI
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
from typing import List, Optional
from tidyfile.core.classification_rules_manager import ClassificationRulesManager

class ClassificationRulesGUI:
    """分类规则管理GUI"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("分类规则管理器")
        
        # 初始化规则管理器
        self.rules_manager = ClassificationRulesManager()
        
        # 创建界面
        self.create_widgets()
        self.load_rules_list()
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="分类规则管理器", font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # 左侧：规则列表
        list_frame = ttk.LabelFrame(main_frame, text="规则列表", padding="5")
        list_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # 规则列表
        self.rules_tree = ttk.Treeview(list_frame, columns=("description", "keywords"), show="tree headings")
        self.rules_tree.heading("#0", text="文件夹名称")
        self.rules_tree.heading("description", text="存放内容说明")
        self.rules_tree.heading("keywords", text="关键词")
        self.rules_tree.column("#0", width=200)
        self.rules_tree.column("description", width=300)
        self.rules_tree.column("keywords", width=200)
        
        # 滚动条
        rules_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.rules_tree.yview)
        self.rules_tree.configure(yscrollcommand=rules_scrollbar.set)
        
        self.rules_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        rules_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 绑定选择事件
        self.rules_tree.bind("<<TreeviewSelect>>", self.on_rule_select)
        
        # 右侧：编辑区域
        edit_frame = ttk.LabelFrame(main_frame, text="编辑规则", padding="5")
        edit_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        edit_frame.columnconfigure(1, weight=1)
        
        # 文件夹名称
        ttk.Label(edit_frame, text="文件夹名称:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.folder_name_var = tk.StringVar()
        self.folder_name_entry = ttk.Entry(edit_frame, textvariable=self.folder_name_var, width=40)
        self.folder_name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=3, padx=(5, 0))
        
        # 存放内容说明
        ttk.Label(edit_frame, text="存放内容说明:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.description_text = tk.Text(edit_frame, height=3, width=40)
        self.description_text.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=3, padx=(5, 0))
        
        # 关键词
        ttk.Label(edit_frame, text="关键词(用逗号分隔):").grid(row=2, column=0, sticky=tk.W, pady=3)
        self.keywords_var = tk.StringVar()
        self.keywords_entry = ttk.Entry(edit_frame, textvariable=self.keywords_var, width=40)
        self.keywords_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=3, padx=(5, 0))
        
        # 按钮区域
        button_frame = ttk.Frame(edit_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=5)
        
        # 第一行按钮
        add_button = ttk.Button(button_frame, text="添加规则", command=self.add_rule)
        add_button.grid(row=0, column=0, padx=2, pady=2)
        
        update_button = ttk.Button(button_frame, text="更新规则", command=self.update_rule)
        update_button.grid(row=0, column=1, padx=2, pady=2)
        
        delete_button = ttk.Button(button_frame, text="删除规则", command=self.delete_rule)
        delete_button.grid(row=0, column=2, padx=2, pady=2)
        
        # 第二行按钮
        clear_button = ttk.Button(button_frame, text="清空表单", command=self.clear_form)
        clear_button.grid(row=1, column=0, padx=2, pady=2)
        
        import_button = ttk.Button(button_frame, text="导入规则", command=self.import_rules)
        import_button.grid(row=1, column=1, padx=2, pady=2)
        
        export_button = ttk.Button(button_frame, text="导出规则", command=self.export_rules)
        export_button.grid(row=1, column=2, padx=2, pady=2)
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
    
    def load_rules_list(self):
        """加载规则列表"""
        # 清空现有项目
        for item in self.rules_tree.get_children():
            self.rules_tree.delete(item)
        
        # 加载规则
        rules = self.rules_manager.get_all_rules()
        for folder_name, rule in rules.items():
            description = rule.get("description", "")
            keywords = ", ".join(rule.get("keywords", []))
            
            self.rules_tree.insert("", "end", text=folder_name, 
                                 values=(description, keywords))
        
        self.status_var.set(f"已加载 {len(rules)} 条规则")
    
    def on_rule_select(self, event):
        """规则选择事件"""
        selection = self.rules_tree.selection()
        if selection:
            item = selection[0]
            folder_name = self.rules_tree.item(item, "text")
            rule = self.rules_manager.get_rule(folder_name)
            
            if rule:
                self.folder_name_var.set(folder_name)
                self.description_text.delete(1.0, tk.END)
                self.description_text.insert(1.0, rule.get("description", ""))
                self.keywords_var.set(", ".join(rule.get("keywords", [])))
    
    def add_rule(self):
        """添加规则"""
        folder_name = self.folder_name_var.get().strip()
        description = self.description_text.get(1.0, tk.END).strip()
        keywords_text = self.keywords_var.get().strip()
        
        if not folder_name or not description:
            messagebox.showwarning("警告", "文件夹名称和存放内容说明不能为空！")
            return
        
        # 解析关键词
        keywords = [k.strip() for k in keywords_text.split(",") if k.strip()] if keywords_text else []
        
        if self.rules_manager.add_rule(folder_name, description, keywords):
            messagebox.showinfo("成功", "规则添加成功！")
            self.load_rules_list()
            self.clear_form()
        else:
            messagebox.showerror("错误", "规则添加失败！")
    
    def update_rule(self):
        """更新规则"""
        folder_name = self.folder_name_var.get().strip()
        description = self.description_text.get(1.0, tk.END).strip()
        keywords_text = self.keywords_var.get().strip()
        
        if not folder_name:
            messagebox.showwarning("警告", "请先选择要更新的规则！")
            return
        
        # 解析关键词
        keywords = [k.strip() for k in keywords_text.split(",") if k.strip()] if keywords_text else []
        
        if self.rules_manager.update_rule(folder_name, description, keywords):
            messagebox.showinfo("成功", "规则更新成功！")
            self.load_rules_list()
        else:
            messagebox.showerror("错误", "规则更新失败！")
    
    def delete_rule(self):
        """删除规则"""
        folder_name = self.folder_name_var.get().strip()
        
        if not folder_name:
            messagebox.showwarning("警告", "请先选择要删除的规则！")
            return
        
        if messagebox.askyesno("确认", f"确定要删除规则 '{folder_name}' 吗？"):
            if self.rules_manager.delete_rule(folder_name):
                messagebox.showinfo("成功", "规则删除成功！")
                self.load_rules_list()
                self.clear_form()
            else:
                messagebox.showerror("错误", "规则删除失败！")
    
    def clear_form(self):
        """清空表单"""
        self.folder_name_var.set("")
        self.description_text.delete(1.0, tk.END)
        self.keywords_var.set("")
    
    def import_rules(self):
        """导入规则"""
        file_path = filedialog.askopenfilename(
            title="选择要导入的规则文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            if self.rules_manager.import_rules(file_path):
                messagebox.showinfo("成功", "规则导入成功！")
                self.load_rules_list()
            else:
                messagebox.showerror("错误", "规则导入失败！")
    
    def export_rules(self):
        """导出规则"""
        file_path = filedialog.asksaveasfilename(
            title="选择导出位置",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            if self.rules_manager.export_rules(file_path):
                messagebox.showinfo("成功", "规则导出成功！")
            else:
                messagebox.showerror("错误", "规则导出失败！")

def main():
    """主函数"""
    root = tk.Tk()
    app = ClassificationRulesGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 