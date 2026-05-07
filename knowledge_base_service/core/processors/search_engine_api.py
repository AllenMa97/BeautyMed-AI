"""
搜索引擎模块
用于模拟浏览器行为直接爬取搜索引擎结果页面
"""
import os
import aiohttp
import asyncio
import random
from typing import List, Dict
import urllib.parse
from bs4 import BeautifulSoup
import re
import time
from dataclasses import dataclass
from typing import Optional

# 导入代理管理器
from .proxy_manager import get_random_working_proxy

# 导入logger
from knowledge_base_service.utils.logger import get_logger

# 初始化日志记录器
logger = get_logger(__name__)


class SearchEngineScraper:
    def __init__(self):
        # 多样化的User-Agent池
        self.user_agents = [
            # Chrome on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            # Firefox on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
            # Chrome on Mac
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            # Safari on Mac
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            # Edge on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
            # Mobile - iPhone
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            # Mobile - Android
            'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        ]
        
        # 多样化的Accept-Language池
        self.accept_languages = [
            'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'zh-CN,zh;q=0.8,en-US;q=0.6,en;q=0.4',
            'zh,zh-CN;q=0.9,en-US;q=0.8,en;q=0.7',
            'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'en,zh-CN;q=0.9,zh;q=0.8,en-US;q=0.7',
        ]
        
        # 多样化的Accept-Encoding池
        self.accept_encodings = [
            'gzip, deflate, br',
            'gzip, deflate',
            'deflate, br',
            'gzip, br',
            '*',
        ]
        
        # 为不同搜索引擎定制的多样化请求头
        self.search_engine_headers = {
            'baidu': [
                {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Referer': 'https://www.baidu.com/',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin',
                    'Cache-Control': 'max-age=0',
                },
                {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.6,en;q=0.4',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Referer': 'https://www.baidu.com/',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin',
                },
                {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Referer': 'https://www.baidu.com/',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin',
                }
            ],
            'sogou': [
                {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Referer': 'https://www.sogou.com/',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin',
                },
                {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.6,en;q=0.4',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Referer': 'https://www.sogou.com/',
                    'Upgrade-Insecure-Requests': '1',
                },
                {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh,zh-CN;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, br',
                    'Connection': 'keep-alive',
                    'Referer': 'https://www.sogou.com/',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin',
                }
            ],
            '360': [
                {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Referer': 'https://www.so.com/',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin',
                },
                {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Referer': 'https://www.so.com/',
                    'Upgrade-Insecure-Requests': '1',
                },
                {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'zh,zh-CN;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, br',
                    'Connection': 'keep-alive',
                    'Referer': 'https://www.so.com/',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin',
                }
            ],
            'zhihu': [
                {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Referer': 'https://www.zhihu.com/',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin',
                },
                {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.6,en;q=0.4',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Referer': 'https://www.zhihu.com/',
                    'Upgrade-Insecure-Requests': '1',
                },
                {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, br',
                    'Connection': 'keep-alive',
                    'Referer': 'https://www.zhihu.com/',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin',
                }
            ]
        }

    async def get_random_proxy(self) -> Optional[str]:
        """
        获取随机代理IP
        使用代理管理器获取可用的代理
        """
        return await get_random_working_proxy()
    
    def simulate_user_behavior(self) -> Dict[str, float]:
        """
        模拟真实用户行为参数
        返回各种延时和行为参数
        """
        return {
            # 页面加载时间（模拟用户阅读）
            'page_load_delay': random.uniform(2, 8),
            # 鼠标移动时间
            'mouse_move_time': random.uniform(0.1, 0.5),
            # 滚动延时
            'scroll_delay': random.uniform(0.5, 2),
            # 点击延时
            'click_delay': random.uniform(0.2, 1),
            # 请求间隔
            'request_interval': random.uniform(1, 5)
        }
    
    async def wait_random_time(self, min_seconds: float = 1, max_seconds: float = 5):
        """
        等待随机时间，模拟真实用户行为
        """
        wait_time = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(wait_time)

    async def search_baidu(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        模拟浏览器爬取百度搜索结果
        """
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.baidu.com/s?wd={encoded_query}&rn={min(num_results, 10)}"
            
            # 获取模拟用户行为参数
            user_behavior = self.simulate_user_behavior()
            
            # 随机选择一个请求头配置
            headers = random.choice(self.search_engine_headers['baidu']).copy()
            
            # 添加额外的反爬虫头部
            headers['Accept-Language'] = random.choice(self.accept_languages)
            headers['Accept-Encoding'] = random.choice(self.accept_encodings)
            
            # 随机等待一段时间以模拟真实用户行为
            await self.wait_random_time(1, 4)
            
            # 获取随机代理
            proxy = await self.get_random_proxy()
            
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.get(url, headers=headers, proxy=proxy) as response:
                    if response.status == 200:
                        # 模拟页面加载时间
                        await asyncio.sleep(user_behavior['page_load_delay'])
                        
                        html = await response.text()
                        results = self._parse_baidu_results(html, num_results)
                        return results
                    elif response.status == 403:
                        logger.warning(f"百度搜索被拒绝访问 (403)，尝试使用代理或等待...")
                        return []
                    elif response.status == 429:
                        logger.warning(f"百度搜索请求过于频繁 (429)，等待后重试...")
                        await self.wait_random_time(10, 20)
                        return []
                    else:
                        logger.error(f"百度搜索返回错误: {response.status}")
                        return []
        except asyncio.TimeoutError:
            logger.error(f"百度搜索请求超时")
            return []
        except Exception as e:
            logger.error(f"百度搜索爬取失败: {str(e)}")
            return []

    def _parse_baidu_results(self, html: str, num_results: int) -> List[Dict]:
        """
        解析百度搜索结果页面
        """
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # 百度搜索结果的主要容器
        result_elements = soup.find_all('div', attrs={'data-click': re.compile(r'tid=')})[:num_results]
        
        for element in result_elements:
            try:
                # 查找标题和链接
                title_elem = element.find('h3')
                if title_elem:
                    link_elem = title_elem.find('a')
                    if link_elem and link_elem.get('href'):
                        title = link_elem.get_text(strip=True)
                        url = link_elem['href']
                        
                        # 如果是百度跳转链接，尝试提取真实URL
                        if '/link?url=' in url:
                            # 这是百度的跳转链接，我们需要提取真实URL
                            # 但为了爬取，我们直接使用原始链接
                            pass
                        
                        # 查找摘要
                        abstract_elem = element.find('div', {'class': re.compile(r'c-abstract|content-right|f13')})
                        snippet = abstract_elem.get_text(strip=True) if abstract_elem else ''
                        
                        if title and url:
                            results.append({
                                'title': title,
                                'url': url,
                                'snippet': snippet
                            })
            except Exception as e:
                logger.error(f"解析百度搜索结果时出错: {str(e)}")
                continue
        
        return results

    async def search_sogou(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        模拟浏览器爬取搜狗搜索结果
        """
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.sogou.com/web?query={encoded_query}&num={min(num_results, 10)}"
            
            # 获取模拟用户行为参数
            user_behavior = self.simulate_user_behavior()
            
            # 随机选择一个请求头配置
            headers = random.choice(self.search_engine_headers['sogou']).copy()
            
            # 添加额外的反爬虫头部
            headers['Accept-Language'] = random.choice(self.accept_languages)
            headers['Accept-Encoding'] = random.choice(self.accept_encodings)
            
            # 随机等待一段时间以模拟真实用户行为
            await self.wait_random_time(1, 4)
            
            # 获取随机代理
            proxy = await self.get_random_proxy()
            
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.get(url, headers=headers, proxy=proxy) as response:
                    if response.status == 200:
                        # 模拟页面加载时间
                        await asyncio.sleep(user_behavior['page_load_delay'])
                        
                        html = await response.text()
                        results = self._parse_sogou_results(html, num_results)
                        return results
                    elif response.status == 403:
                        logger.warning(f"搜狗搜索被拒绝访问 (403)，尝试使用代理或等待...")
                        return []
                    elif response.status == 429:
                        logger.warning(f"搜狗搜索请求过于频繁 (429)，等待后重试...")
                        await self.wait_random_time(10, 20)
                        return []
                    else:
                        logger.error(f"搜狗搜索返回错误: {response.status}")
                        return []
        except asyncio.TimeoutError:
            logger.error(f"搜狗搜索请求超时")
            return []
        except Exception as e:
            logger.error(f"搜狗搜索爬取失败: {str(e)}")
            return []

    def _parse_sogou_results(self, html: str, num_results: int) -> List[Dict]:
        """
        解析搜狗搜索结果页面
        """
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # 搜狗搜索结果的主要容器
        result_elements = soup.find_all('div', class_='vrwrap')[:num_results]
        
        for element in result_elements:
            try:
                # 查找标题和链接
                title_elem = element.find('h3')
                if title_elem:
                    link_elem = title_elem.find('a')
                    if link_elem and link_elem.get('href'):
                        title = link_elem.get_text(strip=True)
                        url = link_elem['href']
                        
                        # 查找摘要
                        abstract_elem = element.find('cite', class_='cite-text')
                        snippet = abstract_elem.get_text(strip=True) if abstract_elem else ''
                        
                        if title and url:
                            results.append({
                                'title': title,
                                'url': url,
                                'snippet': snippet
                            })
            except Exception as e:
                logger.error(f"解析搜狗搜索结果时出错: {str(e)}")
                continue
        
        return results

    async def search_360(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        模拟浏览器爬取360搜索结果
        """
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.so.com/s?q={encoded_query}&pn=1&ie=utf-8&src=home_so.com&fr=so.com&result_num={min(num_results, 10)}"
            
            # 获取模拟用户行为参数
            user_behavior = self.simulate_user_behavior()
            
            # 随机选择一个请求头配置
            headers = random.choice(self.search_engine_headers['360']).copy()
            
            # 添加额外的反爬虫头部
            headers['Accept-Language'] = random.choice(self.accept_languages)
            headers['Accept-Encoding'] = random.choice(self.accept_encodings)
            
            # 随机等待一段时间以模拟真实用户行为
            await self.wait_random_time(1, 4)
            
            # 获取随机代理
            proxy = await self.get_random_proxy()
            
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.get(url, headers=headers, proxy=proxy) as response:
                    if response.status == 200:
                        # 模拟页面加载时间
                        await asyncio.sleep(user_behavior['page_load_delay'])
                        
                        html = await response.text()
                        results = self._parse_360_results(html, num_results)
                        return results
                    elif response.status == 403:
                        logger.warning(f"360搜索被拒绝访问 (403)，尝试使用代理或等待...")
                        return []
                    elif response.status == 429:
                        logger.warning(f"360搜索请求过于频繁 (429)，等待后重试...")
                        await self.wait_random_time(10, 20)
                        return []
                    else:
                        logger.error(f"360搜索返回错误: {response.status}")
                        return []
        except asyncio.TimeoutError:
            logger.error(f"360搜索请求超时")
            return []
        except Exception as e:
            logger.error(f"360搜索爬取失败: {str(e)}")
            return []

    def _parse_360_results(self, html: str, num_results: int) -> List[Dict]:
        """
        解析360搜索结果页面
        """
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # 360搜索结果的主要容器
        result_elements = soup.find_all('li', class_='res-list')[:num_results]
        
        for element in result_elements:
            try:
                # 查找标题和链接
                title_elem = element.find('h3')
                if title_elem:
                    link_elem = title_elem.find('a')
                    if link_elem and link_elem.get('href'):
                        title = link_elem.get_text(strip=True)
                        url = link_elem['href']
                        
                        # 查找摘要
                        abstract_elem = element.find('div', class_='res-desc')
                        snippet = abstract_elem.get_text(strip=True) if abstract_elem else ''
                        
                        if title and url:
                            results.append({
                                'title': title,
                                'url': url,
                                'snippet': snippet
                            })
            except Exception as e:
                logger.error(f"解析360搜索结果时出错: {str(e)}")
                continue
        
        return results

    async def search_zhihu(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        模拟浏览器爬取知乎搜索结果
        """
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.zhihu.com/search?q={encoded_query}&type=content"
            
            # 获取模拟用户行为参数
            user_behavior = self.simulate_user_behavior()
            
            # 随机选择一个请求头配置
            headers = random.choice(self.search_engine_headers['zhihu']).copy()
            
            # 添加额外的反爬虫头部
            headers['Accept-Language'] = random.choice(self.accept_languages)
            headers['Accept-Encoding'] = random.choice(self.accept_encodings)
            
            # 随机等待一段时间以模拟真实用户行为
            await self.wait_random_time(1, 4)
            
            # 获取随机代理
            proxy = await self.get_random_proxy()
            
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.get(url, headers=headers, proxy=proxy) as response:
                    if response.status == 200:
                        # 模拟页面加载时间
                        await asyncio.sleep(user_behavior['page_load_delay'])
                        
                        html = await response.text()
                        results = self._parse_zhihu_results(html, num_results)
                        return results
                    elif response.status == 403:
                        logger.warning(f"知乎搜索被拒绝访问 (403)，尝试使用代理或等待...")
                        return []
                    elif response.status == 429:
                        logger.warning(f"知乎搜索请求过于频繁 (429)，等待后重试...")
                        await self.wait_random_time(10, 20)
                        return []
                    else:
                        logger.error(f"知乎搜索返回错误: {response.status}")
                        return []
        except asyncio.TimeoutError:
            logger.error(f"知乎搜索请求超时")
            return []
        except Exception as e:
            logger.error(f"知乎搜索爬取失败: {str(e)}")
            return []

    def _parse_zhihu_results(self, html: str, num_results: int) -> List[Dict]:
        """
        解析知乎搜索结果页面
        """
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # 知乎搜索结果的主要容器
        result_elements = soup.find_all('div', class_='List-item')[:num_results]
        
        for element in result_elements:
            try:
                # 查找标题和链接
                title_elem = element.find('a', attrs={'data-za-element-name': 'Title'})
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get('href', '')
                    if not url.startswith('http'):
                        url = 'https://www.zhihu.com' + url
                    
                    # 查找摘要
                    abstract_elem = element.find('span', class_='RichText')
                    snippet = abstract_elem.get_text(strip=True) if abstract_elem else ''
                    
                    if title and url:
                        results.append({
                            'title': title,
                            'url': url,
                            'snippet': snippet
                        })
            except Exception as e:
                logger.error(f"解析知乎搜索结果时出错: {str(e)}")
                continue
        
        return results


# 全局实例
search_engine = SearchEngineScraper()


async def perform_web_search(query: str, num_results: int = 10) -> List[Dict]:
    """
    执行网络搜索，整合多个搜索引擎的结果
    """
    logger.info(f"正在执行网络搜索: {query}")
    
    # 尝试多个搜索引擎
    all_results = []
    
    # 国内搜索引擎
    baidu_results = await search_engine.search_baidu(query, num_results)
    all_results.extend(baidu_results)
    
    sogou_results = await search_engine.search_sogou(query, num_results)
    all_results.extend(sogou_results)
    
    search360_results = await search_engine.search_360(query, num_results)
    all_results.extend(search360_results)
    
    # 专业内容平台
    zhihu_results = await search_engine.search_zhihu(query, num_results)
    all_results.extend(zhihu_results)
    
    # 去重，保留唯一的URL
    seen_urls = set()
    unique_results = []
    for result in all_results:
        url = result.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(result)
    
    logger.info(f"搜索完成，找到 {len(unique_results)} 个唯一结果")
    return unique_results[:num_results]


async def perform_iterative_search(query: str, num_results: int = 10, max_iterations: int = 3) -> List[Dict]:
    """
    执行迭代搜索，当搜索结果不足时自动调整查询词
    """
    logger.info(f"开始迭代搜索: {query}")
    
    # 定义查询变体，模拟人类的搜索思路
    query_variants = [
        query,  # 原始查询
        f"{query} 是什么",  # 定义类查询
        f"{query} 怎么做",  # 方法类查询
        f"{query} 详细介绍",  # 详情类查询
        f"{query} 最新进展",  # 进展类查询
        f"{query} 作用",  # 作用类查询
        f"{query} 好处",  # 好处类查询
        f"{query} 原理",  # 原理类查询
        f"{query} 优点",  # 优点类查询
        f"{query} 功能",  # 功能类查询
    ]
    
    all_results = []
    seen_urls = set()
    
    for iteration in range(max_iterations):
        current_query = query_variants[iteration % len(query_variants)]
        logger.info(f"第 {iteration + 1} 次搜索: {current_query}")
        
        # 执行搜索
        results = await perform_web_search(current_query, num_results)
        
        # 添加新结果
        for result in results:
            url = result.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_results.append(result)
        
        # 如果已经收集到足够的结果，提前结束
        if len(all_results) >= num_results:
            logger.info(f"已收集到足够结果 ({len(all_results)}), 提前结束迭代")
            break
        
        logger.info(f"当前迭代找到 {len(results)} 个结果，总计 {len(all_results)} 个结果")
    
    logger.info(f"迭代搜索完成，总计找到 {len(all_results)} 个唯一结果")
    return all_results[:num_results]