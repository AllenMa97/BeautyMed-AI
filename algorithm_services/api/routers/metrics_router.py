# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from fastapi import APIRouter
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


def get_metrics_manager():
    from algorithm_services.core.managers.metrics_manager import metrics_manager
    return metrics_manager


class HourlyStatsResponse(BaseModel):
    date: str
    hourly: dict
    summary: dict


class RealtimeStatsResponse(BaseModel):
    timestamp: str
    llm_calls_this_hour: int
    requests_this_hour: int
    input_tokens_this_hour: int
    output_tokens_this_hour: int
    total_tokens_this_hour: int
    avg_latency_ms: float
    errors_this_hour: int
    active_sessions: int


@router.get("/hourly", response_model=HourlyStatsResponse, summary="小时级统计")
async def get_hourly_stats(date: Optional[str] = None):
    """
    获取指定日期的小时级统计
    
    - **date**: 日期，格式YYYY-MM-DD，默认今天
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    return get_metrics_manager().get_hourly_stats(date)


@router.get("/realtime", response_model=RealtimeStatsResponse, summary="实时统计")
async def get_realtime_stats():
    """
    获取当前小时的实时统计
    """
    return get_metrics_manager().get_realtime_stats()


@router.get("/health")
async def metrics_health():
    """健康检查"""
    mgr = get_metrics_manager()
    return {
        "status": "ok",
        "data_dir": str(mgr.data_dir),
        "memory_llm_records": len(mgr.llm_records),
        "memory_request_records": len(mgr.request_records)
    }


@router.get("/daily/{days}", summary="N天统计")
async def get_daily_stats(days: int):
    """
    获取指定天数的统计
    
    - **days**: 天数，支持 1/3/7/30
    """
    if days not in [1, 3, 7, 30]:
        days = 1  # 默认1天
    return get_metrics_manager().get_stats_by_days(days)


@router.get("/hourly/{days}", summary="N天每小时数据（图表用）")
async def get_hourly_stats_for_days(days: int):
    """
    获取指定天数的每小时统计数据（用于图表展示）
    
    - **days**: 天数，支持 1/3/7/30
    """
    if days not in [1, 3, 7, 30]:
        days = 1
    return get_metrics_manager().get_hourly_stats_for_days(days)


@router.get("/model-key/{days}", summary="N天模型和Key统计")
async def get_model_key_stats(days: int):
    """
    获取指定天数内各模型和API Key的使用统计
    
    - **days**: 天数，支持 1/3/7/30
    """
    if days not in [1, 3, 7, 30]:
        days = 1
    return get_metrics_manager().get_model_key_stats(days)
