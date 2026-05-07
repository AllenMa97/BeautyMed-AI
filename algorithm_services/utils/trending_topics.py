"""
热搜话题工具
获取微博、搜索引擎、小红书等平台的热搜信息
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import os
import requests
from bs4 import BeautifulSoup
import re
import random
from typing import List, Dict, Optional, Any
from datetime import datetime
import time
import threading
from algorithm_services.api.schemas.feature_schemas.trending_topics_schemas import (
    TrendingTopicsRequest,
    TrendingTopicsResponse,
    TrendingTopicsResponseData
)
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from algorithm_services.core.services.browser_trending_service import browser_trending_service, PLAYWRIGHT_AVAILABLE
except ImportError:
    try:
        from browser_trending_service import browser_trending_service, PLAYWRIGHT_AVAILABLE
    except ImportError:
        PLAYWRIGHT_AVAILABLE = False
        browser_trending_service = None
        logger.warning("浏览器自动化服务导入失败")

try:
    from algorithm_services.core.services.fashion_portal_service import fashion_portal_service
except ImportError:
    try:
        from fashion_portal_service import fashion_portal_service
    except ImportError:
        fashion_portal_service = None
        logger.warning("时尚门户服务导入失败")


class TrendingTopicsUtil:
    """热搜话题工具"""

    description = "获取当前热搜话题信息"

    UAPIS_BASE_URL = "https://uapis.cn/api/v1/misc/hotboard"

    FASHION_KEYWORDS = [
        '时尚', '穿搭', '美妆', '护肤', '化妆', '口红', '粉底', '面膜',
        '服装', '衣服', '裙子', '包包', '鞋子', '配饰', '珠宝', '首饰',
        '时装周', '品牌', '奢侈品', '大牌', '设计师', '模特', '街拍',
        '发型', '美甲', '香水', '防晒', '精华', '眼霜', '面霜',
        'vogue', 'elle', 'cosmo', 'bazaar', 'gq', 'fashion',
        '搭配', '风格', '潮流', '流行', '趋势',
    ]

    CATEGORY_KEYWORDS = {
        'fashion': FASHION_KEYWORDS,
    }

    def __init__(self):
        self.session = requests.Session()
        self._cache: Dict[str, any] = {}
        self._cache_lock = threading.Lock()
        self._refresh_thread: Optional[threading.Thread] = None
        self._stop_refresh = threading.Event()
        self._cache_ttl = int(os.getenv("TRENDING_CACHE_TTL", 1800))
        self._initialized = False
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0',
        ]

    def get_random_headers(self):
        user_agent = random.choice(self.user_agents)
        return {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

    def warmup(self) -> bool:
        if self._initialized:
            logger.info("热搜话题工具已预热，跳过")
            return True

        logger.info("正在预热热搜话题工具...")
        try:
            data = self.get_all_trending_topics()
            with self._cache_lock:
                self._cache['trending_topics'] = {
                    'data': data,
                    'timestamp': time.time()
                }
            self._initialized = True
            logger.info(f"热搜话题工具预热完成")
            return True
        except Exception as e:
            logger.warning(f"热搜话题工具预热失败: {e}")
            return False

    def get_all_trending_topics(self) -> Dict[str, any]:
        result = self._get_empty_result()

        try:
            result = self._fetch_via_free_api()
            total = len(result.get('baidu_hot', [])) + len(result.get('zhihu_hot', []))
            if total > 0:
                logger.info(f"免费API获取热搜成功，总计: {total} 条数据")
            else:
                logger.warning("免费API获取数据不足")
        except Exception as e:
            logger.warning(f"免费API获取失败：{e}")

        if fashion_portal_service:
            try:
                fashion_result = fashion_portal_service.get_fashion_news()
                if fashion_result and fashion_result.get('success'):
                    result['fashion_news'] = fashion_result.get('fashion_news', [])
            except Exception as e:
                logger.warning(f"获取时尚门户数据失败：{e}")

        return result

    def _fetch_via_free_api(self) -> Dict[str, any]:
        trending_data = {
            'baidu_hot': [],
            'zhihu_hot': [],
            'douyin_hot': [],
            'xiaohongshu_hot': [],
            'weibo_hot': [],
            'bilibili': [],
            'douban': [],
            'toutiao_hot': [],
            'sina': [],
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'success': True,
            'method': 'free_api'
        }

        platforms = {
            'baidu_hot': 'baidu',
            'zhihu_hot': 'zhihu',
            'douyin_hot': 'douyin',
            'bilibili': 'bilibili',
            'toutiao_hot': 'toutiao',
            'thepaper': 'thepaper',
            'hupu': 'hupu',
            'douban': 'douban',
            '36kr': '36kr',
            'sina': 'sina',
        }

        for key, platform in platforms.items():
            try:
                resp = self.session.get(
                    f"{self.UAPIS_BASE_URL}?type={platform}",
                    timeout=10
                )
                data = resp.json()

                if 'list' in data and isinstance(data.get('list'), list):
                    items = []
                    for item in data['list'][:30]:
                        if isinstance(item, dict):
                            items.append({
                                'rank': len(items) + 1,
                                'title': item.get('title', ''),
                                'url': item.get('url', ''),
                                'hot': item.get('hot', ''),
                                'platform': platform
                            })
                    trending_data[key] = items
            except Exception as e:
                logger.warning(f"获取 {platform} 失败: {e}")

        trending_data['success'] = len(trending_data['baidu_hot']) > 0
        return trending_data

    def _get_empty_result(self) -> Dict[str, any]:
        return {
            'baidu_hot': [],
            'zhihu_hot': [],
            'douyin_hot': [],
            'xiaohongshu_hot': [],
            'weibo_hot': [],
            'bilibili': [],
            'douban': [],
            'toutiao_hot': [],
            'sina': [],
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'success': False,
            'method': 'empty'
        }

    def get_fashion_beauty_trends(self) -> List[Dict[str, str]]:
        all_trends = self.get_all_trending_topics()

        fashion_beauty_keywords = [
            '美妆', '护肤', '口红', '面膜', '精华', '面霜', '防晒', '粉底',
            '眼影', '睫毛膏', '唇膏', '化妆', '卸妆', '洁面', '爽肤水',
            '乳液', '眼霜', '精华液', '面油', '护肤', '美容', '保养',
            '时尚', '穿搭', '发型', '造型', '潮流', '流行', '风格',
        ]

        fashion_beauty_trends = []

        for platform, trends in [('baidu', all_trends.get('baidu_hot', []))]:
            for trend in trends:
                title = trend.get('title', '').lower()
                for keyword in fashion_beauty_keywords:
                    if keyword in title:
                        trend_copy = trend.copy()
                        trend_copy['related_to'] = 'fashion_beauty'
                        fashion_beauty_trends.append(trend_copy)
                        break

        return fashion_beauty_trends

    def get_cached_trending_topics(self) -> Dict[str, any]:
        cached = self._cache.get('trending_topics')
        if cached:
            if time.time() - cached['timestamp'] < self._cache_ttl:
                return cached['data']
            threading.Thread(target=self._refresh_cache_async, daemon=True).start()
            return cached['data']

        return {
            "baidu_hot": [],
            "xiaohongshu_hot": [],
            "combined_context": "暂无热搜信息",
            "success": False
        }

    def _refresh_cache_async(self):
        try:
            data = self.get_all_trending_topics()
            with self._cache_lock:
                self._cache['trending_topics'] = {
                    'data': data,
                    'timestamp': time.time()
                }
        except Exception as e:
            logger.warning(f"异步刷新热搜缓存失败: {e}")

    def get_trending_topics(self, topic_type: str = "general") -> Dict[str, Any]:
        """获取热搜话题（返回字典格式）"""
        try:
            if topic_type == "fashion_beauty":
                trending_data = self.get_fashion_beauty_trends()
                combined_context = f"当前时尚美妆领域的热门话题包括：{', '.join([item['title'] for item in trending_data[:5]]) if trending_data else '暂无热门话题'}"
                return {
                    "fashion_beauty_trends": trending_data,
                    "baidu_hot": [],
                    "xiaohongshu_hot": [],
                    "combined_context": combined_context,
                    "success": True,
                    "fetch_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            else:
                trending_data = self.get_all_trending_topics()
                weibo_tops = [item['title'] for item in trending_data.get('weibo_hot', [])[:3]]
                baidu_tops = [item['title'] for item in trending_data.get('baidu_hot', [])[:3]]
                xhs_tops = [item['title'] for item in trending_data.get('xiaohongshu_hot', [])[:3]]

                combined_context = f"微博热搜前三：{', '.join(weibo_tops) if weibo_tops else '暂无'}；" \
                                  f"百度热搜前三：{', '.join(baidu_tops) if baidu_tops else '暂无'}；" \
                                  f"小红书热门话题：{', '.join(xhs_tops) if xhs_tops else '暂无'}"

                return {
                    "weibo_hot": trending_data.get('weibo_hot', []),
                    "baidu_hot": trending_data.get('baidu_hot', []),
                    "xiaohongshu_hot": trending_data.get('xiaohongshu_hot', []),
                    "combined_context": combined_context,
                    "success": trending_data.get('success', True),
                    "fetch_time": trending_data.get('fetch_time', '')
                }

        except Exception as e:
            logger.error(f"获取热搜话题信息失败: {str(e)}")
            return {
                "fashion_beauty_trends": [],
                "weibo_hot": [],
                "baidu_hot": [],
                "xiaohongshu_hot": [],
                "combined_context": "无法获取当前热搜信息",
                "success": False,
                "fetch_time": ""
            }

    def get_for_context(self, topic_type: str = "general") -> str:
        """获取热搜上下文（返回字符串格式，用于直接插入prompt）"""
        try:
            if topic_type == "fashion_beauty":
                trending_data = self.get_fashion_beauty_trends()
                return f"当前时尚美妆领域的热门话题包括：{', '.join([item['title'] for item in trending_data[:5]]) if trending_data else '暂无热门话题'}"
            else:
                trending_data = self.get_all_trending_topics()
                weibo_tops = [item['title'] for item in trending_data.get('weibo_hot', [])[:3]]
                baidu_tops = [item['title'] for item in trending_data.get('baidu_hot', [])[:3]]
                xhs_tops = [item['title'] for item in trending_data.get('xiaohongshu_hot', [])[:3]]

                return f"微博热搜前三：{', '.join(weibo_tops) if weibo_tops else '暂无'}；" \
                       f"百度热搜前三：{', '.join(baidu_tops) if baidu_tops else '暂无'}；" \
                       f"小红书热门话题：{', '.join(xhs_tops) if xhs_tops else '暂无'}"
        except Exception as e:
            logger.error(f"获取热搜上下文失败: {str(e)}")
            return "无法获取当前热搜信息"


trending_topics_util = TrendingTopicsUtil()
