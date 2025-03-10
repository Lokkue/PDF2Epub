#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pytest配置文件
"""

import os
import sys
import pytest
import tempfile
import shutil
import numpy as np
from PIL import Image
import io

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture(scope="session")
def test_dir():
    """创建测试临时目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_pdf_path(test_dir):
    """创建一个简单的PDF文件路径"""
    return os.path.join(test_dir, "sample.pdf")


@pytest.fixture
def sample_image():
    """创建一个样本图像"""
    # 创建一个简单的图像
    img = np.zeros((300, 200, 3), dtype=np.uint8)
    # 添加一些文本区域（白色矩形）
    img[50:100, 50:150] = 255
    img[150:200, 50:150] = 255
    return img


@pytest.fixture
def sample_image_bytes(sample_image):
    """将样本图像转换为字节流"""
    # 将NumPy数组转换为PIL图像
    pil_img = Image.fromarray(sample_image)
    # 将PIL图像转换为字节流
    img_byte_arr = io.BytesIO()
    pil_img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()


@pytest.fixture
def sample_text():
    """创建一个样本文本"""
    return """这是一个测试文本。
它包含多个段落。

这是第二个段落，用于测试文本处理功能。
"""


@pytest.fixture
def sample_toc_text():
    """创建一个样本目录文本"""
    return """目录

第一章 引言..........................1
    1.1 背景........................2
    1.2 研究意义....................3
第二章 文献综述......................4
    2.1 相关理论....................5
    2.2 研究现状....................6
第三章 方法..........................7
结论.................................8
参考文献.............................9
"""


@pytest.fixture
def sample_footnote_text():
    """创建一个包含脚注的样本文本"""
    return """这是正文内容，其中包含一个脚注引用※1。
    
※1 这是脚注内容，提供了额外的解释和参考信息。"""


@pytest.fixture
def sample_table_text():
    """创建一个样本表格文本"""
    return """项目 | 数量 | 单价
商品A | 10 | 100
商品B | 20 | 200"""


@pytest.fixture
def sample_metadata():
    """创建样本元数据"""
    return {
        "title": "测试文档",
        "author": "测试作者",
        "publisher": "测试出版社",
        "date": "2025-03-10",
        "language": "zh-CN",
        "pages": 100
    }


@pytest.fixture
def mock_llm_ocr_response():
    """模拟大模型OCR响应"""
    return {
        "text": "这是OCR识别的文本内容",
        "confidence": 0.95,
        "blocks": [
            {"text": "这是", "bbox": [10, 10, 50, 30]},
            {"text": "OCR识别的", "bbox": [60, 10, 150, 30]},
            {"text": "文本内容", "bbox": [10, 40, 100, 60]}
        ],
        "language": {
            "zh": 1.0
        }
    }


@pytest.fixture
def mock_db_connection():
    """模拟数据库连接"""
    import sqlite3
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()
