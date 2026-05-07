# Developer: 椹但路椹櫤鍕?
# Position: 澶фā鍨嬬畻娉曞伐绋嬪笀
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class RerankResult:
    id: str
    content: str
    score: float = 0.0
    original_rank: int = 0
    new_rank: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "score": self.score,
            "original_rank": self.original_rank,
            "new_rank": self.new_rank,
            "metadata": self.metadata,
        }


class BaseReranker(ABC):
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[RerankResult]:
        pass
    
    def _normalize_scores(self, results: List[RerankResult]) -> List[RerankResult]:
        if not results:
            return results
        
        scores = [r.score for r in results]
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            for r in results:
                r.score = 1.0
        else:
            for r in results:
                r.score = (r.score - min_score) / (max_score - min_score)
        
        return results
