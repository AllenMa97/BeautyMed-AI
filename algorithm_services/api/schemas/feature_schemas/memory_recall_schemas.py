# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from pydantic import BaseModel, Field
from ..base_schemas import BaseRequest, BaseResponse
from typing import List, Optional

class MemoryRecallRequest(BaseRequest):
    """记忆召回服务请求模型"""
    user_input: str = Field(..., description="用户输入，用于提取检索关键词")
    context: Optional[str] = Field("", description="对话上下文")
    recall_type: Optional[str] = Field("keyword", description="召回类型：keyword/time/entity/mixed")
    max_results: Optional[int] = Field(5, description="最大返回结果数")

class MemoryRecallResponseData(BaseModel):
    """记忆召回服务响应数据"""
    recalled_memories: List[dict] = Field([], description="召回的记忆列表")
    recall_method: str = Field("", description="使用的召回方法")
    total_count: int = Field(0, description="匹配到的记忆总数")

class MemoryRecallResponse(BaseResponse[MemoryRecallResponseData]):
    """记忆召回服务响应模型"""
    code: int = Field(200)
    msg: str = Field("memory recall success")
