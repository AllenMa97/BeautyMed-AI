# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import logging
import threading
import random
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from algorithm_services.utils.trending_topics import trending_topics_util
except ImportError:
    try:
        from trending_topics import trending_topics_util
    except ImportError:
        trending_topics_util = None
        logger.warning("TrendingTopicsUtil 导入失败")

try:
    from .browser_trending_service import browser_trending_service
except ImportError:
    try:
        from browser_trending_service import browser_trending_service
    except ImportError:
        browser_trending_service = None
        logger.warning("BrowserTrendingService 导入失败")

try:
    from .fashion_portal_service import fashion_portal_service
except ImportError:
    try:
        from fashion_portal_service import fashion_portal_service
    except ImportError:
        fashion_portal_service = None
        logger.warning("FashionPortalService 导入失败")

try:
    from .jina_reader_service import jina_reader_service
except ImportError:
    try:
        from jina_reader_service import jina_reader_service
    except ImportError:
        jina_reader_service = None
        logger.warning("JinaReaderService 导入失败")

try:
    from .feature_services.rss_feed_service import rss_feed_service
except ImportError:
    try:
        from rss_feed_service import rss_feed_service
    except ImportError:
        rss_feed_service = None
        logger.warning("RSSFeedService 导入失败")


class ExternalKnowledgeService:
    """
    外来知识服务 - 统一入口
    整合多种数据源获取外来知识：

    1. 热搜榜单服务 (TrendingTopicsService)
       - 微博、百度、知乎、抖音等热搜
       - 通过免费API、浏览器、requests多种方式

    2. 浏览器自动化服务 (BrowserTrendingService)
       - Playwright模拟浏览器
       - 增强反检测能力

    3. 时尚门户服务 (FashionPortalService)
       - 时尚、美妆相关资讯

    4. Jina Reader服务 (JinaReaderService)
       - 读取任意网页内容
       - 绕过反爬虫保护

    5. RSS订阅服务 (RSSFeedService)
       - 多种分类RSS源
       - 中文、英文新闻源

    使用降级机制：
    - 优先使用免费API
    - 失败则使用浏览器自动化
    - 再失败使用RSS源
    - 最后使用Jina Reader
    """

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl = 1800
        self._refresh_thread: Optional[threading.Thread] = None
        self._stop_refresh = threading.Event()
        self._initialized = False
        self.max_retries = 3
        self.sources_priority = [
            'trending_topics',
            'browser',
            'fashion',
            'rss',
            'jina_reader'
        ]

    def _get_from_cache(self, key: str) -> Optional[Any]:
        with self._cache_lock:
            if key in self._cache:
                cached = self._cache[key]
                if datetime.now().timestamp() - cached['timestamp'] < self._cache_ttl:
                    return cached['data']
        return None

    def _save_to_cache(self, key: str, data: Any):
        with self._cache_lock:
            self._cache[key] = {
                'data': data,
                'timestamp': datetime.now().timestamp()
            }

    def get_all_knowledge(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        获取所有外来知识

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            dict: 包含所有知识来源的数据
        """
        cache_key = 'external_knowledge'
        if not force_refresh:
            cached = self._get_from_cache(cache_key)
            if cached:
                logger.info("外来知识命中缓存")
                return cached

        result = {
            'trending_topics': self._get_trending_topics(),
            'browser_data': {'success': False, 'data': {}, 'reason': 'skipped_login_required'},
            'fashion_data': self._get_fashion_data(),
            'rss_data': self._get_rss_data(),
            'jina_reader_status': self._check_jina_reader(),
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'success': True
        }

        total_items = (
            len(result.get('trending_topics', {}).get('weibo_hot', [])) +
            len(result.get('trending_topics', {}).get('baidu_hot', [])) +
            len(result.get('trending_topics', {}).get('zhihu_hot', [])) +
            len(result.get('fashion_data', {}).get('fashion_trends', [])) +
            len(result.get('rss_data', {}).get('fashion', []))
        )

        result['total_items'] = total_items
        result['success'] = total_items > 0

        self._save_to_cache(cache_key, result)
        logger.info(f"外来知识获取完成，总计 {total_items} 条")

        return result

    def _get_trending_topics(self) -> Dict[str, Any]:
        """获取热搜话题"""
        if not trending_topics_util:
            return {'success': False, 'data': {}}

        try:
            result = trending_topics_util.get_all_trending_topics()
            return {
                'success': result.get('success', False),
                'data': result
            }
        except Exception as e:
            logger.warning(f"获取热搜话题失败: {e}")
            return {'success': False, 'data': {}}

    def _get_browser_data(self) -> Dict[str, Any]:
        """获取浏览器数据"""
        if not browser_trending_service:
            return {'success': False, 'data': {}}

        try:
            result = browser_trending_service.get_all_trending_topics()
            return {
                'success': result.get('success', False),
                'data': result
            }
        except Exception as e:
            logger.warning(f"获取浏览器数据失败: {e}")
            return {'success': False, 'data': {}}

    def _get_fashion_data(self) -> Dict[str, Any]:
        """获取时尚数据"""
        if not fashion_portal_service:
            return {'success': False, 'data': {}}

        try:
            result = fashion_portal_service.get_fashion_news()
            return {
                'success': result.get('success', False),
                'data': result
            }
        except Exception as e:
            logger.warning(f"获取时尚数据失败: {e}")
            return {'success': False, 'data': {}}

    def _get_rss_data(self) -> Dict[str, Any]:
        """获取RSS数据"""
        if not rss_feed_service:
            return {'success': False, 'data': {}}

        try:
            result = rss_feed_service.get_all_trends(limit=5)
            return {
                'success': bool(result),
                'data': result
            }
        except Exception as e:
            logger.warning(f"获取RSS数据失败: {e}")
            return {'success': False, 'data': {}}

    def _check_jina_reader(self) -> Dict[str, Any]:
        """检查Jina Reader状态"""
        if not jina_reader_service:
            return {'available': False, 'reason': 'service_not_available'}

        return {'available': True}

    def get_url_content(self, url: str) -> Dict[str, Any]:
        """
        使用Jina Reader获取指定URL的内容

        Args:
            url: 目标URL

        Returns:
            dict: {
                'success': bool,
                'content': str,
                'title': str,
                'error': str,
                'method': str
            }
        """
        if not jina_reader_service:
            return {
                'success': False,
                'content': '',
                'title': '',
                'error': 'Jina Reader服务不可用',
                'method': 'none'
            }

        try:
            return jina_reader_service.read_url(url)
        except Exception as e:
            logger.warning(f"获取URL内容失败: {e}")
            return {
                'success': False,
                'content': '',
                'title': '',
                'error': str(e),
                'method': 'none'
            }

    def get_trending_by_source(self, source: str = 'weibo') -> List[Dict[str, Any]]:
        """
        获取指定来源的热搜

        Args:
            source: 来源名称 (weibo, baidu, zhihu, douyin, bilibili等)

        Returns:
            list: 热搜列表
        """
        all_knowledge = self.get_all_knowledge()

        trending_data = all_knowledge.get('trending_topics', {}).get('data', {})
        browser_data = all_knowledge.get('browser_data', {}).get('data', {})

        source_key = f'{source}_hot'
        items = trending_data.get(source_key, [])

        if not items and browser_data:
            items = browser_data.get(source_key, [])

        return items

    def get_fashion_trends(self) -> List[Dict[str, Any]]:
        """获取时尚趋势"""
        all_knowledge = self.get_all_knowledge()

        fashion_data = all_knowledge.get('fashion_data', {}).get('data', {})
        rss_data = all_knowledge.get('rss_data', {}).get('data', {})

        items = []
        items.extend(fashion_data.get('fashion_trends', []))
        items.extend(rss_data.get('fashion', []))
        items.extend(rss_data.get('chinese_fashion', []))
        items.extend(rss_data.get('beauty', []))

        return items[:50]

    def get_news_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        按分类获取新闻

        Args:
            category: 分类名称 (news, tech, entertainment, chinese_news等)

        Returns:
            list: 新闻列表
        """
        all_knowledge = self.get_all_knowledge()
        rss_data = all_knowledge.get('rss_data', {}).get('data', {})

        return rss_data.get(category, [])

    def get_combined_context(self, max_items: int = 20) -> str:
        """
        获取合并后的上下文信息

        Args:
            max_items: 最大条目数

        Returns:
            str: 格式化的上下文字符串
        """
        all_knowledge = self.get_all_knowledge()

        context_parts = []

        weibo = all_knowledge.get('trending_topics', {}).get('data', {}).get('weibo_hot', [])[:5]
        if weibo:
            context_parts.append("【微博热搜】" + " | ".join([item.get('title', '') for item in weibo if item.get('title')]))

        baidu = all_knowledge.get('trending_topics', {}).get('data', {}).get('baidu_hot', [])[:5]
        if baidu:
            context_parts.append("【百度热搜】" + " | ".join([item.get('title', '') for item in baidu if item.get('title')]))

        zhihu = all_knowledge.get('trending_topics', {}).get('data', {}).get('zhihu_hot', [])[:5]
        if zhihu:
            context_parts.append("【知乎热榜】" + " | ".join([item.get('title', '') for item in zhihu if item.get('title')]))

        fashion = all_knowledge.get('fashion_data', {}).get('data', {}).get('fashion_trends', [])[:5]
        if fashion:
            context_parts.append("【时尚热点】" + " | ".join([item.get('title', '') for item in fashion if item.get('title')]))

        if not context_parts:
            return "暂无外来知识"

        return "\n\n".join(context_parts)

    def search_knowledge(self, keyword: str) -> Dict[str, Any]:
        """
        搜索知识

        Args:
            keyword: 搜索关键词

        Returns:
            dict: 搜索结果
        """
        all_knowledge = self.get_all_knowledge()
        results = {
            'keyword': keyword,
            'trending_matches': [],
            'fashion_matches': [],
            'news_matches': [],
            'total': 0
        }

        keyword_lower = keyword.lower()

        sources = [
            all_knowledge.get('trending_topics', {}).get('data', {}),
            all_knowledge.get('fashion_data', {}).get('data', {}),
            all_knowledge.get('rss_data', {}).get('data', {})
        ]

        for source in sources:
            if not isinstance(source, dict):
                continue

            for key, items in source.items():
                if not isinstance(items, list):
                    continue

                for item in items:
                    title = item.get('title', '')
                    if title and keyword_lower in title.lower():
                        match_type = 'trending_matches' if 'hot' in key else 'fashion_matches'
                        if 'news' in key or 'chinese' in key:
                            match_type = 'news_matches'

                        results[match_type].append({
                            'title': title,
                            'source': key,
                            'url': item.get('url', ''),
                            'hot': item.get('hot', '')
                        })

        results['total'] = (
            len(results['trending_matches']) +
            len(results['fashion_matches']) +
            len(results['news_matches'])
        )

        return results

    def warmup(self) -> bool:
        """预热服务"""
        if self._initialized:
            logger.info("外来知识服务已预热")
            return True

        logger.info("正在预热外来知识服务...")
        try:
            self.get_all_knowledge(force_refresh=True)
            self._initialized = True
            logger.info("外来知识服务预热完成")
            return True
        except Exception as e:
            logger.warning(f"外来知识服务预热失败: {e}")
            return False

    def start_background_refresh(self):
        """启动后台刷新"""
        if self._refresh_thread and self._refresh_thread.is_alive():
            logger.info("外来知识后台刷新线程已在运行")
            return

        self._stop_refresh.clear()
        self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._refresh_thread.start()
        logger.info("外来知识后台刷新线程已启动")

    def stop_background_refresh(self):
        """停止后台刷新"""
        if self._refresh_thread:
            self._stop_refresh.set()
            self._refresh_thread.join(timeout=5)
            logger.info("外来知识后台刷新线程已停止")

    def _refresh_loop(self):
        """后台刷新循环"""
        while not self._stop_refresh.is_set():
            self._stop_refresh.wait(timeout=self._cache_ttl)
            if self._stop_refresh.is_set():
                break
            try:
                logger.debug("后台刷新外来知识...")
                self.get_all_knowledge(force_refresh=True)
            except Exception as e:
                logger.warning(f"后台刷新外来知识失败: {e}")


external_knowledge_service = ExternalKnowledgeService()
