"""
页面处理器模块

此模块包含用于处理不同类型页面的处理器类。
"""

from .base import BaseProcessor
from .cover import CoverProcessor
from .toc import TOCProcessor
from .footnote import FootnoteProcessor
from .table import TableProcessor

# 处理器注册表（按优先级排序）
PROCESSOR_REGISTRY = [
    CoverProcessor,
    TOCProcessor,
    FootnoteProcessor,
    TableProcessor,
    # 通用处理器应放在最后
    BaseProcessor  # 默认文本处理器
]
