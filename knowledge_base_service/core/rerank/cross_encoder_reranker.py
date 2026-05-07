# Developer: 椹但路椹櫤鍕?
# Position: 澶фā鍨嬬畻娉曞伐绋嬪笀
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from typing import List, Dict, Any
import logging

from .base_reranker import BaseReranker, RerankResult

logger = logging.getLogger(__name__)


class CrossEncoderReranker(BaseReranker):
    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-base",
        device: str = None,
        max_length: int = 512,
    ):
        super().__init__(name="cross_encoder")
        self.model_name = model_name
        self.device = device
        self.max_length = max_length
        self.model = None
        self._initialized = False
    
    def _init_model(self):
        if self._initialized:
            return
        
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name, max_length=self.max_length)
            if self.device:
                self.model.to(self.device)
            self._initialized = True
            logger.info(f"Loaded CrossEncoder model: {self.model_name}")
        except ImportError:
            logger.warning("sentence-transformers not installed, CrossEncoder reranker disabled")
            self._initialized = True
            self.model = None
        except Exception as e:
            logger.error(f"Error loading CrossEncoder model: {e}")
            self._initialized = True
            self.model = None
    
    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[RerankResult]:
        self._init_model()
        
        if not self.model or not results:
            return self._fallback_rerank(results, top_k)
        
        try:
            contents = [r.get("content", "") for r in results]
            pairs = [[query, content] for content in contents]
            
            scores = self.model.predict(pairs)
            
            scored_results = list(zip(results, scores))
            scored_results.sort(key=lambda x: x[1], reverse=True)
            
            reranked = []
            for idx, (result, score) in enumerate(scored_results[:top_k]):
                reranked.append(RerankResult(
                    id=result.get("id", ""),
                    content=result.get("content", ""),
                    score=float(score),
                    original_rank=result.get("rank", idx + 1),
                    new_rank=idx + 1,
                    metadata=result.get("metadata", {}),
                ))
            
            return self._normalize_scores(reranked)
        except Exception as e:
            logger.error(f"Error in CrossEncoder reranking: {e}")
            return self._fallback_rerank(results, top_k)
    
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
