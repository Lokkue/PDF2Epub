#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
脚注页处理器
"""

import re
from .base import BaseProcessor


class FootnoteProcessor(BaseProcessor):
    """
    脚注处理器
    
    用于检测和处理包含脚注的页面。
    """
    
    @classmethod
    def detect(cls, image, text):
        """
        检测页面是否包含脚注
        
        参数:
            image: OpenCV图像对象
            text: 页面文本内容
            
        返回:
            float: 置信度分数 0-1
        """
        confidence = 0.0
        
        if not text:
            return confidence
        
        # 特征1: 包含脚注标记
        footnote_markers = [
            r'※\d+',  # ※1, ※2, ...
            r'[①②③④⑤⑥⑦⑧⑨⑩]',  # 圆圈数字
            r'\[\d+\]',  # [1], [2], ...
            r'\(\d+\)',  # (1), (2), ...
            r'\d+\)',  # 1), 2), ...
            r'\*+',  # *, **, ...
        ]
        
        marker_count = 0
        for pattern in footnote_markers:
            matches = re.findall(pattern, text)
            marker_count += len(matches)
        
        if marker_count > 0:
            confidence += min(0.5, marker_count * 0.1)
        
        # 特征2: 包含脚注内容模式
        # 查找形如 "※1 这是脚注内容" 的模式
        footnote_pattern = r'(※\d+|[①②③④⑤⑥⑦⑧⑨⑩]|\[\d+\]|\(\d+\)|\d+\)|\*+)\s+.+'
        lines = text.strip().split('\n')
        footnote_lines = sum(1 for line in lines if re.match(footnote_pattern, line.strip()))
        
        if footnote_lines > 0:
            confidence += min(0.5, footnote_lines * 0.1)
        
        return min(confidence, 1.0)
    
    def process(self):
        """
        处理脚注页
        
        返回:
            str: 处理后的HTML内容
        """
        # 提取脚注
        footnotes = self.extract_footnotes()
        
        # 处理正文（替换脚注标记为链接）
        processed_text = self.text
        for i, footnote in enumerate(footnotes):
            marker = footnote['marker']
            # 转义正则表达式特殊字符
            escaped_marker = re.escape(marker)
            # 替换脚注标记为链接
            processed_text = re.sub(
                f'({escaped_marker})(?!\\s+.+)',  # 匹配不后跟内容的标记
                f'<a href="#footnote-{i+1}" id="footnote-ref-{i+1}" class="footnote-ref">\\1</a>',
                processed_text
            )
        
        # 构建HTML
        html = [f'<div>{processed_text}</div>']
        
        # 添加脚注区域
        if footnotes:
            html.append('<hr>')
            html.append('<div class="footnotes">')
            for i, footnote in enumerate(footnotes):
                html.append(f'<aside id="footnote-{i+1}" class="footnote">')
                html.append(f'<a href="#footnote-ref-{i+1}">{footnote["marker"]}</a> {footnote["content"]}')
                html.append('</aside>')
            html.append('</div>')
        
        return '\n'.join(html)
    
    def extract_footnotes(self):
        """
        从文本中提取脚注
        
        返回:
            list: 脚注列表，每个脚注为字典 {'marker': '※1', 'content': '脚注内容'}
        """
        if not self.text:
            return []
        
        footnotes = []
        lines = self.text.strip().split('\n')
        
        # 脚注模式
        footnote_pattern = r'^(※\d+|[①②③④⑤⑥⑦⑧⑨⑩]|\[\d+\]|\(\d+\)|\d+\)|\*+)\s+(.+)$'
        
        # 提取脚注
        for line in lines:
            line = line.strip()
            match = re.match(footnote_pattern, line)
            if match:
                marker = match.group(1)
                content = match.group(2)
                
                # 检查是否已存在相同标记的脚注
                if not any(f['marker'] == marker for f in footnotes):
                    footnotes.append({
                        'marker': marker,
                        'content': content
                    })
        
        return footnotes
