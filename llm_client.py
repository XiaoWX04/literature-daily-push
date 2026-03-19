#!/usr/bin/env python3
"""
大模型客户端模块
封装各种LLM API调用逻辑，提供统一的接口
"""

import os
import json
import logging
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM 配置"""
    api_key: str
    model: str
    api_url: str
    temperature: float = 0.3
    max_tokens: int = 1000


class LLMClient:
    """大模型客户端
    
    统一封装各种LLM API调用，支持多种模型格式
    """
    
    # 预设的 API 地址
    DEFAULT_APIS = {
        'openai': 'https://api.openai.com/v1/chat/completions',
        'deepseek': 'https://api.deepseek.com/v1/chat/completions',
        'moonshot': 'https://api.moonshot.cn/v1/chat/completions',
        'zhipu': 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
        'gemini': 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
        'claude': 'https://api.anthropic.com/v1/messages',
        'minimax': 'https://api.minimaxi.com/anthropic',
        'dashscope': 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
    }
    
    def __init__(self, config: LLMConfig, delay: float = 2.0, max_retries: int = 3):
        self.config = config
        self.delay = delay  # 请求之间的延迟（秒）
        self.max_retries = max_retries  # 最大重试次数
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {config.api_key}',
            'Content-Type': 'application/json'
        })
    
    def _get_api_url(self) -> str:
        """获取 API 地址"""
        url = self.config.api_url
        # 如果是预设的简称，转换为完整 URL
        if url.lower() in self.DEFAULT_APIS:
            url = self.DEFAULT_APIS[url.lower()]
        # 替换 URL 中的 {model} 占位符
        if '{model}' in url:
            url = url.replace('{model}', self.config.model)
        return url
    
    def call_llm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """调用大模型 API
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            
        Returns:
            模型响应文本
        """
        import time
        
        # 使用默认系统提示如果没有提供
        if not system_prompt:
            system_prompt = '你是一个学术论文分析专家，擅长判断论文与特定研究领域的相关性。'
        
        # 重试机制
        for attempt in range(self.max_retries + 1):
            try:
                url = self._get_api_url()
                
                # 判断 API 类型，构建对应的 payload 和 headers
                if 'generativelanguage.googleapis.com' in url:
                    # Gemini API 格式
                    return self._call_gemini(url, prompt, system_prompt)
                elif 'anthropic.com' in url:
                    # Claude API 格式
                    return self._call_claude(url, prompt, system_prompt)
                elif 'minimax.chat' in url:
                    # MiniMax API 格式
                    return self._call_minimax(url, prompt, system_prompt)
                else:
                    # OpenAI 兼容格式
                    return self._call_openai_compatible(url, prompt, system_prompt)
                
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
                if attempt < self.max_retries:
                    backoff_time = self.delay * (2 ** attempt)  # 指数退避
                    logger.warning(f"LLM API 网络错误 (尝试 {attempt+1}/{self.max_retries+1}): {e}")
                    logger.info(f"{backoff_time:.1f} 秒后重试...")
                    time.sleep(backoff_time)
                else:
                    logger.error(f"LLM API 网络错误 (已达到最大重试次数): {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return ''
            except requests.exceptions.HTTPError as e:
                # HTTP 错误通常不需要重试（如 401, 403, 404 等）
                logger.error(f"LLM API HTTP 错误: {e}")
                if e.response is not None:
                    logger.error(f"响应状态码: {e.response.status_code}")
                    logger.error(f"响应内容: {e.response.text[:500]}")
                return ''
            except Exception as e:
                if attempt < self.max_retries:
                    backoff_time = self.delay * (2 ** attempt)  # 指数退避
                    logger.warning(f"LLM API 调用失败 (尝试 {attempt+1}/{self.max_retries+1}): {e}")
                    logger.info(f"{backoff_time:.1f} 秒后重试...")
                    time.sleep(backoff_time)
                else:
                    logger.error(f"LLM API 调用失败 (已达到最大重试次数): {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return ''
    
    def _call_openai_compatible(self, url: str, prompt: str, system_prompt: str) -> str:
        """调用 OpenAI 兼容格式的 API"""
        payload = {
            'model': self.config.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': self.config.temperature,
            'max_tokens': self.config.max_tokens
        }
        
        response = self.session.post(url, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        # 适配不同 API 的返回格式
        if result.get('choices') and len(result['choices']) > 0:
            choice = result['choices'][0]
            if choice and 'message' in choice:
                return choice['message'].get('content', '')
            elif choice and 'text' in choice:
                return choice['text']
        
        # 检查是否有错误信息
        if 'error' in result:
            logger.error(f"LLM API 返回错误: {result['error']}")
        
        logger.warning(f"无法解析 LLM 响应: {result}")
        return ''
    
    def _call_gemini(self, url: str, prompt: str, system_prompt: str) -> str:
        """调用 Gemini API"""
        # Gemini 使用 API Key 作为查询参数
        api_key = self.config.api_key
        url = f"{url}?key={api_key}"
        
        payload = {
            'contents': [
                {
                    'parts': [
                        {'text': system_prompt},
                        {'text': prompt}
                    ]
                }
            ],
            'generationConfig': {
                'temperature': self.config.temperature,
                'maxOutputTokens': self.config.max_tokens
            }
        }
        
        # Gemini 不需要 Authorization header，使用 API key 作为参数
        headers = {
            'Content-Type': 'application/json'
        }
        
        # 使用会话对象发送请求
        session = requests.Session()
        session.headers.update(headers)
        response = session.post(url, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        # 解析 Gemini 响应格式
        if 'candidates' in result and len(result['candidates']) > 0:
            candidate = result['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                parts = candidate['content']['parts']
                if parts and 'text' in parts[0]:
                    return parts[0]['text']
        
        logger.warning(f"无法解析 Gemini 响应: {result}")
        return ''
    
    def _call_claude(self, url: str, prompt: str, system_prompt: str) -> str:
        """调用 Claude API"""
        payload = {
            'model': self.config.model,
            'max_tokens': self.config.max_tokens,
            'temperature': self.config.temperature,
            'system': system_prompt,
            'messages': [
                {'role': 'user', 'content': prompt}
            ]
        }
        
        # Claude 使用 x-api-key header
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': self.config.api_key,
            'anthropic-version': '2023-06-01'
        }
        
        # 使用会话对象发送请求
        session = requests.Session()
        session.headers.update(headers)
        response = session.post(url, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        # 解析 Claude 响应格式
        if 'content' in result and len(result['content']) > 0:
            return result['content'][0].get('text', '')
        
        logger.warning(f"无法解析 Claude 响应: {result}")
        return ''
    
    def _call_minimax(self, url: str, prompt: str, system_prompt: str) -> str:
        """调用 MiniMax API"""
        # MiniMax 使用特殊的 header 格式
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.config.api_key}'
        }
        
        payload = {
            'model': self.config.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': self.config.temperature,
            'max_tokens': self.config.max_tokens
        }
        
        # 使用会话对象发送请求
        session = requests.Session()
        session.headers.update(headers)
        response = session.post(url, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        # 检查错误
        if result.get('base_resp') and result['base_resp'].get('status_code') != 0:
            logger.error(f"MiniMax API 错误: {result['base_resp']}")
            return ''
        
        # 解析 MiniMax 响应格式
        if 'choices' in result and result['choices']:
            choice = result['choices'][0]
            if 'message' in choice:
                return choice['message'].get('content', '')
            elif 'text' in choice:
                return choice['text']
        
        logger.warning(f"无法解析 MiniMax 响应: {result}")
        return ''


def load_llm_config_from_env() -> LLMConfig:
    """从环境变量加载 LLM 配置"""
    api_key = os.environ.get('LLM_API_KEY', '')
    model = os.environ.get('LLM_MODEL', 'gpt-3.5-turbo')
    api_url = os.environ.get('LLM_API_URL', 'openai')
    
    if not api_key:
        raise ValueError("未设置 LLM_API_KEY")
    
    return LLMConfig(
        api_key=api_key,
        model=model,
        api_url=api_url
    )


# 测试代码
if __name__ == "__main__":
    # 测试配置
    config = LLMConfig(
        api_key="your-api-key",
        model="gpt-3.5-turbo",
        api_url="openai"
    )
    
    client = LLMClient(config)
    
    # 测试调用
    prompt = "请简要介绍 AI Agent 在生物学中的应用"
    response = client.call_llm(prompt)
    print(f"响应: {response}")
