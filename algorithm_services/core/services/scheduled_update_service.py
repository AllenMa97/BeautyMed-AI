"""
定时更新服务
负责实际执行热点和时尚信息的更新操作
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import asyncio
import random
import time
from datetime import datetime
from typing import Dict, Any

from algorithm_services.core.services.browser_trending_service import browser_trending_service
from algorithm_services.core.services.fashion_portal_service import fashion_portal_service
from algorithm_services.utils.trending_topics import trending_topics_util
from algorithm_services.core.services.external_knowledge_service import external_knowledge_service
from algorithm_services.core.services.simulation.user_simulation_service import user_simulation_service
from algorithm_services.core.services.feature_services.user_memory_mining_service import user_memory_mining_service
from algorithm_services.api.schemas.feature_schemas.user_simulation_schema import SimulationConfig
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)


class ScheduledUpdateService:
    """
    定时更新服务
    负责实际执行更新操作
    """

    def update_all(self):
        """
        执行所有更新操作
        由 Manager 定时调用
        """
        try:
            logger.info(f"开始执行定时更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            trending_result = self._update_trending_topics()
            fashion_result = self._update_fashion_news()
            self._update_external_knowledge()
            self._update_cache(trending_result, fashion_result)

            logger.info("定时更新完成")

        except Exception as e:
            logger.error(f"执行定时更新失败：{e}")

    def _update_external_knowledge(self):
        """使用统一的外来知识服务更新"""
        try:
            logger.info("正在使用外来知识服务更新...")
            result = external_knowledge_service.get_all_knowledge(force_refresh=True)
            logger.info(f"外来知识更新完成: {result.get('total_items', 0)} 条数据")
        except Exception as e:
            logger.warning(f"外来知识服务更新失败: {e}")
    
    def _update_trending_topics(self) -> Dict[str, Any]:
        """更新热点话题"""
        try:
            logger.info("正在更新热点话题...")
            
            # 直接使用 trending_topics_util（已禁用微博热搜）
            # 跳过 browser_trending_service（需要登录）
            result = trending_topics_util.get_all_trending_topics()
            if result.get('success', False):
                logger.info(f"热点话题获取成功：{result.get('fetch_time')}")
                return result
            
            # 如果获取失败，保留原有的缓存数据，不覆盖
            logger.warning("热点话题获取失败，保留原有缓存")
            # 获取原有缓存
            cached = trending_topics_util.get_cached_trending_topics()
            if cached.get('success', False):
                logger.info("使用原有热搜缓存数据")
                return cached
            
            # 确实没有缓存，返回空结果
            logger.warning("没有可用的热搜缓存，返回空结果")
            return {
                'weibo_hot': [],
                'baidu_hot': [],
                'zhihu_hot': [],
                'douyin_hot': [],
                'fashion_trends': [],
                'xiaohongshu_hot': [],
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'success': False,
                'method': 'empty'
            }
            
        except Exception as e:
            logger.error(f"更新热点话题失败：{e}")
            return {
                'weibo_hot': [],
                'baidu_hot': [],
                'zhihu_hot': [],
                'douyin_hot': [],
                'fashion_trends': [],
                'xiaohongshu_hot': [],
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'success': False,
                'method': 'fallback'
            }
    
    def _update_fashion_news(self) -> Dict[str, Any]:
        """更新时尚资讯"""
        try:
            logger.info("正在更新时尚资讯...")
            
            # 使用时尚门户服务获取时尚资讯
            if hasattr(fashion_portal_service, 'is_available') and fashion_portal_service.is_available():
                result = fashion_portal_service.get_fashion_news()
                if result.get('success', False):
                    logger.info(f"时尚门户获取成功：{len(result.get('fashion_news', []))} 条")
                    return result
            
            # 如果时尚门户失败，返回空结果
            logger.warning("时尚门户获取失败，返回空结果")
            return {
                'fashion_news': [],
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'success': False,
                'method': 'fallback'
            }
            
        except Exception as e:
            logger.error(f"更新时尚资讯失败：{e}")
            return {
                'fashion_news': [],
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'success': False,
                'method': 'error'
            }
    
    def _update_cache(self, trending_result: Dict[str, Any], fashion_result: Dict[str, Any]):
        """更新缓存 - 修复缓存结构问题"""
        try:
            # 将时尚资讯合并到热点结果中
            if fashion_result and 'fashion_news' in fashion_result:
                trending_result['fashion_trends'] = fashion_result.get('fashion_news', [])
            
            # 更新趋势话题服务的缓存 - 使用正确的嵌套结构
            with trending_topics_util._cache_lock:
                trending_topics_util._cache['trending_topics'] = {
                    'data': trending_result,
                    'timestamp': time.time()
                }
            
            logger.info("缓存更新完成")
            
        except Exception as e:
            logger.error(f"更新缓存失败：{e}")

    async def _generate_simulated_users_async(self):
        """异步生成模拟用户数据"""
        try:
            # 随机生成用户数量（150-300）
            user_count = random.randint(150, 300)
            logger.info(f"[模拟用户] 开始生成 {user_count} 个模拟用户")
            
            config = SimulationConfig(
                user_count=user_count,
                batch_size=5,
                conversation_turns=5,
                provider="aliyun",
                model="qwen-flash"
            )
            
            result = await user_simulation_service.generate_batch_users(config)
            
            if result.success:
                logger.info(f"[模拟用户] 生成完成，成功: {result.total_generated} 个用户")
            else:
                logger.warning(f"[模拟用户] 生成失败: {result.error_message}")
                
        except Exception as e:
            logger.error(f"[模拟用户] 生成过程异常: {e}")

    def update_simulated_users(self):
        """更新模拟用户数据（供定时调用）"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._generate_simulated_users_async())
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"更新模拟用户失败：{e}")

    def update_user_memory_mining(self):
        """挖掘用户记忆并生成话题（供定时调用）"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(user_memory_mining_service.mine_all_users())
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"挖掘用户记忆失败：{e}")


# 全局实例
scheduled_update_service = ScheduledUpdateService()
