# PDF2Epub - PDF转EPUB工具

PDF2Epub是一个基于大模型OCR功能的PDF转EPUB工具，专为中文PDF文档优化，能够智能识别文档结构，包括封面、目录、章节、表格等，并生成结构良好的电子书。

**当前版本：v0.2.0**

> **注意：** 目前仅支持阿里百炼的Qwen-vl-ocr模型进行OCR处理，其他模型或API未经测试。

## 功能特点

- 使用大模型OCR技术，提供高精度的文本识别
- 智能识别文档结构（封面、目录、章节、表格等）
- 支持输出EPUB格式
- 自动处理图像和表格
- 支持断点续传和缓存
- 可定制的样式和排版
- 跨平台支持（Windows、Linux、macOS）
- **新增：交互式界面**，无需命令行操作

## 系统要求

- Python 3.8+
- 支持的操作系统：
  - Windows 10/11
  - Linux (Ubuntu 20.04+, CentOS 8+, 等)
  - macOS 11+

## 安装

### 依赖项

- Python 3.8+
- OpenCV
- NumPy
- Pillow
- requests

### 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/yourusername/PDF2Epub.git
cd PDF2Epub
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置API密钥
```bash
cp config/settings.ini.template config/settings.ini
```
然后编辑`config/settings.ini`文件，填入您的API密钥和其他配置。

## 使用方法

### 基本用法

```bash
python main.py input.pdf output.epub
```

### 高级选项

```bash
python main.py input.pdf output.epub --format epub --max-pages 100 --debug
```

参数说明：
- `input.pdf`: 输入PDF文件路径
- `output.epub`: 输出EPUB文件路径
- `--format`: 输出格式，目前仅支持epub
- `--max-pages`: 最大处理页数，默认处理全部页面
- `--debug`: 启用调试模式，输出详细日志
- `-v, --verbose`: 日志详细程度，可重复使用增加详细级别（例如：-v 或 -vv）

### 日志级别说明

PDF2Epub提供了三种日志详细程度，可通过`-v`或`--verbose`参数控制：

1. **基础级别**（默认，不带参数）
   - 只显示警告和错误信息
   - 简洁彩色输出，适合普通用户
   - 格式：`WARNING: 消息内容`

2. **信息级别**（使用`-v`）
   - 显示处理进度和基本统计信息
   - 包含时间戳，适合想了解更多细节的用户
   - 格式：`时间 - INFO: 消息内容`

3. **开发者级别**（使用`-vv`）
   - 显示详细的技术信息，包括模块名称和更多调试信息
   - 适合开发者和高级用户
   - 格式：`时间 - 模块名称 - DEBUG: 消息内容`

此外，`--debug`标志会直接将日志级别设置为最详细的DEBUG级别，无论`-v`参数如何设置。

### 日志颜色编码

日志输出使用彩色编码以提高可读性：
- DEBUG: 蓝色
- INFO: 绿色
- WARNING: 黄色
- ERROR: 红色
- CRITICAL: 红色加粗

## 交互式使用

PDF2Epub提供了交互式使用模式，可以在转换过程中显示实时进度和统计信息。

### 启动交互式界面

您可以通过以下方式启动交互式界面：

- **Windows**：双击 `toepub_interactive.bat`
- **Linux/macOS**：执行 `./toepub_interactive.py`

### 交互式选项

交互式界面提供以下选项：

1. **PDF文件选择**：使用方向键浏览并选择要转换的PDF文件
2. **输出路径选择**：可以选择默认路径或自定义路径
3. **日志级别选择**：
   - 基础级别：只显示警告和错误
   - 信息级别：显示处理进度和基本统计信息
   - 开发者级别：显示详细技术信息
4. **调试模式选项**：可以启用或禁用调试模式
5. **页数限制选项**：可以限制处理的最大页数

示例界面：
```
请选择要转换的PDF文件:
  > 海德格尔《哲学献文》导论.pdf
    尼采《查拉图斯特拉如是说》.pdf
    黑格尔《精神现象学》.pdf

选择输出路径:
  > 使用默认路径 (./output/)
    自定义路径

选择日志级别:
    基础级别
  > 信息级别
    开发者级别

启用调试模式？ [y/N]: n

限制处理页数？ [y/N]: y
最大处理页数: 10
```

### 转换进度显示

在转换过程中，程序会显示一个进度条，显示当前处理的页面和总页数：

```
📊 转换进度 (页 45/100): 45%|████████████████▌         | 45/100 [01:23<01:42]
```

如果启用了token使用跟踪，进度条还会显示当前已使用的token数量：

```
📊 转换进度 (页 45/100, 已用tokens: 12500): 45%|████████████████▌         | 45/100 [01:23<01:42]
```

### Token使用统计

在转换完成后，如果使用了OCR功能，程序会显示token使用统计信息：

```
🔢 总共使用了 25000 tokens，处理了 100 页OCR文本
💰 估算成本: $0.2500
📊 平均每页OCR使用 250.0 tokens
```

这些信息可以帮助您了解API使用成本和资源消耗情况。

### 断点续传

