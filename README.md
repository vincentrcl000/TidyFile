# TidyFile - 智能文件整理与解读系统

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://github.com/vincentrcl000/TidyFile)

基于AI的智能文件整理和解读系统，让文件管理变得简单高效。

## 🎯 适用场景

- **📁 文件整理**：自动分类大量文档、图片、视频等文件
- **📖 内容摘要**：批量生成文件内容摘要，快速了解文档要点
- **📱 移动阅读**：通过手机、平板访问和阅读处理结果
- **🔄 重复清理**：智能检测和清理重复文件，节省存储空间
- **📋 标签管理**：优化文件标签体系，提升查找效率

## 🚀 快速开始

### 方式一：下载可执行文件（推荐）

1. **下载安装包**
   - 访问 [GitHub Releases](https://github.com/vincentrcl000/TidyFile/releases)
   - 下载 Windows 版本：
     - `TidyFile-Windows-x64.exe` - 便携版可执行文件
     - `TidyFile-Windows-x64.zip` - 压缩包版本
     - `TidyFile-Windows-Installer.zip` - 完整安装包（推荐）

2. **运行程序**
   - 便携版：双击 `.exe` 文件直接运行
   - 安装包：解压后运行 `create_desktop_shortcuts.py` 创建桌面快捷方式

### 方式二：源代码安装

```bash
# 克隆项目
git clone https://github.com/vincentrcl000/TidyFile.git
cd TidyFile

# 安装依赖
pip install -r requirements.txt

# 启动应用
python main.py
```

### 2. 配置AI模型

```bash
# 安装Ollama (推荐)
# 下载地址: https://ollama.ai/

# 下载模型
ollama pull qwen3:4b

# 启动服务
ollama serve
```

### 3. 开始使用

1. **选择源文件夹**：包含要处理的文件
2. **设置目标文件夹**：分类后的存储位置
3. **调整参数**：摘要长度、内容截取等
4. **开始处理**：AI自动分析并分类文件

## 🌟 核心功能

- **🤖 AI智能分类**：基于内容自动分类文件
- **📊 批量处理**：支持多线程并发处理
- **📱 移动访问**：Web界面支持手机平板
- **🌍 多语言**：中文、英文界面切换
- **🔄 便携模式**：无需安装，即插即用
- **📋 操作日志**：完整记录，支持回滚

## 📋 技术栈

- **后端**：Python 3.8+
- **AI模型**：Ollama (qwen3:4b)
- **GUI框架**：tkinter
- **文件处理**：PyPDF2, python-docx, Pillow
- **网络服务**：Flask
- **平台支持**：Windows 10/11

## 📖 使用指南

### 基本操作流程

1. **启动程序**：运行 `python main.py`
2. **选择功能**：AI智能分类、文件解读、重复清理等
3. **配置参数**：设置源文件夹、目标文件夹、处理参数
4. **开始处理**：AI自动分析并执行相应操作
5. **查看结果**：通过文章阅读助手或直接查看文件

### 移动端使用

1. **启动服务器**：运行文章阅读助手
2. **获取地址**：记下显示的局域网地址
3. **手机访问**：在手机浏览器中输入地址
4. **浏览文件**：支持搜索、筛选、预览、下载

### 微信文章管理功能使用方法

重要依赖：该功能需要先用chatlog（https://github.com/sjzar/chatlog）来获取微信里藏的文章，再调用AI来进行下载到本地、生成摘要，合并到文章阅读助手和本地文章一样查看。
1. **chatlog**：请先下载该软件，按照其指引启用后在TidyFile中直接输入收藏文章的账号名来备份文章列表（仅支持链接。微信文件会直接不加密存储在微信用户目录，不依赖chatlog即可直接使用智能分类功能整理到自己的文件目录中）
2. **微信版本要求**：下载安装微信电脑版4.0.3版本，关闭自动更新。因为chatlog已不再更新，它并不支持最新版微信
3. **安全性说明**：TidyFile、chatlog完全本地化运行，理论上无风险，请保障在安全的系统环境中使用

## 📚 更多文档

- **[详细帮助文档](docs/详细帮助文档.md)** - 完整的技术文档
- **[用户手册](docs/用户手册.md)** - 用户使用指南
- **[项目结构](docs/PROJECT_STRUCTURE.md)** - 代码架构说明
- **[贡献指南](CONTRIBUTING.md)** - 参与项目开发

## 免责申明
 - 本项目用于个人学习研究使用，所有代码使用AI生成，相关风险请自行评估

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---

**版本**：1.0.0  
**更新时间**：2025-08-05