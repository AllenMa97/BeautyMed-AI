"""LLM联网搜索路由"""
from fastapi import APIRouter, HTTPException
from algorithm_services.utils.logger import get_logger
from algorithm_services.api.schemas.feature_schemas.llm_web_search_schema import (
    LLMWebSearchRequest,
    LLMWebSearchResponse,
    BatchSearchRequest,
    BatchSearchResponse,
    TrendingContext,
)
from algorithm_services.core.services.llm_web_search_service import llm_web_search_service


logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/feature/llm_search", tags=["LLM联网搜索"])


@router.post("/search", response_model=LLMWebSearchResponse)
async def llm_web_search(request: LLMWebSearchRequest):
    """
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

    LLM联网搜索接口
    
    功能：
    - 基于LLM的智能搜索查询优化
    - 多源信息聚合
    - 可信度评估
    - 与热搜上下文协同
    
    与热搜服务的关系：
    - 可传入trending_context参数，携带热搜话题信息
    - LLM会结合热搜上下文优化搜索结果
    """
    try:
        logger.info(f"[LLM搜索路由] 接收到搜索请求: {request.query}")
        
        result = await llm_web_search_service.search(request)
        
        logger.info(f"[LLM搜索路由] 搜索完成，成功: {result.success}")
        return result
        
    except Exception as e:
        logger.error(f"[LLM搜索路由] 搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/search_with_trending")
async def search_with_trending(
    query: str,
    trending_topics: str = "",
    user_context: dict = None
):
    """
    结合热搜的搜索接口
    
    参数：
    - query: 搜索查询
    - trending_topics: 热搜话题（逗号分隔）
    - user_context: 用户上下文（可选）
    """
    try:
        logger.info(f"[LLM搜索路由] 带热搜的搜索: {query}, 热搜: {trending_topics}")
        
        trending_context = None
        if trending_topics:
            topics = [t.strip() for t in trending_topics.split(",") if t.strip()]
            trending_context = TrendingContext(trending_topics=topics)
        
        result = await llm_web_search_service.search(LLMWebSearchRequest(
            query=query,
            user_context=user_context,
            trending_context=trending_context
        ))
        
        return result
        
    except Exception as e:
        logger.error(f"[LLM搜索路由] 带热搜的搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/batch_search", response_model=BatchSearchResponse)
async def batch_llm_search(request: BatchSearchRequest):
    """
    批量LLM联网搜索接口
    
    同时处理多个搜索查询，适用于需要聚合多个话题信息的场景
    """
    try:
        logger.info(f"[LLM搜索路由] 批量搜索请求，查询数: {len(request.queries)}")
        
        result = await llm_web_search_service.batch_search(request)
        
        logger.info(f"[LLM搜索路由] 批量搜索完成，成功: {result.successful_queries}/{result.total_queries}")
        return result
        
    except Exception as e:
        logger.error(f"[LLM搜索路由] 批量搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量搜索失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "llm_web_search",
        "description": "LLM联网搜索服务 - 与热搜服务协同工作"
    }
