# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from pydantic import Field, BaseModel
from typing import Optional, List, Dict
from algorithm_services.api.schemas.base_schemas import BaseRequest, BaseResponse

# -------------- 请求体 --------------
class DialogSummaryRequest(BaseRequest):
    dialog_content: List[str] = Field(..., description="对话内容列表，每个项为一次用户输入和Agent回答")
    summary_length: Optional[int] = Field(200, description="摘要长度限制")
    summary_type: Optional[str] = Field("brief", description="摘要类型：brief(简洁)/detail(详细)")

# -------------- 响应数据体（专属data结构） --------------
class DialogSummaryResponseData(BaseModel):
    """对话总结响应data结构"""
    dialog_summary: str = Field(..., description="生成的摘要内容") # 生成的摘要内容
    raw_length: Optional[int] = None  # 原始对话长度（可选）
    summary_length: Optional[int] = None  # 实际生成摘要长度（可选）


# -------------- 响应体 --------------
class DialogSummaryResponse(BaseResponse[DialogSummaryResponseData]):
    """对话总结响应体"""
    code: int = Field(200)
    msg: str = Field("dialog summary response success")

