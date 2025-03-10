#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试缓存管理器模块
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import sys
import tempfile
import shutil
import json
import sqlite3
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入被测试模块
from utils.cache import CacheManager


class TestCacheManager(unittest.TestCase):
    """缓存管理器测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_cache.db")
        
        # 测试参数
        self.auto_resume = True
        self.checkpoint_interval = 10
        self.max_checkpoints = 3
        
        # 初始化缓存管理器
        self.cache_manager = CacheManager(
            db_path=self.db_path,
            auto_resume=self.auto_resume,
            checkpoint_interval=self.checkpoint_interval,
            max_checkpoints=self.max_checkpoints
        )
        
        # 测试数据
        self.test_task_id = "test_pdf_123"
        self.test_page_num = 42
        self.test_ocr_text = "这是OCR识别的文本内容"
        self.test_metadata = {
            "title": "测试文档",
            "author": "测试作者",
            "pages": 100
        }
    
    def tearDown(self):
        """测试后清理"""
        # 关闭数据库连接
        if hasattr(self.cache_manager, 'conn') and self.cache_manager.conn:
            self.cache_manager.conn.close()
        
        # 删除临时目录
        shutil.rmtree(self.test_dir)
    
    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.cache_manager.db_path, self.db_path)
        self.assertEqual(self.cache_manager.auto_resume, self.auto_resume)
        self.assertEqual(self.cache_manager.checkpoint_interval, self.checkpoint_interval)
        self.assertEqual(self.cache_manager.max_checkpoints, self.max_checkpoints)
        
        # 验证数据库表是否创建
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查任务表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
        self.assertIsNotNone(cursor.fetchone())
        
        # 检查页面缓存表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='page_cache'")
        self.assertIsNotNone(cursor.fetchone())
        
        # 检查检查点表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='checkpoints'")
        self.assertIsNotNone(cursor.fetchone())
        
        conn.close()
    
    def test_create_task(self):
        """测试创建任务"""
        task_id = self.cache_manager.create_task(
            file_path="test.pdf",
            metadata=self.test_metadata
        )
        
        # 验证任务ID
        self.assertIsNotNone(task_id)
        
        # 验证任务是否存在于数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
        task = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(task)
        self.assertEqual(task[1], "test.pdf")  # file_path
        
        # 解析JSON元数据并验证
        metadata = json.loads(task[2])
        self.assertEqual(metadata["title"], "测试文档")
    
    def test_save_page_cache(self):
        """测试保存页面缓存"""
        # 创建任务
        task_id = self.cache_manager.create_task(
            file_path="test.pdf",
            metadata=self.test_metadata
        )
        
        # 保存页面缓存
        self.cache_manager.save_page_cache(
            task_id=task_id,
            page_num=self.test_page_num,
            ocr_text=self.test_ocr_text,
            processed_text="处理后的文本",
            page_type="normal"
        )
        
        # 验证缓存是否存在于数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM page_cache WHERE task_id=? AND page_num=?",
            (task_id, self.test_page_num)
        )
        cache = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(cache)
        self.assertEqual(cache[1], task_id)           # task_id
        self.assertEqual(cache[2], self.test_page_num)  # page_num
        self.assertEqual(cache[3], self.test_ocr_text)  # ocr_text
        self.assertEqual(cache[4], "处理后的文本")      # processed_text
        self.assertEqual(cache[5], "normal")           # page_type
    
    def test_get_page_cache(self):
        """测试获取页面缓存"""
        # 创建任务
        task_id = self.cache_manager.create_task(
            file_path="test.pdf",
            metadata=self.test_metadata
        )
        
        # 保存页面缓存
        self.cache_manager.save_page_cache(
            task_id=task_id,
            page_num=self.test_page_num,
            ocr_text=self.test_ocr_text,
            processed_text="处理后的文本",
            page_type="normal"
        )
        
        # 获取页面缓存
        cache = self.cache_manager.get_page_cache(
            task_id=task_id,
            page_num=self.test_page_num
        )
        
        # 验证缓存内容
        self.assertIsNotNone(cache)
        self.assertEqual(cache["ocr_text"], self.test_ocr_text)
        self.assertEqual(cache["processed_text"], "处理后的文本")
        self.assertEqual(cache["page_type"], "normal")
    
    def test_get_nonexistent_page_cache(self):
        """测试获取不存在的页面缓存"""
        # 创建任务
        task_id = self.cache_manager.create_task(
            file_path="test.pdf",
            metadata=self.test_metadata
        )
        
        # 获取不存在的页面缓存
        cache = self.cache_manager.get_page_cache(
            task_id=task_id,
            page_num=999  # 不存在的页码
        )
        
        # 验证返回None
        self.assertIsNone(cache)
    
    def test_save_checkpoint(self):
        """测试保存检查点"""
        # 创建任务
        task_id = self.cache_manager.create_task(
            file_path="test.pdf",
            metadata=self.test_metadata
        )
        
        # 保存检查点
        checkpoint_id = self.cache_manager.save_checkpoint(
            task_id=task_id,
            current_page=self.test_page_num,
            state={"status": "processing", "progress": 0.42}
        )
        
        # 验证检查点ID
        self.assertIsNotNone(checkpoint_id)
        
        # 验证检查点是否存在于数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM checkpoints WHERE id=?", (checkpoint_id,))
        checkpoint = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(checkpoint)
        self.assertEqual(checkpoint[1], task_id)           # task_id
        self.assertEqual(checkpoint[2], self.test_page_num)  # current_page
        self.assertIn("processing", checkpoint[3])         # state
    
    def test_get_latest_checkpoint(self):
        """测试获取最新检查点"""
        # 创建任务
        task_id = self.cache_manager.create_task(
            file_path="test.pdf",
            metadata=self.test_metadata
        )
        
        # 保存多个检查点
        self.cache_manager.save_checkpoint(
            task_id=task_id,
            current_page=10,
            state={"status": "processing", "progress": 0.1}
        )
        
        self.cache_manager.save_checkpoint(
            task_id=task_id,
            current_page=20,
            state={"status": "processing", "progress": 0.2}
        )
        
        latest_checkpoint_id = self.cache_manager.save_checkpoint(
            task_id=task_id,
            current_page=30,
            state={"status": "processing", "progress": 0.3}
        )
        
        # 获取最新检查点
        checkpoint = self.cache_manager.get_latest_checkpoint(task_id=task_id)
        
        # 验证检查点内容
        self.assertIsNotNone(checkpoint)
        self.assertEqual(checkpoint["id"], latest_checkpoint_id)
        self.assertEqual(checkpoint["current_page"], 30)
        self.assertEqual(checkpoint["state"]["progress"], 0.3)
    
    def test_cleanup_old_checkpoints(self):
        """测试清理旧检查点"""
        # 创建任务
        task_id = self.cache_manager.create_task(
            file_path="test.pdf",
            metadata=self.test_metadata
        )
        
        # 保存多个检查点（超过max_checkpoints）
        for i in range(5):  # 保存5个检查点，max_checkpoints=3
            self.cache_manager.save_checkpoint(
                task_id=task_id,
                current_page=i * 10,
                state={"status": "processing", "progress": i * 0.1}
            )
        
        # 验证只保留了最新的max_checkpoints个检查点
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM checkpoints WHERE task_id=?", (task_id,))
        count = cursor.fetchone()[0]
        conn.close()
        
        self.assertEqual(count, self.max_checkpoints)
    
    def test_clear_task_cache(self):
        """测试清除任务缓存"""
        # 创建任务
        task_id = self.cache_manager.create_task(
            file_path="test.pdf",
            metadata=self.test_metadata
        )
        
        # 保存页面缓存
        self.cache_manager.save_page_cache(
            task_id=task_id,
            page_num=self.test_page_num,
            ocr_text=self.test_ocr_text,
            processed_text="处理后的文本",
            page_type="normal"
        )
        
        # 保存检查点
        self.cache_manager.save_checkpoint(
            task_id=task_id,
            current_page=self.test_page_num,
            state={"status": "processing", "progress": 0.42}
        )
        
        # 清除任务缓存
        self.cache_manager.clear_task_cache(task_id=task_id)
        
        # 验证缓存和检查点已被清除
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM page_cache WHERE task_id=?", (task_id,))
        page_cache_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM checkpoints WHERE task_id=?", (task_id,))
        checkpoint_count = cursor.fetchone()[0]
        
        conn.close()
        
        self.assertEqual(page_cache_count, 0)
        self.assertEqual(checkpoint_count, 0)
    
    def test_clear_all(self):
        """测试清除所有缓存"""
        # 创建多个任务
        task_id1 = self.cache_manager.create_task(
            file_path="test1.pdf",
            metadata={"title": "测试文档1"}
        )
        
        task_id2 = self.cache_manager.create_task(
            file_path="test2.pdf",
            metadata={"title": "测试文档2"}
        )
        
        # 保存页面缓存
        self.cache_manager.save_page_cache(
            task_id=task_id1,
            page_num=1,
            ocr_text="文本1",
            processed_text="处理后的文本1",
            page_type="normal"
        )
        
        self.cache_manager.save_page_cache(
            task_id=task_id2,
            page_num=1,
            ocr_text="文本2",
            processed_text="处理后的文本2",
            page_type="normal"
        )
        
        # 清除所有缓存
        self.cache_manager.clear_all()
        
        # 验证所有缓存已被清除
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM tasks")
        tasks_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM page_cache")
        page_cache_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM checkpoints")
        checkpoint_count = cursor.fetchone()[0]
        
        conn.close()
        
        self.assertEqual(tasks_count, 0)
        self.assertEqual(page_cache_count, 0)
        self.assertEqual(checkpoint_count, 0)
    
    def test_get_task_progress(self):
        """测试获取任务进度"""
        # 创建任务
        task_id = self.cache_manager.create_task(
            file_path="test.pdf",
            metadata={"title": "测试文档", "pages": 100}
        )
        
        # 保存多个页面缓存
        for i in range(1, 51):  # 保存50页缓存，总页数100
            self.cache_manager.save_page_cache(
                task_id=task_id,
                page_num=i,
                ocr_text=f"页面{i}的文本",
                processed_text=f"处理后的页面{i}文本",
                page_type="normal"
            )
        
        # 获取任务进度
        progress = self.cache_manager.get_task_progress(task_id=task_id)
        
        # 验证进度
        self.assertEqual(progress, 0.5)  # 50/100 = 0.5
    
    def test_get_task_by_file_path(self):
        """测试通过文件路径获取任务"""
        # 创建任务
        original_task_id = self.cache_manager.create_task(
            file_path="unique_test.pdf",
            metadata=self.test_metadata
        )
        
        # 通过文件路径获取任务
        task = self.cache_manager.get_task_by_file_path(file_path="unique_test.pdf")
        
        # 验证任务内容
        self.assertIsNotNone(task)
        self.assertEqual(task["id"], original_task_id)
        self.assertEqual(task["file_path"], "unique_test.pdf")
        self.assertEqual(json.loads(task["metadata"])["title"], "测试文档")
    
    def test_get_nonexistent_task(self):
        """测试获取不存在的任务"""
        # 通过不存在的文件路径获取任务
        task = self.cache_manager.get_task_by_file_path(file_path="nonexistent.pdf")
        
        # 验证返回None
        self.assertIsNone(task)


if __name__ == '__main__':
    unittest.main()
