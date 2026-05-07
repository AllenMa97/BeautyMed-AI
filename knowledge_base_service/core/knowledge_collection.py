"""
医疗知识API接口
提供更可靠的医疗知识获取途径
"""
import asyncio
import aiohttp
from typing import List, Dict, Optional
from urllib.parse import quote
import time
import random

from knowledge_base_service.utils.logger import get_logger
from knowledge_base_service.core.processors.llm_scheduler import LLMScheduler
from knowledge_base_service.core.layered_knowledge_manager import LayeredKnowledgeManager
from knowledge_base_service.core.content_analyzer import ContentAnalyzer
from knowledge_base_service.core.api_knowledge_fetcher import APIKnowledgeFetcher

logger = get_logger(__name__)

class MedicalKnowledgeAPI:
    """
    医疗知识API接口
    提供更可靠的医疗知识获取途径
    """
    
    def __init__(self, email: str = "your_email@example.com"):
        self.session = None
        self.llm = LLMScheduler()
        self.api_fetcher = APIKnowledgeFetcher(email=email)
        self.user_agents = [
            # Chrome on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
            
            # Chrome on Mac
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
            
            # Chrome on Linux
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            
            # Firefox on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0',
            
            # Firefox on Mac
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/118.0',
            
            # Firefox on Linux
            'Mozilla/5.0 (X11; Linux i686; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:119.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0',
            
            # Safari on Mac
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
            
            # Edge on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.0.0',
            
            # Opera on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 OPR/105.0.0.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 OPR/104.0.0.0',
        ]
        
        # Accept-Language variations
        self.accept_languages = [
            'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'zh-CN,zh;q=0.8,en-US;q=0.6,en;q=0.5',
            'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4',
            'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
            'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        ]
        
        # Accept variations
        self.accept_headers = [
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'application/json, text/plain, */*',
            '*/*',
        ]
    
    def get_random_headers(self):
        """
        生成随机请求头，用于反爬虫
        """
        # 生成随机的Accept-Encoding
        accept_encoding = random.choice(['gzip, deflate, br', 'gzip, deflate', 'deflate'])
        
        # 生成随机的Connection
        connection = random.choice(['keep-alive', 'close'])
        
        # 生成随机的Cache-Control
        cache_control = random.choice(['max-age=0', 'no-cache', 'no-store'])
        
        # 生成随机的DNT (Do Not Track)
        dnt = random.choice(['0', '1'])
        
        # 生成随机的Referer
        referers = [
            'https://www.google.com/',
            'https://www.bing.com/',
            'https://www.baidu.com/',
            'https://www.yahoo.com/',
            'https://www.sogou.com/',
            'https://www.so.com/',
            'https://www.google.com/search?q=health+information',
            'https://www.bing.com/search?q=medical+knowledge',
            'https://www.baidu.com/s?wd=医疗知识',
            '',
        ]
        referer = random.choice(referers)
        
        # 生成随机的Sec-Ch-Ua
        sec_ch_ua = random.choice([
            '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            '"Mozilla Firefox";v="118", "Gecko";v="118", "Firefox";v="118"',
            '"Apple Safari";v="17", "WebKit";v="605", "KHTML, like Gecko";v="17"',
            '"Microsoft Edge";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
        ])
        
        # 生成随机的Sec-Ch-Ua-Mobile
        sec_ch_ua_mobile = random.choice(['?0', '?1'])
        
        # 生成随机的Sec-Ch-Ua-Platform
        sec_ch_ua_platform = random.choice([
            '"Windows"',
            '"macOS"',
            '"Linux"',
            '"Android"',
            '"iOS"',
        ])
        
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': random.choice(self.accept_headers),
            'Accept-Language': random.choice(self.accept_languages),
            'Accept-Encoding': accept_encoding,
            'Connection': connection,
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': random.choice(['document', 'empty']),
            'Sec-Fetch-Mode': random.choice(['navigate', 'cors']),
            'Sec-Fetch-Site': random.choice(['none', 'same-site', 'cross-site']),
            'Cache-Control': cache_control,
            'DNT': dnt,
            'Sec-Ch-Ua': sec_ch_ua,
            'Sec-Ch-Ua-Mobile': sec_ch_ua_mobile,
            'Sec-Ch-Ua-Platform': sec_ch_ua_platform,
            'Sec-Fetch-User': '?1',
        }
        
        # 只有当referer不为空时才添加
        if referer:
            headers['Referer'] = referer
        
        # 随机添加一些其他常见的请求头
        if random.random() > 0.5:
            headers['Pragma'] = 'no-cache'
        
        if random.random() > 0.3:
            headers['X-Requested-With'] = 'XMLHttpRequest'
        
        if random.random() > 0.4:
            headers['X-Forwarded-For'] = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
        
        if random.random() > 0.6:
            headers['X-Real-IP'] = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
        
        return headers
        
    async def __aenter__(self):
        headers = self.get_random_headers()
        self.session = aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=30))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_medical_knowledge(self, query: str, max_results: int = 17) -> List[Dict]:
        """
        搜索医疗知识
        使用多个可靠的数据源
        """
        results = []
        
        # 尝试多个数据源，优先使用开放学术资源
        sources = [
            self._search_medical_websites,  # 优先使用开放学术资源
            self._search_wikipedia_medical,  # 维基百科作为备选
        ]
        
        for source_func in sources:
            try:
                source_results = await source_func(query, max_results)
                results.extend(source_results)
                
                # 如果已經找到足夠的結果，就停止
                if len(results) >= max_results:
                    break
                    
                # 避免請求過於頻繁
                await asyncio.sleep(random.uniform(1, 3))
                
            except Exception as e:
                logger.error(f"搜索医疗知识时出错 ({source_func.__name__}): {str(e)}")
                continue
        
        # 如果没有找到足够的结果，尝试使用其他开放资源
        if len(results) < max_results:
            logger.info("尝试使用备用开放资源...")
            try:
                backup_results = await self._search_backup_resources(query, max_results - len(results))
                results.extend(backup_results)
            except Exception as e:
                logger.error(f"使用备用资源时出错: {str(e)}")
        
        # 去重並限制結果數量
        unique_results = []
        seen_titles = set()
        for result in results:
            title = result.get('title', '').lower()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_results.append(result)
        
        return unique_results[:max_results]
    
    async def _search_backup_resources(self, query: str, max_results: int) -> List[Dict]:
        """
        搜索备用开放资源
        """
        results = []
        
        try:
            timeout = aiohttp.ClientTimeout(total=45)
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(headers=self.get_random_headers(), timeout=timeout, connector=connector) as temp_session:
                # 备用开放资源
                backup_sources = [
                    # WHO - 世界卫生组织
                    {
                        'name': 'WHO',
                        'search_url': f"https://www.who.int/search?query={quote(query)}",
                        'is_content_selector': 'article',
                        'link_selector': '.result-item a'
                    },
                    # CDC - 美国疾病控制与预防中心
                    {
                        'name': 'CDC',
                        'search_url': f"https://search.cdc.gov/search?query={quote(query)}&sort=date&dc=610&dc=611&dc=612&dc=613",
                        'is_content_selector': '.content',
                        'link_selector': '.gsc-result a'
                    },
                    # 国家卫健委
                    {
                        'name': '国家卫健委',
                        'search_url': f"http://www.nhc.gov.cn/wjw/search.shtml?keyValue={quote(query)}",
                        'is_content_selector': '.con',
                        'link_selector': '.list a'
                    },
                ]
                
                for source in backup_sources:
                    try:
                        # 添加随机延迟
                        await asyncio.sleep(random.uniform(2, 5))
                        
                        async with temp_session.get(source['search_url']) as response:
                            if response.status == 200:
                                html_content = await response.text()
                                from bs4 import BeautifulSoup
                                soup = BeautifulSoup(html_content, 'html.parser')
                                
                                # 提取链接
                                links = soup.select(source['link_selector'])
                                for link in links[:3]:  # 每个源最多取3个结果
                                    href = link.get('href')
                                    if href:
                                        # 转换相对链接为绝对链接
                                        if not href.startswith(('http://', 'https://')):
                                            if source['name'] == 'WHO':
                                                href = f"https://www.who.int{href}"
                                            elif source['name'] == 'CDC':
                                                href = f"https://search.cdc.gov{href}"
                                            elif source['name'] == '国家卫健委':
                                                href = f"http://www.nhc.gov.cn{href}"
                                        
                                        title = link.get_text(strip=True)
                                        if title and len(title) > 5:
                                            # 尝试获取内容
                                            try:
                                                await asyncio.sleep(random.uniform(1, 3))
                                                async with temp_session.get(href) as content_response:
                                                    if content_response.status == 200:
                                                        content_html = await content_response.text()
                                                        content_soup = BeautifulSoup(content_html, 'html.parser')
                                                        
                                                        # 提取内容
                                                        content_elements = content_soup.select(source['is_content_selector'])
                                                        if content_elements:
                                                            content = ' '.join([elem.get_text(strip=True) for elem in content_elements])
                                                            content = content[:500]  # 限制内容长度
                                                            
                                                            results.append({
                                                                'title': title,
                                                                'url': href,
                                                                'content': content,
                                                                'source': source['name']
                                                            })
                                            except Exception as e:
                                                logger.error(f"获取{source['name']}内容时出错: {str(e)}")
                                                # 如果获取内容失败，至少保存链接
                                                results.append({
                                                    'title': title,
                                                    'url': href,
                                                    'content': f"来自{source['name']}的相关信息",
                                                    'source': source['name']
                                                })
                    except Exception as e:
                        logger.error(f"搜索{source['name']}时出错: {str(e)}")
                        continue
        except Exception as e:
            logger.error(f"搜索备用资源时出错: {str(e)}")
        
        return results
    
    async def _search_wikipedia_medical(self, query: str, max_results: int) -> List[Dict]:
        """
        搜索维基百科医学内容
        """
        results = []
        try:
            # 使用维基百科搜索页面URL
            search_url = f"https://zh.wikipedia.org/w/index.php?search={quote(query)}&title=Special:Search&variant=zh-cn&ns0=1"
            
            # 尝试多次请求以应对网络不稳定和反爬虫
            max_retries = 5  # 减少重试次数，避免被封
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    # 为每个请求创建新的会话，使用不同的请求头
                    timeout = aiohttp.ClientTimeout(total=600)  # 增加超时时间
                    # 创建SSL上下文，禁用证书验证
                    import ssl
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    
                    connector = aiohttp.TCPConnector(ssl=ssl_context)
                    async with aiohttp.ClientSession(headers=self.get_random_headers(), timeout=timeout, connector=connector) as temp_session:
                        # 添加更贴近人类的随机延迟
                        # 模拟人类浏览行为，延迟时间更随机
                        delay = random.uniform(1, 5) + (retry_count * 2)  # 指数退避
                        await asyncio.sleep(delay)
                        logger.info(f"等待 {delay:.2f} 秒后发送请求 (尝试 {retry_count + 1}/{max_retries})")
                        
                        # 获取搜索结果页面
                        async with temp_session.get(search_url) as search_response:
                            if search_response.status == 200:
                                search_html = await search_response.text()
                                
                                # 使用BeautifulSoup解析搜索结果页面
                                from bs4 import BeautifulSoup
                                soup = BeautifulSoup(search_html, 'html.parser')
                                
                                # 查找搜索结果
                                search_results = soup.find_all('div', class_='mw-search-result')
                                
                                # 如果没有找到特定的搜索结果类，尝试其他选择器
                                if not search_results:
                                    search_results = soup.find_all('li', class_='mw-search-result')
                                
                                # 如果还是没有找到，尝试更通用的选择器
                                if not search_results:
                                    search_results = soup.select('.searchresult')
                                
                                # 提取前max_results个结果
                                for i, result in enumerate(search_results[:max_results]):
                                    title_elem = result.find('a')
                                    if title_elem and title_elem.get('title'):
                                        title = title_elem.get('title')
                                        href = title_elem.get('href')
                                        if href:
                                            result_url = f"https://zh.wikipedia.org{href}"
                                            
                                            # 提取摘要
                                            desc_elem = result.find('div', class_='searchresult') or result.find('div', class_='mw-search-result-heading')
                                            if not desc_elem:
                                                desc_elem = result
                                            
                                            snippet = desc_elem.get_text(strip=True)[:200]  # 限制摘要长度
                                            
                                            results.append({
                                                'title': title,
                                                'url': result_url,
                                                'content': snippet,
                                                'source': 'wikipedia'
                                            })
                                
                                success = True  # 成功获取了HTML结果
                            elif search_response.status == 429:  # 请求过多
                                logger.warning(f"维基百科请求过多，等待后重试: {search_response.status}")
                                # 等待更长时间再重试
                                await asyncio.sleep(15 * (retry_count + 1))  # 更长的等待时间
                                retry_count += 1
                            elif search_response.status == 443:  # 被禁止访问
                                logger.warning(f"维基百科访问被禁止 (443)，等待后重试")
                                # 等待更长时间并使用新的请求头
                                await asyncio.sleep(20 * (retry_count + 1))  # 更长的等待时间
                                retry_count += 1
                            else:
                                logger.warning(f"维基百科搜索响应状态码: {search_response.status}")
                                retry_count += 1
                                if retry_count < max_retries:
                                    await asyncio.sleep(5 * (retry_count + 1))  # 增加延迟时间
                except aiohttp.ClientConnectorError as e:
                    logger.warning(f"维基百科连接错误 (尝试 {retry_count + 1}/{max_retries}): {str(e)}")
                    retry_count += 1
                    if retry_count < max_retries:
                        await asyncio.sleep(10 * (retry_count + 1))  # 更长的延迟
                except asyncio.TimeoutError as e:
                    logger.warning(f"维基百科请求超时 (尝试 {retry_count + 1}/{max_retries}): {str(e)}")
                    retry_count += 1
                    if retry_count < max_retries:
                        await asyncio.sleep(10 * (retry_count + 1))  # 更长的延迟
                except Exception as e:
                    logger.warning(f"维基百科搜索请求失败 (尝试 {retry_count + 1}/{max_retries}): {str(e)}")
                    retry_count += 1
                    if retry_count < max_retries:
                        await asyncio.sleep(5 * (retry_count + 1))  # 增加延迟时间
                
                # 每次重试后随机等待一段时间，模拟人类行为
                if not success and retry_count < max_retries:
                    await asyncio.sleep(random.uniform(2, 5))
            
            # 如果通过解析HTML没有找到结果，使用API作为备选
            if not results:
                # 使用维基百科搜索API作为备选
                api_url = f"https://zh.wikipedia.org/w/api.php?action=query&format=json&list=search&srsearch={quote(query)}&srlimit={max_results}"
                
                api_max_retries = 5  # API请求重试次数更少
                retry_count = 0
                success = False
                
                while retry_count < api_max_retries and not success:
                    try:
                        # 为API请求使用新的随机请求头
                        timeout = aiohttp.ClientTimeout(total=600)
                        api_session_headers = self.get_random_headers()
                        # 创建SSL上下文，禁用证书验证
                        import ssl
                        ssl_context = ssl.create_default_context()
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE
                        
                        connector = aiohttp.TCPConnector(ssl=ssl_context)
                        async with aiohttp.ClientSession(headers=api_session_headers, timeout=timeout, connector=connector) as api_session:
                            # 添加更贴近人类的随机延迟
                            delay = random.uniform(1, 5) + (retry_count * 2)  # 指数退避
                            await asyncio.sleep(delay)
                            logger.info(f"等待 {delay:.2f} 秒后发送API请求 (尝试 {retry_count + 1}/{api_max_retries})")
                            
                            api_response = await api_session.get(api_url)
                            if api_response.status == 200:
                                search_data = await api_response.json()
                                pages = search_data.get('query', {}).get('search', [])
                                
                                for page in pages:
                                    title = page.get('title', '')
                                    snippet = page.get('snippet', '')
                                    if title:
                                        # 获取页面摘要
                                        page_url = f"https://zh.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
                                        try:
                                            # 为子请求添加延迟
                                            await asyncio.sleep(random.uniform(1, 3))
                                            page_response = await api_session.get(page_url)
                                            if page_response.status == 200:
                                                page_data = await page_response.json()
                                                results.append({
                                                    'title': page_data.get('title', title),
                                                    'url': page_data.get('content_urls', {}).get('desktop', {}).get('page', '') if page_data.get('content_urls') else '',
                                                    'content': page_data.get('extract', snippet),
                                                    'source': 'wikipedia'
                                                })
                                        except Exception as e:
                                            logger.error(f"获取维基百科页面时出错: {str(e)}")
                                            # 如果获取详细信息失败，至少保存搜索结果
                                            results.append({
                                                'title': title,
                                                'url': f"https://zh.wikipedia.org/wiki/{quote(title)}",
                                                'content': snippet,
                                                'source': 'wikipedia'
                                            })
                                success = True  # 成功获取了API结果
                            elif api_response.status == 429:  # 请求过多
                                logger.warning(f"维基百科API请求过多，等待后重试: {api_response.status}")
                                # 等待更长时间再重试
                                await asyncio.sleep(15 * (retry_count + 1))
                                retry_count += 1
                            elif api_response.status == 443:  # 被禁止访问
                                logger.warning(f"维基百科API访问被禁止 (443)，等待后重试")
                                # 等待更长时间并使用新的请求头
                                await asyncio.sleep(20 * (retry_count + 1))
                                retry_count += 1
                            else:
                                logger.warning(f"维基百科API响应状态码: {api_response.status}")
                                retry_count += 1
                                if retry_count < max_retries:
                                    await asyncio.sleep(5 * (retry_count + 1))  # 增加延迟时间
                    except aiohttp.ClientConnectorError as e:
                        logger.warning(f"维基百科API连接错误 (尝试 {retry_count + 1}/{max_retries}): {str(e)}")
                        retry_count += 1
                        if retry_count < max_retries:
                            await asyncio.sleep(10 * (retry_count + 1))  # 更长的延迟
                    except asyncio.TimeoutError as e:
                        logger.warning(f"维基百科API请求超时 (尝试 {retry_count + 1}/{max_retries}): {str(e)}")
                        retry_count += 1
                        if retry_count < max_retries:
                            await asyncio.sleep(10 * (retry_count + 1))  # 更长的延迟
                    except Exception as e:
                        logger.warning(f"维基百科API请求失败 (尝试 {retry_count + 1}/{max_retries}): {str(e)}")
                        retry_count += 1
                        if retry_count < max_retries:
                            await asyncio.sleep(5 * (retry_count + 1))  # 增加延迟时间
                    
                    # 每次重试后随机等待一段时间
                    if not success and retry_count < max_retries:
                        await asyncio.sleep(random.uniform(2, 5))
        except Exception as e:
            logger.error(f"搜索维基百科时出错: {str(e)}")
        
        return results
    

    
    async def _generate_bilingual_query(self, query: str) -> Dict[str, str]:
        """
        使用LLM生成双语查询（中英文）
        根据输入查询判断语言，生成对应的翻译
        """
        try:
            # 使用LLM进行智能翻译
            prompt = f"""请将以下医学/健康相关的查询词翻译成中英文双语。
            
查询词: {query}

要求:
1. 如果查询词是中文，请提供准确的英文翻译（使用医学专业术语）
2. 如果查询词是英文，请提供准确的中文翻译
3. 返回格式必须是严格的JSON格式: {{"zh": "中文", "en": "English"}}
4. 只返回JSON，不要有任何其他文字

示例:
输入: 抗衰老
输出: {{"zh": "抗衰老", "en": "anti-aging"}}

输入: diabetes
输出: {{"zh": "糖尿病", "en": "diabetes"}}
"""
            
            # 调用LLM进行翻译
            response = await self.llm.client.chat.completions.create(
                model=self.llm.get_model_for_task('fast'),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=100
            )
            
            # 解析LLM返回的内容
            content = response.choices[0].message.content.strip()
            
            # 解析JSON
            import json
            import re
            
            # 尝试从响应中提取JSON
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                result = json.loads(json_match.group())
                if 'zh' in result and 'en' in result:
                    logger.info(f"LLM双语翻译成功: 中文='{result['zh']}', 英文='{result['en']}'")
                    return result
            
            # 如果LLM返回格式不正确，使用备用方案
            logger.warning(f"LLM翻译返回格式不正确，使用备用方案: {content}")
            
        except Exception as e:
            logger.warning(f"LLM翻译失败，使用备用方案: {str(e)}")
        
        # 备用方案：简单判断语言并返回
        import re
        if re.search(r'[\u4e00-\u9fff]', query):
            # 中文查询，英文使用原查询（让搜索引擎处理）
            return {'zh': query, 'en': query}
        else:
            # 英文查询，中文使用原查询
            return {'zh': query, 'en': query}
    
    async def _search_medical_websites(self, query: str, max_results: int) -> List[Dict]:
        """
        搜索专业医疗网站和开放获取学术资源，并分析页面决定是否继续深入爬取
        支持双语查询（中英文）
        """
        results = []
        
        # 生成双语查询（使用LLM智能翻译）
        bilingual_query = await self._generate_bilingual_query(query)
        logger.info(f"双语查询: 中文='{bilingual_query['zh']}', 英文='{bilingual_query['en']}'")
        
        timeout = aiohttp.ClientTimeout(total=45)  # 增加超时时间
        async with aiohttp.ClientSession(headers=self.get_random_headers(), timeout=timeout) as temp_session:
            # 权威医学机构资源（优先搜索）
            authoritative_sources = [
                # 中文权威资源
                # 国家卫生健康委员会 - 中国官方卫生政策和技术规范
                {'url': 'https://zs.kaipuyun.cn/', 'lang': 'zh', 'name': '国家卫健委', 'type': 'authoritative'},
                
                # 美国CDC - 美国疾病控制与预防中心
                {'url': 'https://www.cdc.gov/', 'lang': 'en', 'name': 'CDC', 'type': 'authoritative'},
            ]
            
            # 开放获取的学术文献资源
            open_academic_sources = [
                # 英文资源（使用英文查询）
                # PubMed Central - 开放获取的生物医学文献数据库
                {'url': 'https://www.ncbi.nlm.nih.gov/pmc/', 'lang': 'en', 'name': 'PubMed Central', 'type': 'academic'},
                # Europe PMC - 欧洲PubMed Central
                {'url': 'https://europepmc.org/', 'lang': 'en', 'name': 'Europe PMC', 'type': 'academic'},
                # DOAJ - 开放获取期刊目录
                {'url': 'https://doaj.org/', 'lang': 'en', 'name': 'DOAJ', 'type': 'academic'},
                # PLoS ONE - 开放获取科学期刊
                {'url': 'https://journals.plos.org/plosone/', 'lang': 'en', 'name': 'PLoS ONE', 'type': 'academic'},
                # arXiv - 预印本服务器（医学相关）
                {'url': 'https://arxiv.org/', 'lang': 'en', 'name': 'arXiv', 'type': 'academic'},
                # BioRxiv - 生物学预印本
                {'url': 'https://www.biorxiv.org/', 'lang': 'en', 'name': 'BioRxiv', 'type': 'academic'},
                # MedRxiv - 医学预印本
                {'url': 'https://www.medrxiv.org/', 'lang': 'en', 'name': 'MedRxiv', 'type': 'academic'},
                # Google Scholar - 学术搜索引擎
                {'url': 'https://scholar.google.com/', 'lang': 'en', 'name': 'Google Scholar', 'type': 'academic'},
                # Semantic Scholar - AI驱动的学术搜索引擎
                {'url': 'https://www.semanticscholar.org/', 'lang': 'en', 'name': 'Semantic Scholar', 'type': 'academic'},
                # CORE - 开放获取论文聚合
                {'url': 'https://core.ac.uk/', 'lang': 'en', 'name': 'CORE', 'type': 'academic'},
                # PubMed - 医学文献数据库
                {'url': 'https://pubmed.ncbi.nlm.nih.gov/', 'lang': 'en', 'name': 'PubMed', 'type': 'academic'},
                
                # 中文资源（使用中文查询）
                # 百度学术（开放）
                {'url': 'https://xueshu.baidu.com/', 'lang': 'zh', 'name': '百度学术', 'type': 'academic'},
                # 搜狗学术（开放）
                {'url': 'https://scholar.sogou.com/', 'lang': 'zh', 'name': '搜狗学术', 'type': 'academic'},
                # 360学术（开放）
                {'url': 'https://xueshu.so.com/', 'lang': 'zh', 'name': '360学术', 'type': 'academic'},
                # 中国知网（部分开放）
                {'url': 'https://www.cnki.net/', 'lang': 'zh', 'name': '中国知网', 'type': 'academic'},
                # 万方数据（部分开放）
                {'url': 'https://www.wanfangdata.com.cn/', 'lang': 'zh', 'name': '万方数据', 'type': 'academic'},
                # 维普网（部分开放）
                {'url': 'http://www.cqvip.com/', 'lang': 'zh', 'name': '维普网', 'type': 'academic'},
                # 中华医学会 - 专业医学协会（部分内容开放）
                {'url': 'https://www.cma.org.cn/', 'lang': 'zh', 'name': '中华医学会', 'type': 'academic'},
                # 医学界（部分内容开放）
                {'url': 'https://www.yxj.org.cn/', 'lang': 'zh', 'name': '医学界', 'type': 'academic'},
            ]
            
            # 医疗门户网站资源
            medical_portal_sources = [
                # 丁香园（专业医学社区）
                {'url': 'https://dxy.com/', 'lang': 'zh', 'name': '丁香园', 'type': 'portal'},
                # 医脉通（医学资讯平台）
                {'url': 'https://www.medlive.cn/', 'lang': 'zh', 'name': '医脉通', 'type': 'portal'},
                # 好大夫在线（医生和患者交流平台）
                {'url': 'https://www.haodf.com/', 'lang': 'zh', 'name': '好大夫在线', 'type': 'portal'},
                # 家庭医生在线
                {'url': 'https://www.familydoctor.com.cn/', 'lang': 'zh', 'name': '家庭医生在线', 'type': 'portal'},
                # 39健康网
                {'url': 'https://www.39.net/', 'lang': 'zh', 'name': '39健康网', 'type': 'portal'},
                # 有来医生（健康科普平台）
                {'url': 'https://www.youlai.cn/', 'lang': 'zh', 'name': '有来医生', 'type': 'portal'},
                # 快速问医生
                {'url': 'https://www.120ask.com/', 'lang': 'zh', 'name': '快速问医生', 'type': 'portal'},
                # 寻医问药网
                {'url': 'https://www.xywy.com/', 'lang': 'zh', 'name': '寻医问药网', 'type': 'portal'},
                # 微医（挂号网）
                {'url': 'https://www.guahao.com/', 'lang': 'zh', 'name': '微医', 'type': 'portal'},
                # 平安好医生
                {'url': 'https://www.pingan.com/', 'lang': 'zh', 'name': '平安好医生', 'type': 'portal'},
                # 阿里健康
                {'url': 'https://www.alihealth.cn/', 'lang': 'zh', 'name': '阿里健康', 'type': 'portal'},
                # 京东健康
                {'url': 'https://www.jd.com/', 'lang': 'zh', 'name': '京东健康', 'type': 'portal'},
                # 腾讯医典
                {'url': 'https://baike.qq.com/', 'lang': 'zh', 'name': '腾讯医典', 'type': 'portal'},
                # 网易健康
                {'url': 'https://jiankang.163.com/', 'lang': 'zh', 'name': '网易健康', 'type': 'portal'},
                # 新浪健康
                {'url': 'https://health.sina.com.cn/', 'lang': 'zh', 'name': '新浪健康', 'type': 'portal'},
                # 搜狐健康
                {'url': 'https://health.sohu.com/', 'lang': 'zh', 'name': '搜狐健康', 'type': 'portal'},
                # 凤凰健康
                {'url': 'https://health.ifeng.com/', 'lang': 'zh', 'name': '凤凰健康', 'type': 'portal'},
            ]
            
            # 合并所有资源，学术资源优先，然后是权威资源，最后是医疗门户网站
            all_sources = open_academic_sources + authoritative_sources + medical_portal_sources
            
            # 为所有资源构造搜索URL并分析页面
            for i, site_info in enumerate(all_sources):
                try:
                    site = site_info['url']
                    lang = site_info['lang']
                    name = site_info['name']
                    site_type = site_info.get('type', 'general')
                    
                    # 根据语言选择查询词
                    search_query = bilingual_query['en'] if lang == 'en' else bilingual_query['zh']
                    
                    # 根据不同类型的资源构造搜索URL
                    # 权威医学机构
                    if 'zs.kaipuyun.cn' in site:
                        # 国家卫健委搜索
                        search_url = f"https://zs.kaipuyun.cn/s?token=&siteCode=bm24000006&searchWord={quote(search_query)}&button="
                    elif 'cdc.gov' in site:
                        # CDC搜索
                        search_url = f"https://search.cdc.gov/search/?query={quote(search_query)}&dpage=1"
                    # 学术资源
                    elif 'ncbi.nlm.nih.gov/pmc' in site:
                        search_url = f"https://www.ncbi.nlm.nih.gov/pmc/?term={quote(search_query)}"
                    elif 'pubmed.ncbi.nlm.nih.gov' in site:
                        search_url = f"https://pubmed.ncbi.nlm.nih.gov/?term={quote(search_query)}"
                    elif 'europepmc.org' in site:
                        search_url = f"https://europepmc.org/search?query={quote(search_query)}"
                    elif 'doaj.org' in site:
                        search_url = f"https://doaj.org/search/articles?ref=homepage-box&query={quote(search_query)}"
                    elif 'plosone' in site:
                        search_url = f"https://journals.plos.org/plosone/search?query={quote(search_query)}"
                    elif 'arxiv.org' in site:
                        search_url = f"https://arxiv.org/search/?query={quote(search_query)}&searchtype=all"
                    elif 'biorxiv.org' in site:
                        search_url = f"https://www.biorxiv.org/search/{quote(search_query)}"
                    elif 'medrxiv.org' in site:
                        search_url = f"https://www.medrxiv.org/search/{quote(search_query)}"
                    elif 'scholar.google.com' in site:
                        search_url = f"https://scholar.google.com/scholar?q={quote(search_query)}"
                    elif 'semanticscholar.org' in site:
                        search_url = f"https://www.semanticscholar.org/search?q={quote(search_query)}"
                    elif 'core.ac.uk' in site:
                        search_url = f"https://core.ac.uk/search?q={quote(search_query)}"
                    elif 'cma.org.cn' in site:
                        search_url = f"https://www.cma.org.cn/jsearchfront/search.do?q={quote(search_query)}&websiteid=220111020700000&tpl=2"
                    elif 'yxj.org.cn' in site:
                        search_url = f"https://www.yxj.org.cn/search?kw={quote(search_query)}"
                    elif 'cnki.net' in site:
                        search_url = f"https://www.cnki.net/kns8/defaultresult/index?crossids=YSTT4HG0,LSTPFY1C,JUP3MUPD,MPMFIG1A,WQ0UVIAA,BLZOG7CK,EMRPGLPA,PWFIRAGL,NLBO1Z6R,NN3FJMUV&korder=SU&kw={quote(search_query)}"
                    elif 'wanfangdata.com.cn' in site:
                        search_url = f"https://s.wanfangdata.com.cn/search?key={quote(search_query)}"
                    elif 'cqvip.com' in site:
                        search_url = f"http://www.cqvip.com/main/search.aspx?k={quote(search_query)}"
                    elif 'xueshu.baidu.com' in site:
                        search_url = f"https://xueshu.baidu.com/s?wd={quote(search_query)}"
                    elif 'scholar.sogou.com' in site:
                        search_url = f"https://scholar.sogou.com/xueshu?query={quote(search_query)}"
                    elif 'xueshu.so.com' in site:
                        search_url = f"https://xueshu.so.com/s?q={quote(search_query)}"
                    # 医疗门户网站
                    elif 'dxy.com' in site:
                        search_url = f"https://dxy.com/search/result?query={quote(search_query)}"
                    elif 'medlive.cn' in site:
                        search_url = f"https://so.medlive.cn/result?type=all&keyword={quote(search_query)}"
                    elif 'haodf.com' in site:
                        search_url = f"https://so.haodf.com/index/search?type=&kw={quote(search_query)}"
                    elif 'familydoctor.com.cn' in site:
                        search_url = f"https://so.familydoctor.com.cn/search?t=zh&type=1&s=17169745045154111677&q={quote(search_query)}&keyword={quote(search_query)}"
                    elif '39.net' in site:
                        search_url = f"https://so.39.net/?words={quote(search_query)}"
                    elif 'youlai.cn' in site:
                        search_url = f"https://www.youlai.cn/search/?keyword={quote(search_query)}"
                    elif '120ask.com' in site:
                        search_url = f"https://so.120ask.com/?kw={quote(search_query)}"
                    elif 'xywy.com' in site:
                        search_url = f"https://so.xywy.com/?keyword={quote(search_query)}"
                    elif 'guahao.com' in site:
                        search_url = f"https://www.guahao.com/search?keyword={quote(search_query)}"
                    elif 'pingan.com' in site:
                        search_url = f"https://www.pingan.com/search?query={quote(search_query)}"
                    elif 'alihealth.cn' in site:
                        search_url = f"https://www.alihealth.cn/search?q={quote(search_query)}"
                    elif 'jd.com' in site:
                        search_url = f"https://www.jd.com/search?keyword={quote(search_query)}"
                    elif 'baike.qq.com' in site:
                        search_url = f"https://baike.qq.com/search?word={quote(search_query)}"
                    elif 'jiankang.163.com' in site:
                        search_url = f"https://jiankang.163.com/search?keyword={quote(search_query)}"
                    elif 'health.sina.com.cn' in site:
                        search_url = f"https://health.sina.com.cn/search?q={quote(search_query)}"
                    elif 'health.sohu.com' in site:
                        search_url = f"https://health.sohu.com/search?keyword={quote(search_query)}"
                    elif 'health.ifeng.com' in site:
                        search_url = f"https://health.ifeng.com/search?q={quote(search_query)}"
                    else:
                        # 默认搜索URL格式
                        search_url = f"{site}search?q={quote(search_query)}"
                    
                    # 使用内容分析器判断页面类型并决定是否深入爬取
                    from knowledge_base_service.core.content_analyzer import ContentAnalyzer
                    async with ContentAnalyzer(session=temp_session) as analyzer:
                        # 添加随机延迟以避免请求过于频繁
                        await asyncio.sleep(random.uniform(2, 5))
                        
                        # 尝试多次请求以应对网络不稳定
                        max_retries = 5  # 增加重试次数
                        retry_count = 0
                        success = False
                        
                        while retry_count < max_retries and not success:
                            try:
                                # 判断页面类型并获取HTML内容（避免重复请求）
                                is_content, page_type, html_content = await analyzer.is_content_page(search_url)
                                
                                if is_content:
                                    # 如果是内容页面，直接使用已获取的HTML内容提取内容
                                    content = await analyzer.extract_content_from_page(search_url, html_content)
                                    if content and len(content.strip()) > 50:
                                        results.append({
                                            'title': f"[{i+1}] {name} - 关于{query}",
                                            'url': search_url,
                                            'content': content,
                                            'source': f'{site_type}_content'
                                        })
                                else:
                                    # 如果是搜索结果页面，提取其中的链接（默认20个）
                                    links = await analyzer.extract_links_from_search_page(search_url, max_links=20)
                                    logger.info(f"从 {name} 找到 {len(links)} 个相关链接")
                                    
                                    # 处理每个链接，使用缓存避免重复请求
                                    for link in links:
                                        try:
                                            # 判断链接页面类型并获取HTML内容
                                            is_link_content, link_page_type, link_html = await analyzer.is_content_page(link['url'])
                                            if is_link_content:
                                                # 直接使用已获取的HTML内容提取内容
                                                link_content = await analyzer.extract_content_from_page(link['url'], link_html)
                                                if link_content and len(link_content.strip()) > 50:
                                                    results.append({
                                                        'title': link['title'],
                                                        'url': link['url'],
                                                        'content': link_content,
                                                        'source': f'{site_type}_from_search'
                                                    })
                                                    
                                                    # 如果已经获得足够结果，提前退出
                                                    if len(results) >= max_results:
                                                        break
                                        except Exception as link_e:
                                            logger.warning(f"处理链接 {link['url']} 时出错: {str(link_e)}")
                                            continue
                                
                                success = True  # 成功处理了页面
                            except aiohttp.ClientConnectorError as e:
                                logger.warning(f"处理页面 {search_url} 时连接错误 (尝试 {retry_count + 1}/{max_retries}): {str(e)}")
                                retry_count += 1
                                if retry_count < max_retries:
                                    await asyncio.sleep(5 * (retry_count + 1))  # 更长的延迟
                            except asyncio.TimeoutError as e:
                                logger.warning(f"处理页面 {search_url} 时超时 (尝试 {retry_count + 1}/{max_retries}): {str(e)}")
                                retry_count += 1
                                if retry_count < max_retries:
                                    await asyncio.sleep(5 * (retry_count + 1))  # 更长的延迟
                            except Exception as e:
                                logger.warning(f"处理页面 {search_url} 时失败 (尝试 {retry_count + 1}/{max_retries}): {str(e)}")
                                retry_count += 1
                                if retry_count < max_retries:
                                    await asyncio.sleep(3 * (retry_count + 1))  # 增加延迟时间
                    
                    # 限制结果数量
                    if len(results) >= max_results:
                        break
                except Exception as e:
                    logger.error(f"处理开放获取学术资源时出错 ({site}): {str(e)}")
                    continue
            
            # 如果还没有足够的结果，再处理医疗门户网站
            if len(results) < max_results:
                medical_sites = [
                    # 丁香园 - 医学专业网站
                    'https://dxy.com/',
                    # 医脉通 - 医学资讯平台
                    'https://www.medlive.cn/',
                    # 好大夫在线 - 医生和患者交流平台
                    'https://www.haodf.com/',
                    # 家庭医生在线
                    'https://www.familydoctor.com.cn/',
                ]
                
                for i, site in enumerate(medical_sites, start=len(open_academic_sources)):
                    try:
                        # 根据不同网站的特点构造搜索URL
                        if 'dxy.com' in site:
                            search_url = f"https://dxy.com/search/result?query={quote(query)}"
                        elif 'medlive.cn' in site:
                            search_url = f"https://so.medlive.cn/result?type=all&keyword={quote(query)}"
                        elif 'haodf.com' in site:
                            search_url = f"https://so.haodf.com/index/search?type=&kw={quote(query)}"
                        elif 'familydoctor.com.cn' in site:
                            search_url = f"https://so.familydoctor.com.cn/search?t=zh&type=1&s=17169745045154111677&q={quote(query)}&keyword={quote(query)}"
                        else:
                            # 默认搜索URL格式
                            search_url = f"{site}search?q={quote(query)}"
                        
                        # 使用内容分析器判断页面类型并决定是否深入爬取
                        from knowledge_base_service.core.content_analyzer import ContentAnalyzer
                        async with ContentAnalyzer(session=temp_session) as analyzer:
                            # 添加随机延迟以避免请求过于频繁
                            await asyncio.sleep(random.uniform(2, 5))
                            
                            # 尝试多次请求以应对网络不稳定
                            max_retries = 5  # 增加重试次数
                            retry_count = 0
                            success = False
                            
                            while retry_count < max_retries and not success:
                                try:
                                    # 判断页面类型并获取HTML内容（避免重复请求）
                                    is_content, page_type, html_content = await analyzer.is_content_page(search_url)
                                    
                                    if is_content:
                                        # 如果是内容页面，直接使用已获取的HTML内容提取内容
                                        content = await analyzer.extract_content_from_page(search_url, html_content)
                                        if content and len(content.strip()) > 50:
                                            results.append({
                                                'title': f"[{i+1}] 医疗门户内容 - {site} - 关于{query}",
                                                'url': search_url,
                                                'content': content,
                                                'source': 'medical_portal_content'
                                            })
                                    else:
                                        # 如果是搜索结果页面，提取其中的链接
                                        links = await analyzer.extract_links_from_search_page(search_url, max_links=3)
                                        for link in links:
                                            # 对每个链接也进行内容分析（接收3个返回值）
                                            is_link_content, link_page_type, link_html = await analyzer.is_content_page(link['url'])
                                            if is_link_content:
                                                # 直接使用已获取的HTML内容提取内容
                                                link_content = await analyzer.extract_content_from_page(link['url'], link_html)
                                                if link_content and len(link_content.strip()) > 50:
                                                    results.append({
                                                        'title': link['title'],
                                                        'url': link['url'],
                                                        'content': link_content,
                                                        'source': 'medical_portal_content_from_search'
                                                    })
                                    
                                    success = True  # 成功处理了页面
                                except aiohttp.ClientConnectorError as e:
                                    logger.warning(f"处理页面 {search_url} 时连接错误 (尝试 {retry_count + 1}/{max_retries}): {str(e)}")
                                    retry_count += 1
                                    if retry_count < max_retries:
                                        await asyncio.sleep(5 * (retry_count + 1))  # 更长的延迟
                                except asyncio.TimeoutError as e:
                                    logger.warning(f"处理页面 {search_url} 时超时 (尝试 {retry_count + 1}/{max_retries}): {str(e)}")
                                    retry_count += 1
                                    if retry_count < max_retries:
                                        await asyncio.sleep(5 * (retry_count + 1))  # 更长的延迟
                                except Exception as e:
                                    logger.warning(f"处理页面 {search_url} 时失败 (尝试 {retry_count + 1}/{max_retries}): {str(e)}")
                                    retry_count += 1
                                    if retry_count < max_retries:
                                        await asyncio.sleep(3 * (retry_count + 1))  # 增加延迟时间
                        
                        # 限制结果数量
                        if len(results) >= max_results:
                            break
                    except Exception as e:
                        logger.error(f"处理医疗网站时出错 ({site}): {str(e)}")
                        continue
        
        return results


