#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TidyFile 安装脚本
"""

from setuptools import setup, find_packages
import os

# 读取 README 文件
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# 读取 requirements.txt
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="tidyfile",
    version="1.0.0",
    author="TidyFile Project",
    author_email="your-email@example.com",
    description="基于AI的智能文件整理与解读系统",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/vincentrcl000/TidyFile",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Desktop Environment :: File Managers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.800",
        ],
    },
    entry_points={
        "console_scripts": [
            "tidyfile=src.tidyfile.gui.main_window:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.html", "*.ico", "*.svg"],
    },
    keywords="file-management, ai, classification, document-processing, gui",
    project_urls={
        "Bug Reports": "https://github.com/vincentrcl000/TidyFile/issues",
        "Source": "https://github.com/vincentrcl000/TidyFile",
        "Documentation": "https://github.com/vincentrcl000/TidyFile#readme",
    },
) 