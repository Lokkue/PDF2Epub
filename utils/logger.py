#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日志系统模块
"""

import os
import logging
import json
from logging.handlers import RotatingFileHandler


def setup_logger(log_level="INFO", log_file=None, log_format="text", debug=False):
    """
    设置日志系统
    
    参数:
        log_level: 日志级别
        log_file: 日志文件路径
        log_format: 日志格式（text或json）
        debug: 是否启用调试模式
        
    返回:
        logging.Logger: 日志记录器
    """
    # 转换日志级别
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    if debug:
        numeric_level = logging.DEBUG
    
    # 创建根日志记录器
    logger = logging.getLogger()
    logger.setLevel(numeric_level)
    
    # 清除现有处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    
    # 设置格式化器
    if log_format.lower() == "json":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 如果指定了日志文件，添加文件处理器
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(os.path.abspath(log_file))
        os.makedirs(log_dir, exist_ok=True)
        
        # 创建文件处理器
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # 创建Toepub专用日志记录器
    toepub_logger = logging.getLogger('toepub')
    
    # 记录初始日志
    toepub_logger.info(f"日志系统初始化: 级别={log_level}, 格式={log_format}")
    if debug:
        toepub_logger.debug("调试模式已启用")
    
    return toepub_logger


class JsonFormatter(logging.Formatter):
    """
    JSON格式日志格式化器
    """
    
    def format(self, record):
        """
        格式化日志记录
        
        参数:
            record: 日志记录
            
        返回:
            str: 格式化后的日志
        """
        log_data = {
            "time": self.formatTime(record, datefmt='%Y-%m-%d %H:%M:%S'),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage()
        }
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # 添加额外字段
        for key, value in record.__dict__.items():
            if key not in ["args", "asctime", "created", "exc_info", "exc_text", 
                          "filename", "funcName", "id", "levelname", "levelno", 
                          "lineno", "module", "msecs", "message", "msg", 
                          "name", "pathname", "process", "processName", 
                          "relativeCreated", "stack_info", "thread", "threadName"]:
                log_data[key] = value
        
        return json.dumps(log_data, ensure_ascii=False)
