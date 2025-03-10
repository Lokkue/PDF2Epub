#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF2Epub - PDF转EPUB/MOBI工具
使用大模型OCR功能
"""

import os
import sys
import argparse
import logging
import configparser
import time
from datetime import datetime
import cv2
import numpy as np

# 导入核心模块
from core.pdf_parser import PDFParser
from core.ocr_processor import OCRProcessor
from core.epub_builder import EPUBBuilder
from core.page_processors import PROCESSOR_REGISTRY

# 导入工具模块
from utils.cache import CacheManager
from utils.logger import setup_logger
from utils.signal_handler import setup_signal_handlers, update_state


def parse_args():
    """
    解析命令行参数
    
    返回:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(description='PDF转EPUB/MOBI工具')
    
    # 必需参数
    parser.add_argument('input', help='输入PDF文件路径')
    
    # 可选参数
    parser.add_argument('-o', '--output', help='输出文件路径')
    parser.add_argument('-f', '--format', choices=['epub', 'mobi'], default='epub', help='输出格式 (默认: epub)')
    parser.add_argument('-t', '--title', help='书名')
    parser.add_argument('-a', '--author', help='作者')
    parser.add_argument('-l', '--language', default='zh-CN', help='语言代码 (默认: zh-CN)')
    parser.add_argument('-m', '--max-pages', type=int, help='最大处理页数')
    parser.add_argument('-r', '--resume', action='store_true', help='从断点继续')
    parser.add_argument('-c', '--clean-cache', action='store_true', help='清除缓存')
    parser.add_argument('-d', '--debug', action='store_true', help='启用调试模式')
    
    return parser.parse_args()


def load_config():
    """
    加载配置文件
    
    返回:
        configparser.ConfigParser: 配置对象
    """
    config = configparser.ConfigParser()
    
    # 默认配置文件路径
    config_paths = [
        './config/settings.ini',
        os.path.expanduser('~/.config/pdf2epub/settings.ini'),
        '/etc/pdf2epub/settings.ini'
    ]
    
    # 模板配置文件路径
    template_paths = [
        './config/settings.ini.template',
        os.path.expanduser('~/.config/pdf2epub/settings.ini.template'),
        '/etc/pdf2epub/settings.ini.template'
    ]
    
    # 尝试加载配置文件
    config_loaded = False
    for path in config_paths:
        if os.path.exists(path):
            config.read(path, encoding='utf-8')
            print(f"加载配置文件: {path}")
            config_loaded = True
            break
    
    # 如果没有找到配置文件，检查是否有模板文件
    if not config_loaded:
        template_found = None
        for path in template_paths:
            if os.path.exists(path):
                template_found = path
                break
        
        if template_found:
            error_msg = f"未找到配置文件。请根据模板创建配置文件: {template_found}"
            print(error_msg)
            raise FileNotFoundError(error_msg)
        else:
            error_msg = "未找到配置文件和模板文件"
            print(error_msg)
            raise FileNotFoundError(error_msg)
    
    return config


def setup_logging(config, debug=False):
    """
    设置日志系统
    
    参数:
        config: 配置对象
        debug: 是否启用调试模式
    
    返回:
        logging.Logger: 日志记录器
    """
    log_level = config.get('debug', 'log_level', fallback='INFO')
    log_format = config.get('debug', 'log_format', fallback='text')
    log_file = config.get('debug', 'log_file', fallback=None)
    
    if debug:
        log_level = 'DEBUG'
    
    return setup_logger(log_level, log_file, log_format, debug)


