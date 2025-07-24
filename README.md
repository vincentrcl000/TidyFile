# 智能文件整理器 - 开发者文档

基于 AI 的智能文件分类整理工具，使用本地 Ollama 模型进行文件内容分析和自动分类。

## 🚀 功能特性

- 🤖 **AI 智能分析**: 使用本地 Ollama 模型分析文件内容
- 📁 **自动分类**: 根据文件内容自动分类到合适的文件夹
- 🖥️ **分页界面**: 提供智能分类、文件分类和工具三个分页
- 🔒 **隐私保护**: 完全本地化处理，不上传任何数据
- 📊 **批量处理**: 支持大量文件的批量整理
- 🔄 **操作记录**: 支持操作回滚和文件恢复
- 🗂️ **重复文件删除**: 智能检测和删除重复文件
- 📝 **操作日志**: 详细记录所有操作，便于追踪
- 📖 **文件解读**: 支持多种文档格式的内容解读
- 🔧 **参数调节**: 可调节AI摘要长度和内容截取参数
- 💬 **微信信息管理**: 支持微信收藏文章整理、解读等功能

## 🛠️ 系统要求

- **操作系统**: Windows 10/11 (64位)
- **内存**: 至少 8GB RAM
- **存储**: 至少 5GB 可用磁盘空间
- **Python**: 3.8+ (开发环境)
- **AI服务**: Ollama 服务

## 📦 安装部署

### 方式一：使用可执行文件（生产环境）

1. 下载最新的 Release 版本
2. 解压到任意目录
3. 安装 Ollama 服务
4. 下载 AI 模型
5. 运行 `智能文件整理器.exe`

### 方式二：从源码运行（开发环境）

1. 克隆仓库
```bash
git clone https://github.com/your-username/file-organizer.git
cd file-organizer
```

2. 创建虚拟环境
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 安装和配置 Ollama
```bash
# 访问 https://ollama.com 下载安装
# 下载模型
ollama pull qwen2:0.5b
```

5. 启动程序
```bash
python start.py
# 或双击 启动文件整理器.bat
```

### 微信信息管理功能配置

如需使用微信信息管理功能，需要额外配置：

