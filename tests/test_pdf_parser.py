#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试PDF解析器模块
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import shutil
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入被测试模块
from core.pdf_parser import PDFParser


class TestPDFParser(unittest.TestCase):
    """PDF解析器测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.test_dir = tempfile.mkdtemp()
        
        # 测试文件路径
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
        self.simple_pdf = os.path.join(self.fixtures_dir, 'simple.pdf')
        self.scanned_pdf = os.path.join(self.fixtures_dir, 'scanned.pdf')
        self.corrupted_pdf = os.path.join(self.fixtures_dir, 'corrupted.pdf')
    
    def tearDown(self):
        """测试后清理"""
        # 删除临时目录
        shutil.rmtree(self.test_dir)
    
    @patch('fitz.open')
    def test_init_with_valid_file(self, mock_open):
        """测试使用有效文件初始化"""
        # 设置模拟对象
        mock_doc = MagicMock()
        mock_doc.page_count = 10
        mock_open.return_value = mock_doc
        
        # 初始化解析器
        parser = PDFParser(self.simple_pdf)
        
        # 验证
        mock_open.assert_called_once_with(self.simple_pdf)
        self.assertEqual(parser.get_page_count(), 10)
    
    @patch('fitz.open')
    def test_init_with_max_pages(self, mock_open):
        """测试使用最大页数限制初始化"""
        # 设置模拟对象
        mock_doc = MagicMock()
        mock_doc.page_count = 10
        mock_open.return_value = mock_doc
        
        # 初始化解析器，限制5页
        parser = PDFParser(self.simple_pdf, max_pages=5)
        
        # 验证
        self.assertEqual(parser.get_page_count(), 5)
    
    @patch('fitz.open')
    def test_get_pages(self, mock_open):
        """测试获取页面"""
        # 设置模拟对象
        mock_doc = MagicMock()
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()
        mock_doc.page_count = 2
        mock_doc.__getitem__.side_effect = [mock_page1, mock_page2]
        mock_open.return_value = mock_doc
        
        # 初始化解析器
        parser = PDFParser(self.simple_pdf)
        
        # 获取页面
        pages = list(parser.get_pages())
        
        # 验证
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0], mock_page1)
        self.assertEqual(pages[1], mock_page2)
    
    @patch('fitz.open')
    def test_has_text_layer(self, mock_open):
        """测试检测文本层"""
        # 设置模拟对象
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "This is a test"
        mock_doc.__getitem__.return_value = mock_page
        mock_open.return_value = mock_doc
        
        # 初始化解析器
        parser = PDFParser(self.simple_pdf)
        
        # 检测文本层
        has_text = parser.has_text_layer(0)
        
        # 验证
        self.assertTrue(has_text)
        mock_page.get_text.assert_called_once()
    
    @patch('fitz.open')
    def test_has_no_text_layer(self, mock_open):
        """测试检测无文本层"""
        # 设置模拟对象
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""
        mock_doc.__getitem__.return_value = mock_page
        mock_open.return_value = mock_doc
        
        # 初始化解析器
        parser = PDFParser(self.scanned_pdf)
        
        # 检测文本层
        has_text = parser.has_text_layer(0)
        
        # 验证
        self.assertFalse(has_text)
    
    @patch('fitz.open')
    def test_extract_text(self, mock_open):
        """测试提取文本"""
        # 设置模拟对象
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "This is a test"
        mock_doc.__getitem__.return_value = mock_page
        mock_open.return_value = mock_doc
        
        # 初始化解析器
        parser = PDFParser(self.simple_pdf)
        
        # 提取文本
        text = parser.extract_text(0)
        
        # 验证
        self.assertEqual(text, "This is a test")
        mock_page.get_text.assert_called_once()
    
    @patch('fitz.open')
    @patch('cv2.cvtColor')
    @patch('cv2.imencode')
    def test_extract_image(self, mock_imencode, mock_cvtColor, mock_open):
        """测试提取图像"""
        # 设置模拟对象
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_pix = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix
        mock_pix.samples = b'image_data'
        mock_pix.width = 100
        mock_pix.height = 200
        mock_doc.__getitem__.return_value = mock_page
        mock_open.return_value = mock_doc
        
        # 模拟OpenCV处理
        mock_cvtColor.return_value = "converted_image"
        mock_imencode.return_value = (True, b'encoded_image')
        
        # 初始化解析器
        parser = PDFParser(self.simple_pdf)
        
        # 提取图像
        image = parser.extract_image(0)
        
        # 验证
        self.assertEqual(image, b'encoded_image')
        mock_page.get_pixmap.assert_called_once()
    
    @patch('fitz.open', side_effect=Exception("File not found"))
    def test_init_with_invalid_file(self, mock_open):
        """测试使用无效文件初始化"""
        # 验证异常
        with self.assertRaises(Exception):
            PDFParser("non_existent.pdf")
    
    @patch('fitz.open')
    def test_get_metadata(self, mock_open):
        """测试获取元数据"""
        # 设置模拟对象
        mock_doc = MagicMock()
        mock_doc.metadata = {
            'title': 'Test Document',
            'author': 'Test Author',
            'subject': 'Test Subject',
            'keywords': 'test, pdf, parser',
            'creator': 'Test Creator',
            'producer': 'Test Producer'
        }
        mock_open.return_value = mock_doc
        
        # 初始化解析器
        parser = PDFParser(self.simple_pdf)
        
        # 获取元数据
        metadata = parser.get_metadata()
        
        # 验证
        self.assertEqual(metadata['title'], 'Test Document')
        self.assertEqual(metadata['author'], 'Test Author')


if __name__ == '__main__':
    unittest.main()