def process_pdf(args, config, logger):
    """
    处理PDF文件
    
    参数:
        args: 命令行参数
        config: 配置对象
        logger: 日志记录器
        
    返回:
        str: 输出文件路径
    """
    # 初始化缓存管理器
    db_path = config.get('cache', 'db_path', fallback='./pdf2epub_cache.db')
    auto_resume = config.getboolean('cache', 'auto_resume', fallback=True)
    checkpoint_interval = config.getint('cache', 'checkpoint_interval', fallback=10)
    max_checkpoints = config.getint('cache', 'max_checkpoints', fallback=3)
    
    cache_manager = CacheManager(
        db_path=db_path,
        auto_resume=auto_resume,
        checkpoint_interval=checkpoint_interval,
        max_checkpoints=max_checkpoints
    )
    
    # 设置信号处理器
    setup_signal_handlers(cache_manager)
    
    # 清除缓存
    if args.clean_cache:
        cache_manager.clear_all()
        logger.info("已清除所有缓存")
    
    # 初始化PDF解析器
    pdf_parser = PDFParser(args.input, max_pages=args.max_pages)
    page_count = pdf_parser.get_page_count()
    logger.info(f"PDF文件: {args.input}, 页数: {page_count}")
    
    # 初始化OCR处理器
    model_name = config.get('ocr', 'model_name', fallback='qwen-vl-ocr')
    timeout = config.getint('ocr', 'timeout', fallback=30)
    retry_count = config.getint('ocr', 'retry_count', fallback=3)
    batch_size = config.getint('ocr', 'batch_size', fallback=5)
    
    ocr_processor = OCRProcessor(
        model_name=model_name,
        timeout=timeout,
        retry_count=retry_count,
        batch_size=batch_size,
        preprocess=True
    )
    
    # 确定输出文件路径
    if args.output:
        output_file = args.output
    else:
        base_name = os.path.splitext(os.path.basename(args.input))[0]
        output_file = f"{base_name}.{args.format}"
    
    # 初始化EPUB构建器
    css_template = config.get('epub', 'css_template', fallback='default')
    toc_depth = config.getint('epub', 'toc_depth', fallback=3)
    max_image_width = config.getint('epub', 'max_image_width', fallback=800)
    max_image_height = config.getint('epub', 'max_image_height', fallback=1200)
    image_quality = config.getint('epub', 'image_quality', fallback=85)
    
    epub_builder = EPUBBuilder(
        output_file=output_file,
        format=args.format,
        css_template=css_template,
        toc_depth=toc_depth,
        max_image_width=max_image_width,
        max_image_height=max_image_height,
        image_quality=image_quality
    )
    
    # 设置元数据
    title = args.title or os.path.splitext(os.path.basename(args.input))[0]
    author = args.author or "未知作者"
    language = args.language
    
    epub_builder.set_metadata(title, author, language)
    
    # 创建任务
    task_id = None
    start_page = 0
    
    if args.resume or auto_resume:
        # 查找现有任务
        task = cache_manager.get_task_by_file_path(args.input)
        if task:
            task_id = task['id']
            logger.info(f"找到现有任务: {task_id}")
            
            # 获取最新检查点
            checkpoint = cache_manager.get_latest_checkpoint(task_id)
            if checkpoint:
                start_page = checkpoint['current_page'] + 1
                logger.info(f"从检查点继续: 页码 {start_page}")
    
    if not task_id:
        # 创建新任务
        metadata = {
            'file_path': args.input,
            'pages': page_count,
            'title': title,
            'author': author,
            'language': language,
            'format': args.format
        }
        task_id = cache_manager.create_task(args.input, metadata)
        logger.info(f"创建新任务: {task_id}")
    
    # 更新状态
    update_state(task_id=task_id, page_num=start_page)
    
    # 处理页面
    for page_num in range(start_page, page_count):
        logger.info(f"处理页面 {page_num+1}/{page_count}")
        update_state(page_num=page_num)
        
        # 检查是否有缓存
        cached_page = cache_manager.get_page_cache(task_id, page_num)
        if cached_page and cached_page.get('processed_text'):
            logger.info(f"使用缓存: 页码 {page_num+1}")
            processed_text = cached_page['processed_text']
            page_type = cached_page['page_type']
        else:
            # 提取图像
            image_data = pdf_parser.extract_image(page_num)
            
            # 检查是否有文本层
            has_text_layer = pdf_parser.has_text_layer(page_num)
            
            if has_text_layer:
                # 使用PDF文本层
                text = pdf_parser.extract_text(page_num)
                logger.debug(f"使用PDF文本层: 页码 {page_num+1}")
            else:
                # 使用OCR
                logger.debug(f"使用OCR: 页码 {page_num+1}")
                ocr_result = ocr_processor.ocr_page(image_data)
                text = ocr_result.get('text', '')
            
            # 处理页面
            processed_text, page_type = process_page(image_data, text)
            
            # 保存缓存
            cache_manager.save_page_cache(
                task_id=task_id,
                page_num=page_num,
                ocr_text=text,
                processed_text=processed_text,
                page_type=page_type
            )
        
        # 添加章节
        chapter_title = f"第 {page_num+1} 页"
        epub_builder.add_chapter(chapter_title, processed_text)
        
        # 保存检查点
        if page_num % checkpoint_interval == 0:
            checkpoint_id = cache_manager.save_checkpoint(
                task_id=task_id,
                current_page=page_num
            )
            logger.debug(f"保存检查点: ID={checkpoint_id}, 页码={page_num+1}")
        
        # 显示进度
        progress = (page_num + 1) / page_count * 100
        sys.stdout.write(f"\r进度: {progress:.1f}% ({page_num+1}/{page_count})")
        sys.stdout.flush()
    
    # 构建电子书
    logger.info("\n构建电子书...")
    output_path = epub_builder.build()
    
    # 关闭资源
    pdf_parser.close()
    cache_manager.close()
    
    return output_path


