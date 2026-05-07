# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

# 闲聊器

from fastapi import APIRouter
from algorithm_services.api.schemas.feature_schemas.free_chat_schemas import FreeChatRequest, FreeChatResponse
from algorithm_services.core.services.feature_services.free_chat_service import FreeChatService

router = APIRouter(prefix="/api/v1/feature/free_chat", tags=["闲聊器"])
service = FreeChatService()

@router.post("/free_chat", response_model=FreeChatResponse)
async def chat(request: FreeChatRequest):
    result = await service.chat(request)
    return result