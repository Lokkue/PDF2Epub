#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
信号处理器模块
"""

import os
import signal
import sys
import logging
import json
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)

# 全局变量
_cache_manager = None
_current_state = {}


def handle_interrupt(signum, frame):
    """
    处理中断信号（SIGINT, Ctrl+C）
    
    参数:
        signum: 信号编号
        frame: 当前帧
    """
    global _cache_manager, _current_state
    
    logger.warning("检测到用户中断，正在保存当前状态...")
    
    # 如果有缓存管理器，保存检查点
    if _cache_manager is not None and _current_state.get("task_id") and _current_state.get("page_num") is not None:
        try:
            # 保存检查点
            checkpoint_id = _cache_manager.save_checkpoint(
                task_id=_current_state["task_id"],
                current_page=_current_state["page_num"],
                state=_current_state
            )
            
            logger.info(f"状态已保存到检查点: ID={checkpoint_id}")
            
        except Exception as e:
            logger.error(f"保存检查点失败: {e}")
            
            # 尝试写入本地文件
            try:
                checkpoint_file = f"checkpoint_{_current_state.get('page_num', 'unknown')}.json"
                with open(checkpoint_file, "w", encoding="utf-8") as f:
                    json.dump(_current_state, f, ensure_ascii=False, indent=2)
                logger.info(f"状态已保存到文件: {checkpoint_file}")
            except Exception as e2:
                logger.error(f"保存到文件失败: {e2}")
    
    # 打印提示信息
    print("\n转换已中断，使用 --resume 参数可从断点继续")
    
    # 退出程序
    sys.exit(130)  # 130是SIGINT的标准退出码


def update_state(task_id=None, page_num=None, **kwargs):
    """
    更新当前状态
    
    参数:
        task_id: 任务ID
        page_num: 页码
        **kwargs: 其他状态信息
    """
    global _current_state
    
    if task_id is not None:
        _current_state["task_id"] = task_id
    
    if page_num is not None:
        _current_state["page_num"] = page_num
    
    # 更新其他状态信息
    _current_state.update(kwargs)
    
    # 添加时间戳
    _current_state["timestamp"] = datetime.now().isoformat()


def setup_signal_handlers(cache_manager=None):
    """
    设置信号处理器
    
    参数:
        cache_manager: 缓存管理器实例
    """
    global _cache_manager
    
    # 保存缓存管理器
    _cache_manager = cache_manager
    
    # 注册SIGINT处理器
    signal.signal(signal.SIGINT, handle_interrupt)
    
    logger.debug("信号处理器已设置")


def cleanup_checkpoints(directory=".", pattern="checkpoint_*.json", max_keep=3):
    """
    清理检查点文件
    
    参数:
        directory: 目录
        pattern: 文件模式
        max_keep: 保留的最大文件数
    """
    import glob
    
    # 获取所有检查点文件
    checkpoint_files = glob.glob(os.path.join(directory, pattern))
    
    # 如果文件数量不超过最大值，不需要清理
    if len(checkpoint_files) <= max_keep:
        return
    
    # 按修改时间排序
    checkpoint_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    # 删除旧文件
    for file_path in checkpoint_files[max_keep:]:
        try:
            os.remove(file_path)
            logger.debug(f"已删除旧检查点文件: {file_path}")
        except Exception as e:
            logger.warning(f"删除检查点文件失败: {file_path}, 错误: {e}")
