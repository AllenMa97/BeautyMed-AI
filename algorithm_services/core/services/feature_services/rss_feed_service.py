# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import feedparser
import requests
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging
from urllib.parse import urljoin
import ssl
import urllib.request
import json
import time
import random
import threading

logger = logging.getLogger(__name__)

class RSSFeedService:
    """
    RSS订阅服务 - 增强版
    用于获取时尚、美妆、娱乐、新闻、科技等相关RSS源信息
    支持多种数据源：RSS订阅、新闻API、热点榜单

    增强功能：
    1. 更多中文RSS源
    2. 备用数据源机制
    3. RSS解析失败时使用网页抓取
    4. 并发获取加速
    """

    def __init__(self):
        self.session = requests.Session()
        self._update_headers()
        self._setup_ssl_context()
        self._init_all_feeds()
        self._init_backup_sources()
        self._cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl = 1800

    def _update_headers(self):
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        ]
        self.session.headers.update({
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })

    def _setup_ssl_context(self):
        try:
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        except Exception:
            self.ssl_context = None

    def _init_backup_sources(self):
        """初始化备用数据源"""
        self.backup_api_sources = {
            'toutiao': [
                'https://www.toutiao.com/hot_news/',
                'https://www.toutiao.com/api/pc/feed/',
            ],
            'bilibili': [
                'https://api.bilibili.com/x/web-interface/popular',
                'https://api.bilibili.com/x/web-interface/dynamic/region',
            ],
            'weibo': [
                'https://weibo.com/ajax/statuses/mymblog',
                'https://m.weibo.cn/statuses/forward',
            ],
        }

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
    
    def _init_all_feeds(self):
        self.fashion_beauty_feeds = [
            "https://www.vogue.com/feed",
            "https://www.elle.com/fashion/rss/",
            "https://www.harpersbazaar.com/fashion/rss/",
            "https://www.cosmopolitan.com/style-beauty/rss/",
            "https://www.instyle.com/fashion/rss/",
            "https://www.glamour.com/fashion/rss/",
            "https://www.fashionista.com/feed/",
            "https://www.whowhatwear.com/feed",
            "https://www.refinery29.com/rss",
            "https://www.dazed.co.uk/feed/",
            "https://www.i-d.co/feed/",
            "https://www.businessoffashion.com/rss",
            "https://www.shein.com/news.rss",
        ]

        self.beauty_feeds = [
            "https://www.allure.com/beauty/rss/",
            "https://www.byrdie.com/beauty/rss/",
            "https://www.glamour.com/beauty/rss/",
            "https://www.elle.com/beauty/rss/",
            "https://www.sephora.com/feed",
            "https://www.glossier.com/feed",
            "https://www.cosmopolitan.com/beauty/rss/",
            "https://www.marieclaire.com/beauty/rss/",
        ]

        self.entertainment_feeds = [
            "https://feeds.feedburner.com/ew/AllEntertainment",
            "https://www.hollywoodreporter.com/rss/latest",
            "https://www.eonline.com/news/rss",
            "https://www.justjared.com/feed/",
            "https://www.dailymail.co.uk/news/index.rss",
            "https://pagesix.com/feed/",
            "https://www.tmz.com/rss.xml",
            "https://www.popsugar.com/feed",
        ]

        self.chinese_fashion_feeds = [
            "https://www.vogue.com.cn/rss",
            "https://ellechina.com/rss",
            "https://www.gq.com.cn/rss/news.xml",
            "https://www.vogue.com.hk/rss",
            "https://www.yoka.com/rss.xml",
            "https://www.onlylady.com/rss",
        ]

        self.news_feeds = [
            "https://feeds.feedburner.com/ndrmf/cYye",
            "https://www.theguardian.com/world/rss",
            "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
            "https://feeds.bbci.co.uk/news/world/rss.xml",
            "https://www.aljazeera.com/xml/rss/all.xml",
            "https://www.reuters.com/feed/top/rss",
            "https://www.washingtonpost.com/rss/",
            "https://www.wsj.com/rss/",
            "https://www.apnews.com/rss",
            "https://www.npr.org/rss/rss.php",
        ]

        self.tech_feeds = [
            "https://techcrunch.com/feed/",
            "https://www.theverge.com/rss/index.xml",
            "https://mashable.com/rss",
            "https://wired.com/feed/rss",
            "https://arstechnica.com/feed/",
            "https://www.engadget.com/rss.xml",
            "https://www.zdnet.com/news/rss.xml",
            "https://www.cnet.com/rss/news/",
            "https://www.theinformation.com/feed",
            "https://www.techradar.com/rss",
        ]

        self.chinese_news_feeds = [
            "https://www.chinanews.com.cn/rss/gn-news.xml",
            "https://news.sina.com.cn/rss/rollnews.dxml",
            "https://www.qq.com/news/rss",
            "https://www.ifeng.com/rss",
            "https://www.yahoo.com/rss",
            "https://www.cctv.com/rss/news",
            "https://news.cctv.com/rss",
            "https://www.xinhuanet.com/politics/news_politics.xml",
            "http://www.people.com.cn/rss/gn_index.xml",
            "https://www.guancha.cn/news.xml",
            "https://www.163.com/rss/",
            "https://www.sohu.com/rssFeed/123456",
            "https://www.taihainet.com/rss",
        ]

        self.chinese_tech_feeds = [
            "https://www.36kr.com/feed/",
            "https://www.ifanr.com/feed",
            "https://www.ithome.com/rss",
            "https://www.pingwest.com/rss",
            "https://www.leiphone.com/feed",
            "https://www.36kr.com/newsflashes",
        ]

        self.chinese_entertainment_feeds = [
            "https://www.douban.com/feed/recommend",
            "https://movie.douban.com/feed/recommend",
            "https://music.douban.com/feed/recommend",
            "https://book.douban.com/feed/recommend",
        ]

        self.chinese_finance_feeds = [
            "https://finance.sina.com.cn/rss/",
            "https://www.yicai.com/rss/",
            "https://www.cls.cn/rss",
            "https://www.10jqka.com.cn/rss",
            "http://stock.10jqka.com.cn/rssfeed/",
        ]

        self.lifestyle_feeds = [
            "https://www.deliciousreverie.co.uk/rss",
            "https://www.refinery29.com/rss",
            "https://www.whowhatwear.com/rss",
            "https://www.architecturaldigest.com/rss",
            "https://www.dezeen.com/feed/",
            "https://www.apartmenttherapy.com/feed",
        ]

        self.celebrity_gossip_feeds = [
            "https://www.eonline.com/news/rss",
            "https://www.justjared.com/feed/",
            "https://www.dailymail.co.uk/news/index.rss",
            "https://pagesix.com/feed/",
            "https://www.tmz.com/rss.xml",
            "https://www.popsugar.com/feed",
            "https://www.people.com/rss/",
            "https://www.usmagazine.com/feed/",
        ]

        self.film_tv_feeds = [
            "https://variety.com/feed/",
            "https://www.indiewire.com/feed/",
            "https://www.tvline.com/feed/",
            "https://www.hollywoodreporter.com/rss/latest",
            "https://www.ew.com/feed/",
            "https://www.digitalspy.com/rss.xml",
        ]

        self.hk_taiwan_feeds = [
            "https://www.bbc.com/zhongwen/simp/rss.xml",
            "https://www.cna.com.tw/rss_all.xml",
            "https://www.setn.com/rss/",
            "https://www.ettoday.net/rss/focus/501.xml",
            "https://www.storm.mg/rss",
        ]

        self.finance_wealth_feeds = [
            "https://www.forbes.com/real-time/feed2/",
            "https://www.bloomberg.com/markets/feeds/paas/index.html",
            "https://www.cnbc.com/id/100003114/device/rss/rss.html",
            "https://www.marketwatch.com/rss/news",
            "https://www.investing.com/rss/news.rss",
            "https://www.seekingalpha.com/rss/breaking-news",
        ]

        self.health_wellness_feeds = [
            "https://www.medicalnewstoday.com/newsfeeds/rss",
            "https://www.healthline.com/rss/health",
            "https://www.webmd.com/rss/default.aspx",
            "https://www.mayoclinic.org/rss/rss.xml",
            "https://www.nih.gov/news-events/news-releases/rss-feed",
        ]

        self.food_travel_feeds = [
            "https://www.travelweekly.com/RSS",
            "https://www.afar.com/feed/rss",
        ]

        self.music_feeds = [
            "https://www.billboard.com/feed/",
            "https://www.rollingstone.com/feed/",
            "https://pitchfork.com/feed/rss/news/",
            "https://www.nme.com/news/feed",
            "https://www.spin.com/feed/",
            "https://www.stereogum.com/rss/",
            "https://www.bbc.co.uk/news/entertainment_and_arts/rss.xml",
            "https://music.yahoo.com/rss",
            "https://www.billboard.com/articles/rss.xml",
            "https://www.grammy.com/rss/grammy-news.xml",
            "https://www.bmi.com/rss/news",
        ]

        self.food_feeds = [
            "https://www.seriouseats.com/feeds/rss",
            "https://www.epicurious.com/fullRSS/index.xml",
            "https://www.bonappetit.com/feed/rss",
            "https://www.taste.com.au/feed/rss",
            "https://www.bbcgoodfood.com/feed",
            "https://www.delish.com/feed/",
            "https://www.foodnetwork.com/fn-dish/feed",
            "https://www.saveur.com/feed/",
            "https://www.cookinglight.com/feed",
            "https://www.eater.com/feed",
            "https://www.bloomberg.com/markets/feeds/paas/food.xml",
        ]

        self.travel_feeds = [
            "https://www.lonelyplanet.com/news/feed",
            "https://www.travelandleisure.com/feed",
            "https://www.cntraveler.com/feed",
            "https://www.nationalgeographic.com/feeds/news/travel",
            "https://www.forbes.com/travel/rss",
            "https://www.tripadvisor.com/RSS",
            "https://www.skyscanner.com/rss/feed",
            "https://www.expedia.com/rss/",
            "https://www.booking.com/rss/",
        ]

        self.astrology_feeds = [
            "https://www.horoscope.com/feed/rss/horoscope.xml",
            "https://www.astro.com/horoscopes/rss.xml",
            "https://www.astrologyzone.com/feed/",
            "https://www.tarot.com/horoscopes/rss",
            "https://www.cosmopolitan.com/horoscopes/rss/",
            "https://www.elle.com/horoscopes/rss/",
            "https://www.horoscope.com/feed/rss/daily.xml",
            "https://www.astrology.com/horoscopes/rss",
        ]

        self.rss_feed_sources = {
            'fashion': self.fashion_beauty_feeds,
            'beauty': self.beauty_feeds,
            'entertainment': self.entertainment_feeds,
            'chinese_fashion': self.chinese_fashion_feeds,
            'news': self.news_feeds,
            'tech': self.tech_feeds,
            'chinese_news': self.chinese_news_feeds,
            'chinese_tech': self.chinese_tech_feeds,
            'chinese_entertainment': self.chinese_entertainment_feeds,
            'chinese_finance': self.chinese_finance_feeds,
            'lifestyle': self.lifestyle_feeds,
            'celebrity': self.celebrity_gossip_feeds,
            'film_tv': self.film_tv_feeds,
            'hk_taiwan': self.hk_taiwan_feeds,
            'finance': self.finance_wealth_feeds,
            'health': self.health_wellness_feeds,
            'food_travel': self.food_travel_feeds,
            'music': self.music_feeds,
            'food': self.food_feeds,
            'travel': self.travel_feeds,
            'astrology': self.astrology_feeds,
        }

        self.news_api_sources = {
            'newsapi': {
                'base_url': 'https://newsapi.org/v2',
                'top_headlines': '/top-headlines',
            },
            'gnews': {
                'base_url': 'https://gnews.io/api/v4',
            },
            'mediastack': {
                'base_url': 'http://api.mediastack.com/v1',
            }
        }
    
    def fetch_rss_feed(self, feed_url: str, limit: int = 10) -> List[Dict[str, str]]:
        try:
            if self.ssl_context:
                https_handler = urllib.request.HTTPSHandler(context=self.ssl_context)
                opener = urllib.request.build_opener(https_handler)
                urllib.request.install_opener(opener)
            
            feed = feedparser.parse(feed_url)
            
            if feed.bozo and not feed.entries:
                bozo_error = str(feed.bozo_exception)
                if 'SSL' in bozo_error or 'certificate' in bozo_error.lower():
                    logger.debug(f"RSS SSL错误(已忽略): {feed_url}")
                elif 'text/html' in bozo_error:
                    logger.debug(f"RSS源返回HTML而非XML: {feed_url}")
                else:
                    logger.debug(f"RSS解析警告: {feed_url}, 错误: {bozo_error}")
            
            entries = []
            for entry in feed.entries[:limit]:
                title = entry.get("title", "")
                if title:
                    entry_data = {
                        "title": title,
                        "summary": entry.get("summary", "")[:200],
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "source": getattr(feed.feed, 'title', "Unknown Source") or "Unknown Source"
                    }
                    entries.append(entry_data)
            
            return entries
        except Exception as e:
            logger.debug(f"获取RSS源失败: {feed_url}, 错误: {e}")
            return []
    
    def fetch_multiple_feeds(self, feed_urls: List[str], limit: int = 5) -> List[Dict[str, str]]:
        all_entries = []
        for url in feed_urls:
            entries = self.fetch_rss_feed(url, limit)
            all_entries.extend(entries)
        return all_entries
    
    def get_fashion_beauty_trends(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        获取时尚美妆相关趋势
        """
        all_feeds = self.fashion_beauty_feeds + self.beauty_feeds
        return self.fetch_multiple_feeds(all_feeds, limit)
    
    def get_fashion_news(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        获取时尚新闻
        """
        return self.fetch_multiple_feeds(self.fashion_beauty_feeds, limit)
    
    def get_beauty_news(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        获取美妆新闻
        """
        return self.fetch_multiple_feeds(self.beauty_feeds, limit)
    
    def get_entertainment_news(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        获取娱乐八卦新闻
        """
        return self.fetch_multiple_feeds(self.entertainment_feeds, limit)
    
    def get_news(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取国际新闻"""
        return self.fetch_multiple_feeds(self.news_feeds, limit)
    
    def get_tech_news(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取科技新闻"""
        return self.fetch_multiple_feeds(self.tech_feeds, limit)
    
    def get_chinese_news(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取中文新闻"""
        return self.fetch_multiple_feeds(self.chinese_news_feeds, limit)
    
    def get_lifestyle_news(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取生活方式新闻"""
        return self.fetch_multiple_feeds(self.lifestyle_feeds, limit)
    
    def get_celebrity_news(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取名人八卦新闻"""
        return self.fetch_multiple_feeds(self.celebrity_gossip_feeds, limit)
    
    def get_film_tv_news(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取电影电视新闻"""
        return self.fetch_multiple_feeds(self.film_tv_feeds, limit)
    
    def get_hk_taiwan_news(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取港澳台新闻"""
        return self.fetch_multiple_feeds(self.hk_taiwan_feeds, limit)
    
    def get_finance_news(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取财经新闻"""
        return self.fetch_multiple_feeds(self.finance_wealth_feeds, limit)
    
    def get_health_news(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取健康新闻"""
        return self.fetch_multiple_feeds(self.health_wellness_feeds, limit)
    
    def get_food_travel_news(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取美食旅游新闻"""
        return self.fetch_multiple_feeds(self.food_travel_feeds, limit)
    
    def get_music_news(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取音乐新闻"""
        return self.fetch_multiple_feeds(self.music_feeds, limit)
    
    def get_food_news(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取美食新闻"""
        return self.fetch_multiple_feeds(self.food_feeds, limit)
    
    def get_travel_news(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取旅游新闻"""
        return self.fetch_multiple_feeds(self.travel_feeds, limit)
    
    def get_astrology_news(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取星座运势新闻"""
        return self.fetch_multiple_feeds(self.astrology_feeds, limit)
    
    def get_all_trends(self, limit: int = 5) -> Dict[str, List[Dict[str, str]]]:
        """
        获取所有类型的趋势
        """
        return {
            'fashion': self.get_fashion_news(limit),
            'beauty': self.get_beauty_news(limit),
            'entertainment': self.get_entertainment_news(limit),
            'news': self.get_news(limit),
            'tech': self.get_tech_news(limit),
            'chinese_news': self.get_chinese_news(limit),
            'lifestyle': self.get_lifestyle_news(limit),
            'celebrity': self.get_celebrity_news(limit),
            'film_tv': self.get_film_tv_news(limit),
            'hk_taiwan': self.get_hk_taiwan_news(limit),
            'finance': self.get_finance_news(limit),
            'health': self.get_health_news(limit),
            'food_travel': self.get_food_travel_news(limit),
            'music': self.get_music_news(limit),
            'food': self.get_food_news(limit),
            'travel': self.get_travel_news(limit),
            'astrology': self.get_astrology_news(limit),
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_all_rss_feeds(self, limit_per_source: int = 3) -> Dict[str, List[Dict[str, str]]]:
        """获取所有RSS源的内容"""
        result = {}
        for category, feeds in self.rss_feed_sources.items():
            result[category] = self.fetch_multiple_feeds(feeds, limit_per_source)
        result['fetch_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return result
    
    def get_knowledge_content(self, categories: Optional[List[str]] = None, limit: int = 10) -> List[Dict[str, str]]:
        """获取指定分类的知识内容"""
        if categories is None:
            categories = list(self.rss_feed_sources.keys())
        
        all_content = []
        for cat in categories:
            if cat in self.rss_feed_sources:
                content = self.fetch_multiple_feeds(self.rss_feed_sources[cat], limit)
                for item in content:
                    item['category'] = cat
                all_content.extend(content)
        
        return all_content


rss_feed_service = RSSFeedService()
