"""
新闻/动态搜索服务
使用Tavily API替代爬虫获取医美行业新闻和动态
"""
import asyncio
import os
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

from knowledge_base_service.utils.logger import get_logger
from knowledge_base_service.core.http_client import HTTPClient
from knowledge_base_service.core.processors.llm_scheduler import LLMScheduler

logger = get_logger(__name__)


class NewsSearchService:
    """
    新闻/动态搜索服务
    
    支持的API：
    1. Tavily API - 专为AI设计的搜索API，适合获取新闻和动态
    2. Serper API - Google搜索API备选
    3. Bing News API - 微软新闻API备选
    """
    
    def __init__(self, tavily_api_key: Optional[str] = None, serper_api_key: Optional[str] = None):
        self.http_client = HTTPClient(timeout=30)
        self.llm = LLMScheduler()
        
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY", "")
        self.serper_api_key = serper_api_key or os.getenv("SERPER_API_KEY", "")
        
        self.tavily_endpoint = "https://api.tavily.com/search"
        self.serper_endpoint = "https://google.serper.dev/search"
        
        self.medical_aesthetics_sites = [
            "soeg.kaipuyun.cn",
            "www.nhc.gov.cn",
            "www.cma.org.cn",
            "dxy.com",
            "www.medlive.cn",
            "www.haodf.com",
            "www.youlai.cn",
            "health.sina.com.cn",
            "health.sohu.com",
            "jiankang.163.com",
            "www.39.net",
            "www.yxj.org.cn",
        ]
    
    async def __aenter__(self):
        await self.http_client.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.close()
    
    async def search_news(
        self,
        query: str,
        max_results: int = 10,
        days_back: int = 30,
        include_content: bool = True
    ) -> List[Dict[str, Any]]:
        """
        搜索新闻/动态
        
        Args:
            query: 搜索关键词
            max_results: 最大结果数
            days_back: 搜索最近多少天的新闻
            include_content: 是否包含内容摘要
        """
        results = []
        
        if self.tavily_api_key:
            logger.info(f"使用Tavily API搜索新闻: {query}")
            tavily_results = await self._search_tavily(query, max_results, days_back, include_content)
            results.extend(tavily_results)
        
        if len(results) < max_results and self.serper_api_key:
            logger.info(f"使用Serper API补充搜索: {query}")
            serper_results = await self._search_serper(query, max_results - len(results), days_back)
            results.extend(serper_results)
        
        if not results:
            logger.warning("未配置API密钥，尝试使用免费资源...")
            free_results = await self._search_free_sources(query, max_results)
            results.extend(free_results)
        
        unique_results = self._deduplicate_results(results)
        
        return unique_results[:max_results]
    
    async def _search_tavily(
        self,
        query: str,
        max_results: int,
        days_back: int,
        include_content: bool
    ) -> List[Dict[str, Any]]:
        """使用Tavily API搜索"""
        if not self.tavily_api_key:
            return []
        
        try:
            include_domains = self.medical_aesthetics_sites if "医美" in query or "医疗" in query else []
            
            payload = {
                "api_key": self.tavily_api_key,
                "query": query,
                "search_depth": "advanced",
                "include_answer": True,
                "include_raw_content": include_content,
                "max_results": max_results,
                "include_domains": include_domains if include_domains else None,
                "topic": "news",
            }
            
            data = await self.http_client.post_json(
                self.tavily_endpoint,
                json_data=payload
            )
            
            results = []
            if "results" in data:
                for item in data["results"]:
                    result = {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", ""),
                        "source": item.get("source", ""),
                        "published_date": item.get("published_date", ""),
                        "score": item.get("score", 0),
                        "search_type": "tavily",
                    }
                    results.append(result)
            
            if "answer" in data and data["answer"]:
                results.insert(0, {
                    "title": f"AI摘要: {query}",
                    "url": "",
                    "content": data["answer"],
                    "source": "Tavily AI",
                    "published_date": datetime.now().isoformat(),
                    "score": 1.0,
                    "search_type": "tavily_answer",
                })
            
            logger.info(f"Tavily搜索完成，找到 {len(results)} 条结果")
            return results
            
        except Exception as e:
            logger.error(f"Tavily搜索失败: {str(e)}")
            return []
    
    async def _search_serper(
        self,
        query: str,
        max_results: int,
        days_back: int
    ) -> List[Dict[str, Any]]:
        """使用Serper API搜索"""
        if not self.serper_api_key:
            return []
        
        try:
            headers = {
                "X-API-KEY": self.serper_api_key,
                "Content-Type": "application/json"
            }
            
            date_str = ""
            if days_back > 0:
                from datetime import datetime, timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days_back)
                date_str = f"after:{start_date.strftime('%Y-%m-%d')}"
            
            payload = {
                "q": f"{query} {date_str}".strip(),
                "gl": "cn",
                "hl": "zh-cn",
                "num": max_results,
            }
            
            data = await self.http_client.post_json(
                self.serper_endpoint,
                json_data=payload,
                headers=headers
            )
            
            results = []
            if "organic" in data:
                for item in data["organic"]:
                    result = {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "content": item.get("snippet", ""),
                        "source": item.get("displayedLink", ""),
                        "published_date": "",
                        "score": 0.5,
                        "search_type": "serper",
                    }
                    results.append(result)
            
            if "news" in data:
                for item in data["news"]:
                    result = {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "content": item.get("snippet", ""),
                        "source": item.get("source", ""),
                        "published_date": item.get("date", ""),
                        "score": 0.7,
                        "search_type": "serper_news",
                    }
                    results.append(result)
            
            logger.info(f"Serper搜索完成，找到 {len(results)} 条结果")
            return results
            
        except Exception as e:
            logger.error(f"Serper搜索失败: {str(e)}")
            return []
    
    async def _search_free_sources(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """使用免费资源搜索（备选方案）"""
        results = []
        
        try:
            from knowledge_base_service.core.content_analyzer import ContentAnalyzer
            
            async with ContentAnalyzer() as analyzer:
                search_urls = [
                    f"https://www.baidu.com/s?wd={query}&tn=news",
                    f"https://www.sogou.com/web?query={query}&ie=utf8",
                ]
                
                for url in search_urls[:1]:
                    try:
                        is_content, page_type, html = await analyzer.is_content_page(url)
                        if not is_content:
                            links = await analyzer.extract_links_from_search_page(url, max_links=max_results)
                            for link in links:
                                results.append({
                                    "title": link.get("title", ""),
                                    "url": link.get("url", ""),
                                    "content": "",
                                    "source": link.get("url", "").split("/")[2] if "/" in link.get("url", "") else "",
                                    "published_date": "",
                                    "score": 0.3,
                                    "search_type": "free_crawl",
                                })
                    except Exception as e:
                        logger.warning(f"免费资源搜索失败: {str(e)}")
                        continue
                    
                    if len(results) >= max_results:
                        break
                        
        except Exception as e:
            logger.error(f"免费资源搜索失败: {str(e)}")
        
        return results
    
    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """去重"""
        seen_urls = set()
        unique_results = []
        
        for result in results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
        
        return unique_results
    
    async def search_medical_aesthetics_news(
        self,
        topics: Optional[List[str]] = None,
        max_results_per_topic: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        搜索医美行业新闻
        
        Args:
            topics: 主题列表，如果为None则搜索默认主题
            max_results_per_topic: 每个主题的最大结果数
        """
        if topics is None:
            topics = [
                "医美行业动态",
                "医美新技术",
                "医美政策法规",
                "医美安全事件",
                "医美市场趋势",
            ]
        
        all_results = {}
        
        for topic in topics:
            logger.info(f"搜索主题: {topic}")
            results = await self.search_news(topic, max_results_per_topic)
            all_results[topic] = results
            
            await asyncio.sleep(1)
        
        return all_results
    
    async def summarize_news(self, results: List[Dict[str, Any]], topic: str) -> str:
        """
        使用LLM总结新闻内容
        """
        if not results:
            return f"未找到关于 '{topic}' 的相关新闻。"
        
        news_content = "\n\n".join([
            f"标题: {r.get('title', '')}\n来源: {r.get('source', '')}\n内容: {r.get('content', '')[:500]}"
            for r in results[:10]
        ])
        
        try:
            prompt = f"""请总结以下关于 '{topic}' 的新闻内容，提取关键信息：

{news_content}

请按以下格式输出：
1. 主要动态（3-5条）
2. 重要观点
3. 行业趋势
4. 建议关注点"""
            
            model = await self.llm.get_valid_model_for_task('detailed')
            response = await self.llm.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=2000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"总结新闻失败: {str(e)}")
            return f"总结失败: {str(e)}"
