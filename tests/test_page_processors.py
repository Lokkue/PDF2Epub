#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试页面处理器模块
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import sys
import numpy as np
import cv2

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入被测试模块
from core.page_processors.base import BaseProcessor
from core.page_processors.cover import CoverProcessor
from core.page_processors.toc import TOCProcessor
from core.page_processors.footnote import FootnoteProcessor
from core.page_processors.table import TableProcessor


class TestBaseProcessor(unittest.TestCase):
    """基础处理器测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建测试图像
        self.test_image = np.zeros((300, 200, 3), dtype=np.uint8)
        
        # 创建测试文本
        self.test_text = "这是测试文本内容"
        
        # 初始化基础处理器
        self.processor = BaseProcessor(self.test_image, self.test_text)
    
    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.processor.image.shape, self.test_image.shape)
        self.assertEqual(self.processor.text, self.test_text)
    
    def test_detect(self):
        """测试检测方法"""
        # 基类的detect方法应该返回0（不匹配任何页面类型）
        confidence = BaseProcessor.detect(self.test_image, self.test_text)
        self.assertEqual(confidence, 0.0)
    
    def test_process(self):
        """测试处理方法"""
        # 基类的process方法应该返回原始文本
        processed_text = self.processor.process()
        self.assertEqual(processed_text, self.test_text)
    
    def test_clean_text(self):
        """测试文本清洗方法"""
        # 模拟文本清洗
        dirty_text = "这是\n需要清洗的\n文本"
        self.processor.text = dirty_text
        
        # 调用清洗方法
        with patch('core.text_cleaner.TextCleaner.clean') as mock_clean:
            mock_clean.return_value = "这是需要清洗的文本"
            cleaned_text = self.processor.clean_text()
        
        # 验证结果
        self.assertEqual(cleaned_text, "这是需要清洗的文本")


class TestCoverProcessor(unittest.TestCase):
    """封面处理器测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建测试图像 - 模拟封面（大图像区域）
        self.test_image = np.zeros((600, 400, 3), dtype=np.uint8)
        # 添加一个大矩形区域模拟封面图像
        cv2.rectangle(self.test_image, (50, 50), (350, 550), (255, 255, 255), -1)
        
        # 创建测试文本
        self.test_text = "书名\n作者名"
        
        # 初始化封面处理器
        self.processor = CoverProcessor(self.test_image, self.test_text)
    
    def test_detect_cover(self):
        """测试检测封面"""
        # 封面应该有较高的图像占比和较少的文本
        confidence = CoverProcessor.detect(self.test_image, self.test_text)
        self.assertGreater(confidence, 0.5)  # 封面检测置信度应该较高
    
    def test_detect_not_cover(self):
        """测试检测非封面"""
        # 创建一个有大量文本的图像，不太可能是封面
        text_heavy_image = np.zeros((600, 400, 3), dtype=np.uint8)
        text_heavy_text = """这是一个包含大量文本的页面，
        有很多段落和内容，
        不太可能是封面页。
        这里有更多的文本内容，
        增加文本的数量，
        使其看起来像正文页面。"""
        
        confidence = CoverProcessor.detect(text_heavy_image, text_heavy_text)
        self.assertLess(confidence, 0.5)  # 非封面检测置信度应该较低
    
    def test_process_cover(self):
        """测试处理封面"""
        # 处理封面应该返回HTML格式的封面内容
        html = self.processor.process()
        
        # 验证HTML包含封面标记和内容
        self.assertIn("<div class=\"cover\">", html)
        self.assertIn("书名", html)
        self.assertIn("作者名", html)


class TestTOCProcessor(unittest.TestCase):
    """目录处理器测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建测试图像
        self.test_image = np.zeros((600, 400, 3), dtype=np.uint8)
        
        # 创建测试目录文本
        self.test_toc_text = """目录

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
        
        # 初始化目录处理器
        self.processor = TOCProcessor(self.test_image, self.test_toc_text)
    
    def test_detect_toc(self):
        """测试检测目录"""
        # 包含"目录"关键词和页码模式的文本应该被识别为目录
        confidence = TOCProcessor.detect(self.test_image, self.test_toc_text)
        self.assertGreater(confidence, 0.5)  # 目录检测置信度应该较高
    
    def test_detect_not_toc(self):
        """测试检测非目录"""
        # 创建一个普通文本，不是目录
        normal_text = """这是一个普通的文本页面，
        包含正文内容，
        没有目录结构和页码模式。
        这只是一些普通的段落文本。"""
        
        confidence = TOCProcessor.detect(self.test_image, normal_text)
        self.assertLess(confidence, 0.5)  # 非目录检测置信度应该较低
    
    def test_process_toc(self):
        """测试处理目录"""
        # 处理目录应该返回HTML格式的目录内容
        html = self.processor.process()
        
        # 验证HTML包含目录标记和内容
        self.assertIn("<nav class=\"toc\">", html)
        self.assertIn("<li>", html)
        self.assertIn("第一章 引言", html)
        self.assertIn("1.1 背景", html)
    
    def test_extract_toc_entries(self):
        """测试提取目录条目"""
        # 提取目录条目
        entries = self.processor.extract_toc_entries()
        
        # 验证提取的条目
        self.assertEqual(len(entries), 8)  # 应该有8个条目
        self.assertEqual(entries[0]["title"], "第一章 引言")
        self.assertEqual(entries[0]["page"], 1)
        self.assertEqual(entries[0]["level"], 1)
        self.assertEqual(entries[1]["title"], "1.1 背景")
        self.assertEqual(entries[1]["page"], 2)
        self.assertEqual(entries[1]["level"], 2)


