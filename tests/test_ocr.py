#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试OCR处理器模块 - 使用大模型OCR功能
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import tempfile
import shutil
import numpy as np

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入被测试模块
from core.ocr_processor import OCRProcessor


class TestOCRProcessor(unittest.TestCase):
    """OCR处理器测试类 - 大模型OCR版本"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.test_dir = tempfile.mkdtemp()
        
        # 测试参数
        self.model_name = "qwen-vl-max-latest"
        self.timeout = 30
        self.retry_count = 3
        self.batch_size = 5
        
        # 测试图像数据 - 使用numpy数组模拟图像
        self.test_image = np.zeros((100, 100, 3), dtype=np.uint8)
    
    def tearDown(self):
        """测试后清理"""
        # 删除临时目录
        shutil.rmtree(self.test_dir)
    
    def test_init(self):
        """测试初始化"""
        processor = OCRProcessor(
            model_name=self.model_name,
            timeout=self.timeout,
            retry_count=self.retry_count,
            batch_size=self.batch_size
        )
        
        self.assertEqual(processor.model_name, self.model_name)
        self.assertEqual(processor.timeout, self.timeout)
        self.assertEqual(processor.retry_count, self.retry_count)
        self.assertEqual(processor.batch_size, self.batch_size)
    
    @patch('core.ocr_processor.OCRProcessor._call_llm_ocr')
    def test_ocr_page_success(self, mock_call_llm_ocr):
        """测试OCR处理单页成功"""
        # 设置模拟对象
        mock_call_llm_ocr.return_value = {
            "content": "图中显示一位年轻女孩在公园里与一只金毛犬玩耍。女孩穿着蓝色连衣裙，狗狗正在追逐一个黄色的飞盘。背景有绿树和长椅。",
            "analysis": {
                "objects": ["女孩", "金毛犬", "飞盘", "树", "长椅"],
                "actions": ["追逐", "玩耍"],
                "environment": "户外公园"
            }
        }
        
        # 初始化处理器
        processor = OCRProcessor(model_name=self.model_name)
        
        # 处理页面
        result = processor.ocr_page(self.test_image)
        
        # 验证
        self.assertIn("女孩", result["content"])
        self.assertIn("金毛犬", result["analysis"]["objects"])
        self.assertEqual(result["analysis"]["environment"], "户外公园")
        mock_call_llm_ocr.assert_called_once_with(self.test_image)
    
    @patch('core.ocr_processor.OCRProcessor._call_llm_ocr')
    @patch('time.sleep')  # 避免实际等待
    def test_ocr_page_retry(self, mock_sleep, mock_call_llm_ocr):
        """测试OCR处理重试"""
        # 设置模拟对象
        mock_call_llm_ocr.side_effect = [
            Exception("LLM服务暂时不可用"),  # 第一次调用失败
            {  # 第二次调用成功
                "text": "Retry successful",
                "confidence": 0.9
            }
        ]
        
        # 初始化处理器
        processor = OCRProcessor(
            model_name=self.model_name,
            retry_count=3
        )
        
        # 处理页面
        result = processor.ocr_page(self.test_image)
        
        # 验证
        self.assertEqual(result["text"], "Retry successful")
        self.assertEqual(result["confidence"], 0.9)
        self.assertEqual(mock_call_llm_ocr.call_count, 2)
        mock_sleep.assert_called_once()  # 验证重试等待
    
    @patch('core.ocr_processor.OCRProcessor._call_llm_ocr')
    @patch('time.sleep')  # 避免实际等待
    def test_ocr_page_max_retries_exceeded(self, mock_sleep, mock_call_llm_ocr):
        """测试OCR处理超过最大重试次数"""
        # 设置模拟对象 - 所有调用都失败
        mock_call_llm_ocr.side_effect = Exception("LLM服务不可用")
        
        # 初始化处理器
        processor = OCRProcessor(
            model_name=self.model_name,
            retry_count=3
        )
        
        # 验证异常
        with self.assertRaises(Exception) as context:
            processor.ocr_page(self.test_image)
        
        self.assertIn("LLM服务不可用", str(context.exception))
        self.assertEqual(mock_call_llm_ocr.call_count, 3)  # 验证重试次数
    
    @patch('cv2.cvtColor')
    @patch('cv2.threshold')
    @patch('cv2.GaussianBlur')
    @patch('core.ocr_processor.OCRProcessor._call_llm_ocr')
    def test_preprocess_image(self, mock_call_llm_ocr, mock_blur, mock_threshold, mock_cvtColor):
        """测试图像预处理"""
        # 设置模拟对象
        mock_call_llm_ocr.return_value = {"text": "Preprocessed text"}
        
        # 模拟OpenCV处理
        mock_cvtColor.return_value = "grayscale_image"
        mock_blur.return_value = "blurred_image"
        mock_threshold.return_value = (None, "binary_image")
        
        # 初始化处理器，启用预处理
        processor = OCRProcessor(
            model_name=self.model_name,
            preprocess=True
        )
        
        # 处理页面
        result = processor.ocr_page(self.test_image)
        
        # 验证
        self.assertEqual(result["text"], "Preprocessed text")
        mock_cvtColor.assert_called_once()  # 验证灰度转换
        mock_blur.assert_called_once()      # 验证高斯模糊
        mock_threshold.assert_called_once() # 验证二值化
        mock_call_llm_ocr.assert_called_once_with("binary_image")
    
    @patch('core.ocr_processor.OCRProcessor._call_llm_ocr')
    def test_batch_process(self, mock_call_llm_ocr):
        """测试批量处理"""
        # 设置模拟对象
        mock_call_llm_ocr.return_value = {"text": "Batch text"}
        
        # 初始化处理器
        processor = OCRProcessor(
            model_name=self.model_name,
            batch_size=3
        )
        
        # 准备测试数据
        images = [self.test_image] * 5  # 5个图像，需要2批处理
        
        # 批量处理
        results = processor.batch_process(images)
        
        # 验证
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertEqual(result["text"], "Batch text")
        
        # 验证LLM调用次数（应该是5次，因为我们模拟每个图像单独处理）
        self.assertEqual(mock_call_llm_ocr.call_count, 5)
    
    @patch('core.ocr_processor.OCRProcessor._call_llm_ocr')
    def test_handle_complex_layout(self, mock_call_llm_ocr):
        """测试处理复杂布局"""
        # 模拟LLM返回的复杂布局结果
        mock_call_llm_ocr.return_value = {
            "text": "Title\nParagraph 1\nTable: data1 data2\nFootnote",
            "confidence": 0.9,
            "layout": {
                "title": {"text": "Title", "bbox": [100, 50, 300, 80]},
                "paragraphs": [
                    {"text": "Paragraph 1", "bbox": [100, 100, 500, 150]}
                ],
                "tables": [
                    {
                        "bbox": [100, 200, 500, 250],
                        "cells": [
                            {"text": "data1", "bbox": [100, 200, 300, 250]},
                            {"text": "data2", "bbox": [300, 200, 500, 250]}
                        ]
                    }
                ],
                "footnotes": [
                    {"text": "Footnote", "bbox": [100, 300, 300, 320]}
                ]
            }
        }
        
        # 初始化处理器
        processor = OCRProcessor(model_name=self.model_name)
        
        # 处理页面
        result = processor.ocr_page(self.test_image)
        
        # 验证
        self.assertEqual(result["text"], "Title\nParagraph 1\nTable: data1 data2\nFootnote")
        self.assertEqual(result["confidence"], 0.9)
        self.assertTrue("layout" in result)
        self.assertEqual(result["layout"]["title"]["text"], "Title")
        self.assertEqual(len(result["layout"]["paragraphs"]), 1)
        self.assertEqual(len(result["layout"]["tables"]), 1)
        self.assertEqual(len(result["layout"]["tables"][0]["cells"]), 2)
    
    @patch('core.ocr_processor.OCRProcessor._call_llm_ocr')
    def test_language_detection(self, mock_call_llm_ocr):
        """测试语言检测"""
        # 模拟LLM返回的多语言结果
        mock_call_llm_ocr.return_value = {
            "text": "这是中文文本 This is English text",
            "confidence": 0.95,
            "language": {
                "zh": 0.6,  # 60% 中文
                "en": 0.4   # 40% 英文
            }
        }
        
        # 初始化处理器
        processor = OCRProcessor(model_name=self.model_name)
        
        # 处理页面
        result = processor.ocr_page(self.test_image)
        
        # 验证
        self.assertEqual(result["text"], "这是中文文本 This is English text")
        self.assertTrue("language" in result)
        self.assertEqual(result["language"]["zh"], 0.6)
        self.assertEqual(result["language"]["en"], 0.4)
        
        # 验证主要语言
        self.assertEqual(processor.detect_primary_language(result), "zh")

    def test_dashscope_ocr(self):
        """Test OCR with dashscope.aliyuncs.com API"""
        try:
            from openai import OpenAI
        except ImportError:
            self.skipTest("openai package not installed")

        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            self.skipTest("DASHSCOPE_API_KEY environment variable not set")

        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

        try:
            completion = client.chat.completions.create(
                model="qwen-vl-max-latest",
                messages=[
                    {
                        "role": "system",
                        "content": [{"type": "text", "text": "You are a helpful assistant."}],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg"
                                },
                            },
                            {"type": "text", "text": "图中描绘的是什么景象?"},
                        ],
                    },
                ],
            )

            self.assertIsNotNone(completion.choices[0].message.content)
            self.assertGreater(len(completion.choices[0].message.content), 0)

        except Exception as e:
            self.fail(f"dashscope.aliyuncs.com API call failed: {e}")


if __name__ == '__main__':
    unittest.main()
