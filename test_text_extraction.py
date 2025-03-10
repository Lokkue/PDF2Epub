#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试PDF文本提取
"""

import sys
import fitz  # PyMuPDF
from core.pdf_parser import PDFParser

def test_text_extraction(pdf_path):
    """
    测试从PDF中提取文本
    
    参数:
        pdf_path: PDF文件路径
    """
    print(f"测试从PDF中提取文本: {pdf_path}")
    
    # 使用PDFParser
    parser = PDFParser(pdf_path)
    print(f"PDF页数: {parser.page_count}")
    
    # 提取前5页的文本
    for page_num in range(min(5, int(parser.page_count))):
        text = parser.extract_text(page_num)
        print(f"\n--- 第 {page_num + 1} 页文本 ---")
        print(f"文本长度: {len(text)}")
        print(f"文本内容预览: {text[:200]}...")
    
    # 直接使用PyMuPDF
    print("\n使用PyMuPDF直接提取文本:")
    doc = fitz.open(pdf_path)
    for page_num in range(min(5, doc.page_count)):
        page = doc[page_num]
        text = page.get_text()
        print(f"\n--- 第 {page_num + 1} 页文本 ---")
        print(f"文本长度: {len(text)}")
        print(f"文本内容预览: {text[:200]}...")

if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("用法: python test_text_extraction.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    test_text_extraction(pdf_path)
