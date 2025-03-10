#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试EPUB构建器模块
"""

import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import tempfile
import shutil
import zipfile
import xml.etree.ElementTree as ET

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入被测试模块
from core.epub_builder import EPUBBuilder


class TestEPUBBuilder(unittest.TestCase):
    """EPUB构建器测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.test_dir = tempfile.mkdtemp()
        self.output_file = os.path.join(self.test_dir, "test_output.epub")
        
        # 测试参数
        self.format = "epub"
        self.css_template = "default"
        self.toc_depth = 3
        self.max_image_width = 800
        self.max_image_height = 1200
        self.image_quality = 85
        
        # 测试内容
        self.test_title = "测试书籍"
        self.test_author = "测试作者"
        self.test_chapters = [
            {
                "title": "第一章",
                "content": "<p>这是第一章的内容。</p>",
                "level": 1
            },
            {
                "title": "1.1 小节",
                "content": "<p>这是小节的内容。</p>",
                "level": 2
            },
            {
                "title": "第二章",
                "content": "<p>这是第二章的内容。</p>",
                "level": 1
            }
        ]
    
    def tearDown(self):
        """测试后清理"""
        # 删除临时目录
        shutil.rmtree(self.test_dir)
    
    def test_init(self):
        """测试初始化"""
        builder = EPUBBuilder(
            output_file=self.output_file,
            format=self.format,
            css_template=self.css_template,
            toc_depth=self.toc_depth,
            max_image_width=self.max_image_width,
            max_image_height=self.max_image_height,
            image_quality=self.image_quality
        )
        
        self.assertEqual(builder.output_file, self.output_file)
        self.assertEqual(builder.format, self.format)
        self.assertEqual(builder.css_template, self.css_template)
        self.assertEqual(builder.toc_depth, self.toc_depth)
        self.assertEqual(builder.max_image_width, self.max_image_width)
        self.assertEqual(builder.max_image_height, self.max_image_height)
        self.assertEqual(builder.image_quality, self.image_quality)
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_css_template(self, mock_file, mock_exists):
        """测试加载CSS模板"""
        # 模拟CSS模板文件存在
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "body { font-family: serif; }"
        
        builder = EPUBBuilder(
            output_file=self.output_file,
            css_template="default"
        )
        
        css = builder.load_css_template()
        self.assertEqual(css, "body { font-family: serif; }")
        mock_file.assert_called_once()
    
    @patch('os.path.exists')
    def test_load_css_template_fallback(self, mock_exists):
        """测试加载CSS模板失败时的回退"""
        # 模拟CSS模板文件不存在
        mock_exists.return_value = False
        
        builder = EPUBBuilder(
            output_file=self.output_file,
            css_template="non_existent"
        )
        
        css = builder.load_css_template()
        # 验证是否使用了默认CSS
        self.assertIn("body", css)
        self.assertIn("font-family", css)
    
    @patch('zipfile.ZipFile')
    def test_create_epub_structure(self, mock_zipfile):
        """测试创建EPUB结构"""
        # 设置模拟对象
        mock_zip = MagicMock()
        mock_zipfile.return_value = mock_zip
        mock_zip.__enter__.return_value = mock_zip
        
        builder = EPUBBuilder(output_file=self.output_file)
        builder.create_epub_structure()
        
        # 验证是否创建了必要的文件
        mock_zip.writestr.assert_any_call("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        mock_zip.writestr.assert_any_call("META-INF/container.xml", unittest.mock.ANY)
        mock_zip.writestr.assert_any_call("OEBPS/styles/main.css", unittest.mock.ANY)
    
    def test_add_chapter(self):
        """测试添加章节"""
        builder = EPUBBuilder(output_file=self.output_file)
        
        # 添加章节
        builder.add_chapter("测试章节", "<p>章节内容</p>", 1)
        
        # 验证章节是否被添加
        self.assertEqual(len(builder.chapters), 1)
        self.assertEqual(builder.chapters[0]["title"], "测试章节")
        self.assertEqual(builder.chapters[0]["content"], "<p>章节内容</p>")
        self.assertEqual(builder.chapters[0]["level"], 1)
    
    @patch('zipfile.ZipFile')
    def test_add_image(self, mock_zipfile):
        """测试添加图像"""
        # 设置模拟对象
        mock_zip = MagicMock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip
        
        builder = EPUBBuilder(output_file=self.output_file)
        builder.epub = mock_zip
        
        # 测试图像数据
        image_data = b'test_image_data'
        
        # 添加图像
        image_path = builder.add_image(image_data, "image/jpeg")
        
        # 验证图像是否被添加
        self.assertTrue(image_path.startswith("OEBPS/images/"))
        self.assertTrue(image_path.endswith(".jpg"))
        mock_zip.writestr.assert_called_once_with(image_path, image_data)
    
    @patch('PIL.Image.open')
    @patch('io.BytesIO')
    def test_resize_image(self, mock_bytesio, mock_image_open):
        """测试调整图像大小"""
        # 设置模拟对象
        mock_image = MagicMock()
        mock_image.size = (2000, 1500)  # 原始尺寸
        mock_image_open.return_value = mock_image
        
        mock_bytesio_instance = MagicMock()
        mock_bytesio.return_value = mock_bytesio_instance
        
        builder = EPUBBuilder(
            output_file=self.output_file,
            max_image_width=800,
            max_image_height=600
        )
        
        # 调整图像大小
        builder.resize_image(b'test_image_data')
        
        # 验证图像是否被调整大小
        mock_image.thumbnail.assert_called_once_with((800, 600))
        mock_image.save.assert_called_once()
    
    @patch('zipfile.ZipFile')
    def test_generate_toc(self, mock_zipfile):
        """测试生成目录"""
        # 设置模拟对象
        mock_zip = MagicMock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip
        
        builder = EPUBBuilder(output_file=self.output_file, toc_depth=3)
        builder.epub = mock_zip
        
        # 添加测试章节
        for chapter in self.test_chapters:
            builder.add_chapter(chapter["title"], chapter["content"], chapter["level"])
        
        # 生成目录
        toc_ncx = builder.generate_toc()
        
        # 验证目录内容
        self.assertIn("第一章", toc_ncx)
        self.assertIn("1.1 小节", toc_ncx)
        self.assertIn("第二章", toc_ncx)
        self.assertIn("<navMap>", toc_ncx)
        self.assertIn("<navPoint", toc_ncx)
    
    @patch('zipfile.ZipFile')
    def test_generate_content_opf(self, mock_zipfile):
        """测试生成content.opf文件"""
        # 设置模拟对象
        mock_zip = MagicMock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip
        
        builder = EPUBBuilder(output_file=self.output_file)
        builder.epub = mock_zip
        builder.title = self.test_title
        builder.author = self.test_author
        
        # 添加测试章节
        for chapter in self.test_chapters:
            builder.add_chapter(chapter["title"], chapter["content"], chapter["level"])
        
        # 生成content.opf
        content_opf = builder.generate_content_opf()
        
        # 验证content.opf内容
        self.assertIn(self.test_title, content_opf)
        self.assertIn(self.test_author, content_opf)
        self.assertIn("<manifest>", content_opf)
        self.assertIn("<spine>", content_opf)
        self.assertIn("chapter_", content_opf)
    
    @patch('subprocess.run')
    def test_convert_to_mobi(self, mock_run):
        """测试转换为MOBI格式"""
        # 设置模拟对象
        mock_run.return_value.returncode = 0
        
        builder = EPUBBuilder(
            output_file=self.output_file,
            format="mobi"
        )
        
        # 模拟EPUB文件已创建
        with open(self.output_file, 'w') as f:
            f.write("dummy epub content")
        
        # 转换为MOBI
        mobi_file = builder.convert_to_mobi()
        
        # 验证转换命令
        mock_run.assert_called_once()
        self.assertTrue(mobi_file.endswith(".mobi"))
    
    @patch('zipfile.ZipFile')
    @patch('subprocess.run')
    def test_build_epub(self, mock_run, mock_zipfile):
        """测试构建EPUB"""
        # 设置模拟对象
        mock_zip = MagicMock()
        mock_zipfile.return_value = mock_zip
        mock_zip.__enter__.return_value = mock_zip
        
        builder = EPUBBuilder(output_file=self.output_file)
        
        # 设置元数据
        builder.set_metadata(self.test_title, self.test_author)
        
        # 添加测试章节
        for chapter in self.test_chapters:
            builder.add_chapter(chapter["title"], chapter["content"], chapter["level"])
        
        # 构建EPUB
        result = builder.build()
        
        # 验证结果
        self.assertEqual(result, self.output_file)
        mock_zip.writestr.assert_called()  # 验证文件写入
    
    @patch('zipfile.ZipFile')
    @patch('subprocess.run')
    def test_build_mobi(self, mock_run, mock_zipfile):
        """测试构建MOBI"""
        # 设置模拟对象
        mock_zip = MagicMock()
        mock_zipfile.return_value = mock_zip
        mock_zip.__enter__.return_value = mock_zip
        mock_run.return_value.returncode = 0
        
        builder = EPUBBuilder(
            output_file=self.output_file,
            format="mobi"
        )
        
        # 设置元数据
        builder.set_metadata(self.test_title, self.test_author)
        
        # 添加测试章节
        for chapter in self.test_chapters:
            builder.add_chapter(chapter["title"], chapter["content"], chapter["level"])
        
        # 构建MOBI
        result = builder.build()
        
        # 验证结果
        self.assertTrue(result.endswith(".mobi"))
        mock_zip.writestr.assert_called()  # 验证EPUB文件写入
        mock_run.assert_called_once()      # 验证转换命令


if __name__ == '__main__':
    unittest.main()
