# Developer: 马赫·马智?
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
内容分析和递归爬取模块
用于判断页面类型并递归爬取内容
"""
import asyncio
from typing import List, Dict, Optional, Tuple
import urllib.parse
from bs4 import BeautifulSoup
import re
import random

from utils.logger import get_logger
from core.processors.llm_scheduler import LLMScheduler
from core.http_client import HTTPClient
from core.llm_utils import LLMUtils
from core.llm_prompts import get_page_analysis_prompt

logger = get_logger(__name__)


class ContentAnalyzer:
    """
    内容分析?
    用于判断页面类型并提取内?
    """
    
    def __init__(self, session=None):
        self.llm = LLMScheduler()
        self.llm_utils = LLMUtils()
        self.http_client = HTTPClient(timeout=45)
        self.session = session
        self.own_session = session is None
        self.page_cache = {}
    
    async def __aenter__(self):
        if self.session is None:
            await self.http_client.start()
            self.session = self.http_client.session
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.own_session:
            await self.http_client.close()
    
    async def fetch_page_content(self, url: str) -> Tuple[str, int]:
        """
        获取页面内容,使用缓存避免重复请?
        返回: (HTML内容, HTTP状态码)
        """
        if url in self.page_cache:
            logger.info(f"使用缓存内容: {url}")
            return self.page_cache[url], 200
        
        try:
            delay = random.uniform(1.5, 5)
            await asyncio.sleep(delay)
            logger.info(f"等待 {delay:.2f} 秒后发送请求到 {url}")
            
            html_content = await self.http_client.fetch_text(url)
            
            if html_content:
                self.page_cache[url] = html_content
                return html_content, 200
            else:
                return "", 0
        except Exception as e:
            logger.error(f"获取页面失败 {url}: {str(e)}")
            return "", 0
    
    async def is_content_page(self, url: str, html_content: str = None) -> Tuple[bool, str, str]:
        """
        判断页面是否为内容页?
        返回: (是否为内容页, 页面类型描述, HTML内容)
        """
        if not html_content:
            html_content, status = await self.fetch_page_content(url)
            if status != 200:
                return False, f"无法获取页面内容,状态码: {status}", ""
        
        is_content, page_type = await self._analyze_page_with_llm(url, html_content)
        return is_content, page_type, html_content
    
    async def _analyze_page_with_llm(self, url: str, html_content: str) -> Tuple[bool, str]:
        """
        使用LLM分析页面类型
        """
        try:
            prompt = get_page_analysis_prompt(url, html_content)
            model = await self.llm.get_valid_model_for_task('content_analysis')
            content_response = await self.llm.client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            result = self.llm_utils.parse_json_response(content_response)
            
            is_content = result.get('is_content_page', False)
            confidence = result.get('confidence', 0)
            page_type = result.get('page_type', '其他')
            
            if is_content and confidence > 60:
                return True, f"内容?({page_type})"
            else:
                return False, f"{page_type} (置信? {confidence}%)"
                
        except Exception as e:
            logger.error(f"LLM分析页面类型时出? {str(e)}")
            return self._analyze_page_heuristic(html_content)
    
    def _analyze_page_heuristic(self, html_content: str) -> Tuple[bool, str]:
        """
        使用启发式方法分析页面类?
        """
        content_indicators = [
            'article', 'post', 'content', '正文', '详细', '介绍', '分析', '研究',
            '治疗', '方法', '原理', '效果', '注意事项', '文献', '论文'
        ]
        search_indicators = [
            'search', 'result', 'results', 'list', 'item', '链接', '相关', '搜索结果'
        ]
        
        lower_content = html_content.lower()[:1000]
        
        content_score = sum(1 for indicator in content_indicators if indicator in lower_content)
        search_score = sum(1 for indicator in search_indicators if indicator in lower_content)
        
        if search_score > content_score:
            return False, "搜索结果?(关键词判?"
        else:
            return True, "内容?(关键词判?"
    
    async def extract_content_from_page(self, url: str, html_content: str = None) -> str:
        """
        从内容页面提取主要内?
        """
        try:
            if not html_content:
                html_content, status = await self.fetch_page_content(url)
                if status != 200:
                    logger.error(f"获取页面失败 {url}: HTTP {status}")
                    return ""
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            for script in soup(["script", "style"]):
                script.decompose()
            
            content_selectors = [
                'article', '.content', '#content', '.post-content', 
                '.article-content', '.main-content', '.entry-content',
                '.post-body', '.article-body', 'main', '.main'
            ]
            
            content_text = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content_text = ' '.join([elem.get_text(strip=True) for elem in elements])
                    if len(content_text) > 100:
                        break
            
            if not content_text or len(content_text) < 100:
                body = soup.find('body')
                if body:
                    content_text = body.get_text(strip=True)
            
            content_text = re.sub(r'\s+', ' ', content_text).strip()
            
            if len(content_text) < 100:
                paragraphs = soup.find_all(['p', 'div', 'span'])
                content_parts = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if len(text) > 20:
                        content_parts.append(text)
                content_text = ' '.join(content_parts)
            
            return content_text[:5000]
        except Exception as e:
            logger.error(f"提取页面内容失败 {url}: {str(e)}")
            return ""
    
    async def extract_links_from_search_page(self, url: str, max_links: int = 20) -> List[Dict]:
        """
        从搜索结果页面提取链?
        """
        links = []
        try:
            html_content, status = await self.fetch_page_content(url)
            if status != 200:
                logger.error(f"获取搜索页面失败 {url}: HTTP {status}")
                return []
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            link_patterns = [
                '.result a',
                '.search-result a',
                '.item a',
                'h3 a',
                '.title a',
                'article a',
                '.content a',
                'a[href]',
            ]
            
            seen_urls = set()
            
            for pattern in link_patterns:
                elements = soup.select(pattern)
                for element in elements:
                    href = element.get('href')
                    if href:
                        full_url = urllib.parse.urljoin(url, href)
                        
                        if full_url.startswith(('http://', 'https://')):
                            if full_url not in seen_urls:
                                seen_urls.add(full_url)
                                title = element.get_text(strip=True)
                                
                                if title and len(title) > 5:
                                    links.append({
                                        'url': full_url,
                                        'title': title
                                    })
                                    
                                    if len(links) >= max_links:
                                        return links
            
            return links[:max_links]
        except Exception as e:
            logger.error(f"提取链接失败 {url}: {str(e)}")
            return []
    
    async def recursive_crawl(self, start_url: str, max_depth: int = 2, max_pages: int = 10) -> List[Dict]:
        """
        递归爬取内容页面
        """
        results = []
        visited_urls = set()
        
        async def crawl_page(url: str, depth: int):
            if depth > max_depth or len(results) >= max_pages or url in visited_urls:
                return
            
            visited_urls.add(url)
            
            is_content, page_type, html_content = await self.is_content_page(url)
            
            if is_content:
                content = await self.extract_content_from_page(url, html_content)
                if content:
                    results.append({
                        'url': url,
                        'content': content,
                        'page_type': page_type
                    })
            else:
                links = await self.extract_links_from_search_page(url, max_links=5)
                for link in links:
                    await crawl_page(link['url'], depth + 1)
        
        await crawl_page(start_url, 0)
        return results
