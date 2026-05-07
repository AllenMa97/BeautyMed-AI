"""
基于API的科学知识获取模块
使用公开API获取医学和学术文献，避免爬虫的不稳定性
"""
import asyncio
import json
import ssl
import urllib.request
from typing import List, Dict, Optional, Any
from urllib.parse import quote
from Bio import Entrez

from knowledge_base_service.utils.logger import get_logger
from knowledge_base_service.core.processors.llm_scheduler import LLMScheduler
from knowledge_base_service.core.http_client import HTTPClient

logger = get_logger(__name__)


class APIKnowledgeFetcher:
    """
    基于API的知识获取器
    
    支持的API：
    1. PubMed E-utilities - 全球最大生物医学文献数据库（核心数据源）
    2. Europe PMC REST API - 欧洲生物医学文献数据库
    3. OpenAlex API - 开放学术数据库
    4. Crossref API - 学术文献引用数据库
    """
    
    def __init__(self, email: str = "your_email@example.com"):
        self.llm = LLMScheduler()
        self.http_client = HTTPClient(timeout=30)
        
        Entrez.email = email
        Entrez.tool = "KnowledgeBaseService"
        
        self._configure_ssl()
        
        self.api_endpoints = {
            'europe_pmc': {
                'search': 'https://www.ebi.ac.uk/europepmc/webservices/rest/search',
                'fulltext': 'https://www.ebi.ac.uk/europepmc/webservices/rest/fulltext',
            },
            'openalex': {
                'works': 'https://api.openalex.org/works',
                'authors': 'https://api.openalex.org/authors',
                'concepts': 'https://api.openalex.org/concepts',
            },
            'crossref': {
                'works': 'https://api.crossref.org/works',
            },
        }
    
    def _configure_ssl(self):
        """配置SSL上下文，禁用证书验证"""
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            urllib.request.ssl._create_default_https_context = ssl._create_unverified_context
            logger.info("SSL配置完成：已禁用证书验证")
        except Exception as e:
            logger.warning(f"SSL配置失败: {str(e)}")
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def start(self):
        """启动HTTP会话"""
        await self.http_client.start()
    
    async def close(self):
        """关闭HTTP会话"""
        await self.http_client.close()
    
    async def _translate_to_english(self, query: str) -> str:
        """
        将中文查询翻译为英文医学术语
        """
        try:
            prompt = f"""请将以下中文医学查询翻译为准确的英文医学术语，用于学术文献搜索。

中文查询: {query}

请直接返回英文翻译，不要添加任何解释。如果是专业术语，请使用标准的医学英文术语。"""
            
            model = await self.llm.get_valid_model_for_task('translation')
            response = await self.llm.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=100
            )
            
            english_query = response.choices[0].message.content.strip()
            logger.info(f"翻译结果: {query} -> {english_query}")
            return english_query
            
        except Exception as e:
            logger.error(f"翻译失败: {str(e)}")
            return query
    
    async def search_pubmed(
        self,
        query: str,
        max_results: int = 20,
        use_english: bool = True
    ) -> List[Dict[str, Any]]:
        """
        使用PubMed E-utilities API搜索文献（核心数据源）
        """
        if use_english and any('\u4e00' <= c <= '\u9fff' for c in query):
            query = await self._translate_to_english(query)
        
        try:
            logger.info(f"搜索PubMed: {query}")
            
            search_handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=max_results,
                sort="relevance",
                retmode="json"
            )
            search_record = json.load(search_handle)
            search_handle.close()
            
            pmids = search_record.get("esearchresult", {}).get("idlist", [])
            
            if not pmids:
                logger.info(f"PubMed未找到相关文献")
                return []
            
            logger.info(f"PubMed找到 {len(pmids)} 篇文献")
            
            fetch_handle = Entrez.efetch(
                db="pubmed",
                id=",".join(pmids),
                rettype="abstract",
                retmode="xml"
            )
            fetch_data = fetch_handle.read()
            fetch_handle.close()
            
            import xml.etree.ElementTree as ET
            root = ET.fromstring(fetch_data)
            
            results = []
            for article in root.findall(".//PubmedArticle"):
                medline_citation = article.find("MedlineCitation")
                if medline_citation is None:
                    continue
                
                pmid_elem = medline_citation.find("PMID")
                pmid = pmid_elem.text if pmid_elem is not None else ""
                
                article_elem = medline_citation.find("Article")
                if article_elem is None:
                    continue
                
                title_elem = article_elem.find(".//ArticleTitle")
                title = title_elem.text if title_elem is not None else ""
                
                authors = []
                author_list = article_elem.find("AuthorList")
                if author_list is not None:
                    for author in author_list.findall("Author")[:5]:
                        last_name = author.find("LastName")
                        fore_name = author.find("ForeName")
                        if last_name is not None and fore_name is not None:
                            authors.append(f"{fore_name.text} {last_name.text}")
                        elif last_name is not None:
                            authors.append(last_name.text)
                
                journal_elem = article_elem.find("Journal")
                journal_title = ""
                pub_year = ""
                if journal_elem is not None:
                    title_elem = journal_elem.find("Title")
                    journal_title = title_elem.text if title_elem is not None else ""
                    
                    pub_date = journal_elem.find(".//PubDate")
                    if pub_date is not None:
                        year_elem = pub_date.find("Year")
                        pub_year = year_elem.text if year_elem is not None else ""
                
                abstract_text = ""
                abstract_elem = article_elem.find("Abstract")
                if abstract_elem is not None:
                    abstract_text_elem = abstract_elem.find("AbstractText")
                    if abstract_text_elem is not None:
                        abstract_text = abstract_text_elem.text or ""
                        for text_elem in abstract_elem.findall("AbstractText"):
                            if text_elem.text:
                                label = text_elem.get("Label", "")
                                if label:
                                    abstract_text += f"\n{label}: {text_elem.text}"
                                else:
                                    abstract_text += text_elem.text
                
                doi = ""
                article_ids = article_elem.find("ArticleIdList")
                if article_ids is not None:
                    for article_id in article_ids.findall("ArticleId"):
                        if article_id.get("IdType") == "doi":
                            doi = article_id.text
                            break
                
                result = {
                    'title': title,
                    'authors': ', '.join(authors),
                    'journal': journal_title,
                    'year': pub_year,
                    'pmid': pmid,
                    'doi': doi,
                    'abstract': abstract_text,
                    'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else '',
                    'source': 'PubMed',
                }
                results.append(result)
            
            logger.info(f"PubMed搜索完成，成功解析 {len(results)} 篇文献")
            return results
            
        except Exception as e:
            logger.error(f"PubMed搜索失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    async def search_europe_pmc(
        self,
        query: str,
        max_results: int = 10,
        use_english: bool = True
    ) -> List[Dict[str, Any]]:
        """
        使用Europe PMC API搜索文献
        """
        if use_english and any('\u4e00' <= c <= '\u9fff' for c in query):
            query = await self._translate_to_english(query)
        
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
                self.api_endpoints['europe_pmc']['search'],
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
                    }
                    results.append(result)
            
            logger.info(f"Europe PMC搜索完成，找到 {len(results)} 条结果")
            return results
            
        except Exception as e:
            logger.error(f"Europe PMC搜索失败: {str(e)}")
            return []
    
    async def search_openalex(
        self,
        query: str,
        max_results: int = 10,
        use_english: bool = True
    ) -> List[Dict[str, Any]]:
        """
        使用OpenAlex API搜索文献
        """
        if use_english and any('\u4e00' <= c <= '\u9fff' for c in query):
            query = await self._translate_to_english(query)
        
        try:
            params = {
                'search': query,
                'per-page': max_results,
                'filter': 'has_fulltext:true',
            }
            
            logger.info(f"搜索OpenAlex: {query}")
            
            data = await self.http_client.fetch_json(
                self.api_endpoints['openalex']['works'],
                params=params
            )
            
            results = []
            if 'results' in data:
                for item in data['results']:
                    authors = ', '.join([a.get('display_name', '') for a in item.get('authorships', [])[:3]])
                    
                    result = {
                        'title': item.get('title', ''),
                        'authors': authors,
                        'journal': item.get('primary_location', {}).get('source', {}).get('display_name', ''),
                        'year': item.get('publication_year', ''),
                        'doi': item.get('doi', ''),
                        'abstract': item.get('abstract_inverted_index', ''),
                        'url': item.get('primary_location', {}).get('landing_page_url', ''),
                        'cited_by': item.get('cited_by_count', 0),
                        'source': 'OpenAlex',
                    }
                    results.append(result)
            
            logger.info(f"OpenAlex搜索完成，找到 {len(results)} 条结果")
            return results
            
        except Exception as e:
            logger.error(f"OpenAlex搜索失败: {str(e)}")
            return []
    
    async def search_crossref(
        self,
        query: str,
        max_results: int = 10,
        use_english: bool = True
    ) -> List[Dict[str, Any]]:
        """
        使用Crossref API搜索文献
        """
        if use_english and any('\u4e00' <= c <= '\u9fff' for c in query):
            query = await self._translate_to_english(query)
        
        try:
            params = {
                'query': query,
                'rows': max_results,
                'select': 'title,author,published-print,DOI,abstract,type,link',
            }
            
            logger.info(f"搜索Crossref: {query}")
            
            data = await self.http_client.fetch_json(
                self.api_endpoints['crossref']['works'],
                params=params
            )
            
            results = []
            if 'message' in data and 'items' in data['message']:
                for item in data['message']['items']:
                    authors = ', '.join([a.get('given', '') + ' ' + a.get('family', '') for a in item.get('author', [])[:3]])
                    
                    result = {
                        'title': ' '.join(item.get('title', [])),
                        'authors': authors,
                        'year': item.get('published-print', {}).get('date-parts', [['']])[0][0],
                        'doi': item.get('DOI', ''),
                        'type': item.get('type', ''),
                        'url': f"https://doi.org/{item.get('DOI', '')}" if item.get('DOI') else '',
                        'source': 'Crossref',
                    }
                    results.append(result)
            
            logger.info(f"Crossref搜索完成，找到 {len(results)} 条结果")
            return results
            
        except Exception as e:
            logger.error(f"Crossref搜索失败: {str(e)}")
            return []
    
    async def search_all_apis(
        self,
        query: str,
        max_results_per_api: int = 5,
        use_english: bool = True,
        include_pubmed: bool = True
    ) -> List[Dict[str, Any]]:
        """
        并行搜索所有API
        """
        tasks = []
        
        if include_pubmed:
            tasks.append(self.search_pubmed(query, max_results_per_api, use_english))
        
        tasks.extend([
            self.search_europe_pmc(query, max_results_per_api, use_english),
            self.search_openalex(query, max_results_per_api, use_english),
            self.search_crossref(query, max_results_per_api, use_english),
        ])
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_results = []
        for result in results:
            if isinstance(result, list):
                all_results.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"API搜索异常: {str(result)}")
        
        logger.info(f"所有API搜索完成，共找到 {len(all_results)} 条结果")
        return all_results
