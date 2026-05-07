# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import asyncio
import random
import logging
import threading
import traceback
import requests
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright未安装，时尚门户抓取功能受限")

try:
    from playwright_stealth import Stealth
    STEALTH_AVAILABLE = True
    logger.info("playwright-stealth 已加载，时尚门户将使用隐身模式")
except ImportError:
    STEALTH_AVAILABLE = False
    logger.warning("playwright-stealth未安装，反爬虫能力受限")

MAX_ITEMS_PER_SOURCE = 20

UAPIS_BASE_URL = "https://uapis.cn/api/v1/misc/hotboard"

FASHION_KEYWORDS = [
    '时尚', '穿搭', '美妆', '护肤', '化妆', '口红', '粉底', '面膜',
    '服装', '衣服', '裙子', '包包', '鞋子', '配饰', '珠宝', '首饰',
    '时装周', '品牌', '奢侈品', '大牌', '设计师', '模特', '街拍',
    '发型', '美甲', '香水', '防晒', '精华', '眼霜', '面霜',
    'vogue', 'elle', 'cosmo', 'bazaar', 'gq', 'fashion',
    '搭配', '风格', '潮流', '流行', '趋势',
    '明星同款', '网红', '博主', '种草', '拔草',
    '减肥', '瘦身', '健身', '瑜伽', '塑形',
    '婚礼', '婚纱', '新娘', '婚庆',
    'ootd', 'look', 'style', '彩妆', '眼影', '腮红', '高光', '修容',
    '水乳', '面霜', '眼霜', '精华液', '洁面', '卸妆',
    '眉笔', '眼线', '睫毛膏', '唇釉', '唇膏',
    '耳环', '项链', '手链', '戒指', '手表',
    '西装', '风衣', '大衣', '羽绒服', '毛衣', '衬衫', 'T恤',
    '牛仔裤', '休闲裤', '短裤', '半身裙', '连衣裙',
    '高跟鞋', '运动鞋', '靴子', '凉鞋', '拖鞋',
    '手提包', '单肩包', '双肩包', '斜挎包', '钱包',
    '礼物', '送礼', '礼物推荐', '变美', '瘦脸', '护肤',
]


