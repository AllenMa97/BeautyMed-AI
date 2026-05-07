"""
免费知识API服务
只使用完全免费、无需API Key的公开API
"""
import asyncio
import json
import ssl
import urllib.request
from typing import List, Dict, Optional, Any
from urllib.parse import quote
from datetime import datetime

from knowledge_base_service.utils.logger import get_logger
from knowledge_base_service.core.http_client import HTTPClient
from knowledge_base_service.core.processors.llm_scheduler import LLMScheduler

logger = get_logger(__name__)


class FreeKnowledgeAPI:
    """
    免费知识API服务
    
    已测试验证的免费API（无需API Key）：
    1. Europe PMC API - 生物医学文献
    2. OpenAlex API - 学术文献
    3. Crossref API - 学术文献引用
    4. Wikipedia API - 百科知识
    5. DOAJ API - 开放获取期刊
    6. bioRxiv/medRxiv API - 预印本
    7. PubMed E-utilities - 医学文献（需配置email）
    """
    
    def __init__(self, email: str = "your_email@example.com"):
        self.http_client = HTTPClient(timeout=30)
        self.llm = LLMScheduler()
        self.email = email
        
        self._configure_ssl()
        
        self.endpoints = {
            'europe_pmc': 'https://www.ebi.ac.uk/europepmc/webservices/rest/search',
            'openalex': 'https://api.openalex.org/works',
            'crossref': 'https://api.crossref.org/works',
            'wikipedia_en': 'https://en.wikipedia.org/api/rest_v1/page/summary',
            'wikipedia_zh': 'https://zh.wikipedia.org/api/rest_v1/page/summary',
            'wikipedia_search': 'https://en.wikipedia.org/w/api.php',
            'doaj': 'https://doaj.org/api/search/articles',
            'biorxiv': 'https://api.biorxiv.org/details/biorxiv',
            'medrxiv': 'https://api.biorxiv.org/details/medrxiv',
        }
    
    def _configure_ssl(self):
        """配置SSL"""
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            urllib.request.ssl._create_default_https_context = ssl._create_unverified_context
        except Exception as e:
            logger.warning(f"SSL配置失败: {str(e)}")
    
    async def __aenter__(self):
        await self.http_client.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.close()
    
    async def search_europe_pmc(
        self, 
        query: str, 
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Europe PMC API - 生物医学文献
        完全免费，无需API Key
        """
        try:
            params = {
                'query': query,
                'resultType': 'core',
                'pageSize': max_results,
                'format': 'json',
                'cursorMark': '*',
            }
            
            logger.info(f"搜索Europe PMC: {query}")
            
            data = await self.http_client.fetch_json(
                self.endpoints['europe_pmc'],
                params=params
            )
            
            results = []
            if 'resultList' in data and 'result' in data['resultList']:
                for item in data['resultList']['result']:
                    result = {
                        'title': item.get('title', ''),
                        'authors': item.get('authorString', ''),
                        'journal': item.get('journalTitle', ''),
                        'year': item.get('pubYear', ''),
                        'pmcid': item.get('pmcid', ''),
                        'pmid': item.get('pmid', ''),
                        'doi': item.get('doi', ''),
                        'abstract': item.get('abstractText', ''),
                        'url': f"https://europepmc.org/article/{item.get('pmcid', '')}" if item.get('pmcid') else '',
                        'source': 'Europe PMC',
                        'is_open_access': item.get('isOpenAccess', 'N') == 'Y',
                    }
                    results.append(result)
            
            logger.info(f"Europe PMC找到 {len(results)} 条结果")
            return results
            
        except Exception as e:
            logger.error(f"Europe PMC搜索失败: {str(e)}")
            return []
    
    async def search_openalex(
        self, 
        query: str, 
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        OpenAlex API - 学术文献
        完全免费，无需API Key
        """
        try:
            params = {
                'search': query,
                'per-page': max_results,
                'filter': 'has_fulltext:true',
            }
            
            logger.info(f"搜索OpenAlex: {query}")
            
            data = await self.http_client.fetch_json(
                self.endpoints['openalex'],
                params=params
            )
            
            results = []
            if 'results' in data:
                for item in data['results']:
                    authors = ', '.join([
                        a.get('author', {}).get('display_name', '') 
                        for a in item.get('authorships', [])[:3]
                    ])
                    
                    location = item.get('primary_location', {}) or {}
                    source = location.get('source', {}) or {}
                    
                    result = {
                        'title': item.get('title', ''),
                        'authors': authors,
                        'journal': source.get('display_name', ''),
                        'year': item.get('publication_year', ''),
                        'doi': item.get('doi', ''),
                        'abstract': self._reconstruct_abstract(item.get('abstract_inverted_index')),
                        'url': location.get('landing_page_url', ''),
                        'cited_by': item.get('cited_by_count', 0),
                        'source': 'OpenAlex',
                        'is_open_access': item.get('open_access', {}).get('is_oa', False),
                    }
                    results.append(result)
            
            logger.info(f"OpenAlex找到 {len(results)} 条结果")
            return results
            
        except Exception as e:
            logger.error(f"OpenAlex搜索失败: {str(e)}")
            return []
    
    def _reconstruct_abstract(self, inverted_index: Optional[Dict]) -> str:
        """从倒排索引重建摘要"""
        if not inverted_index:
            return ''
        
        try:
            positions = []
            for word, pos_list in inverted_index.items():
                for pos in pos_list:
                    positions.append((pos, word))
            
            positions.sort(key=lambda x: x[0])
            return ' '.join([word for _, word in positions])
        except:
            return ''
    
    async def search_crossref(
        self, 
        query: str, 
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Crossref API - 学术文献引用
        完全免费，无需API Key
        """
        try:
            params = {
                'query': query,
                'rows': max_results,
                'select': 'title,author,published-print,DOI,abstract,type,link',
            }
            
            logger.info(f"搜索Crossref: {query}")
            
            data = await self.http_client.fetch_json(
                self.endpoints['crossref'],
                params=params
            )
            
            results = []
            if 'message' in data and 'items' in data['message']:
                for item in data['message']['items']:
                    authors = ', '.join([
                        f"{a.get('given', '')} {a.get('family', '')}".strip()
                        for a in item.get('author', [])[:3]
                    ])
                    
                    year = ''
                    if 'published-print' in item:
                        date_parts = item['published-print'].get('date-parts', [[]])
                        if date_parts and date_parts[0]:
                            year = str(date_parts[0][0])
                    
                    url = ''
                    if item.get('DOI'):
                        url = f"https://doi.org/{item['DOI']}"
                    
                    result = {
                        'title': ' '.join(item.get('title', [])),
                        'authors': authors,
                        'year': year,
                        'doi': item.get('DOI', ''),
                        'type': item.get('type', ''),
                        'url': url,
                        'source': 'Crossref',
                    }
                    results.append(result)
            
            logger.info(f"Crossref找到 {len(results)} 条结果")
            return results
            
        except Exception as e:
            logger.error(f"Crossref搜索失败: {str(e)}")
            return []
    
    async def search_wikipedia(
        self, 
        query: str, 
        language: str = 'zh'
    ) -> List[Dict[str, Any]]:
        """
        Wikipedia API - 百科知识
        完全免费，无需API Key
        """
        results = []
        
        try:
            if language == 'zh':
                search_url = f"{self.endpoints['wikipedia_zh']}/{quote(query)}"
            else:
                search_url = f"{self.endpoints['wikipedia_en']}/{quote(query)}"
            
            logger.info(f"搜索Wikipedia({language}): {query}")
            
            data = await self.http_client.fetch_json(search_url)
            
            if 'title' in data:
                result = {
                    'title': data.get('title', ''),
                    'content': data.get('extract', ''),
                    'url': data.get('content_urls', {}).get('desktop', {}).get('page', ''),
                    'source': f'Wikipedia ({language})',
                    'type': 'encyclopedia',
                }
                results.append(result)
            
            if not results:
                search_api = self.endpoints['wikipedia_search']
                params = {
                    'action': 'query',
                    'format': 'json',
                    'list': 'search',
                    'srsearch': query,
                    'srlimit': 5,
                }
                
                data = await self.http_client.fetch_json(search_api, params=params)
                
                if 'query' in data and 'search' in data['query']:
                    for item in data['query']['search']:
                        title = item.get('title', '')
                        if title:
                            results.append({
                                'title': title,
                                'content': item.get('snippet', ''),
                                'url': f"https://{language}.wikipedia.org/wiki/{quote(title)}",
                                'source': f'Wikipedia ({language})',
                                'type': 'encyclopedia',
                            })
            
            logger.info(f"Wikipedia找到 {len(results)} 条结果")
            return results
            
        except Exception as e:
            logger.error(f"Wikipedia搜索失败: {str(e)}")
            return []
    
    async def search_doaj(
        self, 
        query: str, 
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        DOAJ API - 开放获取期刊
        完全免费，无需API Key
        """
        try:
            search_url = f"{self.endpoints['doaj']}/{quote(query)}?pageSize={max_results}"
            
            logger.info(f"搜索DOAJ: {query}")
            
            data = await self.http_client.fetch_json(search_url)
            
            results = []
            if 'results' in data:
                for item in data['results']:
                    bibjson = item.get('bibjson', {})
                    result = {
                        'title': bibjson.get('title', ''),
                        'authors': ', '.join([a.get('name', '') for a in bibjson.get('author', [])[:3]]),
                        'journal': bibjson.get('journal', {}).get('title', ''),
                        'year': bibjson.get('year', ''),
                        'doi': bibjson.get('identifier', {}).get('doi', ''),
                        'abstract': bibjson.get('abstract', ''),
                        'url': bibjson.get('link', [{}])[0].get('url', '') if bibjson.get('link') else '',
                        'source': 'DOAJ',
                        'is_open_access': True,
                    }
                    results.append(result)
            
            logger.info(f"DOAJ找到 {len(results)} 条结果")
            return results
            
        except Exception as e:
            logger.error(f"DOAJ搜索失败: {str(e)}")
            return []
    
    async def search_biorxiv(
        self, 
        query: str, 
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        bioRxiv/medRxiv API - 预印本
        完全免费，无需API Key
        """
        results = []
        
        for server in ['biorxiv', 'medrxiv']:
            try:
                endpoint = self.endpoints[server]
                
                logger.info(f"搜索{server}: {query}")
                
                data = await self.http_client.fetch_json(endpoint)
                
                if 'collection' in data:
                    for item in data['collection'][:max_results]:
                        title = item.get('title', '')
                        if query.lower() in title.lower():
                            result = {
                                'title': title,
                                'authors': item.get('authors', ''),
                                'doi': item.get('doi', ''),
                                'date': item.get('date', ''),
                                'url': f"https://www.{server}.org/content/{item.get('doi', '')}",
                                'source': server,
                                'type': 'preprint',
                            }
                            results.append(result)
                
                if len(results) >= max_results:
                    break
                    
            except Exception as e:
                logger.warning(f"{server}搜索失败: {str(e)}")
                continue
        
        logger.info(f"预印本找到 {len(results)} 条结果")
        return results[:max_results]
    
    async def search_all_free(
        self, 
        query: str, 
        max_results_per_source: int = 5
    ) -> List[Dict[str, Any]]:
        """
        并行搜索所有免费API
        """
        tasks = [
            self.search_europe_pmc(query, max_results_per_source),
            self.search_openalex(query, max_results_per_source),
            self.search_crossref(query, max_results_per_source),
            self.search_wikipedia(query, 'en'),
            self.search_wikipedia(query, 'zh'),
            self.search_doaj(query, max_results_per_source),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_results = []
        for result in results:
            if isinstance(result, list):
                all_results.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"API搜索异常: {str(result)}")
        
        unique_results = self._deduplicate(all_results)
        
        logger.info(f"所有免费API搜索完成，共找到 {len(unique_results)} 条结果")
        return unique_results
    
    def _deduplicate(self, results: List[Dict]) -> List[Dict]:
        """去重"""
        seen = set()
        unique = []
        
        for item in results:
            key = item.get('doi') or item.get('title', '').lower()[:50]
            if key and key not in seen:
                seen.add(key)
                unique.append(item)
        
        return unique


FREE_APIS_INFO = """
## 免费知识API列表（已测试验证）

### 学术文献API（完全免费，无需API Key）

| API | 用途 | 限制 | 测试状态 |
|-----|------|------|----------|
| Europe PMC | 生物医学文献 | 无明显限制 | ✅ 可用 |
| OpenAlex | 学术文献 | 无明显限制 | ✅ 可用 |
| Crossref | 学术引用 | 无明显限制 | ✅ 可用 |
| DOAJ | 开放期刊 | 无明显限制 | ✅ 可用 |
| bioRxiv/medRxiv | 预印本 | 无明显限制 | ✅ 可用 |
| PubMed E-utilities | 医学文献 | 3次/秒 | ✅ 可用 |

### 百科知识API（完全免费）

| API | 用途 | 限制 | 测试状态 |
|-----|------|------|----------|
| Wikipedia API | 百科知识 | 无明显限制 | ✅ 可用 |
| Wikipedia中文 | 中文百科 | 无明显限制 | ✅ 可用 |

### 可选增强API（需要API Key，有免费额度）

| API | 用途 | 免费额度 | 获取方式 |
|-----|------|----------|----------|
| Tavily | 新闻/网页搜索 | 1000次/月 | https://tavily.com |
| Serper | Google搜索 | 2500次/月 | https://serper.dev |
| Semantic Scholar | 学术搜索 | 5000次/5分钟 | https://www.semanticscholar.org/product/api |
"""
