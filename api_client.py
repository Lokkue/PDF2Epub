#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API客户端模块，用于调用OCR或大模型API进行图像文本识别
"""

import os
import requests
import json
import base64
import time
from typing import Dict, Any, List, Optional

class APIClient:
    """
    API客户端基类
    """
    def __init__(self, api_key: str = None, api_url: str = None):
        """
        初始化API客户端
        
        参数:
            api_key: API密钥
            api_url: API地址
        """
        self.api_key = api_key
        self.api_url = api_url
    
    def recognize_text(self, image_path: str) -> str:
        """
        识别图像中的文本
        
        参数:
            image_path: 图像文件路径
            
        返回:
            str: 识别出的文本
        """
        raise NotImplementedError("子类必须实现此方法")


class BaiduOCRClient(APIClient):
    """
    百度OCR API客户端
    """
    def __init__(self, api_key: str, secret_key: str, api_url: str = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"):
        """
        初始化百度OCR API客户端
        
        参数:
            api_key: API Key
            secret_key: Secret Key
            api_url: API地址
        """
        super().__init__(api_key, api_url)
        self.secret_key = secret_key
        self.access_token = None
        self.token_expires = 0
    
    def _get_access_token(self) -> str:
        """
        获取百度API访问令牌
        
        返回:
            str: 访问令牌
        """
        # 检查令牌是否过期
        if self.access_token and time.time() < self.token_expires:
            return self.access_token
        
        # 获取新令牌
        token_url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={self.api_key}&client_secret={self.secret_key}"
        response = requests.get(token_url)
        result = response.json()
        
        if "access_token" in result:
            self.access_token = result["access_token"]
            # 令牌有效期通常为30天，这里设置为29天以确保安全
            self.token_expires = time.time() + 29 * 24 * 60 * 60
            return self.access_token
        else:
            raise Exception(f"获取访问令牌失败: {result}")
    
    def recognize_text(self, image_path: str) -> str:
        """
        使用百度OCR API识别图像中的文本
        
        参数:
            image_path: 图像文件路径
            
        返回:
            str: 识别出的文本
        """
        # 获取访问令牌
        access_token = self._get_access_token()
        
        # 准备请求
        request_url = f"{self.api_url}?access_token={access_token}"
        
        # 读取图像文件
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        # 对图像进行base64编码
        image_base64 = base64.b64encode(image_data).decode("utf-8")
        
        # 发送请求
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        params = {"image": image_base64}
        response = requests.post(request_url, headers=headers, data=params)
        result = response.json()
        
        # 解析结果
        if "words_result" in result:
            text = "\n".join([item["words"] for item in result["words_result"]])
            return text
        else:
            error_msg = result.get("error_msg", "未知错误")
            raise Exception(f"文本识别失败: {error_msg}")


class TencentOCRClient(APIClient):
    """
    腾讯OCR API客户端
    """
    def __init__(self, secret_id: str, secret_key: str, api_url: str = "https://ocr.tencentcloudapi.com"):
        """
        初始化腾讯OCR API客户端
        
        参数:
            secret_id: 密钥ID
            secret_key: 密钥
            api_url: API地址
        """
        super().__init__(secret_id, api_url)
        self.secret_key = secret_key
    
    def recognize_text(self, image_path: str) -> str:
        """
        使用腾讯OCR API识别图像中的文本
        
        参数:
            image_path: 图像文件路径
            
        返回:
            str: 识别出的文本
        """
        # 这里需要实现腾讯OCR API的调用
        # 由于需要使用腾讯云SDK，这里只提供一个示例框架
        # 实际使用时需要安装腾讯云SDK并完善此方法
        
        # 读取图像文件
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        # 对图像进行base64编码
        image_base64 = base64.b64encode(image_data).decode("utf-8")
        
        # 这里应该使用腾讯云SDK发送请求
        # 以下代码仅为示例，实际使用时需要替换
        """
        from tencentcloud.common import credential
        from tencentcloud.common.profile.client_profile import ClientProfile
        from tencentcloud.common.profile.http_profile import HttpProfile
        from tencentcloud.ocr.v20181119 import ocr_client, models
        
        cred = credential.Credential(self.api_key, self.secret_key)
        http_profile = HttpProfile()
        http_profile.endpoint = "ocr.tencentcloudapi.com"
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        client = ocr_client.OcrClient(cred, "ap-guangzhou", client_profile)
        
        req = models.GeneralBasicOCRRequest()
        req.Image = image_base64
        resp = client.GeneralBasicOCR(req)
        result = json.loads(resp.to_json_string())
        
        text = "\n".join([item["DetectedText"] for item in result["TextDetections"]])
        return text
        """
        
        # 由于没有实际调用API，这里返回一个占位符
        return "腾讯OCR API调用示例（需要完善实现）"


class OpenAIVisionClient(APIClient):
    """
    OpenAI Vision API客户端
    """
    def __init__(self, api_key: str, api_url: str = "https://api.openai.com/v1/chat/completions"):
        """
        初始化OpenAI Vision API客户端
        
        参数:
            api_key: API密钥
            api_url: API地址
        """
        super().__init__(api_key, api_url)
    
    def recognize_text(self, image_path: str) -> str:
        """
        使用OpenAI Vision API识别图像中的文本
        
        参数:
            image_path: 图像文件路径
            
        返回:
            str: 识别出的文本
        """
        # 读取图像文件
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        # 对图像进行base64编码
        image_base64 = base64.b64encode(image_data).decode("utf-8")
        
        # 准备请求
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 构建请求体
        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请提取这个图像中的所有文本内容，保持原始格式。只返回文本内容，不要添加任何解释或评论。"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4096
        }
        
        # 发送请求
        response = requests.post(self.api_url, headers=headers, json=payload)
        result = response.json()
        
        # 解析结果
        if "choices" in result and len(result["choices"]) > 0:
            text = result["choices"][0]["message"]["content"]
            return text
        else:
            error_msg = result.get("error", {}).get("message", "未知错误")
            raise Exception(f"文本识别失败: {error_msg}")


# 工厂函数，根据API类型创建相应的客户端
def create_api_client(api_type: str, **kwargs) -> APIClient:
    """
    创建API客户端
    
    参数:
        api_type: API类型，支持 'baidu', 'tencent', 'openai'
        **kwargs: 其他参数，根据API类型不同而不同
        
    返回:
        APIClient: API客户端实例
    """
    if api_type.lower() == "baidu":
        return BaiduOCRClient(
            api_key=kwargs.get("api_key"),
            secret_key=kwargs.get("secret_key"),
            api_url=kwargs.get("api_url", "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic")
        )
    elif api_type.lower() == "tencent":
        return TencentOCRClient(
            secret_id=kwargs.get("secret_id"),
            secret_key=kwargs.get("secret_key"),
            api_url=kwargs.get("api_url", "https://ocr.tencentcloudapi.com")
        )
    elif api_type.lower() == "openai":
        return OpenAIVisionClient(
            api_key=kwargs.get("api_key"),
            api_url=kwargs.get("api_url", "https://api.openai.com/v1/chat/completions")
        )
    else:
        raise ValueError(f"不支持的API类型: {api_type}")
