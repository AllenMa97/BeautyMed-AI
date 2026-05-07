# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from pydantic import BaseModel, Field
from algorithm_services.api.schemas.base_schemas import BaseRequest, BaseResponse
from typing import Optional, List

# -------------- 请求体 --------------
class IntentClarifyRequest(BaseRequest):
    """意图澄清请求模型"""
    user_input: str = Field(..., description="用户本次输入")
    recognized_intent: str = Field(..., description="已识别的一级意图（含未明确）")
    recognized_entities: str = Field(..., description="已识别的实体（JSON字符串格式）")
    context: Optional[str] = Field("", description="对话上下文")

# -------------- 响应数据体 --------------
class IntentClarifyResponseData(BaseModel):
    """意图澄清响应数据"""
    intent: str = Field(..., description="澄清后的一级意图（匹配预设分类）")
    need_clarify: bool = Field(..., description="是否需要澄清")
    clarify_question: str = Field("", description="澄清问题（口语化，≤20字，小白友好）")
    clarify_suggestions: List[str] = Field([], description="澄清选项（选择题形式，最多5个）")

# -------------- 响应体 --------------
class IntentClarifyResponse(BaseResponse[IntentClarifyResponseData]):
    """意图澄清响应模型"""
    code: int = Field(200)
    msg: str = Field("intent clarify response success")
