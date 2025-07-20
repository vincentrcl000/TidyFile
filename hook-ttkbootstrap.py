#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyInstaller hook文件 - ttkbootstrap模块支持
确保ttkbootstrap及其所有依赖被正确打包到可执行文件中

作者: AI Assistant
创建时间: 2025-01-20
"""

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules
import os

# 收集ttkbootstrap的所有模块、数据文件和依赖
datas, binaries, hiddenimports = collect_all('ttkbootstrap')

# 额外收集主题文件和资源文件
theme_datas = collect_data_files('ttkbootstrap.themes', include_py_files=True)
assets_datas = collect_data_files('ttkbootstrap', includes=['*.json', '*.png', '*.gif', '*.ico'])

# 合并数据文件
datas.extend(theme_datas)
datas.extend(assets_datas)

# 确保所有子模块都被包含
all_submodules = collect_submodules('ttkbootstrap')
hiddenimports.extend(all_submodules)

# 添加额外的隐藏导入
extra_imports = [
    'ttkbootstrap.constants',
    'ttkbootstrap.style',
    'ttkbootstrap.themes',
    'ttkbootstrap.widgets',
    'ttkbootstrap.scrolled',
    'ttkbootstrap.tooltip',
    'ttkbootstrap.dialogs',
    'ttkbootstrap.tableview',
    'ttkbootstrap.validation',
    'ttkbootstrap.colorutils',
    'ttkbootstrap.icons',
    'ttkbootstrap.publisher',
    'ttkbootstrap.toast',
    'ttkbootstrap.utility',
    'ttkbootstrap.window',
    'ttkbootstrap.localization'
]

# 去重并添加到隐藏导入列表
hiddenimports.extend([imp for imp in extra_imports if imp not in hiddenimports])

print(f"ttkbootstrap hook: 收集到 {len(datas)} 个数据文件")
print(f"ttkbootstrap hook: 收集到 {len(hiddenimports)} 个隐藏导入")
print(f"ttkbootstrap hook: 收集到 {len(binaries)} 个二进制文件")