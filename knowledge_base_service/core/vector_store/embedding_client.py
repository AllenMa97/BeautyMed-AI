# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import os
import asyncio
from typing import List, Optional, Dict, Any
import logging
import aiohttp

from config.settings import (
    get_embedding_model,
    get_embedding_dimension,
    get_embedding_api_base,
    get_embedding_batch_size,
)

logger = logging.getLogger(__name__)


class EmbeddingClient:
    def __init__(
        self,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimension: Optional[int] = None,
        batch_size: Optional[int] = None,
    ):
        self.api_base = api_base or get_embedding_api_base()
        
        self.api_keys = []
        if api_key:
            self.api_keys.append(api_key)
        else:
            for i in range(1, 10):
                key = os.getenv(f"DASHSCOPE_API_KEY_{i}" if i > 1 else "DASHSCOPE_API_KEY", "")
                if key:
                    self.api_keys.append(key)
        
        if not self.api_keys:
            raise ValueError("没有找到任何可用的API Key,请设置 DASHSCOPE_API_KEY 环境变量")
        
        self.current_key_index = 0
        self.model = model or get_embedding_model()
        self.dimension = dimension or get_embedding_dimension()
        self.batch_size = batch_size or get_embedding_batch_size()
        
        self._timeout = aiohttp.ClientTimeout(total=60.0)
        logger.info(f"初始?EmbeddingClient,使?{len(self.api_keys)} ?API Keys")
    
    def _get_current_api_key(self) -> str:
        """获取当前 API Key(支持轮询)"""
        return self.api_keys[self.current_key_index]
    
    def _switch_to_next_key(self):
        """切换到下一个API Key"""
        if len(self.api_keys) > 1:
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            logger.info(f"切换到下一个API Key: index={self.current_key_index}")
        else:
            logger.warning("只有一个API Key,无法切换")
    
    async def embed(self, text: str) -> List[float]:
        embeddings = await self.embed_batch([text])
        return embeddings[0] if embeddings else []
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        
        all_embeddings = []
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = await self._embed_batch_request(batch)
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    async def _embed_batch_request(self, texts: List[str]) -> List[List[float]]:
        """发送批量Embedding 请求(支持多 Key 轮询和自动重试)"""
        max_retries = len(self.api_keys)  # 最多重试次数
        
        for attempt in range(max_retries):
            try:
                current_key = self._get_current_api_key()
                
                headers = {
                    "Authorization": f"Bearer {current_key}",
                    "Content-Type": "application/json",
                }
                
                payload = {
                    "model": self.model,
                    "input": texts,
                    "dimensions": self.dimension,
                }
                
                async with aiohttp.ClientSession(timeout=self._timeout) as session:
                    async with session.post(
                        f"{self.api_base}/embeddings",
                        headers=headers,
                        json=payload,
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            embeddings = [item["embedding"] for item in result.get("data", [])]
                            return embeddings
                        else:
                            error_text = await response.text()
                            logger.error(f"Embedding API 错误 (Key 索引={self.current_key_index}): {response.status} - {error_text}")
                            
                            # 如果是额度用完的错误,切换到下一个Key
                            if response.status == 400 and ("free tier" in error_text.lower() or "quota" in error_text.lower()):
                                logger.warning(f"当前 API Key 额度用完,尝试切换到下一个Key...")
                                self._switch_to_next_key()
                                continue  # 重试
                            else:
                                raise Exception(f"API 错误:{response.status}")
            
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Embedding 请求失败,尝试切换Key 并重试({attempt+1}/{max_retries}): {e}")
                    self._switch_to_next_key()
                    await asyncio.sleep(1)  # 等待 1 秒后重试
                else:
                    logger.error(f"所有API Key 都已尝试,仍然失败:{e}")
                    raise
        
        # 理论上不会到这里
        return []
    
    async def close(self):
        pass
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
