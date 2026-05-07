# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from fastapi import APIRouter
from algorithm_services.api.schemas.feature_schemas.entity_relation_extraction_schemas import (
    EntityRelationExtractionRequest,
    EntityRelationExtractionResponse
)
from algorithm_services.core.services.feature_services.entity_relation_extraction_service import EntityRelationExtractionService
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/feature/entity_relation_extraction",
    tags=["核心功能 - 实体与关系联合抽取"]
)

entity_relation_extraction_service = EntityRelationExtractionService()

@router.post("/extract", response_model=EntityRelationExtractionResponse)
async def extract_entity_relation(request: EntityRelationExtractionRequest):
    """
    实体与关系联合抽取API（Joint Entity and Relation Extraction）
    - 输入：用户口语化表达 + 会话上下文
    - 输出：结构化实体列表 + 关系三元组列表
    """
    logger.info(f"实体与关系联合抽取请求 - session_id: {request.session_id}, user_input: {request.user_input[:50]}")
    result = await entity_relation_extraction_service.extract(request)
    return result
