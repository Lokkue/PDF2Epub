#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试文本清洗器模块
"""

import os
import unittest
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入被测试模块
from core.text_cleaner import TextCleaner


class TestTextCleaner(unittest.TestCase):
    """文本清洗器测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.cleaner = TextCleaner()
        
        # 测试文本样例 - 使用三引号避免转义问题
        self.text_with_bad_linebreaks = """这是一段测试文本，它包含了
不自然的换行，需要
修复。"""
        
        self.text_with_paragraphs = """第一段落。

第二段落。

第三段落。"""
        
        self.text_with_quotes = """他说："这是一段
引用文本。"
然后继续说道。"""
        
        self.text_with_footnotes = """这是正文。※1
※1 这是脚注内容。"""
        
        self.text_with_indents = """    这是缩进的文本。
        这是更深层次的缩进。"""
        
        self.text_with_tables = """| 列1 | 列2 |
| --- | --- |
| 数据1 | 数据2 |"""
    
    def test_fix_linebreaks(self):
        """测试修复不自然换行"""
        fixed_text = self.cleaner.fix_linebreaks(self.text_with_bad_linebreaks)
        self.assertEqual(fixed_text, "这是一段测试文本，它包含了不自然的换行，需要修复。")
    
    def test_preserve_paragraphs(self):
        """测试保留段落"""
        processed_text = self.cleaner.fix_linebreaks(self.text_with_paragraphs)
        self.assertEqual(processed_text, """第一段落。

第二段落。

第三段落。""")
    
    def test_handle_quotes(self):
        """测试处理引用"""
        processed_text = self.cleaner.fix_linebreaks(self.text_with_quotes)
        self.assertEqual(processed_text, """他说："这是一段引用文本。"
然后继续说道。""")
    
    def test_detect_footnotes(self):
        """测试检测脚注"""
        footnotes = self.cleaner.extract_footnotes(self.text_with_footnotes)
        self.assertEqual(len(footnotes), 1)
        self.assertEqual(footnotes[0]["marker"], "※1")
        self.assertEqual(footnotes[0]["content"], "这是脚注内容。")
    
    def test_clean_text_full(self):
        """测试完整的文本清洗流程"""
        dirty_text = """这是第一段，它有
不自然的换行。这里还有一些
需要修复的问题。

第二段有    多余的空格和
制表符。

"这是一段引用，
它也有不自然的换行。"

※1 这是文档末尾的注释。"""
        
        expected_clean_text = """这是第一段，它有不自然的换行。这里还有一些需要修复的问题。

第二段有多余的空格和制表符。

"这是一段引用，它也有不自然的换行。"

※1 这是文档末尾的注释。"""
        
        clean_text = self.cleaner.clean(dirty_text)
        self.assertEqual(clean_text, expected_clean_text)
    
    def test_normalize_punctuation(self):
        """测试标点符号规范化"""
        text_with_mixed_punctuation = "这是中文句子,使用了英文逗号.还有英文句号..."
        normalized_text = self.cleaner.normalize_punctuation(text_with_mixed_punctuation)
        self.assertEqual(normalized_text, "这是中文句子，使用了英文逗号。还有英文句号……")
    
    def test_detect_and_format_lists(self):
        """测试检测和格式化列表"""
        list_text = """1. 第一项
2. 第二项
3. 第三项"""
        
        formatted_list = self.cleaner.format_lists(list_text)
        self.assertEqual(formatted_list, """1. 第一项
2. 第二项
3. 第三项""")
    
    def test_detect_chapter_titles(self):
        """测试检测章节标题"""
        text_with_titles = """第一章 引言

这是引言内容。

1.1 背景

这是背景部分。"""
        
        titles = self.cleaner.extract_titles(text_with_titles)
        self.assertEqual(len(titles), 2)
        self.assertEqual(titles[0]["level"], 1)
        self.assertEqual(titles[0]["text"], "第一章 引言")
        self.assertEqual(titles[1]["level"], 2)
        self.assertEqual(titles[1]["text"], "1.1 背景")
    
    def test_handle_page_numbers(self):
        """测试处理页码"""
        text_with_page_numbers = """这是第一页的内容。
- 23 -
这是第二页的内容。"""
        
        cleaned_text = self.cleaner.remove_page_numbers(text_with_page_numbers)
        self.assertEqual(cleaned_text, """这是第一页的内容。
这是第二页的内容。""")
    
    def test_handle_tables(self):
        """测试处理表格文本"""
        table_text = self.text_with_tables
        is_table = self.cleaner.is_table(table_text)
        self.assertTrue(is_table)
        
        # 测试表格转HTML
        html_table = self.cleaner.table_to_html(table_text)
        self.assertIn("<table>", html_table)
        self.assertIn("<tr>", html_table)
        self.assertIn("<td>数据1</td>", html_table)
    
    def test_handle_indentation(self):
        """测试处理缩进"""
        processed_text = self.cleaner.preserve_indentation(self.text_with_indents)
        self.assertEqual(processed_text, """    这是缩进的文本。
        这是更深层次的缩进。""")
    
    def test_merge_hyphenated_words(self):
        """测试合并连字符分隔的单词"""
        hyphenated_text = """这是一个被分-
开的词。"""
        merged_text = self.cleaner.merge_hyphenated_words(hyphenated_text)
        self.assertEqual(merged_text, "这是一个被分开的词。")
    
    def test_handle_special_characters(self):
        """测试处理特殊字符"""
        text_with_special_chars = "这里有一些特殊字符：①②③④⑤⑥⑦⑧⑨⑩"
        processed_text = self.cleaner.normalize_special_characters(text_with_special_chars)
        self.assertEqual(processed_text, "这里有一些特殊字符：①②③④⑤⑥⑦⑧⑨⑩")


if __name__ == '__main__':
    unittest.main()
