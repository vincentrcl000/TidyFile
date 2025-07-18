# .doc文件转换支持指南

本应用现在支持多种方式处理传统的.doc文件格式。以下是各种转换引擎的安装和使用说明。

## 支持的转换引擎

### 1. pywin32（推荐 - Windows用户）

**适用平台**: 仅Windows  
**优点**: 转换质量最高，完全兼容Microsoft Word格式  
**缺点**: 需要安装Microsoft Word

**安装方法**:
```bash
pip install pywin32
```

**要求**: 系统必须安装Microsoft Word

### 2. LibreOffice（推荐 - 跨平台）

**适用平台**: Windows, Linux, macOS  
**优点**: 免费开源，转换质量好，支持多种格式  
**缺点**: 需要单独安装LibreOffice

**安装方法**:
1. 下载并安装LibreOffice: https://www.libreoffice.org/download/download/
2. 确保`soffice`命令在系统PATH中可用

**使用示例**:
```bash
# 手动转换命令
soffice --headless --convert-to docx --outdir output_folder input.doc
```

### 3. unoconv

**适用平台**: Linux, macOS（Windows支持有限）  
**优点**: 命令行工具，易于自动化  
**缺点**: 依赖LibreOffice/OpenOffice

**安装方法**:
```bash
# Ubuntu/Debian
sudo apt-get install unoconv

# macOS (使用Homebrew)
brew install unoconv

# 或使用pip
pip install unoconv
```

### 4. antiword（文本提取）

**适用平台**: 主要是Linux/macOS  
**优点**: 轻量级，专门处理.doc文件  
**缺点**: 只能提取文本，不保留格式

**安装方法**:
```bash
# Ubuntu/Debian
sudo apt-get install antiword

# macOS (使用Homebrew)
brew install antiword
```

## 转换引擎优先级

应用会按以下优先级自动选择转换引擎：

### .doc到.docx转换:
1. **pywin32**（Windows系统且可用时）
2. **simple_rename**（检测伪装的.docx文件）
3. **LibreOffice**
4. **unoconv**
5. **antiword**（仅文本提取）

### 其他格式转换:
1. **pypandoc**
2. **LibreOffice**
3. **unoconv**
4. **pywin32**（Windows）
5. **antiword**（仅支持文本输出）

## 安装建议

### Windows用户:
1. 如果已安装Microsoft Word，推荐安装`pywin32`
2. 否则推荐安装LibreOffice

### Linux/macOS用户:
1. 推荐安装LibreOffice
2. 可选安装unoconv和antiword作为备用

### 服务器环境:
1. 推荐LibreOffice headless模式
2. 可选unoconv用于批量处理

## 故障排除

### 常见问题:

1. **"File is not a zip file"错误**
   - 这表示.doc文件是传统二进制格式，需要专门的转换工具
   - 安装上述任一转换引擎即可解决

2. **"没有可用的转换引擎"错误**
   - 检查是否安装了任何转换工具
   - 运行应用时查看日志，确认哪些引擎被检测到

3. **LibreOffice转换失败**
   - 确保LibreOffice正确安装
   - 检查`soffice`命令是否在PATH中
   - 尝试手动运行转换命令测试

4. **pywin32转换失败**
   - 确保Microsoft Word已安装
   - 检查Word是否可以正常打开.doc文件
   - 尝试以管理员权限运行应用

### 测试转换引擎:

可以通过应用日志查看哪些转换引擎被成功检测到：

```
检测到pypandoc引擎
检测到LibreOffice: C:\Program Files\LibreOffice\program\soffice.exe
检测到pywin32引擎（Windows专用）
```

## 性能优化建议

1. **批量转换**: 使用LibreOffice的监听模式可以提高批量转换性能
2. **服务器部署**: 在无GUI环境下使用LibreOffice headless模式
3. **缓存**: 对于重复转换的文件，考虑实现缓存机制

## 格式支持矩阵

| 引擎 | .doc→.docx | .doc→.pdf | .doc→.txt | 质量 | 平台支持 |
|------|------------|-----------|-----------|------|----------|
| pywin32 | ✅ | ✅ | ✅ | 最高 | Windows |
| LibreOffice | ✅ | ✅ | ✅ | 高 | 全平台 |
| unoconv | ✅ | ✅ | ✅ | 高 | Linux/macOS |
| antiword | ✅* | ❌ | ✅ | 中 | Linux/macOS |

*antiword转换的.docx只包含文本内容，不保留原始格式