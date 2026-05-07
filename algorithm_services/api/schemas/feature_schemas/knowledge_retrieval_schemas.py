# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from pydantic import BaseModel, Field
from ..base_schemas import BaseRequest, BaseResponse
from typing import List, Optional, Dict, Any, Union, Literal


class KnowledgeRetrievalRequest(BaseRequest):
    user_input: str = Field(..., description="用户本次输入")
    intent: Optional[str] = Field(None, description="用户意图")
    context: Optional[str] = Field("", description="对话上下文，用于联合抽取时提供上下文信息")
    session_data: Optional[Dict[str, Any]] = Field(
        None,
        description="会话数据，包含已有的实体和关系信息，避免重复抽取"
    )
    entities: Optional[List[Union[str, Dict[str, Any]]]] = Field(
        None,
        description="识别的实体，支持字符串列表或字典列表（由服务内部自动填充，通常无需外部传入）"
    )
    relations: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="抽取的关系三元组列表（由服务内部自动填充，通常无需外部传入）"
    )
    top_k: Optional[int] = Field(20, description="检索结果数量")
    rerank_top_k: Optional[int] = Field(10, description="Rerank后结果数量")
    max_context_tokens: Optional[int] = Field(4000, description="最大上下文Token数")
    search_type: Optional[str] = Field("all", description="检索类型: all/products/entries")
    personalize: bool = Field(True, description="是否启用个性化推荐，默认True")


class ProductItem(BaseModel):
    id: str = Field(..., description="产品ID")
    type: Literal["product"] = Field("product", description="类型标识")
    name: str = Field(..., description="产品名称")
    brand: Optional[str] = Field(None, description="品牌")
    category: Optional[str] = Field(None, description="分类")
    reference_price: Optional[float] = Field(None, description="参考价")
    description: Optional[str] = Field(None, description="描述")
    efficacy: Optional[str] = Field(None, description="功效")
    applicable_skin: Optional[str] = Field(None, description="适用肤质")
    score: Optional[float] = Field(None, description="相关性得分")


class KnowledgeEntry(BaseModel):
    id: str = Field(..., description="知识条目ID")
    type: Literal["entry"] = Field("entry", description="类型标识")
    title: str = Field(..., description="标题")
    topic: Optional[str] = Field(None, description="主题")
    content: Optional[str] = Field(None, description="内容")
    source_url: Optional[str] = Field(None, description="来源URL")
    score: Optional[float] = Field(None, description="相关性得分")


class KnowledgeRetrievalData(BaseModel):
    products: List[ProductItem] = Field([], description="检索到的产品列表")
    entries: List[KnowledgeEntry] = Field([], description="检索到的知识条目列表")
    total_products: int = Field(0, description="产品总数")
    total_entries: int = Field(0, description="知识条目总数")
    query: str = Field("", description="原始查询")


class KnowledgeRetrievalResponse(BaseResponse[KnowledgeRetrievalData]):
    code: int = Field(200)
    msg: str = Field("知识检索成功")
    data: KnowledgeRetrievalData = Field(
        default_factory=lambda: KnowledgeRetrievalData(
            products=[], entries=[], total_products=0, total_entries=0, query=""
        )
    )