1. 安装 [sjzar/chatlog](https://github.com/sjzar/chatlog) 工具
2. 启动 chatlog 并开启 HTTP 服务
3. 确认 `http://127.0.0.1:5030` 可访问

## 🏗️ 项目结构

```
TidyFile/
├── 核心功能/
│   ├── gui_app_tabbed.py          # 主界面程序
│   ├── file_organizer_ai.py       # AI智能分类核心
│   ├── file_organizer_simple.py   # 简单分类逻辑
│   ├── smart_file_classifier.py   # AI文件分类器
│   └── ai_client_manager.py       # AI客户端管理
├── 工具功能/
│   ├── file_reader.py             # 文件解读器
│   ├── document_converter.py      # 文档转换器
│   ├── file_duplicate_cleaner.py  # 重复文件清理器
│   └── transfer_log_manager.py    # 转移日志管理器
├── 微信管理/
│   ├── weixin_manager_gui.py      # 微信管理界面
│   ├── weixin_manager_logic.py    # 微信管理逻辑
│   └── weixin_manager/            # 微信数据目录
├── 配置管理/
│   ├── classification_rules.json  # 分类规则配置
│   ├── ai_models_config.json      # AI模型配置
│   └── classification_rules_manager.py # 规则管理器
├── 界面组件/
│   ├── duplicate_file_remover_gui.py # 重复文件删除界面
│   └── classification_rules_gui.py   # 分类规则界面
├── 文档查看/
│   ├── ai_result_viewer.html      # AI结果查看器
│   ├── start_viewer_server.py     # 查看器服务器
│   ├── weixin_article_renderer.html # 微信文章渲染器
│   └── weixin_article_template.html # 文章模板
├── 启动文件/
│   ├── start.py                   # 程序入口
│   ├── start_viewer_server.pyw    # 无窗口服务器
│   ├── 启动文件整理器.bat         # Windows启动脚本
│   └── install_dependencies.py    # 依赖安装脚本
├── 资源文件/
│   ├── TidyFile.ico              # 程序图标
│   ├── favicon.ico               # 网页图标
│   └── favicon.svg               # SVG图标
├── 文档/
│   ├── README.md                 # 开发者文档
│   ├── 用户手册.md               # 用户使用手册
│   └── requirements.txt          # 依赖列表
└── 数据文件/
    ├── ai_organize_result.json   # AI整理结果
    └── .gitignore                # Git忽略文件
```

## 🔧 技术栈

### 前端技术
- **GUI框架**: Tkinter (分页式界面)
- **Web界面**: HTML5 + CSS3 + JavaScript
- **HTTP服务器**: Python http.server

### 后端技术
- **AI模型**: Ollama (本地部署)
- **HTTP客户端**: requests
- **文件处理**: pathlib, shutil
- **文档解析**: PyPDF2, python-docx, Pillow
- **重复检测**: hashlib (MD5)
- **日志管理**: logging

### 开发工具
- **打包工具**: PyInstaller
- **版本控制**: Git
- **依赖管理**: pip

## 🚀 开发指南

### 环境设置

1. 安装开发依赖
```bash
pip install -r requirements.txt
pip install pytest black flake8  # 开发工具
```

2. 配置代码格式化
```bash
black .  # 代码格式化
flake8 .  # 代码检查
```

### 代码结构

- **模块化设计**: 每个功能模块独立
- **配置分离**: 配置文件和代码分离
- **错误处理**: 完善的异常处理机制
- **日志记录**: 详细的操作日志

### 测试

```bash
# 运行测试
pytest tests/

# 运行特定测试
pytest tests/test_file_organizer.py
```

## 📦 构建部署

### 构建可执行文件

```bash
# 安装PyInstaller
pip install pyinstaller

# 构建可执行文件
pyinstaller --onefile --windowed --icon=TidyFile.ico gui_app_tabbed.py
```

### 构建配置

- **单文件模式**: `--onefile`
- **无窗口模式**: `--windowed`
- **自定义图标**: `--icon=TidyFile.ico`
- **包含数据文件**: `--add-data`

## 🔍 故障排除

### 常见问题

1. **Ollama 连接失败**
   - 检查 Ollama 服务状态
   - 确认防火墙设置
   - 重启 Ollama 服务

2. **模型不可用**
   - 检查模型列表: `ollama list`
   - 重新下载模型: `ollama pull qwen2:0.5b`

3. **依赖安装失败**
   - 升级 pip: `python -m pip install --upgrade pip`
   - 使用国内镜像: `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/`

4. **程序无法启动**
   - 检查 Python 版本
   - 确认依赖完整性
   - 查看错误日志

### 调试模式

```bash
# 启用调试日志
python start.py --debug

# 查看详细错误信息
python -u start.py
```

## 📝 更新日志

### v2.0.2 (2025-01-24)
- ✅ 优化AI结果查看器界面
- ✅ 改进文件路径检查和修复功能
- ✅ 实现异步操作，提升用户体验
- ✅ 优化C盘搜索策略，提高搜索效率
- ✅ 清理项目结构，删除测试文件

### v2.0.1 (2025-01-20)
- ✅ 新增微信文章管理功能
- ✅ 优化文件解读性能
- ✅ 改进错误处理机制

### v2.0.0 (2025-01-15)
- ✅ 全新分页式界面设计
- ✅ 智能分类和文件分类功能分离
- ✅ 新增文件解读功能
- ✅ 优化AI参数调节

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

### 代码规范

- 使用 Python 3.8+ 语法
- 遵循 PEP 8 代码风格
- 添加适当的注释和文档字符串
- 编写单元测试

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 技术支持

- **Issues**: [GitHub Issues](https://github.com/your-username/file-organizer/issues)
- **文档**: [用户手册.md](用户手册.md)
- **邮箱**: your-email@example.com

---

**版本**: v2.0.2 | **最后更新**: 2025年1月24日