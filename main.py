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
from tqdm import tqdm

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
    parser.add_argument('-v', '--verbose', action='count', default=0, help='详细程度 (默认: 0)')
    
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


def setup_logging(config, debug=False, verbose=0):
    """
    设置日志系统
    
    参数:
        config: 配置对象
        debug: 是否启用调试模式
        verbose: 详细程度 (0=基础, 1=信息, 2=开发者)
    
    返回:
        logging.Logger: 日志记录器
    """
    # 创建日志记录器
    logger = logging.getLogger('toepub')
    
    # 设置日志级别
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        if verbose == 0:
            logger.setLevel(logging.WARNING)
        elif verbose == 1:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.DEBUG)
    
    # 清除现有处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    
    # 设置格式
    if verbose == 0:
        # 基础级别：简洁彩色输出
        formatter = ColoredFormatter('%(levelname_colored)s: %(message)s')
    elif verbose == 1:
        # 信息级别：包含时间和模块
        formatter = ColoredFormatter('%(asctime)s - %(levelname_colored)s: %(message)s', 
                                    datefmt='%H:%M:%S')
    else:
        # 开发者级别：详细信息
        formatter = ColoredFormatter('%(asctime)s - %(name)s.%(module)s - %(levelname_colored)s: %(message)s',
                                    datefmt='%H:%M:%S')
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 设置第三方库的日志级别
    if not debug:
        logging.getLogger('httpcore').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('openai').setLevel(logging.WARNING)
    
    return logger

