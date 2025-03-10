#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
封面页处理器
"""

import cv2
import numpy as np
from .base import BaseProcessor


class CoverProcessor(BaseProcessor):
    """
    封面页处理器
    
    用于检测和处理封面页。
    """
    
    @classmethod
    def detect(cls, image, text):
        """
        检测页面是否为封面
        
        参数:
            image: OpenCV图像对象
            text: 页面文本内容
            
        返回:
            float: 置信度分数 0-1
        """
        confidence = 0.0
        
        # 特征1: 图像占比大
        # 计算非空白区域占比
        if image is not None:
            # 转换为灰度图
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
                
            # 二值化
            _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
            
            # 计算非空白像素占比
            non_white_ratio = np.count_nonzero(binary) / binary.size
            
            # 如果非空白区域占比大于30%，增加置信度
            if non_white_ratio > 0.3:
                confidence += 0.3
            
            # 如果非空白区域占比大于50%，进一步增加置信度
            if non_white_ratio > 0.5:
                confidence += 0.1
        
        # 特征2: 文本较少
        if text:
            # 计算文本长度
            text_length = len(text.strip())
            
            # 如果文本较少（少于100个字符），增加置信度
            if text_length < 100:
                confidence += 0.2
            
            # 如果文本非常少（少于50个字符），进一步增加置信度
            if text_length < 50:
                confidence += 0.1
            
            # 如果文本很多（超过200个字符），降低置信度
            if text_length > 200:
                confidence -= 0.2
            
            # 如果文本非常多（超过300个字符），进一步降低置信度
            if text_length > 300:
                confidence -= 0.2
            
            # 计算行数，多行文本不太可能是封面
            lines = text.strip().split('\n')
            if len(lines) > 5:
                confidence -= 0.1
        
        # 特征3: 包含书名和作者信息
        if text:
            lines = text.strip().split('\n')
            
            # 如果行数在2-5之间，可能是书名和作者
            if 2 <= len(lines) <= 5:
                confidence += 0.1
        
        return max(0.0, min(confidence, 1.0))  # 确保值在0-1之间
    
    def process(self):
        """
        处理封面页
        
        返回:
            str: 处理后的HTML内容
        """
        # 提取可能的书名和作者
        title, author = self._extract_title_author()
        
        # 构建HTML
        html = f"""<div class="cover">
    <h1>{title}</h1>
    <div class="author">{author}</div>
</div>"""
        
        return html
    
    def _extract_title_author(self):
        """
        从封面文本中提取书名和作者
        
        返回:
            tuple: (书名, 作者)
        """
        if not self.text:
            return ("未知书名", "未知作者")
        
        lines = self.text.strip().split('\n')
        lines = [line.strip() for line in lines if line.strip()]
        
        # 如果只有一行，假设是书名
        if len(lines) == 1:
            return (lines[0], "未知作者")
        
        # 如果有多行，假设第一行是书名，第二行是作者
        elif len(lines) >= 2:
            return (lines[0], lines[1])
        
        # 默认值
        return ("未知书名", "未知作者")
