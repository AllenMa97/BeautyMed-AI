# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-17
# Copyright (c) 2026. All rights reserved.

"""
图谱增强RAG API路由
提供基于知识图谱和向量检索的混合查询功能
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import os

from pydantic import BaseModel, Field

from core.services.graph_enhanced_rag_service import GraphEnhancedRAGService


router = APIRouter(prefix="/graph_rag", tags=["知识图谱"])


class GraphRAGQueryRequest(BaseModel):
    query: str = Field(..., description="查询文本")
    top_k: int = Field(default=10, ge=1, le=50, description="返回结果数量")
    use_graph: bool = Field(default=True, description="是否使用图谱检索")
    use_vector: bool = Field(default=True, description="是否使用向量检索")
    graph_weight: float = Field(default=0.6, ge=0.0, le=1.0, description="图谱检索权重")
    vector_weight: float = Field(default=0.4, ge=0.0, le=1.0, description="向量检索权重")
    
    # 前端传入的 NER 结果（可选）
    entities: list = Field(default=None, description="前端传入的实体列表（NER 结果）")
    relations: list = Field(default=None, description="前端传入的关系列表（可选）")


class GraphRAGQueryResponse(BaseModel):
    code: int = Field(default=200, description="状态码")
    msg: str = Field(default="success", description="状态消息")
    data: Dict[str, Any] = Field(..., description="查询结果")


def get_graph_rag_service() -> GraphEnhancedRAGService:
    """获取图谱增强RAG服务实例"""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="DASHSCOPE_API_KEY not configured")
    
    service = GraphEnhancedRAGService(
        api_key=api_key,
        store_dir="data/chunk_embeddings",
        max_context_tokens=4000,
        graph_max_hops=2,
        graph_top_k_chunks=10,
        vector_top_k=20
    )
    
    return service


@router.post("/query", response_model=GraphRAGQueryResponse)
async def graph_rag_query(
    request: GraphRAGQueryRequest,
    service: GraphEnhancedRAGService = Depends(get_graph_rag_service)
):
    """
    图谱增强的RAG查询
    
    Args:
        request: 查询请求
    
    Returns:
        GraphRAGQueryResponse: 查询结果
    """
    try:
        await service.initialize()
        
        result = await service.query(
            query=request.query,
            top_k=request.top_k,
            use_graph=request.use_graph,
            use_vector=request.use_vector,
            graph_weight=request.graph_weight,
            vector_weight=request.vector_weight,
            entities=request.entities,
            relations=request.relations
        )
        
        return GraphRAGQueryResponse(
            code=200,
            msg="success",
            data=result
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/stats")
async def get_graph_rag_stats(
    service: GraphEnhancedRAGService = Depends(get_graph_rag_service)
):
    """
    获取图谱增强RAG统计信息
    
    Returns:
        统计信息
    """
    try:
        await service.initialize()
        stats = await service.get_retrieval_stats()
        
        return {
            "code": 200,
            "msg": "success",
            "data": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")
