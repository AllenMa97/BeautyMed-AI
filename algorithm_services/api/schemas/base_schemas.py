# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import json
from pydantic import BaseModel, Field
from typing import Generic,  TypeVar, Optional, Any, Generator, Dict

# 定义泛型类型变量，支持任意类型的data字段（核心：适配不同模块的data类型）
T = TypeVar('T', bound=Any)  # bound=Any兼容所有数据类型

# -------------------------- 通用请求基础模型（带data字段，所有Request继承） --------------------------
class BaseRequest(BaseModel):
    """
    所有功能模块Request的基础父类，内置data字段用于跨功能数据承接
    泛型D：指定data字段类型，默认dict（灵活承接任意数据），可自定义强类型
    """
    session_id: str = Field("", description="会话唯一标识，跨功能统一标识")
    user_id: Optional[str] = Field(None, description="用户ID")
    lang: str = Field(default="zh-CN", description="希望返回的语言类型，默认中文（zh-CN），英文为（en-US）")
    # 核心：data字段 - 用于planner调用不同功能后的数据上下承接，默认字典（灵活存储任意中间数据）
    data: Optional[Dict[str, Any]] = Field(None, description="通用数据载体，用于功能间上下文数据承接")
    # 流式返回字段
    stream_flag: bool = Field(False, description="是否需要流式返回，默认为false")

# -------------------------- 通用响应基础模型（带泛型data字段，所有Response继承） --------------------------
class BaseResponse(BaseModel, Generic[T]):
    """
    所有功能模块Response的基础父类，统一返回格式（code/msg/data）
    泛型T：指定data字段的具体类型（解决各模块data类型不一致问题，强类型校验）
    """
    code: int = Field(..., description="业务状态码，200为成功")
    msg: str = Field(..., description="业务状态信息，success为成功")
    # 核心：泛型data字段 - 不同模块指定不同类型，保留类型校验
    data: Optional[T] = Field(None, description="业务返回数据，各模块自定义具体类型")

    def to_stream(self, is_sse: bool = False) -> str:
        """
        转换为Starlette流式响应可直接yield的JSON字符串
        :param is_sse: 是否适配SSE（Server-Sent Events）协议，默认False
        :return: 可直接yield的字符串
        """
        # 1. 将BaseResponse对象序列化为JSON字符串
        # 兼容 v1 和 v2 的写法
        if hasattr(self, "model_dump_json"):
            json_str = self.model_dump_json(by_alias=False, exclude_unset=False)
        else:
            json_str = self.json(by_alias=False, exclude_unset=False)
        # 2. 若为SSE协议，添加data: 前缀和双换行（SSE标准格式要求）
        if is_sse:
            return f"data: {json_str}\n\n"
        # 3. 非SSE直接返回纯JSON字符串，适配普通流式响应
        return json_str


# 流式响应分片模型
class StreamChunk(BaseModel):
    content: str  # 单次返回的文本分片
    finish: bool  # 是否结束（True=最后一片）
    task_id: str  # 任务唯一标识

# 流式响应模型（兼容批量/流式）
class StreamResponse(BaseResponse):
    data: Optional[Generator[StreamChunk, None, None]]  # 流式数据生成器