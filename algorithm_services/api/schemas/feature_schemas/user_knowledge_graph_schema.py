"""用户知识图谱Schema - 用于User Knowledge Graph Service"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class KGEntity(BaseModel):
    """知识图谱实体"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

    id: str = Field(description="实体ID")
    name: str = Field(description="实体名称")
    entity_type: str = Field(description="实体类型: person, location, event, concept, topic, object")
    description: str = Field(default="", description="实体描述")
    properties: Dict[str, Any] = Field(default_factory=dict, description="实体属性")
    confidence: float = Field(default=1.0, description="置信度")
    source: str = Field(default="conversation", description="来源: conversation, profile, external")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class KGRelationship(BaseModel):
    """知识图谱关系"""
    id: str = Field(description="关系ID")
    source_entity: str = Field(description="源实体ID")
    target_entity: str = Field(description="目标实体ID")
    relationship_type: str = Field(description="关系类型: interested_in, related_to, follows, mentions, owns, uses")
    description: str = Field(default="", description="关系描述")
    confidence: float = Field(default=1.0, description="置信度")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class UserKnowledgeGraph(BaseModel):
    """用户知识图谱"""
    user_id: str = Field(description="用户ID")
    entities: List[KGEntity] = Field(default_factory=list, description="实体列表")
    relationships: List[KGRelationship] = Field(default_factory=list, description="关系列表")
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())


class KGFusionRequest(BaseModel):
    """融合外部知识请求"""
    user_id: str = Field(description="用户ID")
    external_entities: List[Dict[str, Any]] = Field(default_factory=list, description="外部实体")
    external_relationships: List[Dict[str, Any]] = Field(default_factory=list, description="外部关系")
    merge_strategy: str = Field(default="weighted", description="合并策略: weighted, replace, append")


class KGFusionResponse(BaseModel):
    """融合外部知识响应"""
    success: bool
    user_id: str
    merged_entities_count: int
    merged_relationships_count: int
    new_entities: List[str] = Field(default_factory=list)
    updated_entities: List[str] = Field(default_factory=list)
    message: str = ""


class KGQueryRequest(BaseModel):
    """知识图谱查询请求"""
    user_id: str = Field(description="用户ID")
    query: str = Field(description="自然语言查询")
    entity_types: Optional[List[str]] = Field(default=None, description="过滤实体类型")
    max_results: int = Field(default=10, description="最大返回数量")


class KGQueryResult(BaseModel):
    """知识图谱查询结果"""
    entities: List[KGEntity] = Field(default_factory=list)
    relationships: List[KGRelationship] = Field(default_factory=list)
    context: str = Field(default="", description="基于查询的上下文摘要")


class SimulatedKGData(BaseModel):
    """模拟知识图谱数据（用于冷启动）"""
    user_id: str
    entities: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    profile_summary: str = Field(default="", description="从画像总结的核心信息")
    conversation_summary: str = Field(default="", description="从对话总结的核心话题")
