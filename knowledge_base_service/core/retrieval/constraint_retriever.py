# Developer: 椹但路椹櫤鍕?
# Position: 澶фā鍨嬬畻娉曞伐绋嬪笀
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from typing import List, Dict, Any
import logging

from .base_retriever import BaseRetriever, RetrievalQuery, RetrievalResult, Constraint

logger = logging.getLogger(__name__)


class ConstraintRetriever(BaseRetriever):
    def __init__(self, doc_metadata: Dict[str, Dict[str, Any]] = None):
        super().__init__(name="constraint")
        self.doc_metadata = doc_metadata or {}
        
        self.operator_functions = {
            "eq": lambda a, b: a == b,
            "ne": lambda a, b: a != b,
            "gt": lambda a, b: a > b,
            "gte": lambda a, b: a >= b,
            "lt": lambda a, b: a < b,
            "lte": lambda a, b: a <= b,
            "in": lambda a, b: a in b if isinstance(b, list) else False,
            "nin": lambda a, b: a not in b if isinstance(b, list) else True,
            "contains": lambda a, b: b in a if isinstance(a, str) else False,
            "startswith": lambda a, b: a.startswith(b) if isinstance(a, str) else False,
            "endswith": lambda a, b: a.endswith(b) if isinstance(a, str) else False,
        }
    
    def add_doc_metadata(self, doc_id: str, metadata: Dict[str, Any]):
        self.doc_metadata[doc_id] = metadata
    
    def add_docs_metadata(self, docs_metadata: Dict[str, Dict[str, Any]]):
        self.doc_metadata.update(docs_metadata)
    
    async def retrieve(
        self,
        query: RetrievalQuery,
        top_k: int = 20,
    ) -> List[RetrievalResult]:
        if not query.constraints:
            logger.debug("No constraints provided for constraint retrieval")
            return []
        
        matched_docs = []
        
        for doc_id, metadata in self.doc_metadata.items():
            if self._match_constraints(metadata, query.constraints):
                matched_docs.append(doc_id)
        
        results = []
        for idx, doc_id in enumerate(matched_docs[:top_k]):
            results.append(RetrievalResult(
                id=doc_id,
                content="",
                score=1.0,
                source="constraint",
                metadata=self.doc_metadata.get(doc_id, {}),
                rank=idx + 1,
            ))
        
        return results
    
    def _match_constraints(
        self,
        metadata: Dict[str, Any],
        constraints: List[Constraint],
    ) -> bool:
        for constraint in constraints:
            field = constraint.constraint_type
            value = constraint.constraint_value
            operator = constraint.operator
            
            if field not in metadata:
                return False
            
            field_value = metadata[field]
            
            if operator not in self.operator_functions:
                logger.warning(f"Unknown operator: {operator}")
                return False
            
            op_func = self.operator_functions[operator]
            
            try:
                if not op_func(field_value, value):
                    return False
            except Exception as e:
                logger.warning(f"Constraint evaluation error: {e}")
                return False
        
        return True
    
    def filter_by_metadata(
        self,
        doc_ids: List[str],
        metadata_filter: Dict[str, Any],
    ) -> List[str]:
        if not metadata_filter:
            return doc_ids
        
        constraints = []
        for field, value in metadata_filter.items():
            if isinstance(value, dict):
                for op, v in value.items():
                    constraints.append(Constraint(
                        constraint_type=field,
                        constraint_value=v,
                        operator=op,
                    ))
            else:
                constraints.append(Constraint(
                    constraint_type=field,
                    constraint_value=value,
                    operator="eq",
                ))
        
        filtered = []
        for doc_id in doc_ids:
            if doc_id in self.doc_metadata:
                if self._match_constraints(self.doc_metadata[doc_id], constraints):
                    filtered.append(doc_id)
        
        return filtered
