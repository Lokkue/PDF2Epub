#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
缓存管理器模块
"""

import os
import sqlite3
import json
import logging
import time
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)


class CacheManager:
    """
    缓存管理器类
    
    用于管理转换过程中的缓存和断点续传。
    """
    
    def __init__(self, db_path="./toepub_cache.db", auto_resume=True, 
                 checkpoint_interval=10, max_checkpoints=3):
        """
        初始化缓存管理器
        
        参数:
            db_path: 数据库文件路径
            auto_resume: 是否自动恢复
            checkpoint_interval: 检查点间隔（页数）
            max_checkpoints: 最大检查点数量
        """
        self.db_path = db_path
        self.auto_resume = auto_resume
        self.checkpoint_interval = checkpoint_interval
        self.max_checkpoints = max_checkpoints
        
        # 创建数据库目录
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        
        # 连接数据库
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        
        # 初始化数据库表
        self._init_db()
        
        logger.info(f"初始化缓存管理器: 数据库={db_path}, 自动恢复={auto_resume}")
    
    def _init_db(self):
        """
        初始化数据库表
        """
        cursor = self.conn.cursor()
        
        # 创建任务表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            file_path TEXT NOT NULL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # 创建页面缓存表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS page_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            page_num INTEGER NOT NULL,
            ocr_text TEXT,
            processed_text TEXT,
            page_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id),
            UNIQUE(task_id, page_num)
        )
        """)
        
        # 创建检查点表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            current_page INTEGER NOT NULL,
            state TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
        """)
        
        self.conn.commit()
    
    def create_task(self, file_path, metadata=None):
        """
        创建任务
        
        参数:
            file_path: 文件路径
            metadata: 元数据字典
            
        返回:
            str: 任务ID
        """
        # 生成任务ID
        task_id = f"task_{int(time.time())}_{os.path.basename(file_path)}"
        
        # 序列化元数据
        metadata_json = json.dumps(metadata) if metadata else "{}"
        
        # 插入任务记录
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (id, file_path, metadata) VALUES (?, ?, ?)",
            (task_id, file_path, metadata_json)
        )
        self.conn.commit()
        
        logger.info(f"创建任务: ID={task_id}, 文件={file_path}")
        return task_id
    
    def get_task_by_file_path(self, file_path):
        """
        通过文件路径获取任务
        
        参数:
            file_path: 文件路径
            
        返回:
            dict: 任务信息，如果不存在则返回None
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM tasks WHERE file_path = ? ORDER BY created_at DESC LIMIT 1",
            (file_path,)
        )
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def save_page_cache(self, task_id, page_num, ocr_text, processed_text=None, page_type="normal"):
        """
        保存页面缓存
        
        参数:
            task_id: 任务ID
            page_num: 页码
            ocr_text: OCR文本
            processed_text: 处理后的文本
            page_type: 页面类型
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO page_cache 
            (task_id, page_num, ocr_text, processed_text, page_type) 
            VALUES (?, ?, ?, ?, ?)
            """,
            (task_id, page_num, ocr_text, processed_text, page_type)
        )
        self.conn.commit()
        
        logger.debug(f"保存页面缓存: 任务={task_id}, 页码={page_num}, 类型={page_type}")
    
    def get_page_cache(self, task_id, page_num):
        """
        获取页面缓存
        
        参数:
            task_id: 任务ID
            page_num: 页码
            
        返回:
            dict: 页面缓存，如果不存在则返回None
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM page_cache WHERE task_id = ? AND page_num = ?",
            (task_id, page_num)
        )
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def save_checkpoint(self, task_id, current_page, state=None):
        """
        保存检查点
        
        参数:
            task_id: 任务ID
            current_page: 当前页码
            state: 状态信息
            
        返回:
            int: 检查点ID
        """
        # 序列化状态
        state_json = json.dumps(state) if state else "{}"
        
        # 插入检查点记录
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO checkpoints (task_id, current_page, state) VALUES (?, ?, ?)",
            (task_id, current_page, state_json)
        )
        checkpoint_id = cursor.lastrowid
        self.conn.commit()
        
        logger.info(f"保存检查点: ID={checkpoint_id}, 任务={task_id}, 页码={current_page}")
        
        # 清理旧检查点
        self._cleanup_old_checkpoints(task_id)
        
        return checkpoint_id
    
    def _cleanup_old_checkpoints(self, task_id):
        """
        清理旧检查点
        
        参数:
            task_id: 任务ID
        """
        cursor = self.conn.cursor()
        
        # 获取检查点数量
        cursor.execute(
            "SELECT COUNT(*) FROM checkpoints WHERE task_id = ?",
            (task_id,)
        )
        count = cursor.fetchone()[0]
        
        # 如果超过最大数量，删除最旧的检查点
        if count > self.max_checkpoints:
            # 计算需要删除的数量
            to_delete = count - self.max_checkpoints
            
            # 获取最旧的检查点ID
            cursor.execute(
                """
                SELECT id FROM checkpoints 
                WHERE task_id = ? 
                ORDER BY created_at ASC 
                LIMIT ?
                """,
                (task_id, to_delete)
            )
            old_ids = [row[0] for row in cursor.fetchall()]
            
            # 删除旧检查点
            if old_ids:
                placeholders = ",".join(["?"] * len(old_ids))
                cursor.execute(
                    f"DELETE FROM checkpoints WHERE id IN ({placeholders})",
                    old_ids
                )
                self.conn.commit()
                
                logger.debug(f"清理旧检查点: 任务={task_id}, 删除数量={len(old_ids)}")
    
    def get_latest_checkpoint(self, task_id):
        """
        获取最新检查点
        
        参数:
            task_id: 任务ID
            
        返回:
            dict: 检查点信息，如果不存在则返回None
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM checkpoints 
            WHERE task_id = ? 
            ORDER BY id DESC 
            LIMIT 1
            """,
            (task_id,)
        )
        row = cursor.fetchone()
        
        if row:
            checkpoint = dict(row)
            # 解析状态JSON
            if checkpoint["state"]:
                checkpoint["state"] = json.loads(checkpoint["state"])
            return checkpoint
        return None
    
    def get_task_progress(self, task_id):
        """
        获取任务进度
        
        参数:
            task_id: 任务ID
            
        返回:
            float: 进度（0-1）
        """
        cursor = self.conn.cursor()
        
        # 获取任务元数据
        cursor.execute("SELECT metadata FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            return 0.0
        
        metadata = json.loads(row[0])
        total_pages = metadata.get("pages", 0)
        if total_pages <= 0:
            return 0.0
        
        # 获取已处理页数
        cursor.execute(
            "SELECT COUNT(*) FROM page_cache WHERE task_id = ?",
            (task_id,)
        )
        processed_pages = cursor.fetchone()[0]
        
        # 计算进度
        progress = min(1.0, processed_pages / total_pages)
        return progress
    
    def clear_task_cache(self, task_id):
        """
        清除任务缓存
        
        参数:
            task_id: 任务ID
        """
        cursor = self.conn.cursor()
        
        # 删除页面缓存
        cursor.execute("DELETE FROM page_cache WHERE task_id = ?", (task_id,))
        
        # 删除检查点
        cursor.execute("DELETE FROM checkpoints WHERE task_id = ?", (task_id,))
        
        self.conn.commit()
        logger.info(f"清除任务缓存: 任务={task_id}")
    
    def clear_all(self):
        """
        清除所有缓存
        """
        cursor = self.conn.cursor()
        
        # 删除所有数据
        cursor.execute("DELETE FROM page_cache")
        cursor.execute("DELETE FROM checkpoints")
        cursor.execute("DELETE FROM tasks")
        
        self.conn.commit()
        logger.info("清除所有缓存")
    
    def close(self):
        """
        关闭数据库连接
        """
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.debug("关闭缓存数据库连接")
    
    def __del__(self):
        """
        析构函数
        """
        self.close()
