# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-17
# Copyright (c) 2026. All rights reserved.

"""
实体关系联合抽取的Schemas
符合NLP领域命名习惯（Joint Extraction）
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class Entity(BaseModel):
    entity_id: str = Field(..., description="实体唯一标识")
    entity_name: str = Field(..., description="实体名称")
    entity_type: str = Field(..., description="实体类型（如：产品、成分、功效、品牌等）")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class Relation(BaseModel):
    relation_id: str = Field(..., description="关系唯一标识")
    source_entity_id: str = Field(..., description="源实体 ID")
    target_entity_id: str = Field(..., description="目标实体 ID")
    relation_type: str = Field(..., description="关系类型（如：包含、具有功效、适用于等）")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class JointExtractionResult(BaseModel):
    chunk_id: str = Field(..., description="Chunk ID")
    entities: List[Entity] = Field(default_factory=list, description="提取的实体列表")
    relations: List[Relation] = Field(default_factory=list, description="提取的关系列表")
    extraction_time: str = Field(..., description="提取时间")
    model_name: str = Field(..., description="使用的模型")


class JointExtractionRequest(BaseModel):
    text: str = Field(..., description="待提取的文本")
    chunk_id: str = Field(..., description="Chunk ID")
    document_id: Optional[str] = Field(None, description="文档ID")
    domain: Optional[str] = Field("medical_aesthetics", description="领域（如：medical_aesthetics、general等）")
    max_entities: int = Field(default=20, ge=1, le=50, description="最大实体数量")
    max_relations: int = Field(default=30, ge=1, le=100, description="最大关系数量")


class JointExtractionResponse(BaseModel):
    code: int = Field(default=200, description="状态码")
    msg: str = Field(default="success", description="状态消息")
    data: JointExtractionResult = Field(..., description="联合抽取结果")


class BatchJointExtractionRequest(BaseModel):
    chunks: List[Dict[str, Any]] = Field(..., description="Chunk列表，每个包含text和chunk_id")
    domain: Optional[str] = Field("medical_aesthetics", description="领域")
    max_entities_per_chunk: int = Field(default=20, ge=1, le=50, description="每个chunk最大实体数量")
    max_relations_per_chunk: int = Field(default=30, ge=1, le=100, description="每个chunk最大关系数量")


class BatchJointExtractionResponse(BaseModel):
    code: int = Field(default=200, description="状态码")
    msg: str = Field(default="success", description="状态消息")
    data: List[JointExtractionResult] = Field(..., description="批量联合抽取结果")
    total_chunks: int = Field(..., description="处理的chunk总数")
    total_entities: int = Field(..., description="提取的实体总数")
    total_relations: int = Field(..., description="提取的关系总数")


class KnowledgeGraphStats(BaseModel):
    total_entities: int = Field(..., description="实体总数")
    total_relations: int = Field(..., description="关系总数")
    entity_types: Dict[str, int] = Field(default_factory=dict, description="各类型实体数量")
    relation_types: Dict[str, int] = Field(default_factory=dict, description="各类型关系数量")
    chunks_with_entities: int = Field(..., description="包含实体的chunk数量")


class GraphQueryRequest(BaseModel):
    query: str = Field(..., description="查询文本")
    top_k_entities: int = Field(default=10, ge=1, le=50, description="返回的实体数量")
    top_k_chunks: int = Field(default=10, ge=1, le=50, description="返回的chunk数量")
    max_hops: int = Field(default=2, ge=1, le=5, description="最大跳数")
    entity_types: Optional[List[str]] = Field(None, description="过滤的实体类型")


class GraphQueryResponse(BaseModel):
    code: int = Field(default=200, description="状态码")
    msg: str = Field(default="success", description="状态消息")
    data: Dict[str, Any] = Field(..., description="查询结果")
