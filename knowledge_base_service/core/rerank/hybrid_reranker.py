# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from typing import List, Dict, Any
import logging

from .base_reranker import BaseReranker, RerankResult
from .cross_encoder_reranker import CrossEncoderReranker
from .llm_reranker import LLMReranker

logger = logging.getLogger(__name__)


class HybridReranker(BaseReranker):
    def __init__(
        self,
        cross_encoder_model: str = "BAAI/bge-reranker-base",
        llm_model: str = "qwen-plus",
        cross_encoder_weight: float = 0.4,
        llm_weight: float = 0.6,
        use_cross_encoder: bool = True,
        use_llm: bool = True,
    ):
        super().__init__(name="hybrid")
        
        self.cross_encoder_weight = cross_encoder_weight
        self.llm_weight = llm_weight
        self.use_cross_encoder = use_cross_encoder
        self.use_llm = use_llm
        
        self.cross_encoder = None
        self.llm_reranker = None
        
        if use_cross_encoder:
            self.cross_encoder = CrossEncoderReranker(model_name=cross_encoder_model)
        
        if use_llm:
            self.llm_reranker = LLMReranker(model=llm_model)
    
    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[RerankResult]:
        if not results:
            return []
        
        cross_encoder_results = []
        llm_results = []
        
        if self.cross_encoder:
            cross_encoder_results = await self.cross_encoder.rerank(
                query, results, top_k=min(len(results), top_k * 2)
            )
        
        if self.llm_reranker:
            llm_results = await self.llm_reranker.rerank(
                query, results, top_k=min(len(results), top_k * 2)
            )
        
        if not cross_encoder_results and not llm_results:
            return self._fallback_rerank(results, top_k)
        
        if cross_encoder_results and not llm_results:
            return cross_encoder_results[:top_k]
        
        if llm_results and not cross_encoder_results:
            return llm_results[:top_k]
        
        return self._merge_results(
            cross_encoder_results,
            llm_results,
            top_k,
        )
    
    def _merge_results(
        self,
        cross_encoder_results: List[RerankResult],
        llm_results: List[RerankResult],
        top_k: int,
    ) -> List[RerankResult]:
        ce_scores = {r.id: r.score for r in cross_encoder_results}
        llm_scores = {r.id: r.score for r in llm_results}
        
        all_ids = set(ce_scores.keys()) | set(llm_scores.keys())
        
        combined_scores = {}
        for doc_id in all_ids:
            ce_score = ce_scores.get(doc_id, 0.0)
            llm_score = llm_scores.get(doc_id, 0.0)
            
            combined = (
                ce_score * self.cross_encoder_weight +
                llm_score * self.llm_weight
            )
            combined_scores[doc_id] = combined
        
        sorted_ids = sorted(combined_scores.keys(), key=lambda x: combined_scores[x], reverse=True)
        
        id_to_result = {}
        for r in cross_encoder_results:
            id_to_result[r.id] = r
        for r in llm_results:
            if r.id not in id_to_result:
                id_to_result[r.id] = r
        
        reranked = []
        for idx, doc_id in enumerate(sorted_ids[:top_k]):
            result = id_to_result.get(doc_id)
            if result:
                result.score = combined_scores[doc_id]
                result.new_rank = idx + 1
                result.metadata["ce_score"] = ce_scores.get(doc_id, 0.0)
                result.metadata["llm_score"] = llm_scores.get(doc_id, 0.0)
                reranked.append(result)
        
        return reranked
    
    def _fallback_rerank(
        self,
        results: List[Dict[str, Any]],
        top_k: int,
    ) -> List[RerankResult]:
        reranked = []
        for idx, result in enumerate(results[:top_k]):
            reranked.append(RerankResult(
                id=result.get("id", ""),
                content=result.get("content", ""),
                score=result.get("score", 0.0),
                original_rank=result.get("rank", idx + 1),
                new_rank=idx + 1,
                metadata=result.get("metadata", {}),
            ))
        return reranked
    
    def set_weights(self, cross_encoder_weight: float, llm_weight: float):
        total = cross_encoder_weight + llm_weight
        self.cross_encoder_weight = cross_encoder_weight / total
        self.llm_weight = llm_weight / total
