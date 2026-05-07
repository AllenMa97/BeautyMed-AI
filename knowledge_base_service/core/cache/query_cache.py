# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import os
import json
import hashlib
import time
from typing import Dict, List, Optional, Any, Tuple
from collections import OrderedDict
import jieba
from jieba import analyse
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


class QueryCache:
 
    def __init__(
        self,
        max_size: int = 1000,
        ttl: int = 3600,
        similarity_threshold: float = 0.8,
        cache_dir: str = None
    ):
        self.max_size = max_size
        self.ttl = ttl
        self.similarity_threshold = similarity_threshold
        
        self.cache_dir = cache_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data', 'query_cache'
        )
        
        self._exact_cache: OrderedDict[str, Dict] = OrderedDict()
        self._semantic_index: Dict[str, str] = {}
        
        self._hits = 0
        self._misses = 0
        self._semantic_hits = 0
        
        self._load_persistent_cache()
    
    def _get_cache_key(self, query: str, **params) -> str:
        param_str = json.dumps(params, sort_keys=True)
        combined = f"{query}|{param_str}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    def _extract_keywords(self, text: str) -> set:
        keywords = analyse.extract_tags(text, topK=10, withWeight=False)
        return set(keywords)
    
    def _calculate_similarity(self, keywords1: set, keywords2: set) -> float:
        if not keywords1 or not keywords2:
            return 0.0
        intersection = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)
        return intersection / union if union > 0 else 0.0
    
    def _is_expired(self, entry: Dict) -> bool:
        if 'timestamp' not in entry:
            return True
        return time.time() - entry['timestamp'] > self.ttl
    
    def get(self, query: str, **params) -> Optional[Dict]:
        """
        获取缓存结果
        
        优先级:
        1. 精确匹配
        2. 语义相似匹配
        """
        cache_key = self._get_cache_key(query, **params)
        
        if cache_key in self._exact_cache:
            entry = self._exact_cache[cache_key]
            if not self._is_expired(entry):
                self._exact_cache.move_to_end(cache_key)
                self._hits += 1
                logger.debug(f"Cache hit (exact): {query[:50]}...")
                return entry['result']
            else:
                del self._exact_cache[cache_key]
        
        query_keywords = self._extract_keywords(query)
        
        for semantic_key, exact_key in list(self._semantic_index.items()):
            if exact_key not in self._exact_cache:
                del self._semantic_index[semantic_key]
                continue
            
            cached_keywords = set(semantic_key.split('|'))
            similarity = self._calculate_similarity(query_keywords, cached_keywords)
            
            if similarity >= self.similarity_threshold:
                entry = self._exact_cache[exact_key]
                if not self._is_expired(entry):
                    self._exact_cache.move_to_end(exact_key)
                    self._hits += 1
                    self._semantic_hits += 1
                    logger.debug(f"Cache hit (semantic, similarity={similarity:.2f}): {query[:50]}...")
                    return entry['result']
        
        self._misses += 1
        return None
    
    def set(self, query: str, result: Dict, **params) -> None:
        """设置缓存"""
        cache_key = self._get_cache_key(query, **params)
        
        while len(self._exact_cache) >= self.max_size:
            oldest_key, _ = self._exact_cache.popitem(last=False)
            keys_to_remove = [k for k, v in self._semantic_index.items() if v == oldest_key]
            for k in keys_to_remove:
                del self._semantic_index[k]
        
        entry = {
            'result': result,
            'timestamp': time.time(),
            'query': query,
            'params': params
        }
        
        self._exact_cache[cache_key] = entry
        
        query_keywords = self._extract_keywords(query)
        semantic_key = '|'.join(sorted(query_keywords))
        self._semantic_index[semantic_key] = cache_key
    
    def invalidate(self, query: str = None, **params) -> None:
        if query:
            cache_key = self._get_cache_key(query, **params)
            if cache_key in self._exact_cache:
                del self._exact_cache[cache_key]
                keys_to_remove = [k for k, v in self._semantic_index.items() if v == cache_key]
                for k in keys_to_remove:
                    del self._semantic_index[k]
        else:
            self._exact_cache.clear()
            self._semantic_index.clear()
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        
        return {
            'total_entries': len(self._exact_cache),
            'max_size': self.max_size,
            'hits': self._hits,
            'misses': self._misses,
            'semantic_hits': self._semantic_hits,
            'hit_rate': f"{hit_rate * 100:.1f}%"
        }
    
    def _load_persistent_cache(self) -> None:
        cache_file = os.path.join(self.cache_dir, 'query_cache.json')
        
        if not os.path.exists(cache_file):
            return
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            loaded_count = 0
            current_time = time.time()
            
            for key, entry in data.get('cache', {}).items():
                if current_time - entry.get('timestamp', 0) <= self.ttl:
                    self._exact_cache[key] = entry
                    loaded_count += 1
            
            self._semantic_index = data.get('semantic_index', {})
            
            logger.info(f"Loaded {loaded_count} cache entries from disk")
            
        except Exception as e:
            logger.warning(f"Failed to load persistent cache: {e}")
    
    def save_persistent_cache(self) -> None:
        os.makedirs(self.cache_dir, exist_ok=True)
        cache_file = os.path.join(self.cache_dir, 'query_cache.json')
        
        try:
            data = {
                'cache': dict(self._exact_cache),
                'semantic_index': self._semantic_index,
                'saved_at': time.time()
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {len(self._exact_cache)} cache entries to disk")
            
        except Exception as e:
            logger.warning(f"Failed to save persistent cache: {e}")


class WarmupCache:
    
    def __init__(self, query_cache: QueryCache):
        self.query_cache = query_cache
        self.warmup_queries = []
        self._load_warmup_queries()
    
    def _load_warmup_queries(self) -> None:
        """加载预热查询列表"""
        warmup_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data', 'warmup_queries.json'
        )
        
        if os.path.exists(warmup_file):
            try:
                with open(warmup_file, 'r', encoding='utf-8') as f:
                    self.warmup_queries = json.load(f)
                logger.info(f"Loaded {len(self.warmup_queries)} warmup queries")
            except Exception as e:
                logger.warning(f"Failed to load warmup queries: {e}")
    
    async def warmup(self, search_func) -> None:
        """
        执行缓存预热
        
        Args:
            search_func: 异步搜索函数
        """
        if not self.warmup_queries:
            return
        
        logger.info(f"Starting cache warmup with {len(self.warmup_queries)} queries...")
        
        for query_info in self.warmup_queries:
            try:
                query = query_info.get('query')
                params = query_info.get('params', {})
                
                result = await search_func(query, **params)
                
                if result and not result.get('error'):
                    self.query_cache.set(query, result, **params)
                    
            except Exception as e:
                logger.warning(f"Warmup failed for query '{query_info.get('query')}': {e}")
        
        logger.info("Cache warmup completed")


_query_cache: Optional[QueryCache] = None
_warmup_cache: Optional[WarmupCache] = None


def get_query_cache() -> QueryCache:
    """获取全局查询缓存实例"""
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryCache()
    return _query_cache


def get_warmup_cache() -> WarmupCache:
    """获取全局预热缓存实例"""
    global _warmup_cache
    if _warmup_cache is None:
        _warmup_cache = WarmupCache(get_query_cache())
    return _warmup_cache