PDF2Epub支持断点续传功能，可以在转换中断后从上次处理的位置继续：

```bash
python main.py input.pdf output.epub --resume
```

程序会自动查找之前的处理记录，并从上次中断的位置继续处理。

## 跨平台开发

PDF2Epub设计为完全跨平台，可以在Windows、Linux和macOS上运行。以下是在不同平台上开发和使用的注意事项：

### Linux环境

在Linux上开发或运行PDF2Epub时，需要注意以下几点：

1. **路径处理**：代码中使用了平台无关的路径处理方式（`os.path`），确保在不同操作系统上都能正确处理文件路径。

2. **配置文件位置**：
   - 在Linux上，配置文件会按以下顺序查找：
     - `./config/settings.ini`（当前目录）
     - `~/.config/pdf2epub/settings.ini`（用户目录）
     - `/etc/pdf2epub/settings.ini`（系统目录）

3. **依赖安装**：
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install python3-pip python3-opencv
   pip3 install -r requirements.txt
   
   # CentOS/RHEL
   sudo yum install python3-pip
   sudo yum install opencv-python
   pip3 install -r requirements.txt
   ```

4. **权限设置**：
   ```bash
   # 确保脚本可执行
   chmod +x main.py
   
   # 运行
   ./main.py input.pdf output.epub
   ```

### 文件路径兼容性

为确保在不同平台上的兼容性，请遵循以下建议：

- 使用相对路径而非绝对路径
- 使用`os.path.join()`来连接路径组件
- 使用`os.path.expanduser()`来处理用户目录（如`~`）
- 避免使用平台特定的路径分隔符（如Windows的`\`或Linux的`/`）

## 配置文件

配置文件位于`config/settings.ini`，包含以下主要配置项：

```ini
[ocr]
# OCR API配置
model_name = qwen-vl-ocr
timeout = 30
retry_count = 3
batch_size = 5
api_url = https://dashscope.aliyuncs.com/compatible-mode/v1/
api_key = YOUR_API_KEY_HERE

[cache]
# 缓存配置
db_path = ./pdf2epub_cache.db
auto_resume = true
checkpoint_interval = 10
max_checkpoints = 3

[epub]
# EPUB生成配置
css_template = default
toc_depth = 3
max_image_width = 800
max_image_height = 1200
image_quality = 85

[debug]
# 调试配置
log_level = DEBUG  # DEBUG|INFO|WARNING|ERROR
log_format = json  # text|json
log_file = ./conversion.log
```

## 支持的模型

目前，PDF2Epub仅支持以下模型进行OCR处理：

- 阿里百炼的Qwen-vl-ocr

其他模型或API未经测试，可能需要修改代码才能正常工作。如果您成功使用其他模型，欢迎提交贡献。

## 许可证

本项目采用GNU通用公共许可证v3.0（GPLv3）进行许可。

这意味着您可以自由地：
- 使用本软件的完整源代码用于任何目的
- 修改源代码
- 分享原始或修改后的版本

但必须：
- 在分发时包含原始许可证和版权声明
- 声明您对源代码所做的任何更改
- 以相同的许可证（GPLv3）分发您的修改版本

完整的许可证文本可在[GNU网站](https://www.gnu.org/licenses/gpl-3.0.html)上找到。

## 项目结构

```
PDF2Epub/
├── config/                 # 配置文件目录
│   ├── settings.ini        # 主配置文件（不包含在Git仓库中）
│   └── settings.ini.template # 配置文件模板
├── core/                   # 核心代码
│   ├── epub_builder.py     # EPUB构建器
│   ├── ocr_processor.py    # OCR处理器
│   ├── pdf_parser.py       # PDF解析器
│   ├── text_cleaner.py     # 文本清洗器
│   └── page_processors/    # 页面处理器
│       ├── base.py         # 基础处理器
│       ├── cover.py        # 封面处理器
│       ├── footnote.py     # 脚注处理器
│       ├── table.py        # 表格处理器
│       └── toc.py          # 目录处理器
├── docs/                   # 文档
│   └── README_DEV.md       # 开发者文档
├── examples/               # 示例文件
├── samples/                # 示例PDF文件
├── scripts/                # 实用脚本
│   ├── convert_encoding.py # 编码转换脚本
│   └── run_tests.py        # 测试运行脚本
├── tests/                  # 测试代码
│   ├── test_conversion.py  # 转换测试脚本
│   ├── test_epub_builder.py # EPUB构建器测试
│   ├── test_ocr.py         # OCR处理器测试
│   └── ...                 # 其他测试文件
├── utils/                  # 工具函数
│   ├── cache.py            # 缓存工具
│   └── logger.py           # 日志工具
├── main.py                 # 主程序入口
├── api_client.py           # API客户端
├── requirements.txt        # 依赖项列表
└── README.md               # 项目说明
```

## 隐私和安全

- 配置文件`config/settings.ini`包含API密钥，不会被包含在Git仓库中
- 请不要将您的API密钥提交到公共仓库
- 使用`.gitignore`文件确保敏感信息不会被上传

## 贡献

欢迎提交问题和拉取请求！