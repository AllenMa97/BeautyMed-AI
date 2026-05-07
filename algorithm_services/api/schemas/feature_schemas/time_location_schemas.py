# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from pydantic import BaseModel
from typing import Dict, Any, Optional

class TimeLocationRequest(BaseModel):
    """时间地理位置请求"""
    session_id: str
    user_id: Optional[str] = None
    ip_address: Optional[str] = None  # 可选的IP地址，用于地理位置获取
    context: Optional[str] = ""  # 对话上下文
    lang: Optional[str] = "zh-CN"  # 语言设置
    data: Optional[Dict[str, Any]] = None  # 其他数据


class TimeLocationResponseData(BaseModel):
    """时间地理位置响应数据"""
    time_info: Dict[str, Any]  # 时间信息
    location_info: Dict[str, Any]  # 地理位置信息
    combined_context: str  # 组合的上下文信息
    success: bool  # 请求是否成功


class TimeLocationResponse(BaseModel):
    """时间地理位置响应"""
    code: int
    msg: str
    data: TimeLocationResponseData