# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from fastapi import APIRouter
from algorithm_services.api.schemas.feature_schemas.intent_recognize_schemas import (
    IntentRecognizeRequest,
    IntentRecognizeResponse
)
from algorithm_services.core.services.feature_services.intent_recognize_service import IntentRecognizeService
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)

# 意图识别路由
router = APIRouter(
    prefix="/api/v1/feature/intent_recognize",
    tags=["核心功能 - 意图识别器"]
)

# 初始化Service
intent_service = IntentRecognizeService()

@router.post("/recognize", response_model=IntentRecognizeResponse)
async def recognize_intent(request: IntentRecognizeRequest):
    """
    意图识别API（小白友好版）
    - 输入：用户口语化表达 + 会话上下文
    - 输出：3层结构化意图（无技术术语）
    """
    logger.info(f"意图识别请求 - session_id: {request.session_id}, user_input: {request.user_input[:50]}")
    result = await intent_service.recognize(request)
    return result