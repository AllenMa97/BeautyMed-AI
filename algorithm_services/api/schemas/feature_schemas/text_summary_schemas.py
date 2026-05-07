# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from pydantic import BaseModel, Field
from ..base_schemas import BaseRequest, BaseResponse
from typing import List

# -------------- 请求体 --------------
class TextSummaryRequest(BaseRequest):
    """文本摘要请求模型"""
    user_input: str = Field(..., description="用户单次输入")

# -------------- 响应数据体（专属data结构） --------------
class TextSummaryResponseData(BaseModel):
    """文本摘要响应数据"""
    summary: str = Field(..., description="100字以内的核心摘要")
    key_points: List[str] = Field([], description="5个以内的关键要点字符串列表")


# -------------- 响应体 --------------
class TextSummaryResponse(BaseResponse[TextSummaryResponseData]):
    """文本摘要响应模型"""
    code: int = Field(200)
    msg: str = Field("text summary success")

