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
import configparser

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
        self.model_name = "qwen-vl-max"
        self.timeout = 30
        self.retry_count = 3
        self.batch_size = 5
        
        # 创建测试配置
        self.config = configparser.ConfigParser()
        self.config['ocr'] = {
            'model_name': self.model_name,
            'timeout': str(self.timeout),
            'retry_count': str(self.retry_count),
            'batch_size': str(self.batch_size),
            'preprocess': 'False',
            'api_url': 'https://test-api-url.com',
            'api_key': 'test-api-key'
        }
        
        # 测试图像数据 - 使用numpy数组模拟图像
        self.test_image = np.zeros((100, 100, 3), dtype=np.uint8)
    
    def tearDown(self):
        """测试后清理"""
        # 删除临时目录
        shutil.rmtree(self.test_dir)
    
    def test_init(self):
        """测试初始化"""
        # 创建模拟日志记录器
        mock_logger = MagicMock()
        
        # 模拟_check_api_connectivity方法
        with patch('core.ocr_processor.OCRProcessor._check_api_connectivity', return_value=True):
            processor = OCRProcessor(self.config, logger=mock_logger)
            
            # 验证属性
            self.assertEqual(processor.model_name, self.model_name)
            self.assertEqual(processor.timeout, self.timeout)
            self.assertEqual(processor.retry_count, self.retry_count)
            self.assertEqual(processor.batch_size, self.batch_size)
            self.assertEqual(processor.preprocess, False)
            self.assertEqual(processor.total_tokens, 0)
            
            # 验证日志记录
            mock_logger.info.assert_called_with(f"🔍 初始化OCR处理器: 模型={self.model_name}")
    
    @patch('core.ocr_processor.OCRProcessor._call_llm_ocr')
    def test_ocr_page(self, mock_call_llm_ocr):
        """测试OCR处理单页图像"""
        # 模拟OCR结果
        mock_result = {
            'text': '测试文本',
            'confidence': 0.9,
            'blocks': [],
            'language': {'code': 'zh-CN', 'name': '简体中文'},
            'token_usage': 100
        }
        mock_call_llm_ocr.return_value = mock_result
        
        # 模拟_check_api_connectivity方法
        with patch('core.ocr_processor.OCRProcessor._check_api_connectivity', return_value=True):
            # 创建处理器
            processor = OCRProcessor(self.config)
            
            # 调用OCR处理
            result = processor.ocr_page(self.test_image)
            
            # 验证结果
            self.assertEqual(result, mock_result)
            self.assertEqual(processor.total_tokens, 100)
            
            # 验证调用
            mock_call_llm_ocr.assert_called_once_with(self.test_image)
    
    @patch('core.ocr_processor.OCRProcessor._call_llm_ocr')
    def test_batch_process(self, mock_call_llm_ocr):
        """测试批量处理多个图像"""
        # 模拟OCR结果
        mock_result1 = {
            'text': '测试文本1',
            'confidence': 0.9,
            'blocks': [],
            'language': {'code': 'zh-CN', 'name': '简体中文'},
            'token_usage': 100
        }
        mock_result2 = {
            'text': '测试文本2',
            'confidence': 0.9,
            'blocks': [],
            'language': {'code': 'zh-CN', 'name': '简体中文'},
            'token_usage': 150
        }
        mock_call_llm_ocr.side_effect = [mock_result1, mock_result2]
        
        # 模拟_check_api_connectivity方法
        with patch('core.ocr_processor.OCRProcessor._check_api_connectivity', return_value=True):
            # 创建处理器
            processor = OCRProcessor(self.config)
            
            # 创建测试图像列表
            images = [self.test_image, self.test_image]
            
            # 调用批量处理
            results = processor.batch_process(images)
            
            # 验证结果
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0], mock_result1)
            self.assertEqual(results[1], mock_result2)
            self.assertEqual(processor.total_tokens, 250)
            
            # 验证调用次数
            self.assertEqual(mock_call_llm_ocr.call_count, 2)
    
    @patch('core.ocr_processor.OCRProcessor._call_llm_ocr')
    def test_preprocess_enabled(self, mock_call_llm_ocr):
        """测试启用预处理"""
        # 模拟OCR结果
        mock_result = {
            'text': '测试文本',
            'confidence': 0.9,
            'blocks': [],
            'language': {'code': 'zh-CN', 'name': '简体中文'},
            'token_usage': 100
        }
        mock_call_llm_ocr.return_value = mock_result
        
        # 更新配置启用预处理
        self.config['ocr']['preprocess'] = 'True'
        
        # 模拟_check_api_connectivity和_preprocess_image方法
        with patch('core.ocr_processor.OCRProcessor._check_api_connectivity', return_value=True), \
             patch('core.ocr_processor.OCRProcessor._preprocess_image', return_value=self.test_image) as mock_preprocess:
            
            # 创建处理器
            processor = OCRProcessor(self.config)
            
            # 调用OCR处理
            result = processor.ocr_page(self.test_image)
            
            # 验证预处理被调用
            mock_preprocess.assert_called_once_with(self.test_image)
            
            # 验证结果
            self.assertEqual(result, mock_result)
    
    @patch('core.ocr_processor.OCRProcessor._call_llm_ocr')
    def test_retry_mechanism(self, mock_call_llm_ocr):
        """测试重试机制"""
        # 模拟OCR结果和异常
        mock_result = {
            'text': '测试文本',
            'confidence': 0.9,
            'blocks': [],
            'language': {'code': 'zh-CN', 'name': '简体中文'},
            'token_usage': 100
        }
        mock_call_llm_ocr.side_effect = [Exception("测试异常"), mock_result]
        
        # 模拟_check_api_connectivity方法和time.sleep
        with patch('core.ocr_processor.OCRProcessor._check_api_connectivity', return_value=True), \
             patch('time.sleep') as mock_sleep:
            
            # 创建处理器
            processor = OCRProcessor(self.config)
            
            # 调用OCR处理
            result = processor.ocr_page(self.test_image)
            
            # 验证重试
            self.assertEqual(mock_call_llm_ocr.call_count, 2)
            self.assertEqual(result, mock_result)
            mock_sleep.assert_called_once()
    
    @patch('core.ocr_processor.OCRProcessor._call_llm_ocr')
    def test_token_usage_tracking(self, mock_call_llm_ocr):
        """测试token使用情况跟踪功能"""
        # 创建模拟日志记录器
        mock_logger = MagicMock()
        
        # 模拟多次OCR调用的结果
        mock_results = [
            {
                'text': '第一页测试文本',
                'confidence': 0.9,
                'blocks': [],
                'language': {'code': 'zh-CN', 'name': '简体中文'},
                'token_usage': 120
            },
            {
                'text': '第二页测试文本',
                'confidence': 0.85,
                'blocks': [],
                'language': {'code': 'zh-CN', 'name': '简体中文'},
                'token_usage': 150
            },
            {
                'text': '第三页测试文本',
                'confidence': 0.95,
                'blocks': [],
                'language': {'code': 'zh-CN', 'name': '简体中文'},
                'token_usage': 180
            }
        ]
        mock_call_llm_ocr.side_effect = mock_results
        
        # 模拟_check_api_connectivity方法
        with patch('core.ocr_processor.OCRProcessor._check_api_connectivity', return_value=True):
            # 创建处理器
            processor = OCRProcessor(self.config, logger=mock_logger)
            
            # 初始token计数应为0
            self.assertEqual(processor.total_tokens, 0)
            
            # 第一次OCR调用
            result1 = processor.ocr_page(self.test_image)
            self.assertEqual(result1['token_usage'], 120)
            self.assertEqual(processor.total_tokens, 120)
            
            # 第二次OCR调用
            result2 = processor.ocr_page(self.test_image)
            self.assertEqual(result2['token_usage'], 150)
            self.assertEqual(processor.total_tokens, 270)  # 120 + 150
            
            # 第三次OCR调用
            result3 = processor.ocr_page(self.test_image)
            self.assertEqual(result3['token_usage'], 180)
            self.assertEqual(processor.total_tokens, 450)  # 120 + 150 + 180
            
            # 验证日志记录
            mock_logger.debug.assert_any_call(f"🔢 累计token使用量: 450")
    
    @patch('core.ocr_processor.OCRProcessor._call_llm_ocr')
    def test_token_usage_with_missing_data(self, mock_call_llm_ocr):
        """测试当OCR结果中缺少token使用数据时的处理"""
        # 模拟OCR结果，缺少token_usage字段
        mock_result_no_tokens = {
            'text': '测试文本',
            'confidence': 0.9,
            'blocks': [],
            'language': {'code': 'zh-CN', 'name': '简体中文'}
            # 故意缺少token_usage字段
        }
        mock_call_llm_ocr.return_value = mock_result_no_tokens
        
        # 模拟_check_api_connectivity方法
        with patch('core.ocr_processor.OCRProcessor._check_api_connectivity', return_value=True):
            # 创建处理器
            processor = OCRProcessor(self.config)
            
            # 初始token计数应为0
            self.assertEqual(processor.total_tokens, 0)
            
            # 调用OCR处理
            result = processor.ocr_page(self.test_image)
            
            # 验证结果和token计数
            self.assertEqual(result, mock_result_no_tokens)
            self.assertEqual(processor.total_tokens, 0)  # 应该保持为0，因为没有token使用数据
    
    @patch('core.ocr_processor.OCRProcessor._call_llm_ocr')
    def test_max_retry_exceeded(self, mock_call_llm_ocr):
        """测试超过最大重试次数"""
        # 设置重试次数为2
        self.config['ocr']['retry_count'] = '2'
        
        # 模拟连续异常
        test_exception = Exception("测试异常")
        mock_call_llm_ocr.side_effect = [test_exception, test_exception]
        
        # 模拟_check_api_connectivity方法和time.sleep
        with patch('core.ocr_processor.OCRProcessor._check_api_connectivity', return_value=True), \
             patch('time.sleep'):
            
            # 创建处理器
            processor = OCRProcessor(self.config)
            
            # 验证异常被抛出
            with self.assertRaises(Exception):
                processor.ocr_page(self.test_image)
            
            # 验证调用次数
            self.assertEqual(mock_call_llm_ocr.call_count, 2)
    
    def test_detect_primary_language(self):
        """测试检测主要语言"""
        # 模拟_check_api_connectivity方法
        with patch('core.ocr_processor.OCRProcessor._check_api_connectivity', return_value=True):
            # 创建处理器
            processor = OCRProcessor(self.config)
            
            # 测试有语言信息的情况
            ocr_result = {
                'language': {
                    'zh-CN': 0.9,
                    'en': 0.1
                }
            }
            self.assertEqual(processor.detect_primary_language(ocr_result), 'zh-CN')
            
            # 测试无语言信息的情况
            ocr_result = {}
            self.assertEqual(processor.detect_primary_language(ocr_result), 'unknown')
            
            # 测试空语言信息的情况
            ocr_result = {'language': {}}
            self.assertEqual(processor.detect_primary_language(ocr_result), 'unknown')


if __name__ == '__main__':
    unittest.main()
