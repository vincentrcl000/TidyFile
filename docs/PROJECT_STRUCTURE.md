# 项目结构

## 📁 目录结构

```
TidyFile/
├── src/                          # 源代码目录
│   └── tidyfile/                 # 主包
│       ├── __init__.py           # 包初始化文件
│       ├── core/                 # 核心功能模块
│       │   ├── __init__.py
│       │   ├── file_reader.py           # 文件读取器
│       │   ├── smart_classifier.py      # 智能文件分类器
│       │   ├── directory_organizer.py   # 目录整理器
│       │   ├── duplicate_cleaner.py     # 重复文件清理器
│       │   ├── transfer_log_manager.py  # 转移日志管理器
│       │   ├── weixin_manager_logic.py  # 微信管理器逻辑
│       │   ├── classification_rules_manager.py  # 分类规则管理器
│       │   ├── multi_process_file_reader.py     # 多进程文件读取器
│       │   ├── multi_task_file_reader.py        # 多任务文件读取器
│       │   ├── concurrent_result_manager.py     # 并发结果管理器
│       │   ├── batch_add_chain_tags.py          # 批量添加链式标签
│       │   ├── analyze_chain_tags.py            # 分析链式标签
│       │   ├── wechat_article_ai_summary.py     # 微信文章AI摘要
│       │   ├── fix_article_titles.py            # 修复文章标题
│       │   ├── final_safety_check.py            # 最终安全检查
│       │   └── smart_file_classifier_adapter.py # 智能文件分类器适配器
│       ├── gui/                  # GUI模块
│       │   ├── __init__.py
│       │   ├── main_window.py              # 主窗口
│       │   ├── weixin_manager_gui.py       # 微信管理器GUI
│       │   ├── ai_model_config_gui.py      # AI模型配置GUI
│       │   ├── classification_rules_gui.py # 分类规则GUI
│       │   └── duplicate_file_remover_gui.py # 重复文件清理GUI
│       ├── ai/                   # AI模块
│       │   ├── __init__.py
│       │   └── client_manager.py           # AI客户端管理器
│       ├── i18n/                 # 国际化模块
│       │   ├── __init__.py
│       │   ├── i18n_manager.py            # 国际化管理器
│       │   └── gui_language_updater.py    # GUI语言更新器
│       └── utils/                # 工具模块
│           ├── __init__.py
│           ├── path_utils.py              # 路径工具
│           ├── app_paths.py               # 应用路径管理
│           └── config_migrator.py         # 配置迁移器
├── docs/                         # 文档目录
│   ├── 用户手册.md
│   ├── 项目通用化改造计划.md
│   ├── PROJECT_STRUCTURE.md
│   └── portable_mode.txt
├── scripts/                      # 脚本目录
│   ├── start_viewer_server.py
│   ├── start_viewer_server_https.py
│   ├── *.bat                     # Windows启动脚本
│   └── *.vbs                     # Windows VBS脚本
├── resources/                    # 资源文件目录
│   ├── *.html                    # HTML模板文件
│   ├── *.ico                     # 图标文件
│   └── *.svg                     # SVG图标文件
├── tests/                        # 测试目录
├── main.py                       # 主入口文件
├── setup.py                      # 安装脚本
├── requirements.txt              # 依赖列表
├── README.md                     # 项目说明
├── LICENSE                       # 开源许可证
├── CHANGELOG.md                  # 版本更新日志
├── CONTRIBUTING.md               # 贡献指南
├── RELEASE_CHECKLIST.md          # 发布检查清单
└── .gitignore                    # Git忽略文件
```

## 🔧 模块说明

### 核心模块 (core/)
包含所有核心业务逻辑：
- **文件处理**：文件读取、分类、整理
- **AI集成**：智能分类、摘要生成
- **数据管理**：日志记录、结果管理
- **工具功能**：重复文件清理、标签管理
- **微信管理**：微信文章备份、下载、处理

### GUI模块 (gui/)
包含所有图形用户界面：
- **主窗口**：应用程序主界面
- **功能窗口**：各种功能的具体界面
- **配置界面**：设置和配置界面
- **微信管理界面**：微信文章管理专用界面

### AI模块 (ai/)
包含AI相关功能：
- **客户端管理**：AI模型客户端
- **模型配置**：AI模型参数配置

### 国际化模块 (i18n/)
包含多语言支持：
- **翻译管理**：语言文件管理
- **界面更新**：动态语言切换

### 工具模块 (utils/)
包含各种工具函数：
- **路径管理**：文件路径处理
- **应用路径**：跨平台路径管理
- **配置迁移**：配置数据迁移

## 🚀 启动方式

### 开发环境
```bash
python main.py
```

### 安装后使用
```bash
pip install -e .
tidyfile
```

## 📦 打包结构

### 源代码包
- 包含完整的源代码
- 包含文档和资源文件
- 不包含用户数据和配置

### 可执行文件
- Windows: `.exe` 文件
- macOS: `.app` 包
- Linux: 可执行文件

## 🔄 数据流向

```
用户操作 → GUI模块 → 核心模块 → AI模块 → 结果返回
    ↓
配置管理 → 工具模块 → 文件系统
    ↓
国际化模块 → 界面更新

微信文章管理流程：
chatlog → 微信管理模块 → 下载模块 → AI处理 → 静态生成 → 文章阅读助手
```

## 🛠️ 开发指南

### 添加新功能
1. 在相应的模块目录下创建新文件
2. 更新模块的 `__init__.py` 文件
3. 在主包中导入新功能
4. 更新文档

### 修改现有功能
1. 直接修改对应模块的文件
2. 确保导入路径正确
3. 测试功能是否正常

### 添加新的GUI界面
1. 在 `gui/` 目录下创建新文件
2. 在主窗口中集成新界面
3. 添加国际化支持

## 📋 注意事项

1. **导入路径**：使用相对导入避免循环依赖
2. **模块化**：保持模块间的低耦合
3. **国际化**：所有用户界面文本都应支持多语言
4. **配置管理**：用户配置存储在标准应用数据目录
5. **错误处理**：每个模块都应包含适当的错误处理 