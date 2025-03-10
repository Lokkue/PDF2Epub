#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OCR处理器模块 - 使用大模型OCR功能
"""

import os
import time
import logging
import cv2
import numpy as np
import io
from PIL import Image
import configparser
import requests

# 配置日志
logger = logging.getLogger(__name__)


class OCRProcessor:
    """
    OCR处理器类 - 使用大模型OCR功能
    
    用于处理图像OCR识别，使用大模型的视觉OCR能力。
    """
    
    def __init__(self, model_name="qwen-vl-ocr", timeout=30, retry_count=3, 
                 batch_size=5, preprocess=False):
        """
        初始化OCR处理器
        
        参数:
            model_name: 大模型名称
            timeout: API超时时间（秒）
            retry_count: 重试次数
            batch_size: 批处理大小
            preprocess: 是否启用图像预处理
        """
        self.model_name = model_name
        self.timeout = timeout
        self.retry_count = retry_count
        self.batch_size = batch_size
        self.preprocess = preprocess

        # 读取配置文件
        config = configparser.ConfigParser()
        config_path = 'config/settings.ini'
        template_path = 'config/settings.ini.template'
        
        # 检查配置文件是否存在
        if not os.path.exists(config_path):
            if os.path.exists(template_path):
                logger.warning(f"配置文件 {config_path} 不存在，请根据模板 {template_path} 创建")
                raise FileNotFoundError(f"配置文件 {config_path} 不存在，请根据模板创建")
            else:
                logger.error(f"配置文件 {config_path} 和模板 {template_path} 都不存在")
                raise FileNotFoundError(f"配置文件和模板都不存在")
        
        config.read(config_path)
        
        try:
            self.api_url = config.get('ocr', 'api_url')
            self.api_key = config.get('ocr', 'api_key')
            
            # 验证API配置
            if not self.api_url or not self.api_key or self.api_key == "YOUR_API_KEY_HERE":
                logger.error("API配置无效，请在配置文件中设置有效的API URL和密钥")
                raise ValueError("API配置无效，请在配置文件中设置有效的API URL和密钥")
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            logger.error(f"配置文件格式错误: {e}")
            raise
        
        # 检查API连通性
        if not self._check_api_connectivity():
            raise Exception("OCR API无法连通")
        
        logger.info(f"初始化OCR处理器: 模型={model_name}, 预处理={preprocess}")
    
    def _check_api_connectivity(self):
        """
        检查OCR API连通性
        """
        try:
            # 使用 OpenAI 客户端验证连通性
            from openai import OpenAI
            import base64
            import numpy as np
            from PIL import Image
            
            # 创建一个简单的测试图像 - 白底黑字"测试"
            test_image = np.ones((100, 200, 3), dtype=np.uint8) * 255  # 白色背景
            # 添加一些黑色文本 (简化版本，实际上只是一个黑色矩形)
            test_image[40:60, 50:150] = 0
            
            # 将NumPy数组转换为PIL图像
            pil_image = Image.fromarray(test_image.astype('uint8'))
            
            # 将PIL图像转换为base64编码
            buffer = io.BytesIO()
            pil_image.save(buffer, format="JPEG")
            base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # 创建OpenAI客户端
            client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_url,
            )
            
            # 发送包含图像的请求
            logger.debug("发送OCR API连通性测试请求")
            completion = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": [{"type": "text", "text": "你是一个OCR助手，请识别图片中的文字。"}]},
                    {"role": "user", "content": [
                        {"type": "text", "text": "请识别这张图片中的文字"},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }}
                    ]},
                ],
                max_tokens=10  # 最小化请求以节省资源
            )
            
            logger.debug(f"OCR API连通性测试响应: {completion}")
            # 如果没有异常，则连接成功
            return True
        except ImportError:
            logger.warning("OpenAI 包未安装，无法验证 API 连通性")
            return False
        except Exception as e:
            logger.warning(f"OCR API连通性检查失败: {e}")
            return False
    
    def ocr_page(self, image):
        """
        OCR处理单页图像
        
        参数:
            image: 图像数据（NumPy数组或字节流）
            
        返回:
            dict: OCR结果，包含文本、置信度等信息
        """
        # 图像预处理
        if self.preprocess:
            image = self._preprocess_image(image)
        
        # 重试机制
        for attempt in range(self.retry_count):
            try:
                logger.debug(f"OCR处理尝试 {attempt+1}/{self.retry_count}")
                
                # 调用大模型OCR
                result = self._call_llm_ocr(image)
                
                logger.debug(f"OCR处理成功: 文本长度={len(result.get('text', ''))}")
                return result
                
            except Exception as e:
                logger.warning(f"OCR处理失败: {e}")
                
                if attempt < self.retry_count - 1:
                    # 指数退避
                    wait_time = 2 ** attempt
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"OCR处理失败，已达最大重试次数: {e}")
                    raise
    
    def batch_process(self, images):
        """
        批量处理多个图像
        
        参数:
            images: 图像列表
            
        返回:
            list: OCR结果列表
        """
        results = []
        
        for i, image in enumerate(images):
            logger.info(f"处理图像 {i+1}/{len(images)}")
            result = self.ocr_page(image)
            results.append(result)
        
        return results
    
    def _preprocess_image(self, image):
        """
        图像预处理
        
        参数:
            image: 原始图像
            
        返回:
            处理后的图像
        """
        logger.debug("执行图像预处理")
        
        # 确保图像是NumPy数组
        if isinstance(image, bytes):
            nparr = np.frombuffer(image, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 高斯模糊去噪
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 自适应二值化
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
    
    def _call_llm_ocr(self, image):
        """
        调用大模型OCR功能
        
        参数:
            image: 图像数据
            
        返回:
            dict: OCR结果
        """
        logger.debug(f"使用OpenAI兼容接口调用阿里云OCR服务")
        
        try:
            from openai import OpenAI
            import base64
            from io import BytesIO
            from PIL import Image as PILImage
            import tempfile
            import os
            import json
            
            # 确保图像是正确的格式
            if isinstance(image, np.ndarray):
                # 将NumPy数组转换为PIL图像
                if len(image.shape) == 2:  # 灰度图像
                    pil_image = PILImage.fromarray(image)
                    logger.debug(f"转换灰度图像为PIL图像，形状: {image.shape}")
                else:  # 彩色图像
                    # 确保图像是BGR格式（OpenCV默认）并转换为RGB（PIL需要）
                    if image.shape[2] == 3:  # 彩色图像
                        pil_image = PILImage.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                        logger.debug(f"转换BGR彩色图像为PIL图像，形状: {image.shape}")
                    else:  # 可能是BGRA
                        pil_image = PILImage.fromarray(cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA))
                        logger.debug(f"转换BGRA彩色图像为PIL图像，形状: {image.shape}")
            elif isinstance(image, bytes):
                # 已经是字节流，转换为PIL图像
                try:
                    pil_image = PILImage.open(BytesIO(image))
                    logger.debug(f"从字节流转换为PIL图像，大小: {len(image)} 字节")
                except Exception as e:
                    logger.error(f"无法解析图像字节流: {e}")
                    raise ValueError(f"无效的图像字节流: {e}")
            else:
                logger.error(f"不支持的图像格式: {type(image)}")
                raise ValueError(f"不支持的图像格式: {type(image)}")
            
            # 记录图像信息
            logger.debug(f"PIL图像大小: {pil_image.size}, 模式: {pil_image.mode}")
            
            # 将图像保存到临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                temp_image_path = temp_file.name
                pil_image.save(temp_image_path, format="PNG")
                logger.debug(f"图像已保存到临时文件: {temp_image_path}")
            
            try:
                # 将图像转换为base64编码
                def encode_image(image_path):
                    with open(image_path, "rb") as image_file:
                        return base64.b64encode(image_file.read()).decode("utf-8")
                
                # 获取图像的base64编码
                base64_image = encode_image(temp_image_path)
                logger.debug(f"图像已转换为base64编码，长度: {len(base64_image)}")
                
                # 检查临时文件是否存在且大小正常
                file_size = os.path.getsize(temp_image_path)
                logger.debug(f"临时文件大小: {file_size} 字节")
                
                # 创建OpenAI客户端
                client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.api_url,
                )
                logger.debug(f"已创建OpenAI客户端，API URL: {self.api_url}")
                
                # 构建消息
                messages = [
                    {
                        "role": "system",
                        "content": [{"type": "text", "text": "你是一个专业的OCR助手，请识别图片中的所有文字内容，保持原有格式。"}]
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                            },
                            {"type": "text", "text": "请识别这张图片中的所有文字内容，保持原有格式。"}
                        ]
                    }
                ]
                logger.debug(f"已构建请求消息，包含图像URL")
                
                # 记录完整请求信息（不包含图像数据）
                request_info = {
                    "model": self.model_name,
                    "message_count": len(messages),
                    "has_image": True,
                    "base64_length": len(base64_image),
                    "timeout": self.timeout
                }
                logger.debug(f"请求信息: {json.dumps(request_info)}")
                
                # 发送请求
                logger.debug(f"开始发送请求，使用模型: {self.model_name}")
                completion = client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    timeout=self.timeout
                )
                logger.debug(f"请求已完成，获取到响应")
                
                # 提取文本内容
                text_content = completion.choices[0].message.content
                logger.debug(f"提取的文本内容长度: {len(text_content)}")
                
                # 构建结果
                result = {
                    "text": text_content.strip(),
                    "confidence": 0.9,  # 大模型没有返回置信度，使用默认值
                    "blocks": [],  # 大模型没有返回块信息
                    "language": {
                        "code": "zh-CN",
                        "name": "简体中文"
                    }
                }
                
                return result
            except Exception as e:
                logger.error(f"调用OCR API过程中发生错误: {e}")
                # 尝试提供更详细的错误信息
                if hasattr(e, 'response') and hasattr(e.response, 'text'):
                    logger.error(f"API响应内容: {e.response.text}")
                raise e
            finally:
                # 清理临时文件
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
                    logger.debug(f"已删除临时文件: {temp_image_path}")
            
        except ImportError as e:
            logger.error(f"导入必要的包失败: {e}")
            raise Exception(f"导入必要的包失败: {e}")
        except Exception as e:
            logger.error(f"调用OCR API失败: {e}")
            raise Exception(f"调用OCR API失败: {e}")
    
    def detect_primary_language(self, ocr_result):
        """
        检测主要语言
        
        参数:
            ocr_result: OCR结果
            
        返回:
            str: 语言代码
        """
        if "language" not in ocr_result:
            return "unknown"
        
        # 找出置信度最高的语言
        languages = ocr_result["language"]
        if not languages:
            return "unknown"
        
        return max(languages.items(), key=lambda x: x[1])[0]
