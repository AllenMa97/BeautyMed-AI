"""内容检测相关的数据模型"""
from pydantic import BaseModel, Field
from typing import Optional, List


class ModerationRequest(BaseModel):
    """内容检测请求"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

    text: str = Field(..., description="待检测的文本内容")
    use_keyword: bool = Field(True, description="是否使用关键词检测")
    use_llm: bool = Field(True, description="是否使用LLM检测")
    categories: Optional[List[str]] = Field(None, description="指定检测的类别，None表示全部")
    mode: str = Field("parallel", description="检测模式: fast/accurate/parallel")


class ModerationDetail(BaseModel):
    """检测详情"""
    category: str = Field(..., description="违规类别")
    method: str = Field(..., description="检测方法: keyword/llm")
    is_violation: bool = Field(..., description="是否违规")
    confidence: float = Field(..., description="置信度 0-1")
    details: Optional[dict] = Field(None, description="详细信息")


class ModerationResponse(BaseModel):
    """内容检测响应"""
    is_violation: bool = Field(..., description="是否违规")
    violation_categories: List[str] = Field(default_factory=list, description="违规类别列表")
    confidence: float = Field(..., description="综合置信度")
    processing_time: float = Field(..., description="处理时间（秒）")
    details: List[ModerationDetail] = Field(default_factory=list, description="检测详情")


class BatchModerationRequest(BaseModel):
    """批量内容检测请求"""
    requests: List[ModerationRequest] = Field(..., description="检测请求列表")


class BatchModerationResponse(BaseModel):
    """批量内容检测响应"""
    results: List[ModerationResponse] = Field(..., description="检测结果列表")
    total_count: int = Field(..., description="总数量")
    violation_count: int = Field(..., description="违规数量")
    pass_count: int = Field(..., description="通过数量")
    total_time: float = Field(..., description="总处理时间（秒）")
