# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from fastapi import APIRouter
from algorithm_services.api.schemas.feature_schemas.intent_clarify_schemas import (
    IntentClarifyRequest,
    IntentClarifyResponse
)
from algorithm_services.core.services.feature_services.intent_clarify_service import IntentClarifyService
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)

# 意图澄清路由
router = APIRouter(
    prefix="/api/v1/feature/intent_clarify",
    tags=["核心功能 - 意图澄清器"]
)

# 初始化Service
clarify_service = IntentClarifyService()

@router.post("/clarify", response_model=IntentClarifyResponse)
async def clarify_intent(request: IntentClarifyRequest):
    """
    意图澄清API（小白友好版）
    - 输入：用户输入 + 已识别意图/实体 + 上下文
    - 输出：是否需要澄清 + 澄清问题（选择题优先）
    """
    logger.info(f"意图澄清请求 - session_id: {request.session_id}, user_input: {request.user_input[:50]}")
    result = await clarify_service.clarify(request)
    return result