# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import requests
import logging
import random
import re
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional


logger = logging.getLogger(__name__)

try:
    import readability
    READABILITY_AVAILABLE = True
except ImportError:
    READABILITY_AVAILABLE = False
    logger.warning("readability-lxml未安装，将使用简化方案")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    logger.warning("beautifulsoup4未安装，将使用简化方案")


JINA_READER_BASE_URL = "https://r.jina.ai"
JINA_READER_V2_URL = "https://r.jina.ai/v2"

FALLBACK_READERS = [
    "https://r.jina.ai/http://{url}",
    "https://r.jina.ai/https://{url}",
    "https://r.jina.ai/{url}",
]

CHINESE_NEWS_SITES = {
    "weibo": ["https://weibo.com", "https://m.weibo.cn"],
    "zhihu": ["https://www.zhihu.com", "https://zhuanlan.zhihu.com"],
    "baidu": ["https://www.baidu.com", "https://top.baidu.com"],
    "douyin": ["https://www.douyin.com", "https://www.douyin.com/discover"],
    "toutiao": ["https://www.toutiao.com", "https://www.toutiao.com/ch/news_hot_word/"],
    "bilibili": ["https://www.bilibili.com", "https://www.bilibili.com/v/popular/history"],
    "xiaohongshu": ["https://www.xiaohongshu.com", "https://www.xiaohongshu.com/explore"],
    "tencent": ["https://news.qq.com", "https://news.qq.com/gn_index.htm"],
    "netease": ["https://news.163.com", "https://news.163.com/special/cm_yaowen202401/"],
    "sina": ["https://news.sina.com.cn", "https://k.sina.com.cn"],
    "sohu": ["https://www.sohu.com", "https://www.sohu.com/c/"],
    "thepaper": ["https://www.thepaper.cn", "https://www.thepaper.cn/news"],
    "36kr": ["https://www.36kr.com", "https://36kr.com/newsflashes"],
    "hupu": ["https://www.hupu.com", "https://bbs.hupu.com/all-gambia"],
    "douban": ["https://www.douban.com", "https://www.douban.com/group/explore"],
}

CUSTOM_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}

ALTERNATIVE_READERS = [
    ("https://r.jina.ai/http://{url}", "Jina Reader HTTP"),
    ("https://r.jina.ai/https://{url}", "Jina Reader HTTPS"),
    ("https://r.jina.ai/{url}", "Jina Reader Direct"),
    ("https://r.jina.ai/textise.net/showtext.aspx?strURL={url}", "Textise"),
]


