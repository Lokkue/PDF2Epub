#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基础页面处理器
"""

import numpy as np
from core.text_cleaner import TextCleaner


class BaseProcessor:
    """
    页面处理器基类
    
    所有特定类型的页面处理器都应继承此类，并实现相应的方法。
    """
    
    def __init__(self, image, text):
        """
        初始化处理器
        
        参数:
            image: OpenCV图像对象（NumPy数组）
            text: 页面文本内容
        """
        self.image = image
        self.text = text
        self.cleaner = TextCleaner()
    
    @classmethod
    def detect(cls, image, text):
        """
        检测页面是否属于此类型
        
        参数:
            image: OpenCV图像对象
            text: 页面文本内容
            
        返回:
            float: 置信度分数 0-1
        """
        # 基类默认返回0，表示不匹配任何特定类型
        return 0.0
    
    def process(self):
        """
        处理页面并返回处理后的内容
        
        返回:
            str: 处理后的内容（通常是HTML格式）
        """
        # 基类默认返回原始文本
        return self.text
    
    def clean_text(self):
        """
        清洗文本，修复常见问题
        
        返回:
            str: 清洗后的文本
        """
        return self.cleaner.clean(self.text)
