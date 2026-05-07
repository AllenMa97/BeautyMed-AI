# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from collections import defaultdict
import logging

from .deduplicator import SemanticDeduplicator
from .token_budget import TokenBudgetManager

logger = logging.getLogger(__name__)


@dataclass
class AugmentedContext:
    context: str
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    total_tokens: int = 0
    sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "context": self.context,
            "chunks": self.chunks,
            "total_tokens": self.total_tokens,
            "sources": self.sources,
            "metadata": self.metadata,
        }


class ContextBuilder:
    def __init__(
        self,
        max_tokens: int = 4000,
        reserved_tokens: int = 500,
        dedup_threshold: float = 0.85,
        use_dedup: bool = True,
    ):
        self.max_tokens = max_tokens
        self.reserved_tokens = reserved_tokens
        
        self.deduplicator = SemanticDeduplicator(
            similarity_threshold=dedup_threshold,
        ) if use_dedup else None
        
        self.token_manager = TokenBudgetManager(
            max_tokens=max_tokens,
            reserved_tokens=reserved_tokens,
        )
        
        self.source_priority = {
            "patent": 1.0,
            "academic": 0.95,
            "clinical": 0.9,
            "official": 0.85,
            "product": 0.8,
            "news": 0.7,
            "general": 0.5,
        }
    
    def build(
        self,
        chunks: List[Dict[str, Any]],
        query: str,
        metadata: Dict[str, Any] = None,
    ) -> AugmentedContext:
        if not chunks:
            return AugmentedContext(
                context="",
                chunks=[],
                total_tokens=0,
                sources=[],
                metadata={"empty": True},
            )
        
        sorted_chunks = self._sort_by_relevance(chunks)
        
        if self.deduplicator:
            sorted_chunks = self.deduplicator.deduplicate(sorted_chunks)
        
        budget_chunks = self.token_manager.apply_budget(sorted_chunks)
        
        context = self._format_context(budget_chunks, query, metadata)
        
        sources = self._extract_sources(budget_chunks)
        
        total_tokens = self.token_manager.estimate_total_tokens(budget_chunks)
        
        return AugmentedContext(
            context=context,
            chunks=budget_chunks,
            total_tokens=total_tokens,
            sources=sources,
            metadata={
                "query": query,
                "chunk_count": len(budget_chunks),
                "dedup_enabled": self.deduplicator is not None,
            },
        )
    
    def _sort_by_relevance(
        self,
        chunks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        def get_priority(chunk: Dict[str, Any]) -> float:
            authority = chunk.get("metadata", {}).get("authority_level", "general")
            base_priority = self.source_priority.get(authority, 0.5)
            
            score = chunk.get("score", 0.5)
            
            return base_priority * 0.3 + score * 0.7
        
        return sorted(chunks, key=get_priority, reverse=True)
    
    def _format_context(
        self,
        chunks: List[Dict[str, Any]],
        query: str,
        metadata: Dict[str, Any] = None,
    ) -> str:
        by_source = defaultdict(list)
        
        for chunk in chunks:
            source = chunk.get("metadata", {}).get("source", "未知来源")
            source_type = chunk.get("metadata", {}).get("source_type", "general")
            by_source[source_type].append(chunk)
        
        context_parts = []
        
        context_parts.append("【检索到的相关知识】\n")
        
        source_order = ["product", "academic", "clinical", "patent", "official", "news", "general"]
        
        for source_type in source_order:
            if source_type not in by_source:
                continue
            
            chunks_in_source = by_source[source_type]
            
            source_names = {
                "product": "产品信息",
                "academic": "学术文献",
                "clinical": "临床研究",
                "patent": "专利信息",
                "official": "官方资料",
                "news": "新闻动态",
                "general": "相关知识",
            }
            
            context_parts.append(f"\n【{source_names.get(source_type, source_type)}】")
            
            for idx, chunk in enumerate(chunks_in_source, 1):
                content = chunk.get("content", "")
                
                context_parts.append(f"\n{idx}. {content}")
                
                chunk_meta = chunk.get("metadata", {})
                
                references = []
                if chunk_meta.get("document_title"):
                    references.append(chunk_meta["document_title"])
                if chunk_meta.get("reference"):
                    references.append(chunk_meta["reference"])
                
                if references:
                    context_parts.append(f"   [来源: {'; '.join(references)}]")
        
        return "\n".join(context_parts)
    
    def _extract_sources(
        self,
        chunks: List[Dict[str, Any]],
    ) -> List[str]:
        sources = set()
        
        for chunk in chunks:
            source = chunk.get("metadata", {}).get("source", "")
            if source:
                sources.add(source)
        
        return list(sources)
    
    def build_for_generation(
        self,
        chunks: List[Dict[str, Any]],
        query: str,
        system_prompt: str = None,
    ) -> str:
        augmented = self.build(chunks, query)
        
        parts = []
        
        if system_prompt:
            parts.append(system_prompt)
            parts.append("\n")
        
        parts.append(augmented.context)
        parts.append(f"\n\n【用户问题】\n{query}")
        parts.append("\n\n请基于以上知识回答用户问题,如果知识中没有相关信息,请明确说明。")
        
        return "\n".join(parts)
    
    def set_source_priority(
        self,
        source_type: str,
        priority: float,
    ):
        self.source_priority[source_type] = priority
