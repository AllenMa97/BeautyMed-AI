# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from fastapi import APIRouter
from algorithm_services.api.schemas.feature_schemas.title_generation_schemas import TitleGenerationRequest, TitleGenerationResponse
from algorithm_services.core.services.feature_services.title_generation_service import TitleGenerationService
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)

# 意图澄清路由
router = APIRouter(
    prefix="/api/v1/feature/title_generation",
    tags=["核心功能 - 应用标题生成"]
)

# 初始化Service
generation_service = TitleGenerationService()

@router.post("/generation", response_model=TitleGenerationResponse)
async def title_generation(request: TitleGenerationRequest):
    logger.info(f"应用标题生成请求 - session_id: {request.session_id}, user_input: {request.user_input[:50]}")
    result = await generation_service.generation(request)
    return result