class JinaReaderService:
    """
    Jina Reader 服务 - 读取任意网页内容
    使用 Jina AI 的 Reader API 获取网页内容，绕过反爬虫检测

    支持的功能：
    1. 读取任意URL的网页内容
    2. 自动提取正文内容
    3. 支持多个备用读取方案
    4. 可用于获取被反爬保护的页面内容
    """

    def __init__(self):
        self.session = requests.Session()
        self._update_headers()
        self._cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl = 1800
        self.timeout = 30
        self.max_retries = 3
        self.max_content_length = 50000

    def _update_headers(self):
        """更新随机请求头"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        ]
        headers = CUSTOM_HEADERS.copy()
        headers['User-Agent'] = random.choice(user_agents)
        self.session.headers.update(headers)

    def _get_cache_key(self, url: str) -> str:
        return f"jina_reader:{url}"

    def _get_from_cache(self, url: str) -> Optional[str]:
        cache_key = self._get_cache_key(url)
        with self._cache_lock:
            if cache_key in self._cache:
                cached = self._cache[cache_key]
                if datetime.now().timestamp() - cached['timestamp'] < self._cache_ttl:
                    return cached['content']
        return None

    def _save_to_cache(self, url: str, content: str):
        cache_key = self._get_cache_key(url)
        with self._cache_lock:
            self._cache[cache_key] = {
                'content': content,
                'timestamp': datetime.now().timestamp()
            }

    def read_url(self, url: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        读取URL内容

        Args:
            url: 目标URL
            use_cache: 是否使用缓存

        Returns:
            dict: {
                'success': bool,
                'content': str,
                'title': str,
                'error': str,
                'method': str
            }
        """
        if use_cache:
            cached = self._get_from_cache(url)
            if cached:
                logger.info(f"Jina Reader 命中缓存: {url}")
                return {
                    'success': True,
                    'content': cached,
                    'title': '',
                    'error': '',
                    'method': 'cache'
                }

        result = self._read_with_jina(url)

        if result['success']:
            self._save_to_cache(url, result['content'])

        return result

    def _read_with_jina(self, url: str) -> Dict[str, Any]:
        """使用Jina Reader读取内容"""
        for retry in range(self.max_retries):
            try:
                self._update_headers()

                reader_url = f"{JINA_READER_BASE_URL}/http://{url}" if not url.startswith(('http://', 'https://')) else f"{JINA_READER_BASE_URL}/{url.replace('https://', 'http://')}"

                response = self.session.get(reader_url, timeout=self.timeout)
                response.raise_for_status()

                if response.status_code == 200:
                    content = response.text

                    if self._is_valid_content(content):
                        title = self._extract_title(content)
                        cleaned_content = self._clean_content(content)

                        return {
                            'success': True,
                            'content': cleaned_content,
                            'title': title,
                            'error': '',
                            'method': 'jina_reader'
                        }
                    else:
                        logger.warning(f"Jina Reader 返回内容无效 (尝试 {retry + 1}/{self.max_retries})")

            except requests.exceptions.Timeout:
                logger.warning(f"Jina Reader 超时 (尝试 {retry + 1}/{self.max_retries})")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Jina Reader 请求失败 (尝试 {retry + 1}/{self.max_retries}): {e}")
            except Exception as e:
                logger.warning(f"Jina Reader 读取失败 (尝试 {retry + 1}/{self.max_retries}): {e}")

            if retry < self.max_retries - 1:
                import time
                time.sleep(random.uniform(1, 3))

        return self._read_with_fallback(url)

    def _read_with_fallback(self, url: str) -> Dict[str, Any]:
        """使用备用方案读取内容"""
        for pattern, name in ALTERNATIVE_READERS:
            try:
                self._update_headers()
                reader_url = pattern.format(url=url)

                response = self.session.get(reader_url, timeout=self.timeout)
                response.raise_for_status()

                if response.status_code == 200:
                    content = response.text

                    if self._is_valid_content(content):
                        title = self._extract_title(content)
                        cleaned_content = self._clean_content(content)

                        logger.info(f"{name} 读取成功: {url}")
                        return {
                            'success': True,
                            'content': cleaned_content,
                            'title': title,
                            'error': '',
                            'method': name
                        }

            except Exception as e:
                logger.debug(f"{name} 失败: {e}")
                continue

        return self._read_direct(url)

    def _read_direct(self, url: str) -> Dict[str, Any]:
        """直接读取URL（使用requests）"""
        try:
            self._update_headers()

            if '://' not in url:
                url = 'https://' + url

            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            if response.status_code == 200:
                if BS4_AVAILABLE:
                    soup = BeautifulSoup(response.text, 'html.parser')

                    for script in soup(["script", "style"]):
                        script.decompose()

                    content = soup.get_text()
                    lines = (line.strip() for line in content.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    content = ' '.join(chunk for chunk in chunks if chunk)

                    title = soup.title.string if soup.title else ''

                    return {
                        'success': True,
                        'content': content[:self.max_content_length],
                        'title': title,
                        'error': '',
                        'method': 'direct'
                    }
                else:
                    return {
                        'success': True,
                        'content': response.text[:self.max_content_length],
                        'title': '',
                        'error': '',
                        'method': 'direct'
                    }

        except Exception as e:
            logger.warning(f"直接读取失败: {e}")

        return {
            'success': False,
            'content': '',
            'title': '',
            'error': '所有读取方案都失败',
            'method': 'none'
        }

    def _is_valid_content(self, content: str) -> bool:
        """检查内容是否有效"""
        if not content or len(content) < 50:
            return False

        invalid_patterns = [
            'Not Found',
            '404',
            '403',
            'Access Denied',
            'blocked',
            'captcha',
            '验证',
            '访问受限',
        ]

        content_lower = content.lower()
        if any(pattern.lower() in content_lower for pattern in invalid_patterns):
            return False

        return True

    def _extract_title(self, content: str) -> str:
        """从内容中提取标题"""
        try:
            if '## ' in content:
                lines = content.split('\n')
                for line in lines:
                    if line.startswith('## '):
                        return line.replace('## ', '').strip()

            lines = content.split('\n')
            for line in lines[:5]:
                line = line.strip()
                if len(line) > 5 and len(line) < 200 and not line.startswith('#'):
                    return line
        except:
            pass

        return ''

    def _clean_content(self, content: str) -> str:
        """清理内容"""
        lines = content.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if line and len(line) > 2:
                if not line.startswith('#'):
                    cleaned_lines.append(line)

        content = ' '.join(cleaned_lines)

        content = re.sub(r'\s+', ' ', content)

        content = content[:self.max_content_length]

        return content

    def read_multiple_urls(self, urls: List[str], max_concurrent: int = 3) -> List[Dict[str, Any]]:
        """
        批量读取多个URL

        Args:
            urls: URL列表
            max_concurrent: 最大并发数

        Returns:
            list: 每个URL的读取结果
        """
        results = []
        for url in urls[:max_concurrent]:
            result = self.read_url(url)
            results.append(result)

        return results

    def get_trending_content(self, platform: str = 'default', max_items: int = 10) -> Dict[str, Any]:
        """
        获取热点内容

        Args:
            platform: 平台名称
            max_items: 最大条目数

        Returns:
            dict: 热点内容
        """
        urls = CHINESE_NEWS_SITES.get(platform, CHINESE_NEWS_SITES.get('default', []))

        if not urls:
            urls = []
            for site_urls in CHINESE_NEWS_SITES.values():
                urls.extend(site_urls)
            urls = list(set(urls))[:max_items]

        results = self.read_multiple_urls(urls)

        return {
            'success': any(r['success'] for r in results),
            'items': results,
            'count': len(results),
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def extract_keywords(self, content: str, max_keywords: int = 20) -> List[str]:
        """从内容中提取关键词"""
        if not content:
            return []

        try:
            import jieba
            import jieba.analyse

            keywords = jieba.analyse.extract_tags(content, topK=max_keywords, withWeight=False)
            return keywords
        except:
            words = re.findall(r'[\u4e00-\u9fa5]{2,6}', content)
            word_freq = {}
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1

            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            return [word for word, freq in sorted_words[:max_keywords]]


jina_reader_service = JinaReaderService()
