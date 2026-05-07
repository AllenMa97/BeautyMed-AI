# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-21
# Copyright (c) 2026. All rights reserved.

import aiohttp
import json
from typing import List, Dict, Any, Optional


class LLMClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        default_model: str = "qwen-plus",
        timeout: int = 120
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def chat_completions(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        调用 chat/completions 接口

        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数
            response_format: 响应格式,如 {"type": "json_object"}

        Returns:
            API 响应字典
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload: Dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if response_format:
            payload["response_format"] = response_format

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                data = await resp.json()
                if resp.status != 200:
                    raise Exception(
                        f"LLM API 请求失败: status={resp.status}, body={json.dumps(data, ensure_ascii=False)}"
                    )
                return data

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """
        调用 chat/completions 并直接返回文本内容

        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数
            response_format: 响应格式

        Returns:
            模型返回的文本内容
        """
        data = await self.chat_completions(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format
        )
        return data["choices"][0]["message"]["content"].strip()
