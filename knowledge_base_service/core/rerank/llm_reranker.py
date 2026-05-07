# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import os
import json
from typing import List, Dict, Any
import logging
import aiohttp

from .base_reranker import BaseReranker, RerankResult

logger = logging.getLogger(__name__)


class LLMReranker(BaseReranker):
    def __init__(
        self,
        api_base: str = None,
        api_key: str = None,
        model: str = "qwen-plus",
        batch_size: int = 10,
    ):
        super().__init__(name="llm")
        self.api_base = api_base or os.getenv("LLM_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
        self.model = model
        self.batch_size = batch_size
        
        self._timeout = aiohttp.ClientTimeout(total=60.0)
    
    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[RerankResult]:
        if not results:
            return []
        
        all_scored_results = []
        
        for i in range(0, len(results), self.batch_size):
            batch = results[i:i + self.batch_size]
            scored_batch = await self._rerank_batch(query, batch)
            all_scored_results.extend(scored_batch)
        
        all_scored_results.sort(key=lambda x: x[1], reverse=True)
        
        reranked = []
        for idx, (result, score) in enumerate(all_scored_results[:top_k]):
            reranked.append(RerankResult(
                id=result.get("id", ""),
                content=result.get("content", ""),
                score=score,
                original_rank=result.get("rank", idx + 1),
                new_rank=idx + 1,
                metadata=result.get("metadata", {}),
            ))
        
        return self._normalize_scores(reranked)
    
    async def _rerank_batch(
        self,
        query: str,
        results: List[Dict[str, Any]],
    ) -> List[tuple]:
        if not results:
            return []
        
        chunks_text = self._format_chunks(results)
        
        prompt = self._build_prompt(query, chunks_text, len(results))
        
        try:
            response = await self._call_llm(prompt)
            scores = self._parse_scores(response, len(results))
            
            return [(result, score) for result, score in zip(results, scores)]
        except Exception as e:
            logger.error(f"Error in LLM reranking: {e}")
            return [(result, result.get("score", 0.5)) for result in results]
    
    def _format_chunks(self, results: List[Dict[str, Any]]) -> str:
        lines = []
        for idx, result in enumerate(results):
            content = result.get("content", "")[:200]
            lines.append(f"[{idx + 1}] {content}...")
        return "\n".join(lines)
    
    def _build_prompt(self, query: str, chunks_text: str, num_chunks: int) -> str:
        return f"""你是一个专业的相关性评估专家。请评估以下知识片段与用户问题的相关性。

用户问题: {query}

知识片段:
{chunks_text}

请为每个片段打分(0-10分),分数标准:
- 10分:完全相关,直接回答问题
- 7-9分:高度相关,包含关键信息
- 4-6分:部分相关,包含一些有用信息
- 1-3分:低相关,信息有限
- 0分:不相关

请返回JSON格式: {{"scores": [分数1, 分数2, ...]}}
共{num_chunks}个片段,请返回{num_chunks}个分数。"""
    
    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 256,
        }
        
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            async with session.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status != 200:
                    raise Exception(f"LLM API error: {response.status}")
                
                data = await response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                return {"content": content}
    
    def _parse_scores(self, response: Dict[str, Any], expected_count: int) -> List[float]:
        content = response.get("content", "")
        
        try:
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
                scores = data.get("scores", [])
                
                while len(scores) < expected_count:
                    scores.append(5.0)
                
                return [float(s) / 10.0 for s in scores[:expected_count]]
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON")
        
        import re
        numbers = re.findall(r"\d+(?:\.\d+)?", content)
        scores = [float(n) / 10.0 for n in numbers[:expected_count]]
        
        while len(scores) < expected_count:
            scores.append(5.0)
        
        return scores
    
    async def close(self):
        pass
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
