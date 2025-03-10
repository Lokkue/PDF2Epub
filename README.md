# PDF2Epub - PDF转EPUB工具

PDF2Epub是一个基于大模型OCR功能的PDF转EPUB工具，专为中文PDF文档优化，能够智能识别文档结构，包括封面、目录、章节、表格等，并生成结构良好的电子书。

**当前版本：v0.1.0**

> **注意：** 目前仅支持阿里百炼的Qwen-vl-max模型进行OCR处理，其他模型或API未经测试。

## 功能特点

- 使用大模型OCR技术，提供高精度的文本识别
- 智能识别文档结构（封面、目录、章节、表格等）
- 支持输出EPUB格式
- 自动处理图像和表格
- 支持断点续传和缓存
- 可定制的样式和排版

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

- 阿里百炼的Qwen-vl-max

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