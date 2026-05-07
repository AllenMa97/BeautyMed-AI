# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from fastapi import APIRouter
from algorithm_services.api.schemas.feature_schemas.language_setting_schemas import LanguageSettingRequest, LanguageSettingResponse
from algorithm_services.core.services.feature_services.language_setting_service import LanguageSettingService
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)

# 意图澄清路由
router = APIRouter(
    prefix="/api/v1/feature/language_setting",
    tags=["核心功能 - 语言设定"]
)

# 初始化Service
language_setting_service = LanguageSettingService()

@router.post("/setting", response_model=LanguageSettingResponse)
async def language_translation(request: LanguageSettingRequest):
    logger.info(f"语言设定请求 - session_id: {request.session_id}")
    result = await language_setting_service.setting(request)
    return result