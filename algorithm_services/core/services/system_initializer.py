"""
系统基础服务初始化模块
负责启动所有基础服务，包括时间地理位置服务、热点话题服务、自进化服务等
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import concurrent.futures
import time

from algorithm_services.utils.time_location import time_location_util
from algorithm_services.utils.trending_topics import trending_topics_util
from algorithm_services.core.managers.scheduled_update_manager import scheduled_update_manager
from algorithm_services.core.managers.trending_topics_manager import trending_topics_manager
from algorithm_services.core.managers.self_evolution_manager import self_evolution_manager
from algorithm_services.core.managers.screenshot_manager import screenshot_manager
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)


def initialize_basic_services():
    """
    初始化所有基础服务（并行预热）
    """
    logger.info("开始初始化基础服务...")
    start_time = time.time()
    
    try:
        logger.info("正在并行预热时间地理位置和热点话题服务...")
        
        def warmup_time_location():
            try:
                time_location_util.warmup()
                logger.info("时间地理位置服务已就绪")
            except Exception as e:
                logger.error(f"时间地理位置服务预热失败：{e}")
        
        def warmup_trending_topics():
            try:
                trending_topics_util.warmup()
                logger.info("热点话题服务已就绪")
            except Exception as e:
                logger.error(f"热点话题服务预热失败：{e}")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            time_future = executor.submit(warmup_time_location)
            trending_future = executor.submit(warmup_trending_topics)
            
            concurrent.futures.wait([time_future, trending_future])
        
        logger.info("正在启动定时更新管理器...")
        try:
            scheduled_update_manager.start()
            logger.info("定时更新管理器已启动")
        except Exception as e:
            logger.error(f"定时更新管理器启动失败，但继续启动：{e}")
        
        logger.info("正在启动热搜刷新管理器...")
        try:
            trending_topics_manager.start()
            logger.info("热搜刷新管理器已启动")
        except Exception as e:
            logger.error(f"热搜刷新管理器启动失败，但继续启动：{e}")
        
        logger.info("正在启动自进化管理器...")
        try:
            self_evolution_manager.start_periodic_analysis()
            logger.info("自进化管理器已启动")
        except Exception as e:
            logger.error(f"自进化管理器启动失败，但继续启动：{e}")
        
        logger.info("正在启动工作记录截图管理器...")
        try:
            screenshot_manager.start()
            logger.info("截图管理器已启动")
        except Exception as e:
            logger.error(f"截图管理器启动失败，但继续启动：{e}")
        
        logger.info("用户画像服务已就绪")
        
        logger.info("纠错检测服务已就绪")
        
        elapsed = time.time() - start_time
        logger.info(f"所有基础服务初始化完成，耗时 {elapsed:.2f} 秒")
        
    except Exception as e:
        logger.error(f"基础服务初始化失败：{e}")
        raise


def shutdown_basic_services():
    """
    关闭所有基础服务
    """
    logger.info("开始关闭基础服务...")
    
    try:
        trending_topics_manager.stop()
        logger.info("热搜刷新管理器已停止")
        
        scheduled_update_manager.stop()
        logger.info("定时更新管理器已停止")
        
        self_evolution_manager.stop_periodic_analysis()
        logger.info("自进化管理器已关闭")

        screenshot_manager.stop()
        logger.info("截图管理器已停止")
        
        logger.info("所有基础服务已关闭")
        
    except Exception as e:
        logger.error(f"基础服务关闭过程中出现错误：{e}")
        raise


if __name__ == '__main__':
    try:
        initialize_basic_services()
    except Exception as e:
        logger.error(f"系统基础服务初始化失败：{e}")
