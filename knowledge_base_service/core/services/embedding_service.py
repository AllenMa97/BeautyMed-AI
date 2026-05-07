# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
Embedding 服务 - 使用阿里云 dashscope API
支持多级缓存:字符级、词级、句子级
"""
import os
import hashlib
import json
from typing import List, Optional, Dict, Tuple
from pathlib import Path
from collections import OrderedDict
import asyncio
import jieba
import aiohttp
import dotenv
import logging

from config.settings import (
    get_embedding_model,
    get_embedding_dimension,
    get_embedding_api_base,
)

logger = logging.getLogger(__name__)

dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "LLM_API.env"))


class EmbeddingCache:
    """多级 Embedding 缓存"""
    
    def __init__(self, max_size: int = 10000, cache_dir: str = None):
        self.max_size = max_size
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent.parent.parent / "data" / "embedding_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.char_cache: OrderedDict[str, List[float]] = OrderedDict()
        self.word_cache: Dict[str, Tuple[str, List[float]]] = {}
        self.sentence_cache: Dict[str, Tuple[str, List[float]]] = {}
        
        self._load_persistent_cache()
    
    def _get_char_key(self, text: str) -> str:
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _get_word_key(self, text: str) -> str:
        words = list(jieba.cut(text))
        sorted_words = sorted(set(words))
        return hashlib.md5('|'.join(sorted_words).encode('utf-8')).hexdigest()
    
    def _get_sentence_key(self, text: str) -> str:
        sentences = [s.strip() for s in text.replace('。', '.').replace('！', '!').replace('?', '?').split('.') if s.strip()]
        if not sentences:
            return self._get_char_key(text)
        sorted_sentences = sorted(set(sentences))
        return hashlib.md5('|'.join(sorted_sentences).encode('utf-8')).hexdigest()
    
    def get(self, text: str) -> Optional[List[float]]:
        char_key = self._get_char_key(text)
        if char_key in self.char_cache:
            self.char_cache.move_to_end(char_key)
            return self.char_cache[char_key]
        
        word_key = self._get_word_key(text)
        if word_key in self.word_cache:
            original_text, embedding = self.word_cache[word_key]
            if self._texts_similar(text, original_text, level='word'):
                self.char_cache[char_key] = embedding
                self.char_cache.move_to_end(char_key)
                return embedding
        
        sentence_key = self._get_sentence_key(text)
        if sentence_key in self.sentence_cache:
            original_text, embedding = self.sentence_cache[sentence_key]
            if self._texts_similar(text, original_text, level='sentence'):
                self.char_cache[char_key] = embedding
                self.char_cache.move_to_end(char_key)
                return embedding
        
        return None
    
    def set(self, text: str, embedding: List[float]):
        char_key = self._get_char_key(text)
        
        if len(self.char_cache) >= self.max_size:
            self.char_cache.popitem(last=False)
        
        self.char_cache[char_key] = embedding
        
        word_key = self._get_word_key(text)
        self.word_cache[word_key] = (text, embedding)
        
        sentence_key = self._get_sentence_key(text)
        self.sentence_cache[sentence_key] = (text, embedding)
    
    def _texts_similar(self, text1: str, text2: str, level: str = 'word') -> bool:
        if level == 'word':
            words1 = set(jieba.cut(text1))
            words2 = set(jieba.cut(text2))
            if not words1 or not words2:
                return False
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            jaccard = intersection / union if union > 0 else 0
            return jaccard > 0.8
        elif level == 'sentence':
            return text1.strip() == text2.strip()
        return False
    
    def _load_persistent_cache(self):
        cache_file = self.cache_dir / "embedding_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, embedding in data.get('char_cache', {}).items():
                        self.char_cache[key] = embedding
                print(f"Loaded {len(self.char_cache)} cached embeddings")
            except Exception as e:
                print(f"Failed to load cache: {e}")
    
    def save_persistent_cache(self):
        cache_file = self.cache_dir / "embedding_cache.json"
        try:
            data = {
                'char_cache': dict(list(self.char_cache.items())[-5000:])
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Failed to save cache: {e}")
    
    def get_stats(self) -> Dict:
        return {
            "char_cache_size": len(self.char_cache),
            "word_cache_size": len(self.word_cache),
            "sentence_cache_size": len(self.sentence_cache),
            "max_size": self.max_size
        }


class EmbeddingService:
    """Embedding 服务 - 使用阿里云 dashscope API"""
    
    def __init__(self, enable_cache: bool = True):
        self.api_keys = [
            os.getenv("ALIYUN_API_KEY", ""),
            os.getenv("ALIYUN_API_KEY_2", ""),
            os.getenv("ALIYUN_API_KEY_3", "")
        ]
        self.api_keys = [key for key in self.api_keys if key]
        
        if not self.api_keys:
            raise ValueError("未设置任何 ALIYUN_API_KEY 环境变量")
        
        self.current_key_index = 0
        
        self.model = get_embedding_model()
        self.url = f"{get_embedding_api_base()}/embeddings"
        self.dimensions = get_embedding_dimension()
        
        self.enable_cache = enable_cache
        self.cache = EmbeddingCache() if enable_cache else None
        
        self._cache_hits = 0
        self._cache_misses = 0
    
    def _get_next_api_key(self):
        if not self.api_keys:
            raise ValueError("没有可用的API密钥")
        
        key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return key
    
    def _get_payload_for_model(self, input_data, dimensions=None):
        payload = {
            "model": self.model,
            "input": input_data,
            "encoding_format": "float"
        }
        
        if dimensions is not None:
            payload["dimensions"] = dimensions
        
        return payload
    
    async def get_embedding(self, text: str) -> List[float]:
        if self.enable_cache and self.cache:
            cached = self.cache.get(text)
            if cached is not None:
                self._cache_hits += 1
                if self.dimensions is not None and len(cached) != self.dimensions:
                    cached = self._ensure_dimension(cached, self.dimensions)
                return cached
        
        self._cache_misses += 1
        
        processed_text = self._preprocess_text(text)
        
        api_key = self._get_next_api_key()
        
        logger.info(f"尝试API调用: model={self.model}, key_prefix={api_key[:8]}...")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = self._get_payload_for_model(processed_text, self.dimensions)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    embedding = result["data"][0]["embedding"]
                
                if self.dimensions is not None:
                    embedding = self._ensure_dimension(embedding, self.dimensions)
                
                logger.info(f"API调用成功: model={self.model}, 维度: {len(embedding)}")
        except Exception as e:
            logger.error(f"API调用失败 (model={self.model}): {e}")
            raise e
        
        if self.enable_cache and self.cache:
            self.cache.set(text, embedding)
        
        return embedding
    
    def _ensure_dimension(self, vector: List[float], target_dim: int) -> List[float]:
        current_dim = len(vector)
        if current_dim == target_dim:
            return vector
        elif current_dim > target_dim:
            return vector[:target_dim]
        else:
            return vector + [0.0] * (target_dim - current_dim)
    
    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        
        results = []
        uncached_texts = []
        uncached_indices = []
        
        if self.enable_cache and self.cache:
            for i, text in enumerate(texts):
                cached = self.cache.get(text)
                if cached is not None:
                    self._cache_hits += 1
                    if self.dimensions is not None and len(cached) != self.dimensions:
                        cached = self._ensure_dimension(cached, self.dimensions)
                    results.append((i, cached))
                else:
                    self._cache_misses += 1
                    processed_text = self._preprocess_text(text)
                    uncached_texts.append(processed_text)
                    uncached_indices.append(i)
        else:
            for text in texts:
                processed_text = self._preprocess_text(text)
                uncached_texts.append(processed_text)
            uncached_indices = list(range(len(texts)))
        
        if uncached_texts:
            api_key = self._get_next_api_key()
            
            logger.info(f"批量API调用: model={self.model}, key_prefix={api_key[:8]}..., count={len(uncached_texts)}")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = self._get_payload_for_model(uncached_texts, self.dimensions)
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as response:
                        response.raise_for_status()
                        result = await response.json()
                        new_embeddings = [item["embedding"] for item in result["data"]]
                    
                    logger.info(f"批量API调用成功: model={self.model}, count={len(new_embeddings)}")
            except Exception as e:
                logger.error(f"批量API调用失败 (model={self.model}): {e}")
                raise e
            
            for idx, text, embedding in zip(uncached_indices, uncached_texts, new_embeddings):
                if self.dimensions is not None:
                    embedding = self._ensure_dimension(embedding, self.dimensions)
                results.append((idx, embedding))
                if self.enable_cache and self.cache:
                    self.cache.set(text, embedding)
        
        results.sort(key=lambda x: x[0])
        return [embedding for _, embedding in results]
    
    def _preprocess_text(self, text: str) -> str:
        if not text:
            return "空文本"
        
        processed = text.replace('\x00', '')
        processed = processed.replace('\ufffd', '')
        processed = processed.strip()
        
        if len(processed) > 8192:
            processed = processed[:8192]
        
        if not processed:
            processed = "默认文本"
        
        return processed
    
    def get_cache_stats(self) -> Dict:
        stats = {
            "cache_enabled": self.enable_cache,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": self._cache_hits / (self._cache_hits + self._cache_misses) if (self._cache_hits + self._cache_misses) > 0 else 0
        }
        if self.cache:
            stats.update(self.cache.get_stats())
        return stats
    
    def save_cache(self):
        if self.enable_cache and self.cache:
            self.cache.save_persistent_cache()


class EmbeddingServiceProxy:
    """代理类,延迟初始化 EmbeddingService"""
    _instance: Optional[EmbeddingService] = None
    
    def __getattr__(self, name):
        if EmbeddingServiceProxy._instance is None:
            EmbeddingServiceProxy._instance = EmbeddingService()
        return getattr(EmbeddingServiceProxy._instance, name)


embedding_service = EmbeddingServiceProxy()
