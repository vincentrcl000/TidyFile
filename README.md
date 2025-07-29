# TidyFile - 智能文件整理与解读系统

基于AI的智能文件整理和解读系统，支持文件分类、内容摘要生成、批量处理等功能。

## 🚀 核心功能

- **智能文件分类**：基于AI的文件内容分析和分类
- **文件解读与摘要**：单线程/多线程批量文件处理
- **文章阅读助手**：局域网访问，移动端友好界面
- **微信文章管理**：微信文章导入和AI摘要生成
- **重复文件清理**：智能重复文件检测和批量去重

## 📋 技术栈

- **后端**：Python 3.8+
- **前端**：HTML5 + CSS3 + JavaScript
- **AI模型**：Ollama (qwen3:4b)
- **GUI框架**：tkinter
- **文件处理**：PyPDF2, python-docx, Pillow
- **网络服务**：Flask

## 🛠️ 开发环境搭建

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd TidyFile

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
   ```

### 2. AI模型配置

   ```bash
# 安装Ollama
# 下载地址: https://ollama.ai/

# 下载模型
ollama pull qwen3:4b

# 启动Ollama服务
ollama serve
```

### 3. 配置文件

**AI模型配置** (`ai_models_config.json`):
```json
{
  "models": [
    {
      "id": "ollama-local",
      "name": "本地Ollama模型",
      "base_url": "http://localhost:11434",
      "model_name": "qwen3:4b",
      "model_type": "ollama",
      "priority": 3,
      "enabled": true
    }
  ]
}
```

**分类规则配置** (`classification_rules.json`):
```json
{
  "rules": [
    {
      "name": "工作文档",
      "keywords": ["工作", "项目", "报告"],
      "target_folder": "工作文档"
    }
  ]
}
```

## 🏗️ 项目架构

```
TidyFile/
├── gui_app_tabbed.py          # 主程序GUI入口
├── start_viewer_server.py     # 文章阅读助手服务器
├── viewer.html                # 文章阅读助手前端界面
├── ai_client_manager.py       # AI客户端管理核心
├── file_reader.py             # 文件解读核心模块
├── multi_task_file_reader.py  # 批量处理模块
├── smart_file_classifier.py   # 智能文件分类模块
├── weixin_manager_gui.py      # 微信文章管理GUI
├── duplicate_file_remover_gui.py # 重复文件清理GUI
├── path_utils.py              # 路径处理工具
├── concurrent_result_manager.py # 并发结果管理
├── transfer_log_manager.py    # 传输日志管理
└── logs/                      # 日志目录
```

## 🔧 核心模块说明

### AI客户端管理 (`ai_client_manager.py`)

- 支持多种AI模型（Ollama、OpenAI等）
- 模型优先级管理
- 自动故障转移
- 请求重试机制

### 文件解读 (`file_reader.py`)

- 多格式文件支持（PDF、Word、TXT、图片等）
- 内容提取和预处理
- AI摘要生成
- 错误处理和重试

### 批量处理 (`multi_task_file_reader.py`)

- 多线程并发处理
- 进度监控和状态管理
- 结果聚合和去重
- 内存优化

### 智能分类 (`smart_file_classifier.py`)

- 基于AI的内容分析
- 自定义分类规则
- 目标路径匹配
- 文件移动和日志记录

## 🚀 启动方式

### 开发模式

```bash
# 激活虚拟环境
.venv\Scripts\activate

# 启动主程序
python gui_app_tabbed.py

# 启动文章阅读助手
python start_viewer_server.py
```

### 生产模式

```bash
# 使用启动脚本
启动文件整理器_新版本.bat
启动局域网服务器.bat
```

## 📊 数据格式

### 处理结果格式 (`ai_organize_result.json`)

```json
{
  "处理时间": "2025-01-27 10:30:00",
  "文件名": "example.pdf",
  "文章标题": "文档标题",
  "文章摘要": "文档摘要内容...",
  "源文件路径": "D:/原始文件/example.pdf",
  "最终目标路径": "D:/分类结果/工作文档/example.pdf",
  "处理状态": "分类成功",
  "处理耗时": 2.5,
  "文件元数据": {
    "file_size": 1024000,
    "modified_time": "2025-01-27 10:30:00",
    "file_type": "pdf"
  },
  "标签": {
    "链式标签": "工作文档/项目报告/2024年"
  }
}
```

### 日志格式

**系统日志** (`logs/`):
- 程序运行状态
- 错误信息记录
- 性能统计信息

**传输日志** (`transfer_logs/`):
- 文件移动记录
- 操作历史追踪
- 回滚操作支持

## 🔍 开发调试

### 诊断工具

```bash
# 检查Ollama服务
python ollama诊断工具.py

# 测试AI调用
python 测试AI调用.py

# 测试文件解读
python 测试文件解读.py

# 测试批量处理
python 测试批量处理.py
```

### 日志查看

```bash
# 查看最新日志
tail -f logs/app.log

# 查看错误日志
grep "ERROR" logs/app.log
```

### 性能监控

- 内存使用监控
- 处理速度统计
- 并发性能测试
- 错误率统计

## 🧪 测试

### 单元测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定模块测试
python -m pytest tests/test_file_reader.py
```

### 集成测试

```bash
# 测试完整流程
python tests/integration_test.py

# 测试AI模型连接
python tests/test_ai_models.py
```

## 🔧 配置优化

### 性能调优

```json
{
  "performance": {
    "max_workers": 4,
    "chunk_size": 1000,
    "timeout": 30,
    "retry_count": 3
  }
}
```

### 内存优化

- 分批处理大文件
- 及时释放内存
- 使用生成器处理大量数据
- 优化图片处理

## 🚀 部署

### 生产环境

1. **环境准备**：
   - Python 3.8+
   - 4GB+ 内存
   - 稳定的网络连接

2. **服务配置**：
   - 配置AI模型
   - 设置文件权限
   - 配置防火墙

3. **监控配置**：
   - 日志轮转
   - 性能监控
   - 错误告警

### Docker部署

```dockerfile
FROM python:3.8-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "start_viewer_server.py"]
```

## 🤝 贡献指南

### 开发流程

1. Fork 项目
2. 创建功能分支
3. 提交代码
4. 创建 Pull Request

### 代码规范

- 遵循 PEP 8 规范
- 添加类型注解
- 编写文档字符串
- 添加单元测试

### 提交规范

```
feat: 添加新功能
fix: 修复bug
docs: 更新文档
style: 代码格式调整
refactor: 代码重构
test: 添加测试
chore: 构建过程或辅助工具的变动
```

## 📄 许可证

MIT License

## 📞 支持

- **文档**：查看 `用户手册.md`
- **Issues**：提交问题和建议
- **讨论**：参与项目讨论

---

**版本**：2.0.0  
**更新时间**：2025-01-27  
**维护者**：AI Assistant