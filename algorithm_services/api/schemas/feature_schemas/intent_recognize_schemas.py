# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from pydantic import BaseModel, Field, field_validator
from algorithm_services.api.schemas.base_schemas import BaseRequest, BaseResponse
from typing import Optional

# -------------- 请求体 --------------
class IntentRecognizeRequest(BaseRequest):
    """意图识别请求体"""
    user_input: str = Field(..., description="用户原始输入文本")
    context: Optional[str] = Field("", description="多轮对话文本上下文（纯文本拼接）")

# -------------- 响应数据体（专属data结构） --------------
class IntentRecognizeResponseData(BaseModel):
    """意图识别响应数据"""
    intent: str = Field(..., description="识别出的一级意图（严格匹配预设分类）")
    confidence: float = Field(..., ge=0, le=1, description="意图识别置信度")

# -------------- 响应体 --------------
class IntentRecognizeResponse(BaseResponse[IntentRecognizeResponseData]):
    """意图识别响应体"""
    code: int = Field(200)
    msg: str = Field("intent recognize success")

