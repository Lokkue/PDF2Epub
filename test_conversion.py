#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试PDF到EPUB的转换
"""

import os
import sys
import cv2
import numpy as np
import base64
import json
import time
import logging
from core.pdf_parser import PDFParser
from core.epub_builder import EPUBBuilder
from core.text_cleaner import TextCleaner
from core.ocr_processor import OCRProcessor
from core.page_processors.toc import TOCProcessor
from core.page_processors.table import TableProcessor
from core.page_processors.footnote import FootnoteProcessor

# 配置日志
def setup_logging():
    """设置日志配置"""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # 添加处理器到日志记录器
    logger.addHandler(console_handler)
    
    return logger

def convert_pdf_to_epub(pdf_path, epub_path, max_pages=20):
    """
    将PDF转换为EPUB，使用OCR提取文本
    
    参数:
        pdf_path: PDF文件路径
        epub_path: 输出EPUB文件路径
        max_pages: 最大处理页数
    """
    logger = setup_logging()
    logger.info(f"开始处理PDF: {pdf_path}")
    
    # 解析PDF
    parser = PDFParser(pdf_path)
    logger.info(f"PDF页数: {parser.page_count}")
    
    # 获取元数据
    metadata = parser.get_metadata()
    logger.info(f"PDF元数据: {metadata}")
    
    # 创建EPUB构建器
    builder = EPUBBuilder(epub_path)
    
    # 设置元数据
    title = metadata.get('title', os.path.basename(pdf_path).split('.')[0])
    author = metadata.get('author', '未知作者')
    builder.set_metadata(title, author)
    
    # 创建临时目录存储图像
    temp_dir = "temp_images"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    
    # 初始化OCR处理器
    try:
        ocr = OCRProcessor(preprocess=True)
        logger.info("成功初始化OCR处理器")
        use_ocr = True
    except Exception as e:
        logger.warning(f"警告: 初始化OCR处理器失败: {e}")
        logger.info("将使用图像模式继续处理")
        use_ocr = False
    
    # 提取图像并准备OCR
    extracted_pages = []
    
    # 处理页面数量限制
    page_count = min(int(parser.page_count), max_pages)
    
    for page_num in range(page_count):
        logger.info(f"处理第 {page_num + 1} 页...")
        
        # 提取图像
        image_data = parser.extract_image(page_num)
        
        if image_data:
            try:
                # 将JPEG字节数据解码为OpenCV图像
                nparr = np.frombuffer(image_data, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if image is not None:
                    # 调整图像大小，优化EPUB文件大小
                    height, width = image.shape[:2]
                    max_dimension = 1200
                    if height > max_dimension or width > max_dimension:
                        if height > width:
                            new_height = max_dimension
                            new_width = int(width * (max_dimension / height))
                        else:
                            new_width = max_dimension
                            new_height = int(height * (max_dimension / width))
                        image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
                    
                    # 保存图像
                    image_path = os.path.join(temp_dir, f"page_{page_num + 1}.jpg")
                    cv2.imwrite(image_path, image, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    
                    # 记录提取的页面信息
                    extracted_pages.append({
                        "page_num": page_num,
                        "image_path": image_path,
                        "image": image,
                        "width": image.shape[1],
                        "height": image.shape[0]
                    })
                    
                    logger.info(f"  已保存图像: {image_path}")
                else:
                    logger.warning(f"  无法解码图像")
            except Exception as e:
                logger.error(f"  错误: {e}")
        else:
            logger.warning(f"  未能提取图像")
    
    logger.info(f"共提取了 {len(extracted_pages)} 页图像")
    
    # 使用OCR处理器进行文本识别
    recognized_texts = []
    
    if use_ocr:
        logger.info("使用OCR处理器进行文本识别...")
        
        for page_info in extracted_pages:
            page_num = page_info["page_num"]
            image = page_info["image"]
            
            logger.info(f"  识别第 {page_num + 1} 页...")
            try:
                # 调用OCR处理器识别文本
                result = ocr.ocr_page(image)
                
                recognized_texts.append({
                    "page_num": page_num,
                    "text": result.get("text", ""),
                    "confidence": result.get("confidence", 0)
                })
                
                logger.info(f"  成功识别第 {page_num + 1} 页文本，长度: {len(result.get('text', ''))}")
            except Exception as e:
                logger.warning(f"  警告: 识别第 {page_num + 1} 页文本时出错: {e}")
                # 添加空文本，保持页码一致性
                recognized_texts.append({
                    "page_num": page_num,
                    "text": "",
                    "confidence": 0
                })
    
    # 将提取的内容组织成EPUB
    logger.info("组织EPUB内容...")
    
    # 检测是否有有效的文本识别结果
    has_valid_text = any(len(text_info["text"]) > 0 for text_info in recognized_texts)
    
    if has_valid_text:
        logger.info("使用OCR识别的文本内容...")
        # 添加封面（第一页）
        if extracted_pages:
            first_page = extracted_pages[0]
            cover_image_path = first_page["image_path"]
            with open(cover_image_path, "rb") as f:
                cover_image_data = f.read()
            
            # 使用base64编码图像
            b64_image = base64.b64encode(cover_image_data).decode('utf-8')
            cover_html = f'<div class="cover"><img src="data:image/jpeg;base64,{b64_image}" alt="封面"/></div>'
            
            # 添加识别的文本
            if recognized_texts and recognized_texts[0]["page_num"] == 0:
                cover_text = recognized_texts[0]["text"]
                if cover_text:
                    cover_html += f'<div class="cover-text">{cover_text}</div>'
            
            builder.add_chapter("封面", cover_html, 1)
            logger.info("  已添加封面")
        
        # 添加目录
        if len(extracted_pages) > 1:
            second_page = extracted_pages[1]
            toc_image_path = second_page["image_path"]
            with open(toc_image_path, "rb") as f:
                toc_image_data = f.read()
            
            # 使用base64编码图像
            b64_image = base64.b64encode(toc_image_data).decode('utf-8')
            toc_html = f'<div class="toc"><img src="data:image/jpeg;base64,{b64_image}" alt="目录"/></div>'
            
            # 添加识别的文本
            if recognized_texts and recognized_texts[1]["page_num"] == 1:
                toc_text = recognized_texts[1]["text"]
                if toc_text:
                    toc_html += f'<div class="toc-text">{toc_text}</div>'
            
            builder.add_chapter("目录", toc_html, 1)
            logger.info("  已添加目录")
        
        # 添加正文
        chapter_count = 0
        current_chapter = ""
        current_chapter_title = f"第 {chapter_count + 1} 章"
        
        # 从第三页开始（跳过封面和目录）
        for text_info in recognized_texts[2:]:
            page_num = text_info["page_num"]
            text = text_info["text"]
            
            if not text:
                continue
            
            # 改进的章节检测逻辑
            lines = text.split('\n')
            if lines and len(lines) > 0:
                first_line = lines[0].strip()
                # 检测章节标题 - 增加对"总序"、"前言"等特殊标题的支持
                if (first_line.startswith('第') and ('章' in first_line or '节' in first_line)) or \
                   (first_line.startswith('Chapter') or first_line.startswith('CHAPTER')) or \
                   first_line in ["总序", "序言", "前言", "引言", "后记", "附录"]:
                    # 保存之前的章节
                    if current_chapter:
                        builder.add_chapter(current_chapter_title, f'<div class="chapter">{current_chapter}</div>', 1)
                        chapter_count += 1
                    
                    # 开始新章节
                    current_chapter_title = first_line
                    current_chapter = f"<h1>{first_line}</h1>"
                    
                    # 添加章节内容（除了标题）
                    paragraphs = text.split('\n\n')[1:]  # 跳过标题
                    for para in paragraphs:
                        if para.strip():
                            current_chapter += f'<p>{para.strip()}</p>'
                else:
                    # 检测出版信息 - 通常包含ISBN、版权、出版社等信息
                    is_publication_info = any(keyword in text.lower() for keyword in 
                                             ["isbn", "版权", "出版社", "出版日期", "copyright", "出版", "印刷", "责任编辑"])
                    
                    if is_publication_info and page_num < 5:  # 出版信息通常在前几页
                        # 将出版信息作为单独的章节
                        if current_chapter:
                            builder.add_chapter(current_chapter_title, f'<div class="chapter">{current_chapter}</div>', 1)
                            chapter_count += 1
                        
                        builder.add_chapter("出版信息", f'<div class="publication-info">{text}</div>', 1)
                        current_chapter = ""
                        current_chapter_title = f"第 {chapter_count + 1} 章"
                    else:
                        # 继续当前章节
                        paragraphs = text.split('\n\n')
                        for para in paragraphs:
                            if para.strip():
                                current_chapter += f'<p>{para.strip()}</p>'
        
        # 添加最后一个章节
        if current_chapter:
            builder.add_chapter(current_chapter_title, f'<div class="chapter">{current_chapter}</div>', 1)
    else:
        logger.info("使用图像模式生成EPUB...")
        # 如果OCR失败或没有有效文本，使用图像模式
        
        # 添加封面
        if extracted_pages:
            first_page = extracted_pages[0]
            cover_image_path = first_page["image_path"]
            with open(cover_image_path, "rb") as f:
                cover_image_data = f.read()
            
            # 使用base64编码图像
            b64_image = base64.b64encode(cover_image_data).decode('utf-8')
            cover_html = f'<div class="cover"><img src="data:image/jpeg;base64,{b64_image}" alt="封面"/></div>'
            
            builder.add_chapter("封面", cover_html, 1)
            logger.info("  已添加封面")
        
        # 添加目录
        if len(extracted_pages) > 1:
            second_page = extracted_pages[1]
            toc_image_path = second_page["image_path"]
            with open(toc_image_path, "rb") as f:
                toc_image_data = f.read()
            
            # 使用base64编码图像
            b64_image = base64.b64encode(toc_image_data).decode('utf-8')
            toc_html = f'<div class="toc"><img src="data:image/jpeg;base64,{b64_image}" alt="目录"/></div>'
            
            builder.add_chapter("目录", toc_html, 1)
            logger.info("  已添加目录")
        
        # 将剩余页面分为适当的章节
        # 每5页一个章节，避免章节过多
        chapter_size = 5
        current_pages = []
        
        for page_info in extracted_pages[2:]:
            current_pages.append(page_info)
            
            # 当积累了足够的页面或达到最后一页时，创建一个章节
            if len(current_pages) >= chapter_size or page_info["page_num"] == extracted_pages[-1]["page_num"]:
                chapter_num = (current_pages[0]["page_num"] // chapter_size) + 1
                chapter_title = f"第 {chapter_num} 章"
                
                # 创建章节HTML
                chapter_html = f'<div class="chapter"><h1>{chapter_title}</h1>'
                
                # 添加每个页面的图像
                for page in current_pages:
                    with open(page["image_path"], "rb") as f:
                        page_image_data = f.read()
                    
                    # 使用base64编码图像
                    b64_image = base64.b64encode(page_image_data).decode('utf-8')
                    chapter_html += f'<div class="page"><img src="data:image/jpeg;base64,{b64_image}" alt="页面 {page["page_num"] + 1}"/></div>'
                
                chapter_html += '</div>'
                
                # 添加章节
                builder.add_chapter(chapter_title, chapter_html, 1)
                logger.info(f"  已添加章节: {chapter_title} (页面 {current_pages[0]['page_num'] + 1} - {current_pages[-1]['page_num'] + 1})")
                
                # 重置当前页面列表
                current_pages = []
    
    # 生成EPUB
    logger.info("生成EPUB文件...")
    builder.build()
    logger.info(f"EPUB文件已生成: {epub_path}")
    
    # 清理临时文件
    logger.info("清理临时文件...")
    for page_info in extracted_pages:
        try:
            os.remove(page_info["image_path"])
        except:
            pass
    try:
        os.rmdir(temp_dir)
    except:
        pass

def main():
    """
    主函数
    """
    # 设置日志
    logger = setup_logging()
    
    # 检查命令行参数
    if len(sys.argv) < 3:
        logger.error("用法: python test_conversion.py <pdf_path> <epub_path> [max_pages]")
        sys.exit(1)
    
    # 获取参数
    pdf_path = sys.argv[1]
    epub_path = sys.argv[2]
    max_pages = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    
    # 检查文件是否存在
    if not os.path.exists(pdf_path):
        logger.error(f"错误: PDF文件不存在: {pdf_path}")
        sys.exit(1)
    
    # 转换PDF到EPUB
    try:
        convert_pdf_to_epub(pdf_path, epub_path, max_pages)
    except Exception as e:
        logger.error(f"转换过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
