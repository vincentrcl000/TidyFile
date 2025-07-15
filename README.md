# 智能文件整理器

基于 AI 的智能文件分类整理工具，使用本地 Ollama 模型进行文件内容分析和自动分类。

## 功能特性

- 🤖 **AI 智能分析**: 使用本地 Ollama 模型分析文件内容
- 📁 **自动分类**: 根据文件内容自动分类到合适的文件夹
- 🖥️ **友好界面**: 提供直观的图形用户界面
- 🔒 **隐私保护**: 完全本地化处理，不上传任何数据
- 📊 **批量处理**: 支持大量文件的批量整理
- 🔄 **文件恢复**: 支持操作回滚和文件恢复
- 🗂️ **重复文件删除**: 智能检测和删除重复文件
- 📝 **操作日志**: 详细记录所有操作，便于追踪

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
ollama pull gemma2:2b
```

4. 启动程序
```bash
python start.py
```

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
├── start.py              # 程序入口
├── gui_app.py            # 图形界面
├── file_organizer.py     # 核心逻辑
├── transfer_log_manager.py # 日志管理
├── build_exe.py          # 构建脚本
├── requirements.txt      # 依赖列表
├── tests/               # 测试文件
└── README.md            # 说明文档
```

## 技术栈

- **界面**: Tkinter
- **AI模型**: Ollama (本地部署)
- **HTTP客户端**: requests
- **文件处理**: pathlib, shutil
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

### v1.0.0
- 初始版本发布
- 基础文件整理功能
- AI 智能分类
- 图形用户界面
- 重复文件删除
- 操作日志和恢复功能

---

如有问题或建议，请提交 Issue 或联系开发者。