class EnhancedKnowledgeCollectionFlow:
    """
    增强版知识收集流程
    结合LLM和可靠的医疗知识API
    """
    
    def __init__(self, knowledge_base_path: str = "layered_knowledge_base", email: str = "your_email@example.com"):
        self.medical_api = MedicalKnowledgeAPI(email=email)
        self.llm = LLMScheduler()
        self.knowledge_manager = LayeredKnowledgeManager(knowledge_base_path)
        
    async def collect_knowledge(self, topic: str, max_results: int = 5) -> Dict:
        """
        执行增强版知识收集流程（使用API替代爬虫）
        """
        logger.info(f"开始使用增强版流程收集关于 '{topic}' 的知识")
        
        try:
            # 步骤1: 使用LLM生成相关问题/查询
            logger.info("步骤1: 使用LLM生成相关搜索查询...")
            search_queries = await self._generate_search_queries(topic)
            logger.info(f"生成了 {len(search_queries)} 个搜索查询: {search_queries}")
            
            # 步骤2: 使用APIKnowledgeFetcher获取学术文献（替代爬虫）
            logger.info("步骤2: 使用APIKnowledgeFetcher获取学术文献...")
            all_literature = []
            
            async with self.medical_api.api_fetcher as fetcher:
                for query in search_queries:
                    # 使用API获取文献（包括PubMed、Europe PMC、OpenAlex、Crossref）
                    literature_results = await fetcher.search_all_apis(
                        query, 
                        max_results_per_api=max_results // len(search_queries) + 1,
                        include_pubmed=True
                    )
                    all_literature.extend(literature_results)
                    logger.info(f"查询 '{query}' 获取到 {len(literature_results)} 条文献")
                    # 避免请求过于频繁
                    await asyncio.sleep(random.uniform(0.5, 1.5))
            
            logger.info(f"从API获取到 {len(all_literature)} 条学术文献")
            
            # 步骤3: 使用LLM评估文献质量并筛选
            logger.info("步骤3: 使用LLM评估文献质量...")
            filtered_literature = await self._filter_high_quality_literature(all_literature, topic)
            logger.info(f"筛选出 {len(filtered_literature)} 条高质量文献")
            
            # 步骤4: 使用LLM整理和归纳知识
            logger.info("步骤4: 使用LLM整理和归纳知识...")
            organized_knowledge = await self._organize_literature_knowledge(filtered_literature, topic)
            
            # 步骤5: 存储到分层知识库
            logger.info("步骤5: 存储到分层知识库...")
            stored_count = await self._store_literature_knowledge(organized_knowledge, topic)
            
            logger.info(f"增强版知识收集流程完成! 共存储 {stored_count} 个知识条目")
            
            return {
                'status': 'success',
                'total_collected': len(all_literature),
                'total_filtered': len(filtered_literature),
                'total_stored': stored_count,
                'queries_generated': search_queries,
                'message': f'成功收集并存储了 {stored_count} 个知识条目'
            }
            
        except Exception as e:
            logger.error(f"增强版知识收集流程失败: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    async def _generate_search_queries(self, topic: str) -> List[str]:
        """
        使用LLM生成与主题相关的搜索查询
        """
        # 为医美、医疗领域定制的查询生成，生成更短、更精确的关键词
        requirements = f"""
        针对 '{topic}' 这个医美/医疗主题，请生成20个简短、精确的搜索关键词/短语。
        关键词应该涵盖：
        - 核心概念和术语
        - 相关疾病/症状
        - 治疗方法和技术
        - 相关药物/成分
        - 适应症和禁忌症
        - 最新研究方向
        
        每个关键词要简短，精确，适合在学术数据库和百科全书搜索，通常是命名实体或专有名词或概念名词。
        例如：如果主题是'抗衰'，可以生成：['抗衰老', '抗衰机制', '衰老过程', '抗氧化', '胶原蛋白', '皮肤老化', '抗衰成分', '抗衰治疗']
        """
        
        try:
            queries = await self.llm.generate_search_queries(
                topic=topic,
                requirements=requirements,
                num_queries=20
            )
            # 确保返回的是列表
            if not isinstance(queries, list):
                queries = [topic]
            # 确保每个查询都不太长
            return [q[:20] for q in queries if q.strip()]  # 限制每个查询不超过20个字符
        except Exception as e:
            logger.error(f"生成搜索查询失败: {str(e)}")
            # 回退到简单的关键词生成
            return [topic, f"{topic}定义", f"{topic}机制", f"{topic}治疗", f"{topic}方法"]  # 回退到原始主题及相关关键词
    
    async def _filter_high_quality_content(self, results: List[Dict], topic: str) -> List[Dict]:
        """
        使用LLM评估和筛选高质量内容
        """
        filtered_results = []
        
        for i, result in enumerate(results):
            try:
                logger.info(f"评估内容 {i+1}/{len(results)}: {result.get('title', '无标题')[:50]}...")
                
                content = result.get('content', '')
                if not content or len(content.strip()) < 50:
                    logger.info("  内容太短，跳过")
                    continue
                
                # 使用LLM评估内容质量
                quality_assessment = await self.llm.verify_content_quality(
                    content=content,
                    url=result.get('url', ''),
                    original_query=topic
                )
                
                quality_score = quality_assessment.get('quality_score', 0)
                relevance_score = quality_assessment.get('relevance_score', 0)
                
                logger.info(f"  质量评分: {quality_score}, 相关性评分: {relevance_score}")
                
                # 只保留高质量和相关的内容
                if quality_score >= 40 and relevance_score >= 40:
                    result['quality_assessment'] = quality_assessment
                    filtered_results.append(result)
                    logger.info("  内容质量合格，保留")
                else:
                    logger.info("  内容质量不足，跳过")
                    
            except Exception as e:
                logger.error(f"评估内容时出错: {str(e)}")
                continue
        
        return filtered_results
    
    async def _filter_high_quality_content_from_crawler(self, results: List[Dict], topic: str) -> List[Dict]:
        """
        使用LLM评估和筛选从递归爬虫获取的高质量内容
        """
        filtered_results = []
        
        for i, result in enumerate(results):
            try:
                logger.info(f"评估爬取内容 {i+1}/{len(results)}: {result.get('title', '无标题')[:50]}...")
                
                content = result.get('content', '')
                if not content or len(content.strip()) < 50:
                    logger.info("  内容太短，跳过")
                    continue
                
                # 使用LLM评估内容质量
                quality_assessment = await self.llm.verify_content_quality(
                    content=content,
                    url=result.get('url', ''),
                    original_query=topic
                )
                
                quality_score = quality_assessment.get('quality_score', 0)
                relevance_score = quality_assessment.get('relevance_score', 0)
                
                logger.info(f"  质量评分: {quality_score}, 相关性评分: {relevance_score}")
                
                # 只保留高质量和相关的内容
                if quality_score >= 40 and relevance_score >= 40:
                    result['quality_assessment'] = quality_assessment
                    filtered_results.append(result)
                    logger.info("  爬取内容质量合格，保留")
                else:
                    logger.info("  爬取内容质量不足，跳过")
                    
            except Exception as e:
                logger.error(f"评估爬取内容时出错: {str(e)}")
                continue
        
        return filtered_results
    
    async def _organize_knowledge(self, results: List[Dict], topic: str) -> List[Dict]:
        """
        使用LLM整理和归纳知识
        """
        organized_knowledge = []
        
        for i, result in enumerate(results):
            try:
                logger.info(f"整理知识 {i+1}/{len(results)}: {result.get('title', '无标题')[:50]}...")
                
                content = result.get('content', '')
                source_url = result.get('url', '')
                
                # 使用LLM整理内容
                prompt = f"""
                请将以下关于 '{topic}' 的内容整理成结构化的专业知识：

                来源URL: {source_url}
                原始内容:
                {content[:3000]}  # 限制长度以节省token

                请按照以下JSON格式返回整理后的知识：
                {{
                  "title": "整理后的标题",
                  "content": "整理后的专业内容，结构清晰，逻辑完整",
                  "key_points": ["要点1", "要点2", "要点3"],
                  "category": "所属类别（如：原理、方法、注意事项等）",
                  "tags": ["标签1", "标签2", "标签3"]
                }}
                """
                
                model = await self.llm.get_valid_model_for_task('detailed')
                response = await self.llm.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=2000
                )
                
                content_response = response.choices[0].message.content.strip()
                
                # 解析LLM返回的JSON
                import json
                import re
                json_match = re.search(r'\{.*\}', content_response, re.DOTALL)
                
                if json_match:
                    organized_data = json.loads(json_match.group())
                    organized_knowledge.append({
                        'title': organized_data.get('title', result.get('title', '未知标题')),
                        'content': organized_data.get('content', content),
                        'key_points': organized_data.get('key_points', []),
                        'category': organized_data.get('category', 'general'),
                        'tags': organized_data.get('tags', []),
                        'source_url': source_url,
                        'original_query': topic
                    })
                    logger.info("  知识整理完成")
                else:
                    # 如果无法解析JSON，使用原始内容
                    organized_knowledge.append({
                        'title': result.get('title', '未知标题'),
                        'content': content,
                        'key_points': [],
                        'category': 'general',
                        'tags': [topic],
                        'source_url': source_url,
                        'original_query': topic
                    })
                    logger.info("  无法解析整理结果，使用原始内容")
                    
            except Exception as e:
                logger.error(f"整理知识时出错: {str(e)}")
                # 出错时仍然保留原始内容
                organized_knowledge.append({
                    'title': result.get('title', '未知标题'),
                    'content': result.get('content', ''),
                    'key_points': [],
                    'category': 'general',
                    'tags': [topic],
                    'source_url': result.get('url', ''),
                    'original_query': topic
                })
        
        return organized_knowledge
    
    async def _store_knowledge(self, organized_knowledge: List[Dict], topic: str) -> int:
        """
        将整理后的知识存储到分层知识库
        """
        stored_count = 0
        
        for i, knowledge_item in enumerate(organized_knowledge):
            try:
                logger.info(f"存储知识 {i+1}/{len(organized_knowledge)}: {knowledge_item['title'][:50]}...")
                
                success = await self.knowledge_manager.add_knowledge(
                    title=knowledge_item['title'],
                    content=knowledge_item['content'],
                    source_url=knowledge_item['source_url'],
                    query_used=knowledge_item['original_query'],
                    tags=knowledge_item['tags']
                )
                
                if success:
                    stored_count += 1
                    logger.info("  知识存储成功")
                else:
                    logger.info("  知识存储失败或重复")
                    
            except Exception as e:
                logger.error(f"存储知识时出错: {str(e)}")
                continue
        
        return stored_count
    
    async def _filter_high_quality_literature(self, literature: List[Dict], topic: str) -> List[Dict]:
        """
        使用LLM评估和筛选高质量文献
        """
        filtered_literature = []
        
        for i, item in enumerate(literature):
            try:
                logger.info(f"评估文献 {i+1}/{len(literature)}: {item.get('title', '无标题')}...")
                
                title = item.get('title', '')
                abstract = item.get('abstract', '')
                source = item.get('source', '')

                
                # 使用LLM评估文献质量
                prompt = f"""
                请评估以下关于 '{topic}' 的学术文献质量：

                标题: {title}
                摘要: {abstract if abstract else '无摘要'}
                来源: {source}

                请按照以下JSON格式返回评估结果：
                {{
                  "quality_score": 0-100之间的质量评分,
                  "relevance_score": 0-100之间的相关性评分,
                  "reason": "简要说明评估理由"
                }}
                """
                
                model = await self.llm.get_valid_model_for_task('detailed')
                response = await self.llm.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=32768
                )
                
                assessment_response = response.choices[0].message.content.strip()
                
                # 解析LLM返回的JSON
                import json
                import re
                json_match = re.search(r'\{.*\}', assessment_response, re.DOTALL)
                
                if json_match:
                    assessment = json.loads(json_match.group())
                    quality_score = assessment.get('quality_score', 0)
                    relevance_score = assessment.get('relevance_score', 0)
                    
                    logger.info(f"  质量评分: {quality_score}, 相关性评分: {relevance_score}")
                    
                    # 只保留高质量和相关的内容
                    if quality_score >= 50 and relevance_score >= 50:
                        item['quality_assessment'] = assessment
                        filtered_literature.append(item)
                        logger.info("  文献质量合格，保留")
                    else:
                        logger.info("  文献质量不足，跳过")
                else:
                    # 如果无法解析JSON，默认保留
                    filtered_literature.append(item)
                    logger.info("  无法解析评估结果，默认保留")
                    
            except Exception as e:
                logger.error(f"评估文献时出错: {str(e)}")
                continue
        
        return filtered_literature
    
    async def _organize_literature_knowledge(self, literature: List[Dict], topic: str) -> List[Dict]:
        """
        使用LLM整理和归纳文献知识
        """
        organized_knowledge = []
        
        for i, item in enumerate(literature):
            try:
                logger.info(f"整理文献 {i+1}/{len(literature)}: {item.get('title', '无标题')[:50]}...")
                
                title = item.get('title', '')
                abstract = item.get('abstract', '')
                authors = item.get('authors', '')
                journal = item.get('journal', '')
                year = item.get('year', '')
                source_url = item.get('url', '')
                source = item.get('source', '')
                
                # 使用LLM整理文献内容
                prompt = f"""
                请将以下关于 '{topic}' 的学术文献整理成结构化的专业知识：

                标题: {title}
                作者: {authors}
                期刊: {journal}
                年份: {year}
                摘要: {abstract[:2000] if abstract else '无摘要'}
                来源: {source}

                请按照以下JSON格式返回整理后的知识：
                {{
                  "title": "整理后的标题",
                  "content": "基于摘要整理的专业内容，结构清晰，逻辑完整",
                  "key_points": ["要点1", "要点2", "要点3"],
                  "category": "所属类别（如：研究方法、临床应用、机制原理等）",
                  "tags": ["标签1", "标签2", "标签3"],
                  "authors": "作者列表",
                  "journal": "期刊名称",
                  "year": "发表年份"
                }}
                """
                
                model = await self.llm.get_valid_model_for_task('detailed')
                response = await self.llm.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=2000
                )
                
                content_response = response.choices[0].message.content.strip()
                
                # 解析LLM返回的JSON
                import json
                import re
                json_match = re.search(r'\{.*\}', content_response, re.DOTALL)
                
                if json_match:
                    organized_data = json.loads(json_match.group())
                    organized_knowledge.append({
                        'title': organized_data.get('title', title),
                        'content': organized_data.get('content', abstract),
                        'key_points': organized_data.get('key_points', []),
                        'category': organized_data.get('category', 'research'),
                        'tags': organized_data.get('tags', [topic]),
                        'authors': organized_data.get('authors', authors),
                        'journal': organized_data.get('journal', journal),
                        'year': organized_data.get('year', year),
                        'source_url': source_url,
                        'source': source,
                        'original_query': topic
                    })
                    logger.info("  文献整理完成")
                else:
                    # 如果无法解析JSON，使用原始数据
                    organized_knowledge.append({
                        'title': title,
                        'content': abstract,
                        'key_points': [],
                        'category': 'research',
                        'tags': [topic],
                        'authors': authors,
                        'journal': journal,
                        'year': year,
                        'source_url': source_url,
                        'source': source,
                        'original_query': topic
                    })
                    logger.info("  无法解析整理结果，使用原始数据")
                    
            except Exception as e:
                logger.error(f"整理文献时出错: {str(e)}")
                # 出错时仍然保留原始数据
                organized_knowledge.append({
                    'title': item.get('title', '未知标题'),
                    'content': item.get('abstract', ''),
                    'key_points': [],
                    'category': 'research',
                    'tags': [topic],
                    'authors': item.get('authors', ''),
                    'journal': item.get('journal', ''),
                    'year': item.get('year', ''),
                    'source_url': item.get('url', ''),
                    'source': item.get('source', ''),
                    'original_query': topic
                })
        
        return organized_knowledge
    
    async def _store_literature_knowledge(self, organized_knowledge: List[Dict], topic: str) -> int:
        """
        将整理后的文献知识存储到分层知识库
        """
        stored_count = 0
        
        # 收集所有引用，放在文件开头
        all_references = []
        
        for i, knowledge_item in enumerate(organized_knowledge):
            try:
                logger.info(f"存储文献 {i+1}/{len(organized_knowledge)}: {knowledge_item['title'][:50]}...")
                
                # 获取文献完整内容（而不仅仅是摘要）
                title = knowledge_item.get('title', '')
                abstract = knowledge_item.get('abstract', '')
                authors = knowledge_item.get('authors', '')
                journal = knowledge_item.get('journal', '')
                year = knowledge_item.get('year', '')
                source = knowledge_item.get('source', '')
                pmid = knowledge_item.get('pmid', '')
                pmcid = knowledge_item.get('pmcid', '')
                doi = knowledge_item.get('doi', '')
                source_url = knowledge_item.get('source_url', '')
                
                # 收集引用信息
                if pmid:
                    all_references.append(f"PMID: {pmid}")
                if doi:
                    all_references.append(f"DOI: {doi}")
                if source_url:
                    all_references.append(f"URL: {source_url}")
                
                # 尝试获取文献全文
                full_text = ""
                if pmcid:
                    logger.info(f"  尝试获取PMCID {pmcid} 的全文...")
                    full_text = await self.medical_api.api_fetcher.get_full_text(pmcid)
                    if full_text:
                        logger.info(f"  成功获取全文，长度: {len(full_text)} 字符")
                    else:
                        logger.info(f"  无法获取全文，使用摘要")
                
                # 构建完整内容（包含所有元信息和全文）
                content_parts = [
                    f"标题: {title}",
                    f"作者: {authors}",
                    f"期刊: {journal}",
                    f"年份: {year}",
                    f"来源: {source}",
                    f"PMID: {pmid}",
                    f"DOI: {doi}",
                ]
                
                if abstract:
                    content_parts.append(f"摘要:\n{abstract}")
                
                if full_text:
                    content_parts.append(f"\n全文:\n{full_text}")
                elif source_url:
                    content_parts.append(f"\n完整文献链接: {source_url}")
                
                full_content = "\n".join(content_parts)
                
                success = await self.knowledge_manager.add_knowledge(
                    title=title,
                    content=full_content.strip(),
                    source_url=source_url,
                    query_used=knowledge_item['original_query'],
                    tags=knowledge_item['tags']
                )
                
                if success:
                    stored_count += 1
                    logger.info("  文献存储成功")
                else:
                    logger.info("  文献存储失败或重复")
                    
            except Exception as e:
                logger.error(f"存储文献时出错: {str(e)}")
                continue
        
        # 如果有引用，在文件开头添加引用部分
        if all_references:
            logger.info(f"添加 {len(all_references)} 个引用到文件开头")
            references_content = f"""参考文献：

{chr(10).join(all_references)}

"""
            
            # 添加引用到知识库
            await self.knowledge_manager.add_knowledge(
                title=f"{topic} - 参考文献",
                content=references_content.strip(),
                source_url="",
                query_used=topic,
                tags=["references"]
            )
            stored_count += 1
        
        return stored_count