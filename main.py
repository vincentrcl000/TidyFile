#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TidyFile 主入口文件

启动智能文件整理与解读系统的主界面。
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from tidyfile.gui.main_window import main

if __name__ == "__main__":
    main() 