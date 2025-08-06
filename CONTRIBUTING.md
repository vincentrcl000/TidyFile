# Contributing to TidyFile

感谢您对 TidyFile 项目的关注！我们欢迎所有形式的贡献。

## 如何贡献

### 报告 Bug

如果您发现了 bug，请：

1. 检查是否已经有相关的 issue
2. 创建新的 issue，包含：
   - 详细的 bug 描述
   - 重现步骤
   - 期望行为
   - 实际行为
   - 系统环境信息

### 功能请求

如果您有功能建议，请：

1. 检查是否已经有相关的 issue
2. 创建新的 issue，描述：
   - 功能需求
   - 使用场景
   - 预期效果

### 代码贡献

#### 开发环境设置

1. Fork 项目到您的 GitHub 账户
2. Clone 您的 fork：
   ```bash
   git clone https://github.com/vincentrcl000/TidyFile.git
   cd TidyFile
   ```

3. 创建虚拟环境：
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # 或
   .venv\Scripts\activate     # Windows
   ```

4. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

#### 代码规范

- 使用 Python 3.8+
- 遵循 PEP 8 代码风格
- 添加适当的注释和文档字符串
- 使用类型注解
- 确保代码通过所有测试

#### 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
type(scope): description

[optional body]

[optional footer]
```

类型包括：
- `feat`: 新功能
- `fix`: bug 修复
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

#### 提交流程

1. 创建功能分支：
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. 进行修改并提交：
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

3. 推送到您的 fork：
   ```bash
   git push origin feature/your-feature-name
   ```

4. 创建 Pull Request

### 国际化贡献

如果您想帮助翻译，请：

1. 在 `app_data/user_data/locales/` 目录下找到语言文件
2. 添加或修改翻译内容
3. 确保翻译准确且符合本地化习惯

## 开发指南

### 项目结构

```
TidyFile/
├── src/                    # 源代码
├── docs/                   # 文档
├── tests/                  # 测试
├── scripts/                # 脚本
└── resources/              # 资源文件
```

### 运行测试

```bash
python -m pytest tests/
```

### 代码格式化

```bash
black .
flake8 .
```

## 行为准则

- 尊重所有贡献者
- 保持专业和友好的交流
- 接受建设性的批评
- 关注项目的最佳利益

## 许可证

通过贡献代码，您同意您的贡献将在 MIT 许可证下发布。

感谢您的贡献！ 