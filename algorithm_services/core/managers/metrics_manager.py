# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import os
import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from algorithm_services.utils.logger import get_logger
from algorithm_services.core.managers.metrics_models import LLMCostRecord, RequestRecord

logger = get_logger(__name__)


class MetricsManager:
    """指标管理器 - 持久化到JSON文件"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        self.data_dir = Path("data/metrics")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.llm_records: List[LLMCostRecord] = []
        self.request_records: List[RequestRecord] = []
        
        self._stats_timer: Optional[threading.Timer] = None
        self._stats_interval = 3600
        
        self._hourly_stats_cache: Dict[str, Any] = {}
        self._last_stats_time: float = 0
    
    def _get_llm_file_path(self, date: str = None) -> Path:
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return self.data_dir / f"llm_cost_{date}.jsonl"
    
    def _get_request_file_path(self, date: str = None) -> Path:
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return self.data_dir / f"request_{date}.jsonl"
    
    def record_llm_call(self, record: LLMCostRecord):
        self.llm_records.append(record)
        
        file_path = self._get_llm_file_path(record.timestamp[:10])
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.__dict__, ensure_ascii=False) + "\n")
        
        logger.info(
            f"[LLM统计] provider={record.provider} model={record.model} "
            f"input={record.input_tokens} output={record.output_tokens} "
            f"total={record.total_tokens} latency={record.latency_ms}ms "
            f"success={record.success}"
        )
    
    def record_request(self, record: RequestRecord):
        self.request_records.append(record)
        
        file_path = self._get_request_file_path(record.timestamp[:10])
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.__dict__, ensure_ascii=False) + "\n")
    
    def get_hourly_stats(self, date: str = None) -> Dict[str, Any]:
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        cache_key = f"hourly_{date}"
        current_time = time.time()
        
        if cache_key in self._hourly_stats_cache:
            if current_time - self._last_stats_time < 3600:
                return self._hourly_stats_cache[cache_key]
        
        llm_file = self._get_llm_file_path(date)
        request_file = self._get_request_file_path(date)
        
        hourly_data = {}
        for hour in range(24):
            hourly_data[f"{hour:02d}:00"] = {
                "llm_calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "latency_sum": 0,
                "errors": 0,
                "requests": 0,
                "request_latency_sum": 0
            }
        
        if llm_file.exists():
            with open(llm_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        hour = record["timestamp"][11:13]
                        key = f"{hour}:00"
                        if key in hourly_data:
                            hourly_data[key]["llm_calls"] += 1
                            hourly_data[key]["input_tokens"] += record.get("input_tokens", 0)
                            hourly_data[key]["output_tokens"] += record.get("output_tokens", 0)
                            hourly_data[key]["total_tokens"] += record.get("total_tokens", 0)
                            hourly_data[key]["latency_sum"] += record.get("latency_ms", 0)
                            if not record.get("success", True):
                                hourly_data[key]["errors"] += 1
                    except:
                        continue
        
        if request_file.exists():
            with open(request_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        hour = record["timestamp"][11:13]
                        key = f"{hour}:00"
                        if key in hourly_data:
                            hourly_data[key]["requests"] += 1
                            hourly_data[key]["request_latency_sum"] += record.get("total_latency_ms", 0)
                    except:
                        continue
        
        for hour_key, data in hourly_data.items():
            if data["llm_calls"] > 0:
                data["avg_latency_ms"] = round(data["latency_sum"] / data["llm_calls"], 2)
            else:
                data["avg_latency_ms"] = 0
            
            if data["requests"] > 0:
                data["avg_request_latency_ms"] = round(data["request_latency_sum"] / data["requests"], 2)
            else:
                data["avg_request_latency_ms"] = 0
        
        peak_tokens = max((d["total_tokens"] for d in hourly_data.values()), default=0)
        peak_requests = max((d["requests"] for d in hourly_data.values()), default=0)
        
        result = {
            "date": date,
            "hourly": hourly_data,
            "summary": {
                "total_llm_calls": sum(d["llm_calls"] for d in hourly_data.values()),
                "total_input_tokens": sum(d["input_tokens"] for d in hourly_data.values()),
                "total_output_tokens": sum(d["output_tokens"] for d in hourly_data.values()),
                "total_tokens": sum(d["total_tokens"] for d in hourly_data.values()),
                "total_requests": sum(d["requests"] for d in hourly_data.values()),
                "total_errors": sum(d["errors"] for d in hourly_data.values()),
                "peak_hour_tokens": peak_tokens,
                "peak_hour_requests": peak_requests,
                "avg_llm_latency_ms": round(
                    sum(d["latency_sum"] for d in hourly_data.values()) / 
                    max(sum(d["llm_calls"] for d in hourly_data.values()), 1), 2
                ),
                "avg_request_latency_ms": round(
                    sum(d["request_latency_sum"] for d in hourly_data.values()) / 
                    max(sum(d["requests"] for d in hourly_data.values()), 1), 2
                )
            }
        }
        
        self._hourly_stats_cache[cache_key] = result
        self._last_stats_time = current_time
        
        return result
    
    def get_realtime_stats(self) -> Dict[str, Any]:
        current_hour = datetime.now().strftime("%H:00")
        
        hour_llm = [r for r in self.llm_records if r.timestamp[11:13] == current_hour[:2]]
        hour_request = [r for r in self.request_records if r.timestamp[11:13] == current_hour[:2]]
        
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "llm_calls_this_hour": len(hour_llm),
            "requests_this_hour": len(hour_request),
            "input_tokens_this_hour": sum(r.input_tokens for r in hour_llm),
            "output_tokens_this_hour": sum(r.output_tokens for r in hour_llm),
            "total_tokens_this_hour": sum(r.total_tokens for r in hour_llm),
            "avg_latency_ms": round(
                sum(r.latency_ms for r in hour_llm) / max(len(hour_llm), 1), 2
            ),
            "errors_this_hour": sum(1 for r in hour_llm if not r.success),
            "active_sessions": len(set(r.session_id for r in hour_request if r.session_id))
        }
    
    def start_hourly_timer(self):
        def timer_task():
            stats = self.get_hourly_stats()
            logger.info(
                f"[每小时统计] {stats['date']} - "
                f"LLM调用={stats['summary']['total_llm_calls']}, "
                f"Token={stats['summary']['total_tokens']}, "
                f"请求={stats['summary']['total_requests']}, "
                f"平均响应={stats['summary']['avg_request_latency_ms']}ms"
            )
            self._stats_timer = threading.Timer(self._stats_interval, timer_task)
            self._stats_timer.daemon = True
            self._stats_timer.start()
        
        self._stats_timer = threading.Timer(self._stats_interval, timer_task)
        self._stats_timer.daemon = True
        self._stats_timer.start()
        logger.info(f"[Metrics] 已启动每小时统计定时器，间隔{self._stats_interval}秒")
    
    def stop_timer(self):
        if self._stats_timer:
            self._stats_timer.cancel()
    
    def get_stats_by_days(self, days: int) -> Dict[str, Any]:
        """获取指定天数的统计数据"""
        from datetime import timedelta
        cutoff_time = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        
        filtered_llm = [r for r in self.llm_records if r.timestamp >= cutoff_time]
        filtered_request = [r for r in self.request_records if r.timestamp >= cutoff_time]
        
        total_input = sum(r.input_tokens for r in filtered_llm)
        total_output = sum(r.output_tokens for r in filtered_llm)
        total_tokens = sum(r.total_tokens for r in filtered_llm)
        
        return {
            "period": f"{days}天",
            "start_time": cutoff_time,
            "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_llm_calls": len(filtered_llm),
            "total_requests": len(filtered_request),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_tokens,
            "avg_latency_ms": round(sum(r.latency_ms for r in filtered_llm) / max(len(filtered_llm), 1), 2),
            "errors": sum(1 for r in filtered_llm if not r.success),
            "success_rate": round((len(filtered_llm) - sum(1 for r in filtered_llm if not r.success)) / max(len(filtered_llm), 1) * 100, 2),
            "unique_sessions": len(set(r.session_id for r in filtered_request if r.session_id))
        }
    
    def get_model_key_stats(self, days: int = 1) -> Dict[str, Any]:
        """获取指定天数内各模型和key的使用统计"""
        from datetime import timedelta
        cutoff_time = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        
        filtered_llm = [r for r in self.llm_records if r.timestamp >= cutoff_time]
        
        # 按模型分组统计
        model_stats = {}
        for record in filtered_llm:
            model_key = f"{record.provider}:{record.model}"
            if model_key not in model_stats:
                model_stats[model_key] = {
                    "provider": record.provider,
                    "model": record.model,
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "latency_sum": 0,
                    "errors": 0
                }
            model_stats[model_key]["calls"] += 1
            model_stats[model_key]["input_tokens"] += record.input_tokens
            model_stats[model_key]["output_tokens"] += record.output_tokens
            model_stats[model_key]["total_tokens"] += record.total_tokens
            model_stats[model_key]["latency_sum"] += record.latency_ms
            if not record.success:
                model_stats[model_key]["errors"] += 1
        
        # 按 key 分组统计
        key_stats = {}
        for record in filtered_llm:
            key_id = record.key_id if record.key_id else "unknown"
            if key_id not in key_stats:
                key_stats[key_id] = {
                    "key_id": key_id,
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "latency_sum": 0,
                    "errors": 0
                }
            key_stats[key_id]["calls"] += 1
            key_stats[key_id]["input_tokens"] += record.input_tokens
            key_stats[key_id]["output_tokens"] += record.output_tokens
            key_stats[key_id]["total_tokens"] += record.total_tokens
            key_stats[key_id]["latency_sum"] += record.latency_ms
            if not record.success:
                key_stats[key_id]["errors"] += 1
        
        # 计算平均值
        for stats in model_stats.values():
            stats["avg_latency_ms"] = round(stats["latency_sum"] / max(stats["calls"], 1), 2)
            del stats["latency_sum"]
        
        for stats in key_stats.values():
            stats["avg_latency_ms"] = round(stats["latency_sum"] / max(stats["calls"], 1), 2)
            del stats["latency_sum"]
        
        return {
            "period": f"{days}天",
            "by_model": list(model_stats.values()),
            "by_key": list(key_stats.values())
        }
    
    def get_hourly_stats_for_days(self, days: int) -> List[Dict[str, Any]]:
        """获取指定天数的每小时统计数据（用于图表显示）"""
        from datetime import timedelta
        cutoff_time = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        
        filtered_llm = [r for r in self.llm_records if r.timestamp >= cutoff_time]
        
        hourly_data = {}
        for record in filtered_llm:
            hour_key = record.timestamp[:13]  # YYYY-MM-DD HH
            if hour_key not in hourly_data:
                hourly_data[hour_key] = {
                    "hour": hour_key,
                    "llm_calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "latency_sum": 0,
                    "errors": 0
                }
            hourly_data[hour_key]["llm_calls"] += 1
            hourly_data[hour_key]["input_tokens"] += record.input_tokens
            hourly_data[hour_key]["output_tokens"] += record.output_tokens
            hourly_data[hour_key]["total_tokens"] += record.total_tokens
            hourly_data[hour_key]["latency_sum"] += record.latency_ms
            if not record.success:
                hourly_data[hour_key]["errors"] += 1
        
        result = []
        for hour_key in sorted(hourly_data.keys()):
            data = hourly_data[hour_key]
            result.append({
                "hour": hour_key,
                "llm_calls": data["llm_calls"],
                "input_tokens": data["input_tokens"],
                "output_tokens": data["output_tokens"],
                "total_tokens": data["total_tokens"],
                "avg_latency_ms": round(data["latency_sum"] / max(data["llm_calls"], 1), 2),
                "errors": data["errors"]
            })
        
        return result


metrics_manager = MetricsManager()
