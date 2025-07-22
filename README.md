# 智能文件整理器

基于 AI 的智能文件分类整理工具，使用本地 Ollama 模型进行文件内容分析和自动分类。

## 功能特性

- 🤖 **AI 智能分析**: 使用本地 Ollama 模型分析文件内容
- 📁 **自动分类**: 根据文件内容自动分类到合适的文件夹
- 🖥️ **分页界面**: 提供智能分类、文件分类和工具三个分页
- 🔒 **隐私保护**: 完全本地化处理，不上传任何数据
- 📊 **批量处理**: 支持大量文件的批量整理
- 🔄 **文件恢复**: 支持操作回滚和文件恢复
- 🗂️ **重复文件删除**: 智能检测和删除重复文件
- 📝 **操作日志**: 详细记录所有操作，便于追踪
- 📖 **文件解读**: 支持多种文档格式的内容解读
- 🔧 **参数调节**: 可调节AI摘要长度和内容截取参数
- 💬 **微信信息管理**: 支持微信收藏文章整理、解读等功能（需额外依赖，见下方说明）

> ⚠️ 使用“微信信息管理”功能前，请先安装并运行 [sjzar/chatlog](https://github.com/sjzar/chatlog) 工具，并确保其 HTTP API 服务已开启（默认 http://127.0.0.1:5030）。

## 系统要求

- Windows 10/11 (64位)
- 至少 8GB 内存
- 至少 5GB 可用磁盘空间
- Python 3.8+ (开发环境)
- Ollama 服务

## 安装和使用

### 方式一：使用可执行文件（推荐）

1. 下载最新的 Release 版本
2. 解压到任意目录
3. 安装 Ollama 服务
4. 下载 AI 模型
5. 运行 `智能文件整理器.exe`
6. **如需使用微信信息管理功能：**
   - 按照 [sjzar/chatlog](https://github.com/sjzar/chatlog) 官方文档安装并配置 chatlog 工具
   - 启动 chatlog 并开启 HTTP 服务（可在 chatlog 菜单选择“开启 HTTP 服务”）
   - 确认本地 http://127.0.0.1:5030 可访问

### 方式二：从源码运行

1. 克隆仓库
```bash
git clone https://github.com/your-username/file-organizer.git
cd file-organizer
```
2. 安装依赖
```bash
pip install -r requirements.txt
```
3. 安装和配置 Ollama
```bash
# 访问 https://ollama.com 下载安装
# 下载模型
ollama pull qwen3:0.6b
```
4. 启动程序
```bash
python start.py
# 或双击 启动文件整理器.bat
```
5. **如需使用微信信息管理功能：**
   - 参考 [sjzar/chatlog](https://github.com/sjzar/chatlog) 文档安装 chatlog
   - 启动 chatlog 并开启 HTTP 服务
   - 确认 http://127.0.0.1:5030/api/v1/chatlog 可正常访问

## 构建可执行文件

```bash
python build_exe.py
```

构建完成后，可执行文件将生成在 `dist/` 目录中。

## 使用方法

1. **选择源目录**: 选择需要整理的文件夹
2. **选择目标目录**: 选择已建好分类文件夹的目标目录
3. **预览分类**: 查看 AI 的分类建议
4. **开始整理**: 执行文件分类操作
5. **确认删除**: 选择是否删除原文件

## 目录结构示例

目标目录应包含以下类型的文件夹：

```
目标目录/
├── 财经类/
├── 技术类/
├── 研究类/
├── 学习类/
├── 工作类/
├── 生活类/
├── 娱乐类/
├── 健康类/
└── 其他类/
```

## 项目结构

```
文件整理/
├── start.py                    # 程序入口
├── gui_app_tabbed.py          # 分页图形界面
├── file_organizer_ai.py       # AI智能分类核心逻辑
├── file_organizer_simple.py   # 简单分类核心逻辑
├── ai_file_classifier.py      # AI文件分类器
├── file_reader.py             # 文件解读器
├── document_converter.py      # 文档转换器
├── file_duplicate_cleaner.py  # 重复文件清理器
├── transfer_log_manager.py    # 转移日志管理器
├── migration_executor.py      # 迁移执行器
├── migration_planner.py       # 迁移规划器
├── directory_manager.py       # 目录管理器
├── build_exe.py              # 构建脚本
├── install_dependencies.py    # 依赖安装脚本
├── requirements.txt          # 依赖列表
├── 启动文件整理器.bat         # Windows启动脚本
├── 用户手册.md               # 详细用户手册
└── README.md                 # 项目说明
```

## 技术栈

- **界面**: Tkinter (分页式界面)
- **AI模型**: Ollama (本地部署，支持qwen2:0.5b等模型)
- **HTTP客户端**: requests
- **文件处理**: pathlib, shutil
- **文档解析**: PyPDF2, python-docx, Pillow
- **重复检测**: hashlib (MD5)
- **打包工具**: PyInstaller

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 故障排除

### Ollama 连接失败
- 确认 Ollama 服务正在运行
- 检查防火墙设置
- 重启 Ollama 服务

### 模型不可用
- 检查模型是否已下载: `ollama list`
- 重新下载模型: `ollama pull gemma2:2b`

### 程序无法启动
- 确认系统满足最低要求
- 以管理员身份运行
- 检查杀毒软件是否误报

## 更新日志

### v2.0.0
- 全新分页式界面设计
- 智能分类和文件分类功能分离
- 新增文件解读功能
- 新增文档转换功能
- AI参数可调节（摘要长度、内容截取）
- 优化过程数据输出到JSON文件
- 简化启动流程，统一使用gui_app_tabbed.py
- 移除旧版本冗余代码和测试文件

### v1.0.0
- 初始版本发布
- 基础文件整理功能
- AI 智能分类
- 图形用户界面
- 重复文件删除
- 操作日志和恢复功能

---

如有问题或建议，请提交 Issue 或联系开发者。