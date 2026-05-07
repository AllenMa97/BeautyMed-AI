# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-22
# Copyright (c) 2026. All rights reserved.

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., description="查询文本")
    top_k: int = Field(10, description="返回结果数量")
    search_mode: Literal["vector", "keyword", "hybrid"] = Field(
        "hybrid", description="搜索模式: vector/keyword/hybrid"
    )
    use_ann: bool = Field(True, description="是否使用ANN索引加速")
    threshold: float = Field(0.3, description="相似度阈值")
    search_type: Literal["all", "products", "entries"] = Field(
        "all", description="检索类型: all=全部, products=仅产品, entries=仅知识条目"
    )
    entities: Optional[List[Dict[str, Any]]] = Field(None, description="实体列表（可选）")
    relations: Optional[List[Dict[str, Any]]] = Field(None, description="关系三元组列表（可选）")


class ProductItem(BaseModel):
    """产品详情"""
    id: Optional[str] = Field(None, description="产品ID")
    type: Literal["product"] = Field("product", description="类型标识")
    name: str = Field(..., description="产品名称")
    group: Optional[str] = Field(None, description="所属集团")
    brand: Optional[str] = Field(None, description="品牌名称")
    reference_price: Optional[float] = Field(None, description="参考价格")
    category: Optional[str] = Field(None, description="产品类别")
    efficacy: Optional[str] = Field(None, description="功效")
    applicable_skin: Optional[str] = Field(None, description="适用肤质")
    capacity: Optional[str] = Field(None, description="容量规格")
    description: Optional[str] = Field(None, description="产品描述")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    score: Optional[float] = Field(None, description="相关度得分")


class KnowledgeEntry(BaseModel):
    """知识条目详情"""
    id: Optional[str] = Field(None, description="知识条目ID")
    type: Literal["entry"] = Field("entry", description="类型标识")
    title: Optional[str] = Field(None, description="标题")
    topic: Optional[str] = Field(None, description="主题")
    content: Optional[str] = Field(None, description="正文内容")
    category: Optional[str] = Field(None, description="分类")
    references: Optional[List[str]] = Field(None, description="参考依据列表")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    source_url: Optional[str] = Field(None, description="来源URL")
    score: Optional[float] = Field(None, description="相关度得分")


class KnowledgeSearchData(BaseModel):
    """搜索结果数据"""
    query: Optional[str] = Field(None, description="原始查询文本")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="搜索结果原始数据")
    total_found: Optional[int] = Field(0, description="搜索到的结果总数")


class KnowledgeSearchResult(BaseModel):
    """搜索结果（结构化）"""
    code: int = Field(200, description="业务状态码")
    msg: str = Field("搜索完成", description="业务状态信息")
    query: Optional[str] = Field(None, description="原始查询文本")
    products: List[ProductItem] = Field(default_factory=list, description="产品列表")
    entries: List[KnowledgeEntry] = Field(default_factory=list, description="知识条目列表")
    total_found: int = Field(0, description="搜索到的结果总数")

    @classmethod
    def from_response(cls, response_data: Dict[str, Any]) -> "KnowledgeSearchResult":
        """从原始响应数据构建结构化结果"""
        code = response_data.get("code", 200)
        msg = response_data.get("msg", "")
        data = response_data.get("data", {})

        query = data.get("query") if data else None
        results = data.get("results", []) if data else []
        total_found = data.get("total_found", len(results)) if data else 0

        products = []
        entries = []

        for item in results:
            item_type = item.get("type", "")
            if item_type == "product":
                products.append(ProductItem(**item))
            elif item_type == "entry":
                entries.append(KnowledgeEntry(**item))

        return cls(
            code=code,
            msg=msg,
            query=query,
            products=products,
            entries=entries,
            total_found=total_found
        )


class KnowledgeSearchResponse(BaseModel):
    """兼容旧接口的响应"""
    code: int = Field(200, description="业务状态码")
    msg: str = Field("搜索完成", description="业务状态信息")
    data: Optional[KnowledgeSearchData] = Field(None, description="搜索结果")
