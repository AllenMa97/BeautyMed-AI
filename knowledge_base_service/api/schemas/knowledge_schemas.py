# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
知识库相关的 Schemas
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., description="查询文本，如：玻尿酸、美白、抗衰老")
    top_k: int = Field(default=10, ge=1, le=100, description="返回结果数量，默认10")
    search_mode: Literal["hybrid", "vector", "graph", "keyword"] = Field(
        default="hybrid",
        description="搜索模式：hybrid=混合检索（向量+图谱），vector=纯向量检索，graph=纯图谱检索，keyword=精准匹配（字符层面，不走向量计算）"
    )
    use_ann: bool = Field(default=True, description="是否使用 HNSW 索引加速向量检索")
    threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="相似度阈值，低于此分数的结果将被过滤，0表示不过滤")
    search_type: Literal["all", "products", "entries"] = Field(
        default="all",
        description="检索范围：all=产品和知识条目，products=仅产品，entries=仅知识条目"
    )
    keyword_field: Optional[str] = Field(
        default=None,
        description="精准匹配字段（仅 keyword 模式生效）。不传则匹配所有字段。产品可选：name/brand/category/efficacy/description；知识条目可选：title/topic/content"
    )


class KnowledgeSearchResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    data: Dict[str, Any] = {}


class ProductAddRequest(BaseModel):
    name: str = Field(..., description="产品名称")
    group: Optional[str] = Field(default="", description="所属集团")
    brand: Optional[str] = Field(default="", description="品牌名称")
    reference_price: Optional[float] = Field(default=0.0, description="参考价格")
    category: Optional[str] = Field(default="", description="产品类别，如：精华、面霜、面膜")
    efficacy: Optional[str] = Field(default="", description="功效，如：美白、抗衰老、保湿")
    applicable_skin: Optional[str] = Field(default="", description="适用肤质")
    capacity: Optional[str] = Field(default="", description="容量规格")
    description: str = Field(..., description="产品描述")
    tags: Optional[List[str]] = Field(default=[], description="标签列表")


class KnowledgeAddRequest(BaseModel):
    title: str = Field(..., description="知识条目标题")
    category: Optional[str] = Field(default="", description="分类")
    content: str = Field(..., description="知识条目正文内容")
    references: Optional[List[str]] = Field(default=[], description="参考依据列表")
    tags: Optional[List[str]] = Field(default=[], description="标签列表")
