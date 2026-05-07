# Developer: 椹但路椹櫤鍕?
# Position: 澶фā鍨嬬畻娉曞伐绋嬪笀
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import asyncio
from typing import List, Dict, Any, Optional
from collections import defaultdict
import logging

from .base_retriever import BaseRetriever, RetrievalQuery, RetrievalResult
from .vector_retriever import VectorRetriever
from .bm25_retriever import BM25Retriever
from .entity_retriever import EntityRetriever
from .constraint_retriever import ConstraintRetriever

logger = logging.getLogger(__name__)


class MultiPathRetriever(BaseRetriever):
    def __init__(
        self,
        vector_retriever: Optional[VectorRetriever] = None,
        bm25_retriever: Optional[BM25Retriever] = None,
        entity_retriever: Optional[EntityRetriever] = None,
        constraint_retriever: Optional[ConstraintRetriever] = None,
        rrf_k: int = 60,
    ):
        super().__init__(name="multi_path")
        
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        self.entity_retriever = entity_retriever
        self.constraint_retriever = constraint_retriever
        
        self.rrf_k = rrf_k
        
        self.path_weights = {
            "vector": 1.0,
            "bm25": 0.9,
            "entity": 1.1,
            "constraint": 0.8,
        }
    
    async def retrieve(
        self,
        query: RetrievalQuery,
        top_k: int = 20,
    ) -> List[RetrievalResult]:
        tasks = []
        path_names = []
        
        if self.vector_retriever and query.query_embedding:
            tasks.append(self.vector_retriever.retrieve(query, top_k=top_k * 2))
            path_names.append("vector")
        
        if self.bm25_retriever:
            tasks.append(self.bm25_retriever.retrieve(query, top_k=top_k * 2))
            path_names.append("bm25")
        
        if self.entity_retriever and query.entities:
            tasks.append(self.entity_retriever.retrieve(query, top_k=top_k))
            path_names.append("entity")
        
        if self.constraint_retriever and query.constraints:
            tasks.append(self.constraint_retriever.retrieve(query, top_k=top_k * 2))
            path_names.append("constraint")
        
        if not tasks:
            logger.warning("No retrievers available for multi-path retrieval")
            return []
        
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        path_results = {}
        for name, results in zip(path_names, results_list):
            if isinstance(results, Exception):
                logger.warning(f"Retrieval path {name} failed: {results}")
                path_results[name] = []
            else:
                path_results[name] = results
        
        fused_results = self.rrf_fusion(path_results, top_k)
        
        return fused_results
    
    def rrf_fusion(
        self,
        path_results: Dict[str, List[RetrievalResult]],
        top_k: int,
    ) -> List[RetrievalResult]:
        doc_scores = defaultdict(float)
        doc_info: Dict[str, RetrievalResult] = {}
        
        for path_name, results in path_results.items():
            weight = self.path_weights.get(path_name, 1.0)
            
            for rank, result in enumerate(results):
                doc_id = result.id
                
                rrf_score = weight / (self.rrf_k + rank + 1)
                doc_scores[doc_id] += rrf_score
                
                if doc_id not in doc_info:
                    doc_info[doc_id] = result
                else:
                    existing = doc_info[doc_id]
                    if not existing.content and result.content:
                        doc_info[doc_id] = result
        
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for idx, (doc_id, score) in enumerate(sorted_docs[:top_k]):
            result = doc_info[doc_id]
            result.score = score
            result.rank = idx + 1
            result.metadata["rrf_score"] = score
            results.append(result)
        
        return results
    
    def set_path_weight(self, path_name: str, weight: float):
        self.path_weights[path_name] = weight
    
    def get_available_paths(self) -> List[str]:
        paths = []
        if self.vector_retriever:
            paths.append("vector")
        if self.bm25_retriever:
            paths.append("bm25")
        if self.entity_retriever:
            paths.append("entity")
        if self.constraint_retriever:
            paths.append("constraint")
        return paths
    
    async def retrieve_with_path_info(
        self,
        query: RetrievalQuery,
        top_k: int = 20,
    ) -> Dict[str, Any]:
        tasks = []
        path_names = []
        
        if self.vector_retriever and query.query_embedding:
            tasks.append(self.vector_retriever.retrieve(query, top_k=top_k * 2))
            path_names.append("vector")
        
        if self.bm25_retriever:
            tasks.append(self.bm25_retriever.retrieve(query, top_k=top_k * 2))
            path_names.append("bm25")
        
        if self.entity_retriever and query.entities:
            tasks.append(self.entity_retriever.retrieve(query, top_k=top_k))
            path_names.append("entity")
        
        if self.constraint_retriever and query.constraints:
            tasks.append(self.constraint_retriever.retrieve(query, top_k=top_k * 2))
            path_names.append("constraint")
        
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        path_results = {}
        for name, results in zip(path_names, results_list):
            if isinstance(results, Exception):
                path_results[name] = {"results": [], "error": str(results)}
            else:
                path_results[name] = {"results": results, "count": len(results)}
        
        fused_results = self.rrf_fusion(
            {k: v["results"] for k, v in path_results.items() if "results" in v},
            top_k,
        )
        
        return {
            "fused_results": fused_results,
            "path_results": path_results,
            "paths_used": path_names,
        }