def process_page(image, text):
    """
    处理单个页面
    
    参数:
        image: 页面图像（字节数据或OpenCV图像）
        text: 页面文本
        
    返回:
        tuple: (处理后的HTML内容, 页面类型)
    """
    # 检查图像是否为字节数据，如果是则解码
    if isinstance(image, bytes):
        try:
            # 解码JPEG字节数据为OpenCV图像
            nparr = np.frombuffer(image, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            logger.debug("已将字节图像数据解码为OpenCV图像")
        except Exception as e:
            logger.error(f"图像解码失败: {e}")
            # 如果解码失败，返回空白页
            return "<div class='page'><p>图像处理失败</p></div>", "blank"
    
    # 检测页面类型
    best_processor = None
    best_confidence = 0
    
    for processor_class in PROCESSOR_REGISTRY:
        confidence = processor_class.detect(image, text)
        if confidence > best_confidence:
            best_confidence = confidence
            best_processor = processor_class
    
    # 使用最佳处理器
    if best_processor and best_confidence > 0.5:
        processor = best_processor(image, text)
        page_type = best_processor.__name__.replace('Processor', '').lower()
        logger.debug(f"使用 {page_type} 处理器 (置信度: {best_confidence:.2f})")
    else:
        # 使用默认处理器
        processor = PROCESSOR_REGISTRY[-1](image, text)
        page_type = 'base'
        logger.debug(f"使用默认处理器")
    
    # 处理页面
    processed_html = processor.process()
    
    return processed_html, page_type


def main():
    """
    主函数
    """
    # 解析命令行参数
    args = parse_args()
    
    try:
        # 加载配置
        config = load_config()
        
        # 设置日志
        global logger
        logger = setup_logging(config, args.debug)
        
        # 记录开始时间
        start_time = time.time()
        
        # 处理PDF
        output_path = process_pdf(args, config, logger)
        
        # 计算耗时
        elapsed_time = time.time() - start_time
        minutes, seconds = divmod(elapsed_time, 60)
        
        # 显示结果
        logger.info(f"\n转换完成! 耗时: {int(minutes)}分{int(seconds)}秒")
        logger.info(f"输出文件: {output_path}")
        
        return 0
        
    except KeyboardInterrupt:
        if 'logger' in globals():
            logger.warning("\n用户中断")
        else:
            print("\n用户中断")
        return 130
        
    except Exception as e:
        if 'logger' in globals():
            logger.error(f"转换失败: {e}", exc_info=args.debug if 'args' in locals() and hasattr(args, 'debug') else False)
        else:
            print(f"转换失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
