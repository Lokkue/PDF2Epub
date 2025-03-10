#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Toepub - PDF转EPUB工具
主程序入口
"""

import sys
import os

# 确保当前目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入main模块
from main import main

if __name__ == "__main__":
    # 直接调用main函数
    main()
