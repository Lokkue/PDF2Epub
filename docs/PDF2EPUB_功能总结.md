# PDF2Epub 功能总结文档

## 项目概述

PDF2Epub 是一个将PDF文件转换为EPUB电子书的工具，特别优化了对中文学术文献的处理。

## 核心功能

### 1. 基础转换功能
- PDF页面提取与处理
- 文本识别（支持本地和OCR API）
- EPUB生成与打包

### 2. 文本清理功能增强 (v0.2.0)

#### 页码和章节标题移除
- 功能：自动检测和移除页面左上角的页码和章节标题
- 支持格式：
  - 数字+章节名：如 "2 海德格尔《哲学献文》导论"
  - 罗马数字+章节名：如 "IV 存在与时间"
  - 字母+章节名：如 "A 基础概念"
  - 章节标题+页码：如 "第一章 存在与时间 23"
- 实现方法：使用正则表达式匹配模式，智能识别标题结束位置

#### 脚注标记格式化
- 功能：将常见脚注标记转换为HTML上标格式
- 支持格式：
  - 圆圈数字：①②③④⑤⑥⑦⑧⑨⑩
  - 方括号数字：[1], [2], [3]
  - 圆括号数字：(1), (2), (3)
  - 星号数字：*1, *2, *3
  - 其他特殊符号：†1, †2, †3
- 实现方法：使用字符映射和正则表达式替换，将脚注区域格式化为有序列表

### 3. 交互式界面优化 (v0.2.0)

#### 用户取消操作处理
- 功能：优雅处理用户取消选择和键盘中断
- 实现：检查inquirer.prompt返回值，捕获KeyboardInterrupt异常
- 效果：显示友好提示信息，安全退出程序

#### 进度条显示优化
- 功能：简化信息显示，提供更清晰的转换进度
- 改进：
  - 移除每页处理的单独日志输出
  - 在进度条描述中集成页码和token使用信息
  - 格式："转换进度 (页 X/Y, 已用tokens: Z)"

#### 日志级别统一
- 功能：统一日志级别描述，提供直观的选择
- 级别：
  - 基础级别（只显示警告和错误）
  - 信息级别（显示处理进度和基本统计信息）
  - 开发级别（显示详细技术信息）
  - 调试模式（最详细的诊断信息）

## 技术实现

### 文本清理关键代码

```python
# 页码和章节标题移除
def remove_page_headers(self, text):
    paragraphs = text.split('\n\n')
    cleaned_paragraphs = []
    
    for para in paragraphs:
        # 检测模式: 数字 + 空格 + 章节名
        if re.match(r'^\d+\s+[\u4e00-\u9fa5《》""''（）\[\]]+.*?[》」"）\]\.\。]', para):
            match = re.search(r'[。？！\.]\s*', para)
            if match:
                end_pos = match.end()
                if end_pos < len(para):
                    para = para[end_pos:].strip()
                else:
                    continue
        
        if para.strip():
            cleaned_paragraphs.append(para)
    
    return '\n\n'.join(cleaned_paragraphs)

# 脚注标记格式化
def format_footnote_markers(self, text):
    # 处理圆圈数字脚注标记
    circle_numbers = {
        '①': '1', '②': '2', '③': '3', '④': '4', '⑤': '5',
        '⑥': '6', '⑦': '7', '⑧': '8', '⑨': '9', '⑩': '10'
    }
    
    for circle, number in circle_numbers.items():
        text = text.replace(circle, f'<sup>{number}</sup>')
    
    # 处理其他脚注格式
    footnote_patterns = [
        (r'\[(\d+)\]', r'<sup>\1</sup>'),  # [1] -> <sup>1</sup>
        (r'\((\d+)\)', r'<sup>\1</sup>'),  # (1) -> <sup>1</sup>
    ]
    
    for pattern, replacement in footnote_patterns:
        text = re.sub(pattern, replacement, text)
    
    return text
```

### 交互式界面关键代码

```python
# 用户取消操作处理
def select_pdf_file(pdf_files):
    questions = [
        inquirer.List('pdf_file',
                     message='选择要转换的PDF文件',
                     choices=pdf_files)
    ]
    
    answers = inquirer.prompt(questions)
    
    if answers is None:
        print("\n操作已取消。")
        sys.exit(0)
        
    return answers['pdf_file']

# 进度条显示优化
def process_pdf(input_path, output_path, max_pages=None, verbose=0, debug=False):
    # 创建进度条
    with tqdm(total=total_pages, desc=f"📊 转换进度 (页 0/{total_pages})") as pbar:
        for page_num, page in enumerate(pdf_document, 1):
            # 更新进度条描述
            if use_ocr:
                pbar.set_description(f"📊 转换进度 (页 {page_num}/{total_pages}, 已用tokens: {token_usage})")
            else:
                pbar.set_description(f"📊 转换进度 (页 {page_num}/{total_pages})")
            
            # 处理页面...
            pbar.update(1)
```

## 设计决策

1. **模块化设计**：将不同功能拆分为独立方法，便于维护和扩展
2. **正则表达式优化**：精心设计的正则表达式，平衡匹配精度和性能
3. **HTML标准兼容**：使用标准HTML元素确保在各种EPUB阅读器中正确显示
4. **防御性编程**：在所有用户交互点添加错误处理，确保程序不会因用户操作而崩溃
5. **简洁界面设计**：减少不必要的输出，让用户专注于重要信息

## 使用建议

对于学术文献处理，建议使用以下命令：
```bash
python main.py input.pdf -o output.epub --academic-mode
```

## 未来改进方向

1. **文本清理**：
   - 添加更多脚注格式识别模式
   - 实现脚注内容与引用的自动链接
   - 优化对多语言文献的支持
   - 添加对数学公式的特殊处理

2. **交互式界面**：
   - 添加配置保存功能，记住用户的偏好设置
   - 实现批处理模式，允许用户一次选择多个文件进行转换
   - 添加转换后的预览功能
   - 提供更详细的错误诊断和解决建议
