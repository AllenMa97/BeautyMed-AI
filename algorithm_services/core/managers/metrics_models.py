# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class LLMCostRecord:
    """LLM调用成本记录"""
    timestamp: str
    provider: str
    model: str
    key_id: str  # 新增：API Key ID（用于区分不同 key）
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: int
    success: bool
    error_type: Optional[str] = None
    session_id: Optional[str] = None
    request_source: Optional[str] = None


@dataclass
class RequestRecord:
    """请求级别统计"""
    timestamp: str
    session_id: str
    user_input_len: int
    output_len: int
    total_latency_ms: int
    success: bool
    error_message: Optional[str] = None
    functions_called: Optional[List[str]] = None


# 延迟导入metrics_manager
_metrics_manager = None

def get_metrics_manager():
    global _metrics_manager
    if _metrics_manager is None:
        try:
            from algorithm_services.core.managers.metrics_manager import metrics_manager
            _metrics_manager = metrics_manager
        except ImportError:
            _metrics_manager = None
    return _metrics_manager
