#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试PDF图像提取，为OCR或API调用做准备
"""

import os
import sys
import cv2
import numpy as np
from core.pdf_parser import PDFParser

def test_image_extraction(pdf_path, output_dir="extracted_images"):
    """
    从PDF中提取图像并保存到指定目录
    
    参数:
        pdf_path: PDF文件路径
        output_dir: 输出目录
    """
    print(f"从PDF中提取图像: {pdf_path}")
    
    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 使用PDFParser提取图像
    parser = PDFParser(pdf_path)
    print(f"PDF页数: {parser.page_count}")
    
    # 提取前5页的图像
    for page_num in range(min(5, int(parser.page_count))):
        print(f"处理第 {page_num + 1} 页...")
        
        # 提取图像
        image_data = parser.extract_image(page_num)
        
        if image_data:
            # 将JPEG字节数据解码为OpenCV图像
            try:
                nparr = np.frombuffer(image_data, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if image is not None:
                    # 保存图像
                    output_path = os.path.join(output_dir, f"page_{page_num + 1}.jpg")
                    cv2.imwrite(output_path, image)
                    print(f"  已保存图像: {output_path}")
                    
                    # 获取图像信息
                    height, width = image.shape[:2]
                    print(f"  图像尺寸: {width}x{height}")
                else:
                    print(f"  警告: 无法解码图像")
            except Exception as e:
                print(f"  错误: {e}")
        else:
            print(f"  警告: 未能提取图像")
    
    print(f"\n图像已提取到目录: {output_dir}")
    print("接下来可以使用OCR或大模型API对这些图像进行文本识别")

if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("用法: python test_image_extraction.py <pdf_file> [output_dir]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "extracted_images"
    
    test_image_extraction(pdf_path, output_dir)