class TestFootnoteProcessor(unittest.TestCase):
    """脚注处理器测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建测试图像
        self.test_image = np.zeros((600, 400, 3), dtype=np.uint8)
        
        # 创建测试文本（包含脚注）
        self.test_footnote_text = """这是正文内容，其中包含一个脚注引用※1。
        
※1 这是脚注内容，提供了额外的解释和参考信息。"""
        
        # 初始化脚注处理器
        self.processor = FootnoteProcessor(self.test_image, self.test_footnote_text)
    
    def test_detect_footnote(self):
        """测试检测脚注"""
        # 包含脚注标记和脚注内容的文本应该被识别为包含脚注
        confidence = FootnoteProcessor.detect(self.test_image, self.test_footnote_text)
        self.assertGreater(confidence, 0.3)  # 脚注检测置信度应该较高

    def test_detect_not_footnote(self):
        """测试检测非脚注"""
        # 创建一个没有脚注的普通文本
        normal_text = """这是一个普通的文本页面，
        没有脚注标记和脚注内容。
        只是一些普通的段落文本。"""
        
        confidence = FootnoteProcessor.detect(self.test_image, normal_text)
        self.assertLess(confidence, 0.5)  # 非脚注检测置信度应该较低
    
    def test_process_footnote(self):
        """测试处理脚注"""
        # 处理脚注应该返回HTML格式的内容，包含脚注链接
        html = self.processor.process()
        
        # 验证HTML包含脚注标记和内容
        self.assertIn("<a href=\"#footnote-1\" id=\"footnote-ref-1\" class=\"footnote-ref\">", html)
        self.assertIn("<aside id=\"footnote-1\" class=\"footnote\">", html)
        self.assertIn("这是脚注内容", html)
    
    def test_extract_footnotes(self):
        """测试提取脚注"""
        # 提取脚注
        footnotes = self.processor.extract_footnotes()
        
        # 验证提取的脚注
        self.assertEqual(len(footnotes), 1)  # 应该有1个脚注
        self.assertEqual(footnotes[0]["marker"], "※1")
        self.assertEqual(footnotes[0]["content"], "这是脚注内容，提供了额外的解释和参考信息。")


class TestTableProcessor(unittest.TestCase):
    """表格处理器测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建测试图像 - 模拟表格（网格线）
        self.test_image = np.zeros((600, 400, 3), dtype=np.uint8)
        # 添加水平线
        cv2.line(self.test_image, (50, 100), (350, 100), (255, 255, 255), 2)
        cv2.line(self.test_image, (50, 200), (350, 200), (255, 255, 255), 2)
        cv2.line(self.test_image, (50, 300), (350, 300), (255, 255, 255), 2)
        # 添加垂直线
        cv2.line(self.test_image, (50, 100), (50, 300), (255, 255, 255), 2)
        cv2.line(self.test_image, (200, 100), (200, 300), (255, 255, 255), 2)
        cv2.line(self.test_image, (350, 100), (350, 300), (255, 255, 255), 2)
        
        # 创建测试表格文本
        self.test_table_text = """项目 | 数量 | 单价
商品A | 10 | 100
商品B | 20 | 200"""
        
        # 初始化表格处理器
        self.processor = TableProcessor(self.test_image, self.test_table_text)
    
    def test_detect_table(self):
        """测试检测表格"""
        # 包含网格线的图像和表格式文本应该被识别为表格
        confidence = TableProcessor.detect(self.test_image, self.test_table_text)
        self.assertGreater(confidence, 0.5)  # 表格检测置信度应该较高
    
    def test_detect_not_table(self):
        """测试检测非表格"""
        # 创建一个没有网格线的图像和普通文本
        normal_image = np.zeros((600, 400, 3), dtype=np.uint8)
        normal_text = """这是一个普通的文本页面，
        没有表格结构。
        只是一些普通的段落文本。"""
        
        confidence = TableProcessor.detect(normal_image, normal_text)
        self.assertLess(confidence, 0.5)  # 非表格检测置信度应该较低
    
    def test_process_table(self):
        """测试处理表格"""
        # 处理表格应该返回HTML格式的表格
        html = self.processor.process()
        
        # 验证HTML包含表格标记和内容
        self.assertIn("<table", html)
        self.assertIn("<tr", html)
        self.assertIn("<td", html)
        self.assertIn("项目", html)
        self.assertIn("数量", html)
        self.assertIn("商品A", html)

    def detect_table_structure(self):
        """测试检测表格结构"""
        # 这里应该实现检测表格结构的逻辑
        # 为了测试，我们简单地返回一个固定的行列数
        return 3, 3

    def extract_cells(self):
        """测试提取单元格"""
        # 这里应该实现提取单元格的逻辑
        # 为了测试，我们简单地返回一个空的单元格列表
        return []


if __name__ == '__main__':
    unittest.main()
