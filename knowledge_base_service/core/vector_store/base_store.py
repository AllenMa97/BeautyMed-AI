# Developer: 椹但路椹櫤鍕?
# Position: 澶фā鍨嬬畻娉曞伐绋嬪笀
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class SearchResult:
    id: str
    content: str = ""
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "score": self.score,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchResult":
        return cls(
            id=data.get("id", ""),
            content=data.get("content", ""),
            score=data.get("score", 0.0),
            metadata=data.get("metadata", {}),
            embedding=data.get("embedding"),
        )


class BaseVectorStore(ABC):
    @abstractmethod
    async def add(
        self,
        id: str,
        vector: List[float],
        content: str,
        metadata: Dict[str, Any],
    ) -> bool:
        pass
    
    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        pass
    
    @abstractmethod
    async def get(self, id: str) -> Optional[SearchResult]:
        pass
    
    @abstractmethod
    async def save(self) -> bool:
        pass
    
    @abstractmethod
    async def load(self) -> bool:
        pass
    
    def cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float],
    ) -> float:
        import math
        
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
