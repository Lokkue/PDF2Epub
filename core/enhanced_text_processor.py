#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
增强型文本处理器模块

用于解析和处理OCR识别出的特殊格式标记，支持更丰富的排版元素。
"""

import re
import logging
from core.text_cleaner import TextCleaner

# 配置日志
logger = logging.getLogger(__name__)


class EnhancedTextProcessor:
    """
    增强型文本处理器类
    
    用于解析和处理OCR识别出的特殊格式标记，支持更丰富的排版元素。
    """
    
    def __init__(self):
        """
        初始化增强型文本处理器
        """
        logger.debug("初始化增强型文本处理器")
        self.text_cleaner = TextCleaner()
        self.book_metadata = {
            "title": "",
            "subtitle": "",
            "author": "",
            "translator": "",
            "publisher": "",
            "isbn": "",
            "year": "",
            "toc_entries": []  # 存储目录条目，格式为 [{"title": "标题", "level": 层级, "page": 页码}, ...]
        }
    
    def process(self, text, page_type="text"):
        """
        处理文本，解析特殊格式标记并转换为合适的HTML格式
        
        参数:
            text: 原始文本
            page_type: 页面类型
            
        返回:
            tuple: (处理后的HTML文本, 提取的元数据)
        """
        if not text:
            return "", {}
        
        # 先应用基础清洗规则
        text = self.text_cleaner.clean(text)
        
        # 根据页面类型调用不同的处理方法
        if page_type == "toc":
            return self.process_toc(text)
        elif page_type == "table":
            return self.process_table(text)
        elif page_type == "cover":
            return self.process_cover(text)
        elif page_type == "publication_info":
            return self.process_publication_info(text)
        elif page_type == "preface":
            return self.process_preface(text)
        elif page_type == "afterword":
            return self.process_afterword(text)
        else:
            # 默认处理普通文本
            return self.process_text(text)
    
    def process_text(self, text):
        """
        处理普通文本页面
        
        参数:
            text: 原始文本
            
        返回:
            tuple: (处理后的HTML文本, 提取的元数据)
        """
        metadata = {}
        html = []
        
        # 提取页码信息
        page_number = None
        page_number_match = re.search(r'#PAGE_NUMBER:\s*([0-9]+)#', text)
        if page_number_match:
            page_number = page_number_match.group(1)
            metadata["page_number"] = page_number
            text = re.sub(r'#PAGE_NUMBER:\s*[0-9]+#', '', text)
        
        # 提取页眉信息
        header_text = None
        header_match = re.search(r'#HEADER:\s*(.*?)#', text)
        if header_match:
            header_text = header_match.group(1)
            metadata["header"] = header_text
            text = re.sub(r'#HEADER:\s*.*?#', '', text)
        
        # 提取页脚信息
        footer_text = None
        footer_match = re.search(r'#FOOTER:\s*(.*?)#', text)
        if footer_match:
            footer_text = footer_match.group(1)
            metadata["footer"] = footer_text
            text = re.sub(r'#FOOTER:\s*.*?#', '', text)
        
        # 提取章节标题
        chapter_title = None
        chapter_match = re.search(r'#CHAPTER:\s*(.*?)#', text)
        if chapter_match:
            chapter_title = chapter_match.group(1)
            metadata["chapter"] = chapter_title
            html.append(f'<h1 class="chapter-title">{chapter_title}</h1>')
            text = re.sub(r'#CHAPTER:\s*.*?#', '', text)
        
        # 提取小节标题
        section_matches = re.finditer(r'#SECTION:\s*(.*?)#', text)
        for match in section_matches:
            section_title = match.group(1)
            html.append(f'<h2 class="section-title">{section_title}</h2>')
        text = re.sub(r'#SECTION:\s*.*?#', '', text)
        
        # 处理脚注
        footnote_matches = re.finditer(r'#FOOTNOTE:\s*([0-9]+|[①-⑩]|[a-zA-Z])\|(.*?)#', text)
        footnotes = []
        for match in footnote_matches:
            footnote_id = match.group(1)
            footnote_content = match.group(2)
            footnotes.append((footnote_id, footnote_content))
        
        # 替换正文中的脚注引用
        for footnote_id, _ in footnotes:
            text = re.sub(
                r'#FOOTNOTE_REF:\s*' + re.escape(footnote_id) + r'#',
                f'<sup class="footnote-ref" id="fnref:{footnote_id}">{footnote_id}</sup>',
                text
            )
        
        # 移除脚注定义
        text = re.sub(r'#FOOTNOTE:\s*([0-9]+|[①-⑩]|[a-zA-Z])\|.*?#', '', text)
        
        # 处理段落
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        for p in paragraphs:
            html.append(f'<p>{p}</p>')
        
        # 添加脚注区域
        if footnotes:
            html.append('<div class="footnotes">')
            html.append('<hr>')
            html.append('<ol>')
            for footnote_id, footnote_content in footnotes:
                html.append(f'<li id="fn:{footnote_id}">{footnote_content}</li>')
            html.append('</ol>')
            html.append('</div>')
        
        return '\n'.join(html), metadata
    
    def process_toc(self, text):
        """
        处理目录页面
        
        参数:
            text: 原始文本
            
        返回:
            tuple: (处理后的HTML文本, 提取的元数据)
        """
        metadata = {"toc_entries": []}
        html = ['<div class="toc">']
        
        # 添加目录标题
        html.append('<h1 class="toc-title">目录</h1>')
        html.append('<nav class="toc-nav">')
        html.append('<ul>')
        
        # 提取目录条目
        toc_entries = re.finditer(r'#TOC_ENTRY:\s*(.*?)\|(.*?)#', text)
        for match in toc_entries:
            title = match.group(1).strip()
            page = match.group(2).strip()
            
            # 根据缩进判断层级
            indent_level = 0
            while title.startswith('  '):
                indent_level += 1
                title = title[2:]
            
            # 记录目录条目
            metadata["toc_entries"].append({
                "title": title,
                "level": indent_level,
                "page": page
            })
            
            # 生成HTML
            html.append(f'<li class="toc-level-{indent_level}"><span class="toc-title">{title}</span><span class="toc-page">{page}</span></li>')
        
        # 提取特殊页面标记
        special_pages = re.finditer(r'#SPECIAL_PAGE:\s*(.*?)\|(.*?)#', text)
        for match in special_pages:
            page_type = match.group(1).strip()
            page = match.group(2).strip()
            
            # 记录特殊页面
            metadata["special_pages"] = metadata.get("special_pages", [])
            metadata["special_pages"].append({
                "type": page_type,
                "page": page
            })
            
            # 生成HTML
            html.append(f'<li class="toc-special"><span class="toc-title">{page_type}</span><span class="toc-page">{page}</span></li>')
        
        html.append('</ul>')
        html.append('</nav>')
        html.append('</div>')
        
        return '\n'.join(html), metadata
    
    def process_table(self, text):
        """
        处理表格页面
        
        参数:
            text: 原始文本
            
        返回:
            tuple: (处理后的HTML文本, 提取的元数据)
        """
        metadata = {}
        html = []
        
        # 提取表格标题
        table_caption = None
        caption_match = re.search(r'#TABLE_CAPTION:\s*(.*?)#', text)
        if caption_match:
            table_caption = caption_match.group(1)
            metadata["table_caption"] = table_caption
            text = re.sub(r'#TABLE_CAPTION:\s*.*?#', '', text)
        
        # 提取表格内容
        table_match = re.search(r'#TABLE_START#(.*?)#TABLE_END#', text, re.DOTALL)
        if table_match:
            table_content = table_match.group(1).strip()
            
            # 分割行
            rows = [row.strip() for row in table_content.split('\n') if row.strip()]
            
            # 生成HTML表格
            html.append('<div class="table-container">')
            if table_caption:
                html.append(f'<p class="table-caption">{table_caption}</p>')
            
            html.append('<table>')
            
            # 处理每一行
            for i, row in enumerate(rows):
                html.append('<tr>')
                
                # 分割列
                columns = [col.strip() for col in row.split('|')]
                
                # 确定是否为表头行
                cell_tag = 'th' if i == 0 else 'td'
                
                # 生成列
                for col in columns:
                    html.append(f'<{cell_tag}>{col}</{cell_tag}>')
                
                html.append('</tr>')
            
            html.append('</table>')
            html.append('</div>')
            
            # 移除表格内容
            text = re.sub(r'#TABLE_START#.*?#TABLE_END#', '', text, flags=re.DOTALL)
        
        # 处理表格外的文本
        text = text.strip()
        if text:
            # 处理段落
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            for p in paragraphs:
                html.append(f'<p>{p}</p>')
        
        return '\n'.join(html), metadata
    
    def process_cover(self, text):
        """
        处理封面页面
        
        参数:
            text: 原始文本
            
        返回:
            tuple: (处理后的HTML文本, 提取的元数据)
        """
        metadata = {}
        html = ['<div class="cover">']
        
        # 提取书名
        title_match = re.search(r'#BOOK_TITLE:\s*(.*?)#', text)
        if title_match:
            title = title_match.group(1)
            metadata["title"] = title
            html.append(f'<h1 class="book-title">{title}</h1>')
        
        # 提取副标题
        subtitle_match = re.search(r'#BOOK_SUBTITLE:\s*(.*?)#', text)
        if subtitle_match:
            subtitle = subtitle_match.group(1)
            metadata["subtitle"] = subtitle
            html.append(f'<h2 class="book-subtitle">{subtitle}</h2>')
        
        # 提取作者
        author_match = re.search(r'#BOOK_AUTHOR:\s*(.*?)#', text)
        if author_match:
            author = author_match.group(1)
            metadata["author"] = author
            html.append(f'<p class="book-author">{author}</p>')
        
        # 提取出版社
        publisher_match = re.search(r'#BOOK_PUBLISHER:\s*(.*?)#', text)
        if publisher_match:
            publisher = publisher_match.group(1)
            metadata["publisher"] = publisher
            html.append(f'<p class="book-publisher">{publisher}</p>')
        
        # 提取出版年份
        year_match = re.search(r'#BOOK_YEAR:\s*(.*?)#', text)
        if year_match:
            year = year_match.group(1)
            metadata["year"] = year
            html.append(f'<p class="book-year">{year}</p>')
        
        # 提取丛书名称
        series_match = re.search(r'#BOOK_SERIES:\s*(.*?)#', text)
        if series_match:
            series = series_match.group(1)
            metadata["series"] = series
            html.append(f'<p class="book-series">{series}</p>')
        
        html.append('</div>')
        
        return '\n'.join(html), metadata
    
    def process_publication_info(self, text):
        """
        处理出版信息页面
        
        参数:
            text: 原始文本
            
        返回:
            tuple: (处理后的HTML文本, 提取的元数据)
        """
        metadata = {}
        html = ['<div class="publication-info">']
        
        # 提取所有出版信息
        info_patterns = [
            ('title', r'#BOOK_TITLE:\s*(.*?)#'),
            ('author', r'#BOOK_AUTHOR:\s*(.*?)#'),
            ('translator', r'#BOOK_TRANSLATOR:\s*(.*?)#'),
            ('publisher', r'#BOOK_PUBLISHER:\s*(.*?)#'),
            ('isbn', r'#BOOK_ISBN:\s*(.*?)#'),
            ('price', r'#BOOK_PRICE:\s*(.*?)#'),
            ('edition', r'#BOOK_EDITION:\s*(.*?)#'),
            ('print_info', r'#BOOK_PRINT_INFO:\s*(.*?)#'),
            ('copyright', r'#BOOK_COPYRIGHT:\s*(.*?)#')
        ]
        
        for info_key, pattern in info_patterns:
            match = re.search(pattern, text)
            if match:
                info_value = match.group(1)
                metadata[info_key] = info_value
                html.append(f'<p class="pub-{info_key}">{info_value}</p>')
        
        html.append('</div>')
        
        return '\n'.join(html), metadata
    
    def process_preface(self, text):
        """
        处理前言页面
        
        参数:
            text: 原始文本
            
        返回:
            tuple: (处理后的HTML文本, 提取的元数据)
        """
        metadata = {}
        html = ['<div class="preface">']
        
        # 提取前言标题
        title_match = re.search(r'#PREFACE_TITLE:\s*(.*?)#', text)
        if title_match:
            title = title_match.group(1)
            metadata["preface_title"] = title
            html.append(f'<h1 class="preface-title">{title}</h1>')
            text = re.sub(r'#PREFACE_TITLE:\s*.*?#', '', text)
        
        # 提取前言作者
        author_match = re.search(r'#PREFACE_AUTHOR:\s*(.*?)#', text)
        if author_match:
            author = author_match.group(1)
            metadata["preface_author"] = author
            html.append(f'<p class="preface-author">{author}</p>')
            text = re.sub(r'#PREFACE_AUTHOR:\s*.*?#', '', text)
        
        # 提取前言日期
        date_match = re.search(r'#PREFACE_DATE:\s*(.*?)#', text)
        if date_match:
            date = date_match.group(1)
            metadata["preface_date"] = date
            html.append(f'<p class="preface-date">{date}</p>')
            text = re.sub(r'#PREFACE_DATE:\s*.*?#', '', text)
        
        # 提取前言内容
        content_match = re.search(r'#PREFACE_CONTENT:\s*(.*?)#', text, re.DOTALL)
        if content_match:
            content = content_match.group(1)
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            for p in paragraphs:
                html.append(f'<p class="preface-content">{p}</p>')
            text = re.sub(r'#PREFACE_CONTENT:\s*.*?#', '', text, flags=re.DOTALL)
        
        # 处理剩余文本
        text = text.strip()
        if text:
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            for p in paragraphs:
                html.append(f'<p>{p}</p>')
        
        html.append('</div>')
        
        return '\n'.join(html), metadata
    
    def process_afterword(self, text):
        """
        处理后记页面
        
        参数:
            text: 原始文本
            
        返回:
            tuple: (处理后的HTML文本, 提取的元数据)
        """
        metadata = {}
        html = ['<div class="afterword">']
        
        # 提取后记标题
        title_match = re.search(r'#AFTERWORD_TITLE:\s*(.*?)#', text)
        if title_match:
            title = title_match.group(1)
            metadata["afterword_title"] = title
            html.append(f'<h1 class="afterword-title">{title}</h1>')
            text = re.sub(r'#AFTERWORD_TITLE:\s*.*?#', '', text)
        
        # 提取后记作者
        author_match = re.search(r'#AFTERWORD_AUTHOR:\s*(.*?)#', text)
        if author_match:
            author = author_match.group(1)
            metadata["afterword_author"] = author
            html.append(f'<p class="afterword-author">{author}</p>')
            text = re.sub(r'#AFTERWORD_AUTHOR:\s*.*?#', '', text)
        
        # 提取后记日期
        date_match = re.search(r'#AFTERWORD_DATE:\s*(.*?)#', text)
        if date_match:
            date = date_match.group(1)
            metadata["afterword_date"] = date
            html.append(f'<p class="afterword-date">{date}</p>')
            text = re.sub(r'#AFTERWORD_DATE:\s*.*?#', '', text)
        
        # 提取后记内容
        content_match = re.search(r'#AFTERWORD_CONTENT:\s*(.*?)#', text, re.DOTALL)
        if content_match:
            content = content_match.group(1)
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            for p in paragraphs:
                html.append(f'<p class="afterword-content">{p}</p>')
            text = re.sub(r'#AFTERWORD_CONTENT:\s*.*?#', '', text, flags=re.DOTALL)
        
        # 处理剩余文本
        text = text.strip()
        if text:
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            for p in paragraphs:
                html.append(f'<p>{p}</p>')
        
        html.append('</div>')
        
        return '\n'.join(html), metadata