class FashionPortalService:
    """
    时尚资讯服务
    多渠道获取时尚资讯：
    1. uapis.cn 热榜API筛选时尚话题
    2. B站时尚分区
    3. 微博热搜筛选
    4. 知乎话题筛选
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.bilibili.com/',
        })
        self._cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl = 1800
    
    def get_fashion_news(self) -> Dict[str, Any]:
        """获取时尚资讯"""
        result = {
            'fashion_trends': [],
            'bilibili_fashion': [],
            'weibo_fashion': [],
            'zhihu_fashion': [],
            'douyin_fashion': [],
            'douban_fashion': [],
            'toutiao_fashion': [],
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'success': False,
            'method': 'multi_source'
        }
        
        try:
            result = self._fetch_all_sources()
            total = len(result.get('fashion_trends', []))
            result['success'] = total > 0
            logger.info(f"时尚资讯获取完成，总计 {total} 条")
        except Exception as e:
            logger.error(f"获取时尚资讯失败: {e}")
            result['success'] = False
        
        return result
    
    def _fetch_all_sources(self) -> Dict[str, Any]:
        """从多个来源获取时尚资讯"""
        result = {
            'fashion_trends': [],
            'bilibili_fashion': [],
            'weibo_fashion': [],
            'zhihu_fashion': [],
            'douyin_fashion': [],
            'douban_fashion': [],
            'toutiao_fashion': [],
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'success': False,
            'method': 'multi_source'
        }
        
        all_fashion = []
        
        # 1. B站时尚分区
        try:
            items = self._fetch_bilibili_fashion()
            if items:
                result['bilibili_fashion'] = items
                all_fashion.extend(items)
                logger.info(f"B站时尚分区: {len(items)}条")
        except Exception as e:
            logger.warning(f"B站时尚分区获取失败: {e}")
        
        # 2. uapis.cn 热榜筛选
        platforms = {
            'weibo_fashion': 'weibo',
            'zhihu_fashion': 'zhihu',
            'douyin_fashion': 'douyin',
            'douban_fashion': 'douban-group',
        }
        
        for key, platform in platforms.items():
            try:
                items = self._fetch_from_uapis(platform)
                if items:
                    result[key] = items
                    all_fashion.extend(items)
                    logger.info(f"{platform} 时尚话题: {len(items)}条")
            except Exception as e:
                logger.warning(f"{platform} 获取失败: {e}")
        
        # 3. 今日头条时尚频道
        try:
            items = self._fetch_toutiao_fashion()
            if items:
                result['toutiao_fashion'] = items
                all_fashion.extend(items)
                logger.info(f"今日头条时尚: {len(items)}条")
        except Exception as e:
            logger.warning(f"今日头条时尚获取失败: {e}")
        
        result['fashion_trends'] = all_fashion[:100]
        result['success'] = len(all_fashion) > 0
        
        return result
    
    def _fetch_bilibili_fashion(self) -> List[Dict[str, str]]:
        """获取B站时尚分区内容"""
        items = []
        
        # B站时尚分区 rid=157
        url = "https://api.bilibili.com/x/web-interface/dynamic/region"
        params = {'ps': 20, 'rid': 157}
        
        try:
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            
            if data.get('code') == 0:
                archives = data.get('data', {})
                if isinstance(archives, dict):
                    archives = archives.get('archives', [])
                elif not isinstance(archives, list):
                    archives = []
                
                if isinstance(archives, list):
                    for i, item in enumerate(archives, 1):
                        if isinstance(item, dict):
                            items.append({
                                'rank': i,
                                'title': item.get('title', ''),
                                'url': f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                                'hot': item.get('stat', {}).get('view', 0),
                                'platform': 'bilibili_fashion',
                            })
        except Exception as e:
            logger.warning(f"B站时尚分区API失败: {e}")
        
        # B站热门
        try:
            url = "https://api.bilibili.com/x/web-interface/popular"
            params = {'ps': 30, 'pn': 1}
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            
            if data.get('code') == 0:
                bilibili_list = data.get('data', {})
                if isinstance(bilibili_list, dict):
                    bilibili_list = bilibili_list.get('list', [])
                elif not isinstance(bilibili_list, list):
                    bilibili_list = []
                
                if isinstance(bilibili_list, list):
                    for item in bilibili_list:
                        if isinstance(item, dict):
                            title = item.get('title', '').lower()
                            if any(kw in title for kw in FASHION_KEYWORDS):
                                if not any(i['title'] == item.get('title') for i in items):
                                    items.append({
                                        'rank': len(items) + 1,
                                        'title': item.get('title', ''),
                                        'url': f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                                        'hot': item.get('stat', {}).get('view', 0),
                                        'platform': 'bilibili_hot',
                                    })
        except Exception as e:
            logger.warning(f"B站热门API失败: {e}")
        
        return items[:MAX_ITEMS_PER_SOURCE]
    
    def _fetch_from_uapis(self, platform: str) -> List[Dict[str, str]]:
        """从uapis.cn获取并筛选时尚话题"""
        items = []
        
        try:
            resp = self.session.get(
                f"{UAPIS_BASE_URL}?type={platform}",
                timeout=10
            )
            data = resp.json()
            
            if 'list' in data and isinstance(data['list'], list):
                for item in data['list']:
                    if isinstance(item, dict):
                        title = item.get('title', '').lower()
                        if any(kw in title for kw in FASHION_KEYWORDS):
                            items.append({
                                'rank': len(items) + 1,
                                'title': item.get('title', ''),
                                'url': item.get('url', ''),
                                'hot': item.get('hot', ''),
                                'platform': platform,
                            })
        except Exception as e:
            logger.warning(f"uapis {platform} 失败: {e}")
        
        return items[:MAX_ITEMS_PER_SOURCE]
    
    def _fetch_toutiao_fashion(self) -> List[Dict[str, str]]:
        """获取今日头条时尚频道"""
        items = []
        
        try:
            url = "https://www.toutiao.com/api/pc/realtime_news/"
            params = {'category': 'news_fashion'}
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            
            news_list = data.get('data', {})
            if isinstance(news_list, dict):
                news_list = news_list.get('news_list', [])
            elif not isinstance(news_list, list):
                news_list = []
            
            if isinstance(news_list, list):
                for i, item in enumerate(news_list[:20], 1):
                    if isinstance(item, dict):
                        items.append({
                            'rank': i,
                            'title': item.get('title', ''),
                            'url': item.get('source_url', ''),
                            'hot': item.get('hot_value', ''),
                            'platform': 'toutiao_fashion',
                        })
        except Exception as e:
            logger.warning(f"今日头条时尚失败: {e}")
        
        return items


fashion_portal_service = FashionPortalService()
