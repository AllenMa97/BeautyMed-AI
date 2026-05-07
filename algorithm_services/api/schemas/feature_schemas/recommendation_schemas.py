# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from pydantic import BaseModel, Field
from ..base_schemas import BaseRequest, BaseResponse
from typing import List, Optional, Dict, Any

class RecommendationRequest(BaseRequest):
    """推荐服务请求模型"""
    user_input: str = Field(..., description="用户输入")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="用户上下文(肤质、关注问题等)")
    recommendation_type: Optional[str] = Field("hybrid", description="推荐策略: semantic/heuristic/generative/hybrid")

class RecommendationResponseData(BaseModel):
    """推荐服务响应数据"""
    recommendations: List[dict] = Field(default_factory=list, description="推荐列表")
    reason: str = Field("", description="推荐理由")

class RecommendationResponse(BaseResponse[RecommendationResponseData]):
    """推荐服务响应模型"""
    code: int = Field(200)
    msg: str = Field("recommendation success")
