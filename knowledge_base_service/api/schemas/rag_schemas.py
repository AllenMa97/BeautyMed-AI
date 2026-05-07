# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

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
class RAGQueryRequest:
    query: str
    intent: Optional[str] = None
    entities: List[Entity] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    top_k: int = 20
    rerank_top_k: int = 10
    max_context_tokens: int = 4000
    metadata_filter: Dict[str, Any] = field(default_factory=dict)
    use_rerank: bool = True
    use_dedup: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "intent": self.intent,
            "entities": [e.to_dict() for e in self.entities],
            "constraints": [c.to_dict() for c in self.constraints],
            "top_k": self.top_k,
            "rerank_top_k": self.rerank_top_k,
            "max_context_tokens": self.max_context_tokens,
            "metadata_filter": self.metadata_filter,
            "use_rerank": self.use_rerank,
            "use_dedup": self.use_dedup,
        }


@dataclass
class RAGQueryResponse:
    augmented_context: str
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    total_chunks: int = 0
    total_tokens: int = 0
    sources: List[str] = field(default_factory=list)
    retrieval_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "augmented_context": self.augmented_context,
            "chunks": self.chunks,
            "total_chunks": self.total_chunks,
            "total_tokens": self.total_tokens,
            "sources": self.sources,
            "retrieval_metadata": self.retrieval_metadata,
        }
