"""LLM联网搜索服务 - 与热搜服务协同"""
import asyncio
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from algorithm_services.utils.logger import get_logger
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest
from algorithm_services.api.schemas.feature_schemas.llm_web_search_schema import (
    LLMWebSearchRequest,
    LLMWebSearchResponse,
    LLMOptimizedQuery,
    SearchSource,
    BatchSearchRequest,
    BatchSearchResponse,
    TrendingContext,
)


logger = get_logger(__name__)


class LLMWebSearchService:
    """
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

    LLM联网搜索服务
    
    与热搜服务的关系：
    - 热搜服务：获取结构化的热搜榜单（如微博热搜、知乎热榜等）
    - LLM搜索服务：获取非结构化的深度信息
    
    协同流程：
    1. 先调用热搜服务获取当前热点话题
    2. 如需深入了解某个热点，调用LLM搜索服务获取详情
    3. LLM搜索可以结合热搜上下文，生成更精准的搜索结果
    
    特点：
    - LLM驱动的智能查询优化
    - 多源信息聚合
    - 可信度评估
    - 与热搜上下文协同
    """
    
    def __init__(self):
        self.default_provider = "aliyun"
        self.default_model = "qwen-vl-plus-2025-08-15"
    
    async def _optimize_query(self, query: str, user_context: Optional[Dict] = None, 
                              trending_context: Optional[TrendingContext] = None) -> LLMOptimizedQuery:
        """使用LLM优化搜索查询"""
        try:
            # 构建上下文提示
            context_hint = ""
            if user_context:
                context_hint += f"\n用户背景: {json.dumps(user_context, ensure_ascii=False)}"
            if trending_context:
                context_hint += f"\n当前热搜: {', '.join(trending_context.trending_topics[:5])}"
            
            system_prompt = """你是一个搜索查询优化专家。根据用户查询和上下文，优化搜索关键词，使搜索结果更精准。
要求：
1. 生成的优化查询要简洁、明确
2. 提取3-5个核心搜索关键词
3. 解释优化理由
4. 以JSON格式返回"""
            
            user_prompt = f"""请优化以下搜索查询：

原始查询: {query}
{context_hint}

请生成JSON格式数据，包含:
- original_query: 原始查询
- optimized_query: 优化后的查询（适合搜索引擎）
- search_keywords: 搜索关键词列表
- reasoning: 优化理由（简短）

请生成JSON格式数据。"""
            
            llm_request = LLMRequest(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=512,
                provider=self.default_provider,
                model=self.default_model
            )
            
            response = await llm_client_singleton.call_llm(llm_request)
            
            if isinstance(response, dict):
                text = response.get("text", "").strip()
            else:
                text = str(response)
            
            # 解析JSON
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            data = json.loads(text.strip())
            
            return LLMOptimizedQuery(
                original_query=data.get("original_query", query),
                optimized_query=data.get("optimized_query", query),
                search_keywords=data.get("search_keywords", []),
                reasoning=data.get("reasoning", "")
            )
            
        except Exception as e:
            logger.warning(f"[LLM搜索] 查询优化失败: {e}")
            return LLMOptimizedQuery(
                original_query=query,
                optimized_query=query,
                search_keywords=query.split()[:5],
                reasoning="使用原始查询"
            )
    
    async def _generate_summary(self, query: str, sources: List[SearchSource], 
                               user_context: Optional[Dict] = None) -> str:
        """使用LLM聚合搜索结果生成摘要"""
        try:
            sources_text = "\n\n".join([
                f"来源{i+1}: {s.title}\n内容: {s.snippet}"
                for i, s in enumerate(sources)
            ])
            
            context_hint = ""
            if user_context:
                context_hint = f"\n用户背景: {json.dumps(user_context, ensure_ascii=False)}"
            
            system_prompt = """你是一个信息摘要专家。根据搜索来源，生成简洁准确的摘要。
要求：
1. 摘要要准确反映搜索结果的核心内容
2. 突出重要信息和关键细节
3. 保持客观中立
4. 以用户友好的方式呈现"""
            
            user_prompt = f"""基于以下搜索结果，为用户的查询生成摘要：

用户查询: {query}
{context_hint}

搜索结果:
{sources_text}

请生成一段简洁的摘要（不超过200字），概括搜索结果的核心信息。"""
            
            llm_request = LLMRequest(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.5,
                max_tokens=512,
                provider=self.default_provider,
                model=self.default_model
            )
            
            response = await llm_client_singleton.call_llm(llm_request)
            
            if isinstance(response, dict):
                return response.get("text", "").strip()
            else:
                return str(response).strip()
                
        except Exception as e:
            logger.warning(f"[LLM搜索] 摘要生成失败: {e}")
            return "无法生成摘要"
    
    async def _assess_credibility(self, sources: List[SearchSource]) -> float:
        """评估信息来源可信度"""
        if not sources:
            return 0.0
        
        # 简单计算平均可信度
        total = sum(s.credibility_score for s in sources)
        return round(total / len(sources), 2)
    
    async def search(self, request: LLMWebSearchRequest) -> LLMWebSearchResponse:
        """执行LLM联网搜索"""
        start_time = time.time()
        
        try:
            logger.info(f"[LLM搜索] 开始搜索: {request.query}")
            
            # 1. 优化查询（可选择是否使用LLM优化）
            if request.user_context or request.trending_context:
                optimized = await self._optimize_query(
                    request.query, 
                    request.user_context, 
                    request.trending_context
                )
                logger.info(f"[LLM搜索] 查询优化: {optimized.optimized_query}")
            else:
                optimized = LLMOptimizedQuery(
                    original_query=request.query,
                    optimized_query=request.query,
                    search_keywords=request.query.split()[:5],
                    reasoning="无额外上下文"
                )
            
            # 2. 模拟搜索结果（这里需要接入真实的搜索API）
            # TODO: 接入真实搜索API（如Google、Bing等）
            sources = await self._mock_search(optimized.optimized_query, request.max_sources)
            
            # 3. 生成摘要
            summary = await self._generate_summary(
                request.query, 
                sources, 
                request.user_context
            )
            
            # 4. 评估可信度
            credibility = await self._assess_credibility(sources)
            
            processing_time = time.time() - start_time
            
            logger.info(f"[LLM搜索] 搜索完成，来源数: {len(sources)}, 耗时: {processing_time:.2f}s")
            
            return LLMWebSearchResponse(
                success=True,
                query=request.query,
                optimized_query=optimized,
                summary=summary,
                sources=sources,
                credibility_score=credibility,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"[LLM搜索] 搜索失败: {e}")
            return LLMWebSearchResponse(
                success=False,
                query=request.query,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    async def _mock_search(self, query: str, max_sources: int) -> List[SearchSource]:
        """模拟搜索（待接入真实搜索API）"""
        # TODO: 接入真实搜索API
        # 这里返回模拟数据，实际使用需要接入Google、Bing等搜索API
        
        await asyncio.sleep(0.1)  # 模拟网络延迟
        
        mock_sources = [
            SearchSource(
                title=f"关于{query}的最新报道",
                url=f"https://example.com/search?q={query}",
                snippet=f"这是关于{query}的搜索结果摘要...",
                credibility_score=0.8,
                published_time=datetime.now().isoformat()
            ),
            SearchSource(
                title=f"{query}相关分析",
                url=f"https://news.example.com/{query}",
                snippet=f"{query}是当前热门话题，引发广泛讨论...",
                credibility_score=0.7,
                published_time=datetime.now().isoformat()
            ),
        ]
        
        return mock_sources[:max_sources]
    
    async def batch_search(self, request: BatchSearchRequest) -> BatchSearchResponse:
        """批量搜索"""
        start_time = time.time()
        
        try:
            logger.info(f"[LLM搜索] 开始批量搜索，查询数: {len(request.queries)}")
            
            tasks = [
                self.search(LLMWebSearchRequest(
                    query=q,
                    user_context=request.user_context,
                    max_sources=request.max_sources_per_query
                ))
                for q in request.queries
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful = sum(1 for r in results if isinstance(r, LLMWebSearchResponse) and r.success)
            
            processing_time = time.time() - start_time
            
            logger.info(f"[LLM搜索] 批量搜索完成，成功: {successful}/{len(request.queries)}")
            
            return BatchSearchResponse(
                success=True,
                results=[r for r in results if isinstance(r, LLMWebSearchResponse)],
                total_queries=len(request.queries),
                successful_queries=successful,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"[LLM搜索] 批量搜索失败: {e}")
            return BatchSearchResponse(
                success=False,
                results=[],
                total_queries=len(request.queries),
                successful_queries=0,
                processing_time=time.time() - start_time
            )
    
    async def search_with_trending(self, query: str, user_context: Optional[Dict] = None) -> LLMWebSearchResponse:
        """结合热搜上下文的搜索（供外部调用）"""
        # TODO: 可以在这里获取热搜上下文，然后调用search
        return await self.search(LLMWebSearchRequest(
            query=query,
            user_context=user_context,
            max_sources=5
        ))


# 创建全局实例
llm_web_search_service = LLMWebSearchService()
