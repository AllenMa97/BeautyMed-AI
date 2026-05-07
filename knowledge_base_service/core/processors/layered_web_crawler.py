import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
from urllib.parse import urljoin, urlparse
import time
import random
import os
import json

# 导入模块
from knowledge_base_service.core.processors.search_engine_api import perform_iterative_search
from knowledge_base_service.core.processors.llm_scheduler import LLMScheduler
from knowledge_base_service.core.layered_knowledge_manager import LayeredKnowledgeManager, KnowledgeLayer
from knowledge_base_service.core.llm_prompts.get_real_urls_prompt import get_real_urls_prompt
from knowledge_base_service.core.llm_prompts.generate_search_queries_prompt import get_generate_search_queries_prompt
from knowledge_base_service.utils.logger import get_logger

logger = get_logger(__name__)

class LayeredWebCrawler:
    """
    分层网络爬虫处理器
    根据不同知识层级（领域背景、具体知识、关联知识）采用不同的搜索和收集策略
    """

    def __init__(self, knowledge_base_path: str = "layered_knowledge_base"):
        """
        初始化分层爬虫处理器
        """
        self.session = None
        self.knowledge_manager = LayeredKnowledgeManager(knowledge_base_path)
        # 使用更多样化的User-Agent以避免被检测
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/110.0',
            'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/110.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36 Edg/120.0.0.0',
            'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
        ]
        self.common_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'TE': 'Trailers',
        }

    async def __aenter__(self):
        """
        异步上下文管理器入口
        """
        headers = self.common_headers.copy()
        headers['User-Agent'] = random.choice(self.user_agents)
        self.session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        异步上下文管理器出口
        关闭会话连接
        """
        if self.session:
            await self.session.close()

    async def generate_layered_queries(self, initial_topic: str) -> Dict[KnowledgeLayer, List[str]]:
        """
        为不同知识层级生成相应的搜索查询
        """
        llm = LLMScheduler()
        
        # 为领域背景知识生成查询
        domain_queries = await llm.generate_search_queries(
            topic=initial_topic,
            requirements="生成关于该主题的基础概念、理论框架、行业概况等相关搜索查询",
            num_queries=3
        )
        
        # 为具体知识生成查询
        specific_queries = await llm.generate_search_queries(
            topic=initial_topic,
            requirements="生成关于该主题的具体解决方案、详细步骤、精确数据、实践指南等相关搜索查询",
            num_queries=3
        )
        
        # 为关联知识生成查询
        associative_queries = await llm.generate_search_queries(
            topic=initial_topic,
            requirements="生成关于该主题的跨领域连接、类比、启发性信息、相关趋势等相关搜索查询",
            num_queries=3
        )
        
        return {
            "domain_background": domain_queries,
            "specific": specific_queries,
            "associative": associative_queries
        }

    async def crawl_by_layer(self, initial_topic: str, max_results_per_layer: int = 5, max_concurrent: int = 3) -> Dict[KnowledgeLayer, List[Dict]]:
        """
        按知识层级分别进行爬取
        """
        logger.info(f"开始按层级爬取主题: {initial_topic}")

        # 生成各层面对应的查询
        layered_queries = await self.generate_layered_queries(initial_topic)

        results = {}
        
        for layer, queries in layered_queries.items():
            logger.info(f"开始爬取 {layer} 层，使用查询: {queries}")
            
            # 为当前层收集知识
            layer_results = await self._crawl_layer(
                queries=queries,
                layer=layer,
                max_results=max_results_per_layer,
                max_concurrent=max_concurrent
            )
            
            results[layer] = layer_results
            logger.info(f"{layer} 层爬取完成，收集到 {len(layer_results)} 个结果")
        
        logger.info(f"分层爬取完成，总计收集到 {sum(len(results[layer]) for layer in results)} 个结果")
        return results

    async def _crawl_layer(self, queries: List[str], layer: KnowledgeLayer, max_results: int, max_concurrent: int) -> List[Dict]:
        """
        爬取指定层级的知识
        """
        all_results = []
        
        for query in queries:
            if len(all_results) >= max_results:
                break
                
            logger.info(f"  处理查询 '{query}' (层级: {layer})")
            
            # 获取搜索结果
            search_results = await self._get_real_urls_from_search(query, max_results)
            
            if not search_results:
                logger.info(f"  未能找到与 '{query}' 相关的真实网站")
                continue
            
            logger.info(f"  找到 {len(search_results)} 个相关网站")
            
            # 处理搜索结果
            processed_results = await self._process_search_results_by_layer(
                search_results=search_results,
                layer=layer,
                max_to_process=min(max_results - len(all_results), len(search_results)),
                max_concurrent=max_concurrent
            )
            
            all_results.extend(processed_results)
            
            if len(all_results) >= max_results:
                break
        
        return all_results[:max_results]

    async def _get_real_urls_from_search(self, query: str, max_results: int) -> List[Dict]:
        """
        使用真正的搜索引擎API查找与查询相关的实际URL
        """
        logger.info(f"开始搜索: {query}")
        
        try:
            # 使用迭代搜索获取结果
            direct_results = await perform_iterative_search(query, max_results)
            
            # 转换格式以匹配现有接口
            formatted_results = []
            for result in direct_results:
                if 'url' in result and 'title' in result:
                    formatted_results.append({
                        'url': result['url'],
                        'title': result['title']
                    })
            
            logger.info(f"搜索获得 {len(formatted_results)} 个结果")
            return formatted_results[:max_results]
            
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            return []

    async def _process_search_results_by_layer(self, search_results: List[Dict], layer: KnowledgeLayer, max_to_process: int, max_concurrent: int) -> List[Dict]:
        """
        按指定层级处理搜索结果，爬取内容
        实现递归审查机制，对搜索结果进行深度分析
        """
        logger.info(f"处理 {len(search_results)} 个搜索结果，层级: {layer}，最多处理 {max_to_process} 个")
        
        # 限制处理数量
        limited_results = search_results[:max_to_process]
        
        # 并发爬取
        crawled_pages = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def crawl_single_site(result, idx):
            async with semaphore:
                logger.info(f"    正在爬取第 {idx+1}/{len(limited_results)} 个网站: {result['url']}")
                logger.info(f"      网站标题: {result['title']}")
                
                # 添加随机延时
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                try:
                    logger.info(f"      正在获取网页内容...")
                    page_content = await self._fetch_page_content(result['url'])
                    
                    if page_content is None:
                        logger.info(f"      无法获取初始内容，尝试递归审查...")
                        # 如果初始内容获取失败，尝试递归审查
                        recursive_content = await self._recursive_content_review(result['url'], max_depth=3)
                        if recursive_content:
                            page_content = recursive_content
                        else:
                            logger.info(f"      递归审查也未找到有效内容，跳过该网站...")
                            return None
                    
                    logger.info(f"      成功获取内容，长度: {len(page_content)} 字符")
                    
                    # 使用LLM验证内容相关性
                    llm = LLMScheduler()
                    relevance_check = await llm.verify_content_quality(page_content, result['url'], result.get('title', ''))
                    
                    if relevance_check.get('is_relevant', True):  # 默认认为相关
                        logger.info(f"      内容与查询相关，准备添加到{layer}层")
                        
                        # 尝试从标题中提取标签
                        title = result['title']
                        tags = [tag.strip() for tag in title.split('-') if len(tag.strip()) > 1]
                        
                        # 将知识添加到指定层级的知识库
                        success = await self.knowledge_manager.add_knowledge(
                            title=title,
                            content=page_content,
                            layer=layer,  # 指定层级
                            source_url=result['url'],
                            query_used=title,
                            tags=tags
                        )
                        
                        if success:
                            logger.info(f"      内容已成功添加到{layer}层知识库")
                            return {
                                'title': result['title'],
                                'url': result['url'],
                                'content': page_content,
                                'layer': layer,
                                'query_used': title,
                                'relevance_score': relevance_check.get('relevance_score', 80)
                            }
                        else:
                            logger.info(f"      内容未添加到{layer}层知识库（可能是重复或低质量内容）")
                            return None
                    else:
                        logger.info(f"      内容与查询不相关，尝试递归审查...")
                        # 即使初步判断不相关，也尝试递归审查，因为深层内容可能有价值
                        recursive_content = await self._recursive_content_review(result['url'], max_depth=2)
                        if recursive_content:
                            # 对递归获取的内容再次进行相关性检查
                            recursive_relevance_check = await llm.verify_content_quality(recursive_content, result['url'], result.get('title', ''))
                            if recursive_relevance_check.get('is_relevant', True):
                                logger.info(f"      递归审查发现相关内容，准备添加到{layer}层")
                                
                                success = await self.knowledge_manager.add_knowledge(
                                    title=f"[递归审查]{result['title']}",
                                    content=recursive_content,
                                    layer=layer,
                                    source_url=result['url'],
                                    query_used=result.get('title', ''),
                                    tags=tags
                                )
                                
                                if success:
                                    logger.info(f"      递归内容已成功添加到{layer}层知识库")
                                    return {
                                        'title': f"[递归审查]{result['title']}",
                                        'url': result['url'],
                                        'content': recursive_content,
                                        'layer': layer,
                                        'query_used': result.get('title', ''),
                                        'relevance_score': recursive_relevance_check.get('relevance_score', 80)
                                    }
                        
                        logger.info(f"      内容与查询不相关，跳过该页面")
                        return None
                        
                except Exception as e:
                    logger.error(f"      爬取失败 {result['url']}: {str(e)}")
                    # 即使发生异常，也尝试递归审查
                    try:
                        recursive_content = await self._recursive_content_review(result['url'], max_depth=2)
                        if recursive_content:
                            llm = LLMScheduler()
                            relevance_check = await llm.verify_content_quality(recursive_content, result['url'], result.get('title', ''))
                            if relevance_check.get('is_relevant', True):
                                logger.info(f"      递归审查发现相关内容，准备添加到{layer}层")
                                
                                title = result['title']
                                tags = [tag.strip() for tag in title.split('-') if len(tag.strip()) > 1]
                                
                                success = await self.knowledge_manager.add_knowledge(
                                    title=f"[异常恢复]{result['title']}",
                                    content=recursive_content,
                                    layer=layer,
                                    source_url=result['url'],
                                    query_used=result.get('title', ''),
                                    tags=tags
                                )
                                
                                if success:
                                    logger.info(f"      异常恢复内容已成功添加到{layer}层知识库")
                                    return {
                                        'title': f"[异常恢复]{result['title']}",
                                        'url': result['url'],
                                        'content': recursive_content,
                                        'layer': layer,
                                        'query_used': result.get('title', ''),
                                        'relevance_score': relevance_check.get('relevance_score', 80)
                                    }
                    except Exception as rec_e:
                        logger.error(f"      递归审查也失败 {result['url']}: {str(rec_e)}")
                    
                    return None
        
        # 并发执行爬取任务
        tasks = [crawl_single_site(result, i) for i, result in enumerate(limited_results)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤掉异常和None结果
        valid_results = []
        for result in results:
            if result is not None and not isinstance(result, Exception):
                valid_results.append(result)
        
        return valid_results

    async def _recursive_content_review(self, url: str, max_depth: int = 3, current_depth: int = 0) -> str:
        """
        递归审查内容，模拟人类研究员的深度探索行为
        """
        if current_depth >= max_depth:
            return None
        
        logger.info(f"      递归审查第 {current_depth + 1} 层: {url}")
        
        try:
            # 首先尝试获取当前页面内容
            page_content = await self._fetch_page_content(url)
            
            if page_content and len(page_content.strip()) > 100:  # 如果内容足够长，认为是有价值的
                logger.info(f"      在第 {current_depth + 1} 层找到有价值内容，长度: {len(page_content)} 字符")
                return page_content
            
            # 如果当前页面内容不足，尝试从页面中提取更多链接进行递归
            if current_depth < max_depth - 1:  # 还有递归空间
                additional_links = await self._extract_links_from_page(url)
                
                if additional_links:
                    logger.info(f"      从当前页面提取到 {len(additional_links)} 个链接，继续递归审查...")
                    
                    # 尝试前几个最有希望的链接
                    for link in additional_links[:3]:  # 只尝试前3个链接以避免过度递归
                        recursive_result = await self._recursive_content_review(
                            link['url'], 
                            max_depth, 
                            current_depth + 1
                        )
                        
                        if recursive_result and len(recursive_result) > 100:
                            logger.info(f"      递归审查成功，在第 {current_depth + 2} 层找到内容")
                            return recursive_result
            
            return page_content  # 返回当前获取到的内容（即使是None或短内容）
            
        except Exception as e:
            logger.error(f"      递归审查第 {current_depth + 1} 层失败 {url}: {str(e)}")
            return None

    async def _extract_links_from_page(self, url: str) -> List[Dict]:
        """
        从页面中提取相关链接，用于递归审查
        """
        try:
            if not self.session:
                headers = self.common_headers.copy()
                headers['User-Agent'] = random.choice(self.user_agents)
                self.session = aiohttp.ClientSession(headers=headers)

            timeout = aiohttp.ClientTimeout(total=15)
            headers = self.common_headers.copy()
            headers['User-Agent'] = random.choice(self.user_agents)

            async with self.session.get(url, timeout=timeout, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # 使用BeautifulSoup解析HTML并提取链接
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 查找页面中的链接
                    links = []
                    for link_tag in soup.find_all('a', href=True)[:20]:  # 限制为前20个链接
                        href = link_tag['href']
                        title = link_tag.get_text(strip=True)
                        
                        # 转换相对链接为绝对链接
                        full_url = urljoin(url, href)
                        
                        # 过滤掉非HTTP链接和外部链接（可根据需要调整）
                        if full_url.startswith(('http://', 'https://')):
                            # 检查是否与原域名相关（避免跳转到无关站点）
                            original_domain = urlparse(url).netloc
                            link_domain = urlparse(full_url).netloc
                            
                            # 如果是同一域名或相关域名，则保留
                            if original_domain in link_domain or link_domain in original_domain:
                                if title and len(title) > 5:  # 标题长度大于5字符
                                    links.append({
                                        'url': full_url,
                                        'title': title
                                    })
                    
                    logger.info(f"      从 {url} 提取到 {len(links)} 个相关链接")
                    return links[:10]  # 返回前10个链接
                
        except Exception as e:
            logger.error(f"      从页面提取链接失败 {url}: {str(e)}")

        return []

    async def _fetch_page_content(self, url: str) -> str:
        """
        获取并提取网页内容，带有反爬虫机制和重试逻辑
        """
        if not self.session:
            headers = self.common_headers.copy()
            headers['User-Agent'] = random.choice(self.user_agents)
            self.session = aiohttp.ClientSession(headers=headers)

        # 定义多种策略来获取内容
        strategies = [
            self._try_basic_request,
            self._try_with_referrer,
            self._try_with_different_ua,
            self._try_with_delay,
            self._try_with_cookies_and_session,
            self._try_with_proxy_like_headers
        ]

        for strategy in strategies:
            try:
                content = await strategy(url)
                if content and len(content.strip()) > 50:  # 检查内容是否有效
                    # 使用LLM验证内容质量
                    llm = LLMScheduler()
                    verification = await llm.verify_content_quality(content, url, "")
                    
                    if verification.get('is_valid', False) and verification.get('quality_score', 0) > 30:
                        logger.info(f"成功获取有效内容 from {url}")
                        return content
                    else:
                        logger.info(f"内容质量不佳 from {url}, 尝试其他策略")
                        continue
                else:
                    logger.info(f"获取到空内容 from {url}, 尝试其他策略")
                    continue
            except Exception as e:
                logger.error(f"策略 {strategy.__name__} 失败 for {url}: {str(e)}")
                continue

        logger.error(f"所有策略都失败 for {url}")
        return None

    async def _try_basic_request(self, url: str) -> str:
        """基础请求策略"""
        timeout = aiohttp.ClientTimeout(total=30)
        headers = self.common_headers.copy()
        headers['User-Agent'] = random.choice(self.user_agents)

        async with self.session.get(url, timeout=timeout, headers=headers) as response:
            if response.status == 200:
                html = await response.text()
                # 使用LLM来解析HTML内容
                llm = LLMScheduler()
                topic = url.split('/')[-1].replace('-', ' ').replace('_', ' ') or url.split('/')[2]
                extracted_content = await llm.extract_content_from_html(html, topic)
                return extracted_content['content']
            else:
                raise Exception(f"HTTP {response.status} for {url}")

    async def _try_with_referrer(self, url: str) -> str:
        """带Referer的请求策略"""
        timeout = aiohttp.ClientTimeout(total=30)
        headers = self.common_headers.copy()
        headers['User-Agent'] = random.choice(self.user_agents)
        headers['Referer'] = 'https://www.google.com/'
        headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'

        async with self.session.get(url, timeout=timeout, headers=headers) as response:
            if response.status == 200:
                html = await response.text()
                # 使用LLM来解析HTML内容
                llm = LLMScheduler()
                topic = url.split('/')[-1].replace('-', ' ').replace('_', ' ') or url.split('/')[2]
                extracted_content = await llm.extract_content_from_html(html, topic)
                return extracted_content['content']
            else:
                raise Exception(f"HTTP {response.status} for {url}")

    async def _try_with_different_ua(self, url: str) -> str:
        """使用不同User-Agent的请求策略"""
        timeout = aiohttp.ClientTimeout(total=30)
        headers = self.common_headers.copy()
        headers['User-Agent'] = random.choice([
            'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/91.0.4472.124 Safari/537.36'
        ])

        async with self.session.get(url, timeout=timeout, headers=headers) as response:
            if response.status == 200:
                html = await response.text()
                # 使用LLM来解析HTML内容
                llm = LLMScheduler()
                topic = url.split('/')[-1].replace('-', ' ').replace('_', ' ') or url.split('/')[2]
                extracted_content = await llm.extract_content_from_html(html, topic)
                return extracted_content['content']
            else:
                raise Exception(f"HTTP {response.status} for {url}")

    async def _try_with_delay(self, url: str) -> str:
        """带延迟的请求策略"""
        await asyncio.sleep(2)  # 增加延迟以避免被检测
        timeout = aiohttp.ClientTimeout(total=30)
        headers = self.common_headers.copy()
        headers['User-Agent'] = random.choice(self.user_agents)

        async with self.session.get(url, timeout=timeout, headers=headers) as response:
            if response.status == 200:
                html = await response.text()
                # 使用LLM来解析HTML内容
                llm = LLMScheduler()
                topic = url.split('/')[-1].replace('-', ' ').replace('_', ' ') or url.split('/')[2]
                extracted_content = await llm.extract_content_from_html(html, topic)
                return extracted_content['content']
            else:
                raise Exception(f"HTTP {response.status} for {url}")

    async def _try_with_cookies_and_session(self, url: str) -> str:
        """带Cookies和Session的请求策略"""
        timeout = aiohttp.ClientTimeout(total=30)
        headers = self.common_headers.copy()
        headers['User-Agent'] = random.choice(self.user_agents)

        # 创建临时session来处理cookies
        temp_session = aiohttp.ClientSession(headers=headers, cookie_jar=aiohttp.CookieJar())

        try:
            # 先访问主页获取cookies
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            # 访问根域名获取cookies
            async with temp_session.get(base_url, timeout=timeout) as base_response:
                pass  # Just to get cookies

            # 然后访问目标URL
            async with temp_session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    html = await response.text()
                    # 使用LLM来解析HTML内容
                    llm = LLMScheduler()
                    topic = url.split('/')[-1].replace('-', ' ').replace('_', ' ') or url.split('/')[2]
                    extracted_content = await llm.extract_content_from_html(html, topic)
                    return extracted_content['content']
                else:
                    raise Exception(f"HTTP {response.status} for {url}")
        finally:
            await temp_session.close()

    async def _try_with_proxy_like_headers(self, url: str) -> str:
        """使用代理样式请求头的策略"""
        timeout = aiohttp.ClientTimeout(total=30)
        headers = self.common_headers.copy()
        headers['User-Agent'] = random.choice(self.user_agents)
        # 模拟来自不同地理位置的请求
        headers.update({
            'X-Forwarded-For': f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
            'X-Real-IP': f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
            'X-Originating-IP': f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
            'CF-Connecting-IP': f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
        })

        async with self.session.get(url, timeout=timeout, headers=headers) as response:
            if response.status == 200:
                html = await response.text()
                # 使用LLM来解析HTML内容
                llm = LLMScheduler()
                topic = url.split('/')[-1].replace('-', ' ').replace('_', ' ') or url.split('/')[2]
                extracted_content = await llm.extract_content_from_html(html, topic)
                return extracted_content['content']
            else:
                raise Exception(f"HTTP {response.status} for {url}")

    async def crawl_and_extract(self, urls: List[str], max_depth: int = 2) -> List[Dict]:
        """
        爬取并提取多个URL的内容
        """
        all_contents = []
        
        for url in urls:
            logger.info(f"开始爬取URL: {url}")
            
            content = await self._recursive_content_review(url, max_depth=max_depth)
            
            if content and len(content.strip()) > 50:  # 只保存有意义的内容
                all_contents.append({
                    'url': url,
                    'content': content,
                    'length': len(content)
                })
                logger.info(f"成功提取内容，长度: {len(content)} 字符")
            else:
                logger.warning(f"未能从 {url} 提取到有效内容")
        
        return all_contents
    
    async def crawl_search_results(self, search_results: List[Dict], max_depth: int = 2) -> List[Dict]:
        """
        爬取搜索引擎结果的内容
        :param search_results: 搜索引擎返回的结果列表，每个元素包含title, url, snippet
        :param max_depth: 最大递归深度
        :return: 包含URL、内容、原始搜索结果信息的列表
        """
        logger.info(f"开始爬取 {len(search_results)} 个搜索结果")
        
        crawled_contents = []
        
        for idx, result in enumerate(search_results):
            url = result.get('url', '')
            title = result.get('title', '')
            snippet = result.get('snippet', '')
            
            if not url:
                logger.warning(f"搜索结果 {idx+1} 缺少URL，跳过")
                continue
            
            logger.info(f"正在爬取搜索结果 {idx+1}/{len(search_results)}: {title[:50]}...")
            
            # 尝试爬取该URL的内容
            content = await self._recursive_content_review(url, max_depth=max_depth)
            
            if content and len(content.strip()) > 50:
                crawled_contents.append({
                    'url': url,
                    'title': title,
                    'snippet': snippet,
                    'content': content,
                    'length': len(content),
                    'original_result': result
                })
                logger.info(f"成功从 '{title[:30]}...' 提取内容，长度: {len(content)} 字符")
            else:
                logger.warning(f"未能从 '{title[:30]}...' 提取到有效内容")
        
        logger.info(f"完成爬取，共获得 {len(crawled_contents)} 个有效内容")
        return crawled_contents