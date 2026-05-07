# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

# 文本摘要生成器

from fastapi import APIRouter
from algorithm_services.api.schemas.feature_schemas.text_summary_schemas import (
    TextSummaryRequest,
    TextSummaryResponse
)
from algorithm_services.core.services.feature_services.text_summary_service import TextSummaryService
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)

# 文本摘要路由
router = APIRouter(
    prefix="/api/v1/feature/text_summary",
    tags=["核心功能 - 文本摘要生成器"]
)

# 初始化Service
summary_service = TextSummaryService()

@router.post("/generate", response_model=TextSummaryResponse)
async def generate_text_summary(request: TextSummaryRequest):
    """
    文本摘要API（小白友好版）
    - 输入：用户单次输入
    - 输出：50字以内核心摘要 + 关键要点
    """
    logger.info(f"文本摘要请求 - session_id: {request.session_id}, user_input: {request.user_input[:50]}")
    result = await summary_service.generate(request)
    return result

