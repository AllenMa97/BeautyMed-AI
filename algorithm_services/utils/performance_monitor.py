# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import time
import asyncio
from functools import wraps
from typing import Callable, Any
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)

class PerformanceMonitor:
    """性能监控器，用于跟踪函数执行时间和资源使用情况"""
    
    def __init__(self):
        self.metrics = {}
    
    def monitor_async(self, name: str = None, log_threshold: float = 1.0):
        """
        异步函数性能监控装饰器
        :param name: 监控名称，如果不提供则使用函数名
        :param log_threshold: 记录日志的时间阈值（秒），超过此值会记录警告日志
        """
        def decorator(func: Callable) -> Callable:
            nonlocal name
            if name is None:
                name = func.__name__

            import inspect
            if inspect.isasyncgenfunction(func):
                @wraps(func)
                async def wrapper(*args, **kwargs):
                    start_time = time.time()
                    try:
                        async for item in func(*args, **kwargs):
                            yield item
                    finally:
                        end_time = time.time()
                        duration = end_time - start_time
                        if name not in self.metrics:
                            self.metrics[name] = {
                                'calls': 0,
                                'total_time': 0,
                                'avg_time': 0,
                                'min_time': float('inf'),
                                'max_time': 0,
                                'errors': 0
                            }
                        metrics = self.metrics[name]
                        metrics['calls'] += 1
                        metrics['total_time'] += duration
                        metrics['avg_time'] = metrics['total_time'] / metrics['calls']
                        metrics['min_time'] = min(metrics['min_time'], duration)
                        metrics['max_time'] = max(metrics['max_time'], duration)
                        if duration > log_threshold:
                            logger.warning(
                                f"Performance Alert: {name} took {duration:.2f}s "
                                f"(threshold: {log_threshold}s, avg: {metrics['avg_time']:.2f}s)"
                            )
                        logger.debug(
                            f"Performance: {name} completed in {duration:.2f}s "
                            f"(total_calls: {metrics['calls']})"
                        )
                return wrapper
            else:
                @wraps(func)
                async def wrapper(*args, **kwargs):
                    start_time = time.time()
                    start_loop_time = asyncio.get_event_loop().time() if asyncio.get_event_loop() else 0

                    try:
                        result = await func(*args, **kwargs)
                        success = True
                    except Exception as e:
                        result = e
                        success = False
                        raise
                    finally:
                        end_time = time.time()
                        duration = end_time - start_time

                        # 记录指标
                        if name not in self.metrics:
                            self.metrics[name] = {
                                'calls': 0,
                                'total_time': 0,
                                'avg_time': 0,
                                'min_time': float('inf'),
                                'max_time': 0,
                                'errors': 0
                            }

                        metrics = self.metrics[name]
                        metrics['calls'] += 1
                        metrics['total_time'] += duration
                        metrics['avg_time'] = metrics['total_time'] / metrics['calls']
                        metrics['min_time'] = min(metrics['min_time'], duration)
                        metrics['max_time'] = max(metrics['max_time'], duration)

                        if not success:
                            metrics['errors'] += 1

                        # 如果执行时间超过阈值，记录警告
                        if duration > log_threshold:
                            logger.warning(
                                f"Performance Alert: {name} took {duration:.2f}s "
                                f"(threshold: {log_threshold}s, avg: {metrics['avg_time']:.2f}s)"
                            )

                        logger.debug(
                            f"Performance: {name} completed in {duration:.2f}s "
                            f"(success: {success}, total_calls: {metrics['calls']})"
                        )

                    return result

                return wrapper
        return decorator
    
    def monitor_sync(self, name: str = None, log_threshold: float = 1.0):
        """
        同步函数性能监控装饰器
        :param name: 监控名称，如果不提供则使用函数名
        :param log_threshold: 记录日志的时间阈值（秒），超过此值会记录警告日志
        """
        def decorator(func: Callable) -> Callable:
            nonlocal name
            if name is None:
                name = func.__name__
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    success = True
                except Exception as e:
                    result = e
                    success = False
                    raise
                finally:
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    # 记录指标
                    if name not in self.metrics:
                        self.metrics[name] = {
                            'calls': 0,
                            'total_time': 0,
                            'avg_time': 0,
                            'min_time': float('inf'),
                            'max_time': 0,
                            'errors': 0
                        }
                    
                    metrics = self.metrics[name]
                    metrics['calls'] += 1
                    metrics['total_time'] += duration
                    metrics['avg_time'] = metrics['total_time'] / metrics['calls']
                    metrics['min_time'] = min(metrics['min_time'], duration)
                    metrics['max_time'] = max(metrics['max_time'], duration)
                    
                    if not success:
                        metrics['errors'] += 1
                    
                    # 如果执行时间超过阈值，记录警告
                    if duration > log_threshold:
                        logger.warning(
                            f"Performance Alert: {name} took {duration:.2f}s "
                            f"(threshold: {log_threshold}s, avg: {metrics['avg_time']:.2f}s)"
                        )
                    
                    logger.debug(
                        f"Performance: {name} completed in {duration:.2f}s "
                        f"(success: {success}, total_calls: {metrics['calls']})"
                    )
                
                return result
            
            return wrapper
        return decorator
    
    def get_metrics(self, name: str = None):
        """
        获取性能指标
        :param name: 指标名称，如果不提供则返回所有指标
        """
        if name is None:
            return self.metrics
        return self.metrics.get(name, {})
    
    def reset_metrics(self, name: str = None):
        """
        重置性能指标
        :param name: 指标名称，如果不提供则重置所有指标
        """
        if name is None:
            self.metrics.clear()
        elif name in self.metrics:
            del self.metrics[name]


# 全局性能监控实例
performance_monitor = PerformanceMonitor()

# 便捷装饰器
monitor_async = performance_monitor.monitor_async
monitor_sync = performance_monitor.monitor_sync