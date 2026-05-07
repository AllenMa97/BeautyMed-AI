"""LLM联网搜索相关的数据模型"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class TrendingContext(BaseModel):
    """热搜上下文信息"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

    trending_topics: List[str] = Field(default_factory=list, description="热搜话题列表")
    trending_summary: Optional[str] = Field(None, description="热搜摘要")


class SearchSource(BaseModel):
    """搜索结果来源"""
    title: str = Field(..., description="来源标题")
    url: str = Field(..., description="来源URL")
    snippet: str = Field(..., description="内容摘要")
    credibility_score: float = Field(0.5, description="可信度评分 0-1")
    published_time: Optional[str] = Field(None, description="发布时间")


class LLMWebSearchRequest(BaseModel):
    """LLM联网搜索请求"""
    query: str = Field(..., description="用户查询")
    user_context: Optional[Dict[str, Any]] = Field(None, description="用户上下文")
    trending_context: Optional[TrendingContext] = Field(None, description="热搜上下文")
    max_sources: int = Field(5, description="最大来源数量")
    include_credibility: bool = Field(True, description="是否包含可信度评估")


class LLMOptimizedQuery(BaseModel):
    """LLM优化后的查询"""
    original_query: str = Field(..., description="原始查询")
    optimized_query: str = Field(..., description="优化后的查询")
    search_keywords: List[str] = Field(default_factory=list, description="搜索关键词")
    reasoning: str = Field(..., description="优化理由")


class LLMWebSearchResponse(BaseModel):
    """LLM联网搜索响应"""
    success: bool = Field(..., description="是否成功")
    query: str = Field(..., description="原始查询")
    optimized_query: Optional[LLMOptimizedQuery] = Field(None, description="优化后的查询")
    summary: Optional[str] = Field(None, description="搜索结果摘要")
    sources: List[SearchSource] = Field(default_factory=list, description="信息来源列表")
    credibility_score: float = Field(0.0, description="综合可信度评分")
    processing_time: float = Field(0.0, description="处理时间(秒)")
    error_message: Optional[str] = Field(None, description="错误信息")


class BatchSearchRequest(BaseModel):
    """批量搜索请求"""
    queries: List[str] = Field(..., description="查询列表")
    user_context: Optional[Dict[str, Any]] = Field(None, description="用户上下文")
    max_sources_per_query: int = Field(3, description="每个查询的最大来源数")


class BatchSearchResponse(BaseModel):
    """批量搜索响应"""
    success: bool = Field(..., description="是否成功")
    results: List[LLMWebSearchResponse] = Field(default_factory=list, description="搜索结果列表")
    total_queries: int = Field(0, description="总查询数")
    successful_queries: int = Field(0, description="成功查询数")
    processing_time: float = Field(0.0, description="总处理时间(秒)")
