# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from pydantic import BaseModel
from typing import Dict, Any, Optional, List

class TrendingTopicsRequest(BaseModel):
    """热搜话题请求"""
    session_id: str
    user_id: Optional[str] = None
    topic_type: Optional[str] = "all"  # all, fashion_beauty
    context: Optional[str] = ""  # 对话上下文
    lang: Optional[str] = "zh-CN"  # 语言设置
    data: Optional[Dict[str, Any]] = None  # 其他数据


class TrendingTopicsResponseData(BaseModel):
    """热搜话题响应数据"""
    weibo_hot: List[Dict[str, Any]]  # 微博热搜
    baidu_hot: List[Dict[str, Any]]  # 百度热搜
    xiaohongshu_hot: List[Dict[str, Any]]  # 小红书热搜
    combined_context: str  # 组合的上下文信息
    success: bool  # 请求是否成功
    fetch_time: str  # 获取时间


class TrendingTopicsResponse(BaseModel):
    """热搜话题响应"""
    code: int
    msg: str
    data: TrendingTopicsResponseData