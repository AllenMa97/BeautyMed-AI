"""
热搜话题后台刷新管理器
负责定时刷新热搜数据
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import threading
from algorithm_services.utils.logger import get_logger
from algorithm_services.utils.trending_topics import trending_topics_util

logger = get_logger(__name__)

class TrendingTopicsManager:
    """
    热搜话题后台刷新管理器
    负责启动和管理热搜数据的定时刷新
    """

    def __init__(self):
        self._refresh_thread = None
        self._stop_event = threading.Event()

    def start(self):
        """启动后台刷新"""
        if self._refresh_thread and self._refresh_thread.is_alive():
            logger.info("热搜后台刷新线程已在运行")
            return

        self._stop_event.clear()
        self._refresh_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._refresh_thread.start()
        logger.info("热搜后台刷新管理器已启动")

    def stop(self):
        """停止后台刷新"""
        if self._refresh_thread:
            self._stop_event.set()
            self._refresh_thread.join(timeout=5)
            logger.info("热搜后台刷新管理器已停止")

    def _run_loop(self):
        """定时刷新循环"""
        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=trending_topics_util._cache_ttl)
            if self._stop_event.is_set():
                break
            try:
                logger.debug("检查热搜缓存状态...")
            except Exception as e:
                logger.warning(f"热搜缓存检查异常: {e}")


trending_topics_manager = TrendingTopicsManager()
