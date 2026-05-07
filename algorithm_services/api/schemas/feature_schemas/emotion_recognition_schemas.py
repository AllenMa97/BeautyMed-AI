# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from pydantic import BaseModel, Field
from ..base_schemas import BaseRequest, BaseResponse
from typing import List, Optional

class EmotionRecognitionRequest(BaseRequest):
    """情感识别服务请求模型"""
    user_input: str = Field(..., description="用户输入")
    context: Optional[str] = Field("", description="对话上下文")

class EmotionRecognitionResponseData(BaseModel):
    """情感识别服务响应数据"""
    primary_emotion: str = Field("", description="主要情感类别")
    emotion_intensity: float = Field(0.0, description="情感强度 0-1")
    emotion_details: dict = Field({}, description="情感细节")
    suggested_response_tone: str = Field("", description="建议的回复语气")

class EmotionRecognitionResponse(BaseResponse[EmotionRecognitionResponseData]):
    """情感识别服务响应模型"""
    code: int = Field(200)
    msg: str = Field("emotion recognition success")
