#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文件整理器启动脚本
"""

import sys
import os
from pathlib import Path

def main():
    """主函数"""
    try:
        # 确保当前目录在Python路径中
        current_dir = Path(__file__).parent
        if str(current_dir) not in sys.path:
            sys.path.insert(0, str(current_dir))
        
        # 导入并启动GUI应用
        from gui_app_tabbed import FileOrganizerTabGUI
        
        # 创建并运行应用
        app = FileOrganizerTabGUI()
        app.run()
        
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保已安装所有依赖包")
        print("运行: pip install -r requirements.txt")
        input("按回车键退出...")
    except Exception as e:
        print(f"程序启动失败: {e}")
        input("按回车键退出...")

if __name__ == "__main__":
    main()