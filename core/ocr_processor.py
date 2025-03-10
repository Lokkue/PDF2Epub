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
    
    def __init__(self, config, logger=None):
        """
        初始化OCR处理器
        
        参数:
            config: 配置对象
            logger: 日志记录器
        """
        # 设置日志记录器
        self.logger = logger or logging.getLogger(__name__)
        
        # 从配置中读取OCR设置
        self.model_name = config.get('ocr', 'model_name', fallback='qwen-vl-max')
        self.timeout = config.getint('ocr', 'timeout', fallback=30)
        self.retry_count = config.getint('ocr', 'retry_count', fallback=3)
        self.batch_size = config.getint('ocr', 'batch_size', fallback=5)
        self.preprocess = config.getboolean('ocr', 'preprocess', fallback=False)
        
        # 读取API配置
        self.api_url = config.get('ocr', 'api_url')
        self.api_key = config.get('ocr', 'api_key')
        
        # 验证API配置
        if not self.api_url or not self.api_key or self.api_key == "YOUR_API_KEY_HERE":
            self.logger.error("API配置无效，请在配置文件中设置有效的API URL和密钥")
            raise ValueError("API配置无效，请在配置文件中设置有效的API URL和密钥")
        
        # 初始化token计数器
        self.total_tokens = 0
        
        # 检查API连通性
        if not self._check_api_connectivity():
            raise Exception("OCR API无法连通")
        
        self.logger.info(f"🔍 初始化OCR处理器: 模型={self.model_name}")
    
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
            self.logger.debug("发送OCR API连通性测试请求")
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
            
            self.logger.debug(f"OCR API连通性测试响应: {completion}")
            # 如果没有异常，则连接成功
            return True
        except ImportError:
            self.logger.warning("OpenAI 包未安装，无法验证 API 连通性")
            return False
        except Exception as e:
            self.logger.warning(f"OCR API连通性检查失败: {e}")
            return False
    
    def ocr_page(self, image, page_type="text"):
        """
        OCR处理单页图像
        
        参数:
            image: 图像数据（NumPy数组或字节流）
            page_type: 页面类型（text, toc, table, footnote, image_caption等）
            
        返回:
            dict: OCR结果，包含文本、置信度等信息
        """
        # 图像预处理
        if self.preprocess:
            image = self._preprocess_image(image)
        
        # 重试机制
        for attempt in range(self.retry_count):
            try:
                self.logger.debug(f"OCR处理尝试 {attempt+1}/{self.retry_count}, 页面类型: {page_type}")
                
                # 调用大模型OCR，传递页面类型
                result = self._call_llm_ocr(image, page_type)
                
                # 记录文本长度
                text_length = len(result.get('text', ''))
                self.logger.debug(f"OCR处理成功: 文本长度={text_length}")
                
                # 更新token使用情况
                if 'token_usage' in result:
                    token_usage = result['token_usage']
                    self.total_tokens += token_usage
                    if self.logger:
                        self.logger.debug(f"🔢 累计token使用量: {self.total_tokens}")
                
                return result
                
            except Exception as e:
                self.logger.warning(f"OCR处理失败: {e}")
                
                if attempt < self.retry_count - 1:
                    # 指数退避
                    wait_time = 2 ** attempt
                    self.logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"OCR处理失败，已达最大重试次数: {e}")
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
            self.logger.info(f"处理图像 {i+1}/{len(images)}")
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
        self.logger.debug("执行图像预处理")
        
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
    
    def _call_llm_ocr(self, image, page_type="text"):
        """
        调用大模型OCR功能
        
        参数:
            image: 图像数据
            page_type: 页面类型（text, toc, table, footnote, image_caption等）
            
        返回:
            dict: OCR结果
        """
        self.logger.debug(f"使用OpenAI兼容接口调用阿里云OCR服务，页面类型: {page_type}")
        
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
                    self.logger.debug(f"转换灰度图像为PIL图像")
                else:  # 彩色图像
                    # 确保图像是BGR格式（OpenCV默认）并转换为RGB（PIL需要）
                    if image.shape[2] == 3:  # 彩色图像
                        pil_image = PILImage.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                        self.logger.debug(f"转换BGR彩色图像为PIL图像")
                    else:  # 可能是BGRA
                        pil_image = PILImage.fromarray(cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA))
                        self.logger.debug(f"转换BGRA彩色图像为PIL图像")
            elif isinstance(image, bytes):
                # 已经是字节流，转换为PIL图像
                try:
                    pil_image = PILImage.open(BytesIO(image))
                    self.logger.debug(f"从字节流转换为PIL图像")
                except Exception as e:
                    self.logger.error(f"无法解析图像字节流: {e}")
                    raise ValueError(f"无效的图像字节流: {e}")
            else:
                self.logger.error(f"不支持的图像格式: {type(image)}")
                raise ValueError(f"不支持的图像格式: {type(image)}")
            
            # 将图像保存到临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                temp_image_path = temp_file.name
                pil_image.save(temp_image_path, format="PNG")
                self.logger.debug(f"图像已保存到临时文件")
            
            try:
                # 将图像转换为base64编码
                def encode_image(image_path):
                    with open(image_path, "rb") as image_file:
                        return base64.b64encode(image_file.read()).decode("utf-8")
                
                # 获取图像的base64编码
                base64_image = encode_image(temp_image_path)
                self.logger.debug(f"图像已转换为base64编码")
                
                # 根据页面类型选择提示词
                system_prompts = {
                    "text": "你是一个专业的OCR助手，请识别图片中的所有文字内容。请特别注意：1) 使用 #PAGE_NUMBER: X# 标记页码；2) 使用 #CHAPTER: X# 标记章节标题；3) 使用 #SECTION: X# 标记小节标题；4) 使用 #HEADER: X# 标记页眉；5) 使用 #FOOTER: X# 标记页脚；6) 保持原有段落格式；7) 使用 > 标记引用文本；8) 使用 #FOOTNOTE: X# 标记脚注。",
                    "toc": "你是一个专业的OCR助手，这是一个目录页面。请识别所有目录条目，并使用以下格式：1) 使用 #TOC_ENTRY: 标题|页码# 标记每个目录条目；2) 使用缩进表示层级关系，每一级缩进使用两个空格；3) 对于特殊页面如封面、封底、出版信息、前言、后记等，使用 #SPECIAL_PAGE: 类型|页码# 进行标记。",
                    "table": "你是一个专业的OCR助手，这是一个包含表格的页面。请识别表格内容并使用以下格式：1) 使用 #TABLE_START# 和 #TABLE_END# 标记表格的开始和结束；2) 使用 | 分隔表格列；3) 使用 #TABLE_CAPTION: X# 标记表格标题；4) 表格外的文字请单独段落输出，并使用适当的标记如 #SECTION:# 或 #PARAGRAPH:# 标记。",
                    "footnote": "你是一个专业的OCR助手，请识别正文和脚注。对于脚注，请使用 #FOOTNOTE: 编号|内容# 格式标记。对于正文中的脚注引用，请使用 #FOOTNOTE_REF: 编号# 格式标记。",
                    "image_caption": "你是一个专业的OCR助手，请识别图片及其说明文字。对于图片说明，请使用 #FIGURE: 编号|说明内容# 格式标记。如果图片有引用或来源说明，请使用 #FIGURE_SOURCE: 内容# 标记。",
                    "academic": "你是一个专业的OCR助手，这是一个学术文献页面。请识别所有文字内容，并使用以下格式：1) 使用 #TITLE: X# 标记文章标题；2) 使用 #AUTHOR: X# 标记作者；3) 使用 #ABSTRACT: X# 标记摘要；4) 使用 #KEYWORDS: X# 标记关键词；5) 使用 #REFERENCE: X# 标记参考文献；6) 使用 #CITATION: X# 标记引用；7) 对于公式，使用 #FORMULA: X# 标记；8) 使用 #SECTION: X# 标记章节标题；9) 使用 #PAGE_NUMBER: X# 标记页码。",
                    "cover": "你是一个专业的OCR助手，这是一个封面页面。请识别所有文字内容，并使用以下格式：1) 使用 #BOOK_TITLE: X# 标记书名；2) 使用 #BOOK_SUBTITLE: X# 标记副标题；3) 使用 #BOOK_AUTHOR: X# 标记作者；4) 使用 #BOOK_PUBLISHER: X# 标记出版社；5) 使用 #BOOK_YEAR: X# 标记出版年份；6) 使用 #BOOK_SERIES: X# 标记丛书名称（如果有）。",
                    "publication_info": "你是一个专业的OCR助手，这是一个出版信息页面。请识别所有文字内容，并使用以下格式：1) 使用 #BOOK_TITLE: X# 标记书名；2) 使用 #BOOK_AUTHOR: X# 标记作者；3) 使用 #BOOK_TRANSLATOR: X# 标记译者（如果有）；4) 使用 #BOOK_PUBLISHER: X# 标记出版社；5) 使用 #BOOK_ISBN: X# 标记ISBN；6) 使用 #BOOK_PRICE: X# 标记定价；7) 使用 #BOOK_EDITION: X# 标记版次；8) 使用 #BOOK_PRINT_INFO: X# 标记印刷信息；9) 使用 #BOOK_COPYRIGHT: X# 标记版权信息。",
                    "preface": "你是一个专业的OCR助手，这是一个前言或序言页面。请识别所有文字内容，并使用以下格式：1) 使用 #PREFACE_TITLE: X# 标记前言标题；2) 使用 #PREFACE_AUTHOR: X# 标记前言作者；3) 使用 #PREFACE_DATE: X# 标记前言日期；4) 使用 #PREFACE_CONTENT: X# 标记前言正文内容；5) 使用 #PAGE_NUMBER: X# 标记页码。",
                    "afterword": "你是一个专业的OCR助手，这是一个后记页面。请识别所有文字内容，并使用以下格式：1) 使用 #AFTERWORD_TITLE: X# 标记后记标题；2) 使用 #AFTERWORD_AUTHOR: X# 标记后记作者；3) 使用 #AFTERWORD_DATE: X# 标记后记日期；4) 使用 #AFTERWORD_CONTENT: X# 标记后记正文内容；5) 使用 #PAGE_NUMBER: X# 标记页码。"
                }
                
                user_prompts = {
                    "text": "请识别这张图片中的所有文字内容，使用特殊标记表示页码、章节标题、页眉页脚等元素，保持原有段落格式。",
                    "toc": "这是一个目录页面，请识别所有目录条目，使用特殊标记表示每个条目的标题和页码，并保持层级结构。",
                    "table": "这是一个包含表格的页面，请识别表格内容并使用特殊标记表示表格的开始、结束、标题和内容结构。",
                    "footnote": "请识别正文和脚注，使用特殊标记表示脚注及其在正文中的引用位置。",
                    "image_caption": "请识别图片及其说明文字，使用特殊标记表示图片标题、说明内容和来源。",
                    "academic": "这是一个学术文献页面，请识别所有文字内容，使用特殊标记表示标题、作者、摘要、关键词、章节、引用、参考文献和公式等元素。",
                    "cover": "这是一个封面页面，请识别所有文字内容，使用特殊标记表示书名、副标题、作者、出版社和出版年份等信息。",
                    "publication_info": "这是一个出版信息页面，请识别所有文字内容，使用特殊标记表示书名、作者、译者、出版社、ISBN、定价、版次、印刷信息和版权信息等。",
                    "preface": "这是一个前言或序言页面，请识别所有文字内容，使用特殊标记表示前言标题、作者、日期和正文内容。",
                    "afterword": "这是一个后记页面，请识别所有文字内容，使用特殊标记表示后记标题、作者、日期和正文内容。"
                }
                
                # 获取当前页面类型的提示词，如果不存在则使用默认文本提示词
                system_prompt = system_prompts.get(page_type, system_prompts["text"])
                user_prompt = user_prompts.get(page_type, user_prompts["text"])
                
                # 创建OpenAI客户端
                client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.api_url,
                )
                
                # 构建消息
                messages = [
                    {
                        "role": "system",
                        "content": [{"type": "text", "text": system_prompt}]
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                            },
                            {"type": "text", "text": user_prompt}
                        ]
                    }
                ]
                
                # 发送请求
                self.logger.debug(f"开始发送OCR请求")
                completion = client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    timeout=self.timeout
                )
                self.logger.debug(f"请求已完成，获取到响应")
                
                # 提取文本内容
                text_content = completion.choices[0].message.content
                
                # 提取token使用情况
                token_usage = 0
                if hasattr(completion, 'usage') and completion.usage:
                    token_usage = completion.usage.total_tokens
                    self.logger.debug(f"本次请求使用了 {token_usage} tokens")
                
                # 构建结果
                result = {
                    "text": text_content.strip(),
                    "confidence": 0.9,  # 大模型没有返回置信度，使用默认值
                    "blocks": [],  # 大模型没有返回块信息
                    "language": {
                        "code": "zh-CN",
                        "name": "简体中文"
                    },
                    "token_usage": token_usage
                }
                
                return result
            except Exception as e:
                self.logger.error(f"调用OCR API过程中发生错误: {e}")
                # 尝试提供更详细的错误信息
                if hasattr(e, 'response') and hasattr(e.response, 'text'):
                    self.logger.error(f"API响应内容: {e.response.text}")
                raise e
            finally:
                # 清理临时文件
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
                    self.logger.debug(f"已删除临时文件")
            
        except ImportError as e:
            self.logger.error(f"导入必要的包失败: {e}")
            raise Exception(f"导入必要的包失败: {e}")
        except Exception as e:
            self.logger.error(f"调用OCR API失败: {e}")
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
