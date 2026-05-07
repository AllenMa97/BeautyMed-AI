# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from pydantic import BaseModel, Field, field_validator
from algorithm_services.api.schemas.base_schemas import BaseRequest, BaseResponse
from typing import Optional, List, Dict


class EntityRelationExtractionRequest(BaseRequest):
    """实体与关系联合抽取请求模型"""
    user_input: str = Field(..., description="用户本次输入（口语化）")
    context: Optional[str] = Field("", description="对话上下文")


class RecognizedEntity(BaseModel):
    """识别出的单个实体信息"""
    entity_name: str = Field(..., description="实体名称")
    entity_type: str = Field(..., description="实体类型")
    confidence: float = Field(..., ge=0, le=1, description="实体识别置信度")


class ExtractedRelation(BaseModel):
    """抽取出的单个关系三元组"""
    subject: str = Field(..., description="头实体名称")
    subject_type: str = Field(..., description="头实体类型")
    predicate: str = Field(..., description="关系类型")
    object: str = Field(..., description="尾实体名称")
    object_type: str = Field(..., description="尾实体类型")
    confidence: float = Field(..., ge=0, le=1, description="关系抽取置信度")


class EntityRelationExtractionResponseData(BaseModel):
    """实体与关系联合抽取响应data结构"""
    entities: List[RecognizedEntity] = Field([], description="识别出的实体列表")
    relations: List[ExtractedRelation] = Field([], description="抽取出的关系三元组列表")
    entity_count: int = Field(0, description="识别的实体总数（自动计算，无需手动赋值）")
    relation_count: int = Field(0, description="抽取的关系总数（自动计算，无需手动赋值）")

    @field_validator("entity_count", mode="before")
    @classmethod
    def calculate_entity_count(cls, v, values):
        entities = values.data.get("entities", []) if hasattr(values, "data") else values.get("entities", [])
        return len(entities)

    @field_validator("relation_count", mode="before")
    @classmethod
    def calculate_relation_count(cls, v, values):
        relations = values.data.get("relations", []) if hasattr(values, "data") else values.get("relations", [])
        return len(relations)


class EntityRelationExtractionResponse(BaseResponse[EntityRelationExtractionResponseData]):
    """实体与关系联合抽取响应体"""
    code: int = Field(200)
    msg: str = Field("entity and relation extraction response success")
