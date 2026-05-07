import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict
import re
from urllib.parse import urljoin, urlparse
import time
import random
import os
import json

# 导入模块（移除行内导入）
from knowledge_base_service.core.processors.search_engine_api import perform_iterative_search
from knowledge_base_service.core.processors.llm_scheduler import LLMScheduler
from knowledge_base_service.core.layered_knowledge_manager import LayeredKnowledgeManager
from knowledge_base_service.core.llm_prompts.get_real_urls_prompt import get_real_urls_prompt
from knowledge_base_service.core.llm_prompts.generate_search_queries_prompt import get_generate_search_queries_prompt
from knowledge_base_service.utils.logger import get_logger

# 初始化日志记录器
logger = get_logger(__name__)

class WebCrawlerProcessor:
    """
    网页爬虫处理器类
    负责执行网页爬取任务，包括获取URL、提取内容等功能
    """
    
    def __init__(self, knowledge_base_path: str = "layered_knowledge_base"):
        """
        初始化爬虫处理器
        设置请求头和用户代理以避免被检测
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
        # 初始请求头，User-Agent会在每次请求时随机化
        headers = self.common_headers.copy()
        headers['User-Agent'] = random.choice(self.user_agents)
        self.session = aiohttp.ClientSession(headers=headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        异步上下文管理器退出时的清理工作
        """
        await self.close()  # 调用新增的close方法
    
    async def crawl_multiple(self, search_queries: List[str], max_results_per_query: int = 10, max_concurrent: int = 3) -> List[Dict]:
        """
        并发爬取多个搜索查询
        使用迭代式搜索策略，让LLM像专业资料收集者一样逐步搜索、判断和决策
        """
        logger.info(f"开始并发爬取 {len(search_queries)} 个搜索查询...")
        
        all_crawled_pages = []
        
        for i, query in enumerate(search_queries):
            logger.info(f"正在处理第 {i+1}/{len(search_queries)} 个查询: '{query}'")
            
            # 使用智能迭代式搜索策略
            crawled_pages = await self._iterative_intelligent_search(query, max_results_per_query, max_concurrent)
            
            logger.info(f"  查询 '{query}' 处理完成，成功爬取 {len(crawled_pages)} 个页面")
            all_crawled_pages.extend(crawled_pages)
        
        logger.info(f"爬取完成，共获取 {len(all_crawled_pages)} 个页面")
        return all_crawled_pages
    
    async def _crawl_single_query(self, query: str, max_results: int, max_concurrent: int = 3) -> List[Dict]:
        """
        爬取单个搜索查询
        """
        try:
            logger.info(f"  开始搜索: '{query}'")
            # print(f"  正在使用LLM生成相关网站URL...")
            # 使用搜索引擎API来获取相关网站URL
            search_results = await self._get_real_urls_from_search(query, max_results)
            
            if not search_results:
                logger.info(f"  未能找到与 '{query}' 相关的真实网站，使用模拟数据")
                search_results = await self._simulate_search(query, max_results)
            
            logger.info(f"  找到 {len(search_results)} 个相关网站")
            
            # 并发爬取多个网站以提高速度
            crawled_pages = []
            semaphore = asyncio.Semaphore(max_concurrent)  # 使用用户指定的并发数，避免对目标服务器造成过大压力
            
            async def crawl_single_site(result, idx):
                async with semaphore:
                    logger.info(f"    正在爬取第 {idx+1}/{len(search_results)} 个网站: {result['url']}")
                    logger.info(f"      网站标题: {result['title']}")
                    # 添加随机延时以避免过于频繁的请求
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    try:
                        logger.info(f"      正在获取网页内容...")
                        page_content = await self._fetch_page_content(result['url'])
                        if page_content is None:
                            logger.info(f"      无法获取内容，跳过该网站...")
                            return None
                        logger.info(f"      成功爬取内容，长度: {len(page_content)} 字符")
                        return {
                            'title': result['title'],
                            'url': result['url'],
                            'content': page_content,
                            'query_used': query
                        }
                    except Exception as e:
                        logger.error(f"      爬取失败 {result['url']}: {str(e)}")
                        return None
            
            # 并发执行爬取任务
            tasks = [crawl_single_site(result, i) for i, result in enumerate(search_results)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 过滤掉异常和None结果
            for result in results:
                if result is not None and not isinstance(result, Exception):
                    crawled_pages.append(result)
            
            logger.info(f"  查询 '{query}' 处理完成，成功爬取 {len(crawled_pages)} 个页面")
            return crawled_pages
        except Exception as e:
            logger.error(f"错误爬取查询 '{query}': {str(e)}")
            return []
    
    async def _get_real_urls_from_search(self, query: str, max_results: int) -> List[Dict]:
        """
        使用真正的搜索引擎API查找与查询相关的实际URL
        优化流程：使用简洁关键词并行搜索，提取真实内容链接，再对URL进行质量判断
        更适合医学、医美、美容等专业领域
        """
        
        logger.info(f"开始智能搜索: {query}")
        
        # 第一步：生成简洁的相关查询
        logger.info(f"第一步：生成简洁的相关查询")
        llm = LLMScheduler()
        
        # 为医学、医美、美容领域生成简洁的专业查询（避免过长的查询）
        professional_queries = await llm.generate_search_queries(
            topic=query,
            requirements=f"""针对医学、医美、美容领域，生成简洁的专业化搜索查询词。
            查询词应该简短但专业，例如：
            - 核心专业术语
            - 疾病/症状名称
            - 药品/器械名称
            - 治疗方法名称
            - 不要超过4个词""",
            num_queries=3
        )
        
        # 包含原始查询的核心部分
        # 提取原始查询的核心关键词
        core_query = query.split()[0] if query.split() else query  # 使用第一个词作为核心查询
        all_queries = [core_query] + professional_queries[:2]  # 总共最多3个简洁查询
        logger.info(f"生成了 {len(all_queries)} 个简洁查询: {all_queries}")
        
        # 第二步：并行搜索所有查询，获取搜索结果页面
        logger.info(f"第二步：并行搜索所有查询")
        
        # 并行执行搜索
        search_tasks = []
        for q in all_queries:
            search_tasks.append(perform_iterative_search(q, max_results))
        
        all_search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # 收集所有搜索结果中的URL
        all_raw_urls = set()  # 使用集合去重
        for i, results in enumerate(all_search_results):
            if not isinstance(results, Exception):
                for result in results:
                    if 'url' in result and result['url']:
                        all_raw_urls.add(result['url'])
        
        logger.info(f"从 {len(all_queries)} 个查询中收集到 {len(all_raw_urls)} 个唯一URL")
        
        # 第三步：使用LLM从搜索结果页面中识别真实内容链接（过滤广告）
        logger.info(f"第三步：使用LLM识别真实内容链接")
        content_urls = await self._identify_content_urls(list(all_raw_urls))
        
        logger.info(f"识别出 {len(content_urls)} 个真实内容链接")
        
        # 第四步：对识别出的内容链接进行质量判断和内容提取
        logger.info(f"第四步：对内容链接进行质量判断")
        detailed_results = []
        
        # 限制处理数量以控制时间和资源消耗
        urls_to_process = content_urls[:max_results * 2]  # 处理适量URL以平衡效率和质量
        
        # 优先处理专业医学网站
        medical_urls = []
        other_urls = []
        
        for url in urls_to_process:
            url_lower = url.lower()
            if any(domain in url_lower for domain in [
                'cnki.net', 'wanfangdata', 'vipinfo', 'pubmed', 'nejm', 'lancet',
                'nmpa.gov.cn', 'cmaph.org', 'cma.org.cn', 'cpma.org.cn',
                'dxy.cn', 'medlive.cn', 'cmtopdr.com',
                'clinicaltrials.gov', 'fda.gov', 'nhs.uk',
                '丁香园', '医脉通', '好大夫', '寻医问药',
                'health', 'medical', 'clinic', 'hospital', 'doctor',
                'dermatology', 'cosmetic', 'esthetic', 'beauty', 'aesthetic',
                'patent', 'sipo', 'uspto'
            ]):
                medical_urls.append(url)
            else:
                other_urls.append(url)
        
        # 优先处理医学专业网站
        prioritized_urls = medical_urls + other_urls
        logger.info(f"优先处理 {len(medical_urls)} 个医学专业网站链接")
        
        for i, url in enumerate(prioritized_urls):
            logger.info(f"  正在处理第 {i+1}/{len(prioritized_urls)} 个URL: {url}")
            
            try:
                # 获取页面内容
                page_content = await self._fetch_page_content(url)
                
                if page_content and len(page_content.strip()) > 50:  # 确保内容有意义
                    logger.info(f"    成功获取内容，长度: {len(page_content)} 字符")
                    
                    # 使用LLM验证内容相关性和质量
                    relevance_check = await llm.verify_content_quality(page_content, url, query)
                    
                    if relevance_check.get('is_relevant', True) and relevance_check.get('quality_score', 0) > 50:  # 适度降低质量门槛以获得更多结果
                        logger.info(f"    内容与查询相关且质量合格，添加到结果")
                        
                        detailed_results.append({
                            'url': url,
                            'title': relevance_check.get('title', url),  # 如果LLM提供了标题则使用
                            'content': page_content,
                            'relevance_score': relevance_check.get('relevance_score', 80),
                            'quality_score': relevance_check.get('quality_score', 70)
                        })
                        
                        # 如果已达到所需数量，提前退出
                        if len(detailed_results) >= max_results:
                            logger.info(f"已达到所需数量 {max_results}，提前退出")
                            break
                    else:
                        logger.info(f"    内容质量不够高或不相关，跳过")
                else:
                    logger.info(f"    无法获取有效内容，跳过")
                        
            except Exception as e:
                logger.error(f"    处理URL失败 {url}: {str(e)}")
        
        logger.info(f"最终获取到 {len(detailed_results)} 个高质量内容，目标数量: {max_results}")
        
        # 如果没有获取到任何内容，返回空列表
        if len(detailed_results) == 0:
            logger.warning("未获取到任何高质量内容")
            return []
            
        return detailed_results[:max_results]

    async def _identify_content_urls(self, urls: List[str]) -> List[str]:
        """
        使用LLM识别真实内容链接，过滤广告和其他非内容链接
        优先保留医学、医美、美容领域的专业内容链接
        """
        if not urls:
            return []
        
        llm = LLMScheduler()
        
        # 首先使用基于域名的快速过滤，找出可能的医学专业网站
        medical_urls = []
        other_urls = []
        
        for url in urls:
            url_lower = url.lower()
            # 检查是否属于医学、医美专业领域
            is_medical_source = any(domain in url_lower for domain in [
                'cnki.net', 'wanfangdata', 'vipinfo', 'vip.com',  # 知网、万方、维普
                'pubmed', 'nejm', 'lancet', 'sciencedirect', 'nature.com', 'cell.com',  # 国际期刊
                'nmpa.gov.cn', 'fda.gov', 'nhs.uk', 'gov.cn',  # 监管机构
                'cmaph.org', 'cma.org.cn', 'cpma.org.cn', 'asm.org',  # 专业协会
                'dxy.cn', 'medlive.cn', 'cmtopdr.com', '丁香园', '医脉通',  # 医学资讯平台
                'health', 'medical', 'medicine', 'hospital', 'clinic', 'doctor',  # 医疗相关
                'dermatology', 'derma', 'skin', 'cosmetic', 'esthetic', 'beauty', 'aesthetic',  # 皮肤美容
                'patent', 'sipo', 'uspto', 'freepatentsonline',  # 专利
                'clinicaltrials', 'nih.gov',  # 临床试验
                'who.int', 'cdc.gov',  # 卫生组织
                'journal', 'academic', 'research', 'study', 'guideline', 'protocol',  # 学术相关
                'pharmaceutical', 'therapy', 'treatment', 'procedure', 'symptom', 'disease',  # 医疗术语
                'dermatologist', 'plastic', 'surgery', 'surgical', 'oncology', 'cardiology',  # 专科术语
                'biomed', 'bio', 'science', 'lab', 'laboratory', 'scientific',  # 生物科学
                'medicalcenter', 'hospital', 'clinic', 'physician', 'physiology',  # 医疗机构
                'wenku.so.com', 'doc.paperpass.com.cn', 'max.book118.com'  # 文档分享网站（可能包含学术文档）
            ])
            
            # 排除明显的非专业网站
            is_excluded = any(exclude in url_lower for exclude in [
                'baidu.com', 'so.com', 'sogou.com', 'bing.com', 'google.com',
                'weibo', 'zhihu', 'tieba', 'blog', 'shop', 'mall', 'taobao',
                'jd.com', 'tmall.com', 'ad.', 'ads.', 'click?',
                'track?', 'redirect?', 'affiliate', 'promotion', 'buy', 'sale',
                'groupon', 'deal', 'coupon', 'discount', 'offer',
                'video', 'youtube', 'tiktok', 'instagram', 'facebook', 'twitter',  # 视频社交媒体
                'forum', 'bbs', 'community', 'discuss', 'thread',  # 论坛
                'news', 'toutiao', 'qq.com', '163.com', 'sina.com'  # 新闻门户（除非是专业医疗新闻）
            ])
            
            if is_medical_source and not is_excluded:
                medical_urls.append(url)
            elif not is_excluded:  # 非专业但非明确排除的URL
                other_urls.append(url)
        
        # 将医学专业URL放在前面，优先处理
        prioritized_urls = medical_urls + other_urls
        
        logger.info(f"初步筛选: {len(medical_urls)} 个医学专业URL, {len(other_urls)} 个其他URL")
        
        # 如果没有医学专业URL，但有其他URL，尝试从其他URL中识别可能的医学内容
        if not medical_urls and other_urls:
            logger.info("没有找到医学专业URL，尝试从其他URL中识别可能的医学内容")
            # 检查其他URL中是否包含医学关键词
            for url in other_urls[:]:  # 使用副本进行遍历
                url_lower = url.lower()
                contains_medical_keywords = any(keyword in url_lower for keyword in [
                    'medical', 'health', 'clinic', 'hospital', 'doctor', 'dermatology', 
                    'derma', 'skin', 'cosmetic', 'esthetic', 'beauty', 'aesthetic',
                    'therapy', 'treatment', 'procedure', 'symptom', 'disease',
                    'dermatologist', 'plastic', 'surgery', 'oncology', 'cardiology',
                    'pharmaceutical', 'medicine', 'biomed', 'bio', 'research', 'study'
                ])
                
                if contains_medical_keywords:
                    medical_urls.append(url)
                    other_urls.remove(url)
        
        # 将URL列表分成小批次处理，避免超出LLM的上下文长度
        batch_size = 15  # 减小批次大小以提高LLM处理准确性
        content_urls = set()
        
        for i in range(0, len(prioritized_urls), batch_size):
            batch = prioritized_urls[i:i + batch_size]
            
            # 创建提示，让LLM识别真实内容链接，特别关注医学、医美领域
            prompt = f"""
            请分析以下URL列表，识别出哪些是医学、医美、美容领域的专业内容页面链接，
            如学术论文、临床研究、医学指南、药品说明书、医疗器械信息、专业期刊文章、
            政府医疗法规、行业协会指南、专利文献等。

            URL列表:
            {chr(10).join([f"- {url}" for url in batch])}

            请返回一个JSON数组，只包含医学、医美、美容领域的专业内容页面URL：
            [
                "https://medical-journal.org/article1",
                "https://clinicaltrials.gov/study1",
                ...
            ]

            优先考虑以下专业医学、医美、美容领域的网站：
            - 中国知网 (cnki.net)、万方数据、维普资讯
            - PubMed、NEJM、Lancet、ScienceDirect等国际医学期刊
            - 国家药品监督管理局 (nmpa.gov.cn)、FDA (fda.gov)、NHS (nhs.uk)
            - 中华医学会、中国医师协会、ASM等专业协会网站
            - 三甲医院官网、医学院校网站
            - 专业医学资讯平台（如丁香园、医脉通）
            - 医疗器械信息网
            - 美容整形专业网站
            - 皮肤科专业网站
            - 医美机构官方网站
            - 专利数据库（特别是医疗器械和药品专利）
            - WHO、CDC等卫生组织网站
            - 临床试验注册网站
            - 学术文档分享网站（如wenku.so.com等，可能包含学术论文）

            排除以下类型的链接：
            - 广告和推广链接
            - 社交媒体和个人博客
            - 电商平台商品页面
            - 导航和聚合页面
            - 明显的商业推广页面
            - 论坛和讨论区
            """

            try:
                model = await llm.get_valid_model_for_task('content_analysis')
                response = await llm.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,  # 降低温度以获得更一致的结果
                    max_tokens=2000
                )
                
                content = response.choices[0].message.content.strip()
                
                # 解析LLM返回的JSON
                try:
                    import json
                    batch_content_urls = json.loads(content)
                    if isinstance(batch_content_urls, list):
                        content_urls.update(batch_content_urls)
                except json.JSONDecodeError:
                    # 如果无法解析JSON，尝试提取URL
                    import re
                    found_urls = re.findall(r'https?://[^\s"\'<>]+', content)
                    content_urls.update(found_urls)
                    
            except Exception as e:
                logger.error(f"识别内容URL时LLM调用出错: {str(e)}")
                # 如果LLM调用失败，使用基于域名的过滤作为后备
                for url in batch:
                    url_lower = url.lower()
                    is_medical_source = any(domain in url_lower for domain in [
                        'cnki.net', 'wanfangdata', 'vipinfo', 'vip.com',
                        'pubmed', 'nejm', 'lancet', 'sciencedirect', 'nature.com', 'cell.com',
                        'nmpa.gov.cn', 'fda.gov', 'nhs.uk', 'gov.cn',
                        'cmaph.org', 'cma.org.cn', 'cpma.org.cn', 'asm.org',
                        'dxy.cn', 'medlive.cn', 'cmtopdr.com', '丁香园', '医脉通',
                        'health', 'medical', 'medicine', 'hospital', 'clinic', 'doctor',
                        'dermatology', 'derma', 'skin', 'cosmetic', 'esthetic', 'beauty', 'aesthetic',
                        'patent', 'sipo', 'uspto', 'freepatentsonline',
                        'clinicaltrials', 'nih.gov',
                        'who.int', 'cdc.gov',
                        'journal', 'academic', 'research', 'study', 'guideline', 'protocol',
                        'pharmaceutical', 'therapy', 'treatment', 'procedure', 'symptom', 'disease',
                        'dermatologist', 'plastic', 'surgery', 'surgical', 'oncology', 'cardiology',
                        'biomed', 'bio', 'science', 'lab', 'laboratory', 'scientific',
                        'medicalcenter', 'hospital', 'clinic', 'physician', 'physiology',
                        'wenku.so.com', 'doc.paperpass.com.cn', 'max.book118.com'  # 文档分享网站
                    ])
                    
                    is_excluded = any(exclude in url_lower for exclude in [
                        'baidu.com', 'so.com', 'sogou.com', 'bing.com', 'google.com',
                        'weibo', 'zhihu', 'tieba', 'blog', 'shop', 'mall', 'taobao',
                        'jd.com', 'tmall.com', 'ad.', 'ads.', 'click?',
                        'track?', 'redirect?', 'affiliate', 'promotion', 'buy', 'sale',
                        'groupon', 'deal', 'coupon', 'discount', 'offer'
                    ])
                    
                    if is_medical_source and not is_excluded:
                        content_urls.add(url)
        
        # 最终过滤，确保只返回有效的医学专业URL
        final_content_urls = []
        for url in content_urls:
            if url.startswith(('http://', 'https://')):
                url_lower = url.lower()
                is_medical_source = any(domain in url_lower for domain in [
                    'cnki.net', 'wanfangdata', 'vipinfo', 'vip.com',
                    'pubmed', 'nejm', 'lancet', 'sciencedirect', 'nature.com', 'cell.com',
                    'nmpa.gov.cn', 'fda.gov', 'nhs.uk', 'gov.cn',
                    'cmaph.org', 'cma.org.cn', 'cpma.org.cn', 'asm.org',
                    'dxy.cn', 'medlive.cn', 'cmtopdr.com', '丁香园', '医脉通',
                    'health', 'medical', 'medicine', 'hospital', 'clinic', 'doctor',
                    'dermatology', 'derma', 'skin', 'cosmetic', 'esthetic', 'beauty', 'aesthetic',
                    'patent', 'sipo', 'uspto', 'freepatentsonline',
                    'clinicaltrials', 'nih.gov',
                    'who.int', 'cdc.gov',
                    'journal', 'academic', 'research', 'study', 'guideline', 'protocol',
                    'pharmaceutical', 'therapy', 'treatment', 'procedure', 'symptom', 'disease',
                    'dermatologist', 'plastic', 'surgery', 'surgical', 'oncology', 'cardiology',
                    'biomed', 'bio', 'science', 'lab', 'laboratory', 'scientific',
                    'medicalcenter', 'hospital', 'clinic', 'physician', 'physiology',
                    'wenku.so.com', 'doc.paperpass.com.cn', 'max.book118.com'  # 文档分享网站
                ])
                
                if is_medical_source:
                    final_content_urls.append(url)
        
        logger.info(f"最终识别出 {len(final_content_urls)} 个医学专业内容链接")
        return final_content_urls
    
    async def _simplify_query(self, query: str) -> str:
        """
        简化查询词，提取核心概念
        """
        # 简单的规则：移除修饰词，只保留核心名词
        # 在实际应用中，这里可以集成NLP工具进行更复杂的处理
        import re
        
        # 移除一些常见的修饰词
        modifiers = ['如何', '怎样', '怎么', '什么', '为什么', '哪个', '哪里', '何时', '谁', '最', '非常', '特别', '十分', '比较', '相对']
        
        simplified = query
        for modifier in modifiers:
            simplified = simplified.replace(modifier, '').strip()
        
        # 清理多余的空格
        simplified = re.sub(r'\s+', ' ', simplified).strip()
        
        # 如果简化后的查询为空或太短，返回原查询
        if not simplified or len(simplified) < 2:
            return query
        
        return simplified
    
    async def _generate_query_variants(self, query: str) -> List[str]:
        """
        生成查询变体
        """
        variants = [
            query,
            f"什么是{query}",
            f"{query}介绍",
            f"{query}定义",
            f"{query}含义",
            f"{query}原理",
            f"{query}作用",
            f"{query}好处",
            f"{query}方法",
            f"{query}步骤"
        ]
        
        # 返回非重复的变体
        return list(dict.fromkeys(variants))  # 去重但保持顺序
    
    async def _evaluate_search_results_quality(self, query: str, results: List[Dict], llm: LLMScheduler) -> Dict:
        """
        使用LLM评估搜索结果质量并决定下一步操作
        """
        # 构建结果摘要
        results_summary = []
        for i, result in enumerate(results[:5]):  # 只评估前5个结果
            results_summary.append(f"{i+1}. 标题: {result.get('title', '无标题')}, URL: {result.get('url', '无URL')}")
        
        evaluation_prompt = f"""
        请评估以下针对查询 '{query}' 的搜索结果质量：

        搜索结果摘要:
        {chr(10).join(results_summary)}

        请从以下几个维度评估这些结果：
        1. 相关性：结果与查询的相关程度
        2. 权威性：结果来源的可信度
        3. 完整性：结果是否提供了充分的信息
        4. 新颖性：结果是否提供了独特视角

        请返回一个JSON对象，包含以下字段：
        {{
            "overall_quality_score": 0-100之间的分数,
            "relevance_score": 0-100之间的分数,
            "authoritativeness_score": 0-100之间的分数,
            "completeness_score": 0-100之间的分数,
            "novelty_score": 0-100之间的分数,
            "quality_issues": ["问题1", "问题2", ...],
            "recommendations": ["建议1", "建议2", ...],
            "next_action": "refine_search|broaden_search|deepen_search|accept_results|try_alternative_approach",
            "new_search_queries": ["query1", "query2", ...] // 如果需要新的搜索查询
        }}
        """
        
        try:
            model = await llm.get_valid_model_for_task('research')
            response = await llm.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": evaluation_prompt}],
                temperature=0.4,  # 较低的温度以获得一致的评估
                max_tokens=1500
            )
            
            content = response.choices[0].message.content.strip()
            
            try:
                evaluation = json.loads(content)
                return evaluation
            except json.JSONDecodeError:
                logger.warning(f"LLM返回的不是有效JSON格式: {content[:200]}...")
                # 返回默认评估
                return {
                    "overall_quality_score": 50,
                    "relevance_score": 50,
                    "authoritativeness_score": 50,
                    "completeness_score": 50,
                    "novelty_score": 50,
                    "quality_issues": ["无法解析LLM评估结果"],
                    "recommendations": ["尝试其他搜索策略"],
                    "next_action": "refine_search",
                    "new_search_queries": [query]
                }
        except Exception as e:
            logger.error(f"调用LLM评估搜索结果质量时出错: {str(e)}")
            # 返回默认评估
            return {
                "overall_quality_score": 50,
                "relevance_score": 50,
                "authoritativeness_score": 50,
                "completeness_score": 50,
                "novelty_score": 50,
                "quality_issues": [str(e)],
                "recommendations": ["尝试其他搜索策略"],
                "next_action": "refine_search",
                "new_search_queries": [query]
            }
    
    async def _perform_intelligent_search_cycle(self, query: str, max_results: int, llm: LLMScheduler) -> List[Dict]:
        """
        执行智能搜索周期，多次调用LLM评估结果质量并决定下一步操作
        """
        all_results = []
        seen_urls = set()
        search_round = 1
        max_search_rounds = 3  # 最多进行3轮搜索
        
        current_query = query
        
        while len(all_results) < max_results and search_round <= max_search_rounds:
            logger.info(f"搜索轮次 {search_round}: 使用查询 '{current_query}'")
            
            # 执行当前查询
            round_results = await perform_iterative_search(current_query, max_results)
            
            # 添加新结果，避免重复
            for result in round_results:
                if result.get('url') and result.get('url') not in seen_urls and len(all_results) < max_results:
                    all_results.append({
                        'url': result.get('url'),
                        'title': result.get('title', '无标题')
                    })
                    seen_urls.add(result.get('url'))
            
            logger.info(f"第 {search_round} 轮搜索获得 {len(round_results)} 个结果，累计 {len(all_results)} 个结果")
            
            # 如果已满足需求，退出循环
            if len(all_results) >= max_results:
                break
            
            # 评估当前结果质量
            if all_results:
                evaluation = await self._evaluate_search_results_quality(current_query, all_results, llm)
                
                logger.info(f"搜索结果质量评估 - 总体评分: {evaluation.get('overall_quality_score', 0)}, "
                           f"下一步操作: {evaluation.get('next_action', 'unknown')}")
                
                # 根据评估结果决定下一步操作
                next_action = evaluation.get('next_action', 'refine_search')
                
                if next_action == 'accept_results':
                    logger.info("LLM建议接受当前结果")
                    break
                elif next_action == 'refine_search' or next_action == 'broaden_search':
                    # 使用LLM建议的新查询
                    new_queries = evaluation.get('new_search_queries', [])
                    if new_queries:
                        current_query = new_queries[0]  # 使用第一个建议的查询
                        logger.info(f"使用LLM建议的新查询: '{current_query}'")
                    else:
                        # 如果没有建议新查询，尝试变体
                        variants = await self._generate_query_variants(current_query)
                        if variants:
                            current_query = variants[search_round % len(variants)]
                elif next_action == 'deepen_search':
                    # 尝试更深入的搜索
                    current_query = f"{current_query} 详细信息"
                elif next_action == 'try_alternative_approach':
                    # 尝试替代方法
                    variants = await self._generate_query_variants(current_query)
                    if variants:
                        current_query = variants[search_round % len(variants)]
                else:
                    # 默认行为：细化搜索
                    current_query = f"{current_query} 相关信息"
            else:
                # 如果没有结果，尝试查询变体
                variants = await self._generate_query_variants(current_query)
                if variants:
                    current_query = variants[search_round % len(variants)]
            
            search_round += 1
        
        return all_results
    
    async def _simulate_search(self, query: str, max_results: int) -> List[Dict]:
        """
        模拟搜索结果（当LLM未返回有效URL时的备选方案）
        """
        # 定义查询变体，以增加找到相关内容的机会
        query_variants = [
            query,  # 原始查询
            f"{query} 是什么",  # 定义类查询
            f"{query} 怎么做",  # 方法类查询
            f"{query} 详细介绍",  # 详情类查询
            f"{query} 最新进展",  # 进展类查询
            f"{query} 作用",  # 作用类查询
            f"{query} 好处",  # 好处类查询
            f"{query} 原理",  # 原理类查询
        ]
        
        # 使用更多真实、可访问的URL进行模拟，以便实际爬取
        sample_results = []
        
        for variant in query_variants:
            encoded_variant = variant.replace(' ', '%20').replace('%20', '_')
            encoded_plus = variant.replace(' ', '+')
            encoded_q = variant.replace(' ', '%20')
            
            sample_results.extend([
                {
                    'title': f"百度百科 - {variant}",
                    'url': f"https://baike.baidu.com/item/{encoded_variant}"
                },
                {
                    'title': f"知乎问答 - {variant}",
                    'url': f"https://www.zhihu.com/search?q={encoded_q}&type=content"
                },
                {
                    'title': f"维基百科 - {variant}",
                    'url': f"https://zh.wikipedia.org/wiki/Special:Search?search={encoded_plus}"
                },
                {
                    'title': f"百度知道 - {variant}",
                    'url': f"https://zhidao.baidu.com/search?word={encoded_q}"
                },
                {
                    'title': f"360搜索 - {variant}",
                    'url': f"https://www.so.com/s?q={encoded_q}"
                },
                {
                    'title': f"搜狗搜索 - {variant}",
                    'url': f"https://www.sogou.com/web?query={encoded_q}"
                },
                {
                    'title': f"必应搜索 - {variant}",
                    'url': f"https://cn.bing.com/search?q={encoded_plus}"
                },
                {
                    'title': f"夸克搜索 - {variant}",
                    'url': f"https://quark.sm.cn/s?q={encoded_q}"
                },
                {
                    'title': f"头条搜索 - {variant}",
                    'url': f"https://so.toutiao.com/search/?keyword={encoded_q}"
                },
                {
                    'title': f"微信公众号 - {variant}",
                    'url': f"https://weixin.sogou.com/weixin?type=2&query={encoded_q}"
                },
                {
                    'title': f"豆瓣 - {variant}",
                    'url': f"https://www.douban.com/search?q={encoded_q}"
                },
                {
                    'title': f"微博 - {variant}",
                    'url': f"https://s.weibo.com/weibo?q={encoded_q}"
                },
                {
                    'title': f"CSDN技术文章 - {variant}",
                    'url': f"https://so.csdn.net/api/search?q={encoded_q}"
                },
                {
                    'title': f"中国知网 - {variant}",
                    'url': f"https://kns.cnki.net/kns8/DefaultResult/Index?kw={encoded_q}"
                },
                {
                    'title': f"万方数据 - {variant}",
                    'url': f"http://www.wanfangdata.com.cn/search/searchList.do?searchWord={encoded_q}"
                }
            ])
        
        # 根据需要的数量返回结果
        results = []
        for i in range(min(max_results, len(sample_results))):
            result = sample_results[i % len(sample_results)].copy()
            results.append(result)
        
        # 如果还需要更多结果，循环使用现有结果
        while len(results) < max_results:
            index = len(results) % len(sample_results)
            next_result = sample_results[index].copy()
            # 添加补充标记
            next_result['title'] = f"{next_result['title']} - 补充{len(results) - len(sample_results) + 1}"
            results.append(next_result)
        
        return results[:max_results]
    
    async def _fetch_page_content(self, url: str) -> str:
        """
        获取并提取网页内容，带有反爬虫机制和重试逻辑
        """
        # 确保会话存在
        if not self.session:
            headers = self.common_headers.copy()
            headers['User-Agent'] = random.choice(self.user_agents)
            self.session = aiohttp.ClientSession(headers=headers)
        
        # 尝试不同的策略来获取内容
        strategies = [
            self._try_basic_request,
            self._try_with_referrer,
            self._try_with_different_ua,
            self._try_with_delay,
            self._try_with_cookies_and_session,
            self._try_with_proxy_like_headers,
            self._try_with_headless_browser  # 添加无头浏览器策略作为最后手段
        ]
        
        for i, strategy in enumerate(strategies):
            try:
                logger.info(f"  尝试策略 {i+1}/{len(strategies)}: {strategy.__name__} for {url}")
                content = await strategy(url)
                
                if content and len(content.strip()) > 50:  # 检查内容是否有效
                    logger.info(f"  策略 {strategy.__name__} 成功获取内容，长度: {len(content)} 字符")
                    
                    # 使用LLM验证内容质量
                    llm = LLMScheduler()
                    verification = await llm.verify_content_quality(content, url, "")
                    
                    if verification.get('is_valid', False) and verification.get('quality_score', 0) > 30:
                        # 额外使用LLM判断是否为具体知识页面而非搜索结果页面
                        is_specific_content = await self._is_specific_content_page(content, url)
                        
                        if is_specific_content:
                            logger.info(f"成功获取有效内容 from {url} (具体知识页面)")
                            return content
                        else:
                            logger.info(f"内容为搜索结果页面或非具体知识页面 from {url}, 尝试其他策略")
                            continue
                    else:
                        logger.info(f"内容质量不佳 from {url} (评分: {verification.get('quality_score', 0)}), 尝试其他策略")
                        continue
                else:
                    logger.info(f"获取到空内容或内容太少 from {url}, 尝试其他策略")
                    continue
            except Exception as e:
                logger.error(f"策略 {strategy.__name__} 失败 for {url}: {str(e)}")
                continue
        
        logger.error(f"所有策略都失败 for {url}")
        return None

    async def close(self):
        """
        关闭客户端会话以释放资源
        """
        if self.session:
            await self.session.close()

    async def _is_specific_content_page(self, content: str, url: str) -> bool:
        """
        使用LLM判断页面是否为具体知识内容页面，而非搜索结果页面
        """
        llm = LLMScheduler()
        
        # 创建一个提示，询问LLM这个页面是否包含具体知识内容
        prompt = f"""
        请分析以下网页内容，判断它是否为具体的知识内容页面，还是仅仅是搜索结果页面或其他导航页面。

        网址: {url}
        
        网页内容:
        {content[:2000]}  # 限制内容长度以节省token
        
        请回答以下问题：
        1. 这是一个具体的知识内容页面吗？（如文章、教程、产品说明、研究报告等）
        2. 这是一个搜索结果页面吗？（列出多个链接供用户选择）
        3. 这是一个导航页面吗？（如首页、菜单页等）
        
        请返回一个JSON对象，包含以下字段：
        {{
            "is_specific_content": true/false,
            "confidence": 0-100之间的置信度分数,
            "reason": "简要说明判断理由",
            "page_type": "具体内容页|搜索结果页|导航页|其他"
        }}
        """
        
        try:
            model = await llm.get_valid_model_for_task('content_analysis')
            response = await llm.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            
            # 尝试解析LLM返回的JSON
            try:
                import json
                result = json.loads(content)
                return result.get('is_specific_content', False) and result.get('confidence', 0) > 60
            except json.JSONDecodeError:
                # 如果无法解析JSON，根据返回内容判断
                content_lower = content.lower()
                if 'is_specific_content' in content_lower or '"true"' in content_lower:
                    return True
                elif 'is_search_results' in content_lower or 'search result' in content_lower:
                    return False
                else:
                    # 默认情况下，如果包含肯定的词汇则认为是具体内容页
                    positive_indicators = ['是', 'true', 'specific', 'content', 'article', 'tutorial', 'report', 'information']
                    negative_indicators = ['否', 'false', 'search', 'result', '导航', 'menu', 'list', 'links']
                    
                    pos_count = sum(1 for indicator in positive_indicators if indicator in content_lower)
                    neg_count = sum(1 for indicator in negative_indicators if indicator in content_lower)
                    
                    return pos_count > neg_count
                    
        except Exception as e:
            logger.error(f"调用LLM判断页面类型时出错: {str(e)}")
            # 出错时默认认为不是具体内容页，以避免误判
            return False
    
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

    async def _iterative_intelligent_search(self, initial_query: str, max_results: int, max_concurrent: int) -> List[Dict]:
        """
        迭代式智能搜索 - 像专业资料收集者一样逐步搜索、判断和决策
        """
        logger.info(f"开始迭代式智能搜索: {initial_query}")
        
        all_crawled_pages = []
        search_history = []  # 记录搜索历史
        llm = LLMScheduler()
        
        # 初始搜索
        current_query = initial_query
        iteration = 0
        max_iterations = 10  # 设置最大迭代次数
        
        while len(all_crawled_pages) < max_results and iteration < max_iterations:
            logger.info(f"迭代 {iteration + 1}: 搜索查询 '{current_query}'")
            
            # 执行当前查询
            search_results = await self._get_real_urls_from_search(current_query, max_results)
            
            if not search_results:
                logger.info(f"  当前查询未找到结果，尝试使用LLM生成替代查询...")
                # 让LLM生成替代查询
                alternative_queries = await llm.generate_search_queries(
                    topic=initial_query,
                    requirements="生成一个相关的搜索查询，可以从互联网上找到相关信息",
                    num_queries=3
                )
                
                if alternative_queries:
                    current_query = alternative_queries[0]
                    logger.info(f"  使用LLM生成的替代查询: '{current_query}'")
                    iteration += 1
                    continue
                else:
                    logger.info(f"  无法生成有效的替代查询，尝试简化原始查询...")
                    # 尝试简化查询
                    current_query = await self._simplify_query(current_query)
                    if current_query == initial_query:  # 如果无法进一步简化
                        break
                    iteration += 1
                    continue
            
            # 对搜索结果进行评估和筛选
            logger.info(f"  找到 {len(search_results)} 个搜索结果，开始评估...")
            
            # 评估搜索结果质量
            search_evaluation = await llm.evaluate_search_results(
                query=current_query,
                search_results=search_results,
                target_count=max_results - len(all_crawled_pages)
            )
            
            logger.info(f"  LLM评估结果: {search_evaluation.get('summary', '无摘要')}")
            
            # 根据评估结果决定下一步行动
            next_action = search_evaluation.get('next_action', 'process_results')
            
            if next_action == 'process_results':
                # 处理当前搜索结果
                processed_pages = await self._process_search_results(
                    search_results, 
                    max_results - len(all_crawled_pages),
                    max_concurrent,
                    initial_query
                )
                
                all_crawled_pages.extend(processed_pages)
                
                # 让LLM决定是否需要更多搜索
                decision = await llm.decide_next_search_action(
                    initial_query=initial_query,
                    collected_results=all_crawled_pages,
                    target_count=max_results,
                    search_history=search_history
                )
                
                if decision.get('continue_search', False):
                    # 根据LLM建议生成新查询
                    new_queries = decision.get('new_queries', [])
                    if new_queries:
                        current_query = new_queries[0]
                        logger.info(f"  根据LLM建议使用新查询: '{current_query}'")
                    else:
                        # 生成相关查询
                        related_queries = await llm.generate_search_queries(
                            topic=initial_query,
                            requirements="生成一个与原始主题相关但角度不同的搜索查询",
                            num_queries=2
                        )
                        if related_queries:
                            current_query = related_queries[0]
                        else:
                            break
                else:
                    logger.info("  LLM建议停止搜索，已收集足够信息")
                    break
                    
            elif next_action == 'refine_query':
                # 精炼查询
                refined_query = search_evaluation.get('refined_query', current_query)
                if refined_query != current_query:
                    logger.info(f"  根据评估结果精炼查询: '{refined_query}'")
                    current_query = refined_query
                else:
                    # 尝试生成变体查询
                    query_variants = await self._generate_query_variants(current_query)
                    if query_variants:
                        current_query = query_variants[0]
                    else:
                        break
                        
            elif next_action == 'broaden_query':
                # 扩展查询范围
                broadened_query = search_evaluation.get('broadened_query', current_query)
                if broadened_query != current_query:
                    logger.info(f"  根据评估结果扩展查询: '{broadened_query}'")
                    current_query = broadened_query
                else:
                    # 尝试更通用的查询
                    general_query = f"{initial_query.split()[0] if initial_query.split() else initial_query} 概述" if ' ' in initial_query else f"{initial_query} 是什么"
                    current_query = general_query
                    
            elif next_action == 'change_approach':
                # 改变搜索方法
                logger.info("  尝试改变搜索方法...")
                new_queries = search_evaluation.get('alternative_queries', [])
                if new_queries:
                    current_query = new_queries[0]
                else:
                    # 尝试完全不同的角度
                    angle_queries = await llm.generate_search_queries(
                        topic=initial_query,
                        requirements="从一个完全不同的角度或领域生成搜索查询，但仍与原始主题相关",
                        num_queries=2
                    )
                    if angle_queries:
                        current_query = angle_queries[0]
                    else:
                        break
            
            # 更新搜索历史
            search_history.append({
                'query': current_query,
                'results_count': len(search_results),
                'pages_collected': len([p for p in all_crawled_pages if p.get('query_used') == initial_query]),
                'iteration': iteration
            })
            
            iteration += 1
        
        logger.info(f"迭代式搜索完成，总共收集了 {len(all_crawled_pages)} 个页面")
        return all_crawled_pages
    
    async def _process_search_results(self, search_results: List[Dict], max_to_process: int, max_concurrent: int, original_query: str) -> List[Dict]:
        """
        处理搜索结果，爬取内容，并将有效内容添加到知识库
        现在搜索结果已经包含内容，因此只需验证和存储
        """
        logger.info(f"处理 {len(search_results)} 个搜索结果，最多处理 {max_to_process} 个")
        
        # 限制处理数量
        limited_results = search_results[:max_to_process]
        
        # 处理结果（现在搜索结果已经包含内容）
        processed_pages = []
        
        for i, result in enumerate(limited_results):
            logger.info(f"    正在处理第 {i+1}/{len(limited_results)} 个结果: {result.get('title', '无标题')}")
            
            # 检查结果是否包含内容
            if 'content' in result and result['content']:
                content = result['content']
                url = result['url']
                title = result.get('title', '无标题')
                
                logger.info(f"      发现预提取内容，长度: {len(content)} 字符")
                
                # 使用LLM验证内容相关性（如果尚未验证）
                llm = LLMScheduler()
                
                # 检查是否已有相关性评分
                if 'relevance_score' not in result or 'quality_score' not in result:
                    logger.info(f"      内容尚未验证，正在进行相关性检查...")
                    relevance_check = await llm.verify_content_quality(content, url, original_query)
                else:
                    relevance_check = {
                        'is_relevant': result.get('relevance_score', 70) > 50,
                        'relevance_score': result.get('relevance_score', 70),
                        'quality_score': result.get('quality_score', 70)
                    }
                
                if relevance_check.get('is_relevant', True):  # 默认认为相关
                    logger.info(f"      内容与查询相关，保留该页面")
                    
                    # 尝试从标题中提取标签
                    tags = [tag.strip() for tag in title.split('-') if len(tag.strip()) > 1]
                    
                    # 将知识添加到分层知识库
                    success = await self.knowledge_manager.add_knowledge(
                        title=title,
                        content=content,
                        source_url=url,
                        query_used=original_query,
                        tags=tags
                    )
                    
                    if success:
                        logger.info(f"      内容已成功添加到分层知识库")
                        processed_pages.append({
                            'title': title,
                            'url': url,
                            'content': content,
                            'query_used': original_query,
                            'relevance_score': relevance_check.get('relevance_score', 80)
                        })
                    else:
                        logger.info(f"      内容未添加到知识库（可能是重复或低质量内容）")
                else:
                    logger.info(f"      内容与查询不相关，跳过该页面")
            else:
                # 如果结果不包含内容，尝试爬取（向后兼容）
                logger.info(f"      结果不包含内容，尝试爬取...")
                
                try:
                    logger.info(f"      正在获取网页内容...")
                    page_content = await self._fetch_page_content(result['url'])
                    
                    if page_content is None:
                        logger.info(f"      无法获取内容，跳过该网站...")
                        continue
                    
                    logger.info(f"      成功爬取内容，长度: {len(page_content)} 字符")
                    
                    # 使用LLM验证内容相关性
                    llm = LLMScheduler()
                    relevance_check = await llm.verify_content_quality(page_content, result['url'], original_query)
                    
                    if relevance_check.get('is_relevant', True):  # 默认认为相关
                        logger.info(f"      内容与查询相关，保留该页面")
                        
                        # 尝试从标题中提取标签
                        title = result['title']
                        tags = [tag.strip() for tag in title.split('-') if len(tag.strip()) > 1]
                        
                        # 将知识添加到分层知识库
                        success = await self.knowledge_manager.add_knowledge(
                            title=title,
                            content=page_content,
                            source_url=result['url'],
                            query_used=original_query,
                            tags=tags
                        )
                        
                        if success:
                            logger.info(f"      内容已成功添加到分层知识库")
                            processed_pages.append({
                                'title': result['title'],
                                'url': result['url'],
                                'content': page_content,
                                'query_used': original_query,
                                'relevance_score': relevance_check.get('relevance_score', 80)
                            })
                        else:
                            logger.info(f"      内容未添加到知识库（可能是重复或低质量内容）")
                    else:
                        logger.info(f"      内容与查询不相关，跳过该页面")
                        
                except Exception as e:
                    logger.error(f"      处理失败 {result['url']}: {str(e)}")
        
        return processed_pages
    
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
        # 使用移动端User-Agent
        mobile_ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
        headers = self.common_headers.copy()
        headers['User-Agent'] = mobile_ua
        
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
        # 随机延迟以避免被检测
        await asyncio.sleep(random.uniform(1, 3))
        
        timeout = aiohttp.ClientTimeout(total=30)
        headers = self.common_headers.copy()
        headers['User-Agent'] = random.choice(self.user_agents)
        # 添加更多headers来模拟真实浏览器
        headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
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
    
    async def _try_with_cookies_and_session(self, url: str) -> str:
        """使用cookies和session的请求策略"""
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
        """使用代理样式的请求头策略"""
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

    async def _try_with_headless_browser(self, url: str) -> str:
        """
        使用无头浏览器获取内容（需要安装selenium和webdriver）
        这是处理JavaScript渲染页面的最后手段
        """
        try:
            # 检查是否安装了selenium
            import selenium
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except ImportError:
            logger.warning("Selenium未安装，跳过无头浏览器策略")
            return None
        
        try:
            # 配置Chrome选项
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # 无头模式
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument(f"--user-agent={random.choice(self.user_agents)}")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # 创建WebDriver实例
            driver = webdriver.Chrome(options=chrome_options)
            
            # 访问页面
            driver.get(url)
            
            # 等待页面加载
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 等待一些时间让JavaScript执行
            time.sleep(3)
            
            # 获取页面内容
            html = driver.page_source
            driver.quit()
            
            # 使用LLM来解析HTML内容
            llm = LLMScheduler()
            topic = url.split('/')[-1].replace('-', ' ').replace('_', ' ') or url.split('/')[2]
            extracted_content = await llm.extract_content_from_html(html, topic)
            return extracted_content['content']
            
        except Exception as e:
            logger.error(f"无头浏览器策略失败 for {url}: {str(e)}")
            try:
                driver.quit()
            except:
                pass
            return None

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
            
            if page_content:
                # 使用LLM判断是否为具体知识内容页面
                is_specific_content = await self._is_specific_content_page(page_content, url)
                
                if is_specific_content and len(page_content.strip()) > 100:  # 如果内容足够长且是具体知识页面
                    logger.info(f"      在第 {current_depth + 1} 层找到有价值内容，长度: {len(page_content)} 字符")
                    return page_content
                elif len(page_content.strip()) > 100:
                    logger.info(f"      在第 {current_depth + 1} 层找到内容，但不是具体知识页面，继续递归...")
            
            # 如果当前页面内容不足或不是具体知识页面，尝试从页面中提取更多链接进行递归
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
                        
                        if recursive_result:
                            # 检查递归结果是否为具体知识内容
                            is_recursive_specific = await self._is_specific_content_page(recursive_result, link['url'])
                            
                            if is_recursive_specific and len(recursive_result) > 100:
                                logger.info(f"      递归审查成功，在第 {current_depth + 2} 层找到具体知识内容")
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