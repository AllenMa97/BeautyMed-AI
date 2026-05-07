# Developer: 椹但路椹櫤鍕?
# Position: 澶фā鍨嬬畻娉曞伐绋嬪笀
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Entity:
    entity_type: str
    entity_value: str
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_value": self.entity_value,
            "confidence": self.confidence,
        }


@dataclass
class Constraint:
    constraint_type: str
    constraint_value: Any
    operator: str = "eq"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraint_type": self.constraint_type,
            "constraint_value": self.constraint_value,
            "operator": self.operator,
        }


@dataclass
class RetrievalQuery:
    query: str
    query_embedding: Optional[List[float]] = None
    intent: Optional[str] = None
    entities: List[Entity] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    top_k: int = 20
    metadata_filter: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "intent": self.intent,
            "entities": [e.to_dict() for e in self.entities],
            "constraints": [c.to_dict() for c in self.constraints],
            "top_k": self.top_k,
            "metadata_filter": self.metadata_filter,
        }


@dataclass
class RetrievalResult:
    id: str
    content: str
    score: float = 0.0
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    rank: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "score": self.score,
            "source": self.source,
            "metadata": self.metadata,
            "rank": self.rank,
        }


class BaseRetriever(ABC):
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def retrieve(
        self,
        query: RetrievalQuery,
        top_k: int = 20,
    ) -> List[RetrievalResult]:
        pass
    
    def _normalize_scores(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
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
