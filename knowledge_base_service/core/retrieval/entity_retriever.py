# Developer: 椹但路椹櫤鍕?
# Position: 澶фā鍨嬬畻娉曞伐绋嬪笀
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from typing import List, Dict, Any
import logging

from .base_retriever import BaseRetriever, RetrievalQuery, RetrievalResult, Entity

logger = logging.getLogger(__name__)


class EntityRetriever(BaseRetriever):
    def __init__(self, entity_index: Dict[str, List[str]] = None):
        super().__init__(name="entity")
        self.entity_index = entity_index or {}
        
        self.entity_type_weights = {
            "product": 1.0,
            "ingredient": 0.9,
            "brand": 0.8,
            "category": 0.7,
            "symptom": 0.9,
            "treatment": 0.85,
            "default": 0.5,
        }
    
    def add_entity_mapping(
        self,
        entity_type: str,
        entity_value: str,
        doc_ids: List[str],
    ):
        key = f"{entity_type}:{entity_value}"
        self.entity_index[key] = doc_ids
    
    def add_entity_mappings(
        self,
        mappings: Dict[str, List[str]],
    ):
        for key, doc_ids in mappings.items():
            self.entity_index[key] = doc_ids
    
    async def retrieve(
        self,
        query: RetrievalQuery,
        top_k: int = 20,
    ) -> List[RetrievalResult]:
        if not query.entities:
            logger.debug("No entities provided for entity retrieval")
            return []
        
        doc_scores: Dict[str, float] = {}
        
        for entity in query.entities:
            key = f"{entity.entity_type}:{entity.entity_value}"
            
            if key in self.entity_index:
                doc_ids = self.entity_index[key]
                weight = self.entity_type_weights.get(
                    entity.entity_type,
                    self.entity_type_weights["default"],
                )
                score = weight * entity.confidence
                
                for doc_id in doc_ids:
                    if doc_id in doc_scores:
                        doc_scores[doc_id] = max(doc_scores[doc_id], score)
                    else:
                        doc_scores[doc_id] = score
        
        if not doc_scores:
            return []
        
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for idx, (doc_id, score) in enumerate(sorted_docs[:top_k]):
            results.append(RetrievalResult(
                id=doc_id,
                content="",
                score=score,
                source="entity",
                metadata={"entity_matched": True},
                rank=idx + 1,
            ))
        
        return results
    
    def get_entity_types(self) -> List[str]:
        types = set()
        for key in self.entity_index.keys():
            if ":" in key:
                entity_type = key.split(":")[0]
                types.add(entity_type)
        return list(types)
    
    def get_entities_by_type(self, entity_type: str) -> List[str]:
        entities = []
        for key in self.entity_index.keys():
            if key.startswith(f"{entity_type}:"):
                entity_value = key.split(":")[1]
                entities.append(entity_value)
        return entities