class ColoredFormatter(logging.Formatter):
    """
    彩色日志格式化器
    """
    COLORS = {
        'DEBUG': '\033[94m',  # 蓝色
        'INFO': '\033[92m',   # 绿色
        'WARNING': '\033[93m', # 黄色
        'ERROR': '\033[91m',  # 红色
        'CRITICAL': '\033[91m\033[1m',  # 红色加粗
        'RESET': '\033[0m'    # 重置
    }
    
    def format(self, record):
        # 添加彩色级别
        levelname = record.levelname
        record.levelname_colored = f"{self.COLORS.get(levelname, '')}{levelname}{self.COLORS['RESET']}"
        
        # 限制长消息
        if record.levelno == logging.DEBUG and len(record.msg) > 500:
            record.msg = record.msg[:500] + "... [内容已截断]"
            
        return super().format(record)


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
    input_file = args.input
    output_file = args.output
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        logger.error(f"输入文件不存在: {input_file}")
        return None
    
    # 初始化token计数器
    total_tokens = 0
    total_pages_with_ocr = 0
    
    # 创建PDF解析器
    pdf_parser = PDFParser(input_file, args.max_pages)
    page_count = pdf_parser.get_page_count()
    
    logger.info(f" PDF文件: {os.path.basename(input_file)} ({page_count}页)")
    
    # 初始化OCR处理器
    ocr_processor = OCRProcessor(config, logger)
    
    # 初始化缓存管理器
    cache_db_path = "./pdf2epub_cache.db"  # 默认路径
    if 'Cache' in config and 'db_path' in config['Cache']:
        cache_db_path = config['Cache']['db_path']
    
    cache_manager = CacheManager(cache_db_path)
    
    # 初始化EPUB构建器
    epub_builder = EPUBBuilder(
        output_file
    )
    
    # 设置元数据
    title = args.title or os.path.splitext(os.path.basename(args.input))[0]
    author = args.author or "未知作者"
    language = args.language
    
    epub_builder.set_metadata(title, author, language)
    
    # 创建任务
    task_id = None
    start_page = 0
    
    # 检查是否自动恢复
    auto_resume = False  # 默认不自动恢复
    if 'General' in config and 'auto_resume' in config['General']:
        auto_resume = config['General'].getboolean('auto_resume')
    
    if args.resume or auto_resume:
        # 查找现有任务
        task = cache_manager.get_task_by_file_path(args.input)
        if task:
            task_id = task['id']
            logger.info(f" 找到现有任务: {task_id}")
            
            # 获取最新检查点
            checkpoint = cache_manager.get_latest_checkpoint(task_id)
            if checkpoint:
                start_page = checkpoint['current_page'] + 1
                logger.info(f" 从检查点继续: 页码 {start_page}")
    
    if not task_id:
        # 创建新任务
        metadata = {
            'file_path': args.input,
            'pages': page_count,
            'title': title,
            'author': author
        }
        task_id = cache_manager.create_task(args.input, metadata)
        logger.info(f" 创建新任务: {task_id}")
    
    # 处理页面
    try:
        # 使用tqdm创建进度条
        pbar = tqdm(total=page_count, desc=" 转换进度", unit="页", 
                   bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")
        
        # 更新进度条到起始位置
        if start_page > 0:
            pbar.update(start_page)
        
        for page_num in range(start_page, page_count):
            # 检查缓存
            cache = cache_manager.get_page_cache(task_id, page_num)
            if cache:
                logger.debug(f"使用缓存: 页码 {page_num+1}")
                processed_text = cache['processed_text']
                page_type = cache['page_type']
            else:
                # 获取页面图像
                image_data = pdf_parser.extract_image(page_num)
                
                # 检查是否有文本层
                has_text_layer = pdf_parser.has_text_layer(page_num)
                
                if has_text_layer:
                    # 使用PDF文本层
                    text = pdf_parser.extract_text(page_num)
                    if args.verbose >= 1:
                        pass
                    else:
                        logger.debug(f"使用PDF文本层: 页码 {page_num+1}")
                else:
                    # 使用OCR
                    if args.verbose >= 1:
                        pass
                    else:
                        logger.debug(f"使用OCR: 页码 {page_num+1}")
                    
                    ocr_result = ocr_processor.ocr_page(image_data)
                    text = ocr_result.get('text', '')
                    
                    # 累计token使用量
                    if 'token_usage' in ocr_result:
                        tokens_used = ocr_result['token_usage']
                        total_tokens += tokens_used
                        total_pages_with_ocr += 1
                        if args.verbose >= 1:
                            pass
                
                # 处理页面
                # 确保image_data是字节数据或OpenCV图像，而不是字典
                if isinstance(image_data, dict) and 'image' in image_data:
                    image_for_processing = image_data['image']
                else:
                    image_for_processing = image_data
                
                processed_text, page_type = process_page(image_for_processing, text)
                
                # 保存缓存
                cache_manager.save_page_cache(
                    task_id=task_id,
                    page_num=page_num,
                    ocr_text=text,
                    processed_text=processed_text,
                    page_type=page_type
                )
            
            # 添加到EPUB
            epub_builder.add_page(processed_text, page_type)
            
            # 创建检查点
            cache_manager.save_checkpoint(task_id, page_num)
            
            # 更新进度条
            pbar.update(1)
            
            # 更新进度条描述以显示token使用情况和当前页码
            if total_tokens > 0:
                pbar.set_description(f" 转换进度 (页 {page_num+1}/{page_count}, 已用tokens: {total_tokens})")
            else:
                pbar.set_description(f" 转换进度 (页 {page_num+1}/{page_count})")
        
        # 关闭进度条
        pbar.close()
        
        # 构建EPUB
        logger.info(" 构建EPUB文件...")
        epub_builder.build()
        
        # 显示token使用统计
        if total_tokens > 0:
            logger.info(f" 总共使用了 {total_tokens} tokens，处理了 {total_pages_with_ocr} 页OCR文本")
            # 估算成本 (按照GPT-4的价格估算)
            estimated_cost = (total_tokens / 1000) * 0.01  # 假设每1K tokens $0.01
            logger.info(f" 估算成本: ${estimated_cost:.4f}")
            if total_pages_with_ocr > 0:
                avg_tokens = total_tokens / total_pages_with_ocr
                logger.info(f" 平均每页OCR使用 {avg_tokens:.1f} tokens")
        
        logger.info(f" 转换完成! 输出文件: {output_file}")
        
        return output_file
        
    except Exception as e:
        logger.error(f"转换失败: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        return None
    finally:
        # 关闭PDF
        pdf_parser.close()


def process_page(image, text):
    """
    处理页面内容
    
    参数:
        image: 页面图像（字节数据或图像对象）
        text: 页面文本
        
    返回:
        tuple: (处理后的HTML内容, 页面类型)
    """
    # 检查图像是否为字节数据，如果是则解码
    if isinstance(image, bytes):
        try:
            # 解码图像数据
            nparr = np.frombuffer(image, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            logger.debug("已将图像数据解码为处理格式")
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
        logger = setup_logging(config, args.debug, args.verbose)
        
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
