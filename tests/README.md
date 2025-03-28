# Toepub 测试套件

本目录包含 Toepub 项目的测试套件，用于验证各个模块的功能正确性。

## 测试结构

`
tests/
 __init__.py          # 测试包初始化文件
 conftest.py          # Pytest配置和共享fixture
 fixtures/            # 测试数据文件
    README.md        # 测试数据说明
 test_pdf_parser.py   # PDF解析器测试
 test_ocr.py          # OCR处理器测试
 test_text_cleaner.py # 文本清洗器测试
 test_epub_builder.py # EPUB构建器测试
 test_cache.py        # 缓存管理器测试
 test_page_processors.py # 页面处理器测试
`

## 运行测试

### 运行所有测试

`ash
pytest
`

### 运行特定模块测试

`ash
pytest tests/test_pdf_parser.py
`

### 运行带标记的测试

`ash
# 运行单元测试
pytest -m unit

# 跳过耗时测试
pytest -m \
not
slow\
`

### 生成覆盖率报告

`ash
pytest --cov=core --cov-report=html:coverage_report
`

## 测试标记

- @pytest.mark.slow: 标记耗时较长的测试
- @pytest.mark.integration: 标记集成测试
- @pytest.mark.unit: 标记单元测试
- @pytest.mark.api: 标记需要API访问的测试

## 共享Fixture

测试套件提供了多个共享的fixture，可在测试中直接使用：

- 	est_dir: 创建临时测试目录
- sample_pdf_path: 样本PDF文件路径
- sample_image: 样本图像（NumPy数组）
- sample_image_bytes: 样本图像（字节流）
- sample_text: 样本文本
- sample_toc_text: 样本目录文本
- sample_footnote_text: 样本脚注文本
- sample_table_text: 样本表格文本
- sample_metadata: 样本元数据
- mock_llm_ocr_response: 模拟大模型OCR响应
- mock_db_connection: 模拟数据库连接

## 添加新测试

1. 创建新的测试文件，命名为 	est_*.py
2. 导入必要的模块和被测试的组件
3. 创建测试类，命名为 Test*
4. 添加测试方法，命名为 	est_*
5. 使用断言验证结果

