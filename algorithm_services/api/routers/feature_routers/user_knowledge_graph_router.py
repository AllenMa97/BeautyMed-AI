"""用户知识图谱Router"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from algorithm_services.api.schemas.feature_schemas.user_knowledge_graph_schema import (
    KGFusionRequest,
    KGFusionResponse,
    KGQueryRequest,
    KGQueryResult,
    UserKnowledgeGraph,
)
from algorithm_services.core.services.feature_services.user_knowledge_graph_service import (
    user_knowledge_graph_service,
)


router = APIRouter(prefix="/api/kg", tags=["knowledge-graph"])


@router.get("/{user_id}", response_model=UserKnowledgeGraph)
async def get_user_knowledge_graph(user_id: str):
    """获取用户知识图谱"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

    kg = await user_knowledge_graph_service.get_user_kg(user_id)
    if kg is None:
        raise HTTPException(status_code=404, detail="用户知识图谱不存在")
    return kg


@router.post("/extract", response_model=UserKnowledgeGraph)
async def extract_from_conversation(user_id: str, user_input: str, ai_response: str):
    """从对话中提取知识图谱"""
    kg = await user_knowledge_graph_service.extract_from_conversation(
        user_id=user_id,
        user_input=user_input,
        ai_response=ai_response
    )
    return kg


@router.post("/merge", response_model=KGFusionResponse)
async def merge_external_knowledge(request: KGFusionRequest):
    """融合外部知识到用户图谱"""
    return await user_knowledge_graph_service.merge_external_knowledge(request)


@router.post("/query", response_model=KGQueryResult)
async def query_knowledge_graph(request: KGQueryRequest):
    """查询知识图谱"""
    return await user_knowledge_graph_service.query_kg(request)


@router.get("/context/{user_id}")
async def get_kg_context(user_id: str):
    """获取用于对话的知识图谱上下文"""
    context = await user_knowledge_graph_service.get_kg_context_for_chat(user_id)
    return {"user_id": user_id, "context": context}
