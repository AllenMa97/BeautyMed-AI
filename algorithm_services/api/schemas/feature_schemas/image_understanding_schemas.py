# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from pydantic import BaseModel, Field
from ..base_schemas import BaseRequest, BaseResponse
from typing import Optional

class ImageUnderstandingRequest(BaseRequest):
    """图片理解服务请求模型"""
    user_input: str = Field(..., description="用户输入")
    image_url: Optional[str] = Field("", description="图片URL")
    image_base64: Optional[str] = Field("", description="图片Base64编码")
    context: Optional[str] = Field("", description="对话上下文")

class ImageUnderstandingResponseData(BaseModel):
    """图片理解服务响应数据"""
    description: str = Field("", description="图片描述")
    extracted_info: dict = Field({}, description="提取的关键信息")
    related_topics: list = Field([], description="相关话题")

class ImageUnderstandingResponse(BaseResponse[ImageUnderstandingResponseData]):
    """图片理解服务响应模型"""
    code: int = Field(200)
    msg: str = Field("image understanding success")
