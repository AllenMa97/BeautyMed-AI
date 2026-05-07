"""
知识库服务客户端
统一调用 knowledge_base_service 的接口
"""
import httpx
import os
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

logger = logging.getLogger("YISIA")

from algorithm_services.api.schemas.feature_schemas.knowledge_base_schemas import (
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
)

load_dotenv(os.path.join(os.path.dirname(__file__), "../../config/KNOWLEDGE.env"), override=True)


class KnowledgeBaseClient:
    """调用 knowledge_base_service 的客户端"""

    def __init__(self):
        self.base_url = os.getenv("KNOWLEDGE_BASE_SERVICE_URL", "http://localhost:8002")
        self.api_prefix = "/api/v1"

        self.default_search_mode = os.getenv("KNOWLEDGE_DEFAULT_SEARCH_MODE", "hybrid")
        self.default_top_k = int(os.getenv("KNOWLEDGE_DEFAULT_TOP_K", "10"))
        self.default_threshold = float(os.getenv("KNOWLEDGE_DEFAULT_THRESHOLD", "0.1"))
        self.default_search_type = os.getenv("KNOWLEDGE_DEFAULT_SEARCH_TYPE", "all")

    async def search_knowledge(
        self,
        query: str,
        top_k: int = 10,
        search_mode: str = "hybrid",
        use_ann: bool = True,
        threshold: float = 0.3,
        search_type: str = "all",
        entities: List[Dict[str, Any]] = None,
        relations: List[Dict[str, Any]] = None,
    ) -> KnowledgeSearchResult:
        """
        搜索知识库（使用 /knowledge/search 接口）

        Returns:
            KnowledgeSearchResult: 结构化的搜索结果，包含 products 和 entries 列表

        Example:
            result = await client.search_knowledge("美白精华")
            for product in result.products:
                print(f"产品: {product.name}, 品牌: {product.brand}")
            for entry in result.entries:
                print(f"知识: {entry.title}")
        """
        request = KnowledgeSearchRequest(
            query=query,
            top_k=top_k,
            search_mode=search_mode,
            use_ann=use_ann,
            threshold=threshold,
            search_type=search_type,
            entities=entities,
            relations=relations,
        )
        payload = request.model_dump(exclude_none=True)

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    logger.info(f"知识检索请求: url={self.base_url}{self.api_prefix}/knowledge/search, payload_keys={list(payload.keys())}, search_type={payload.get('search_type')}, attempt={attempt+1}")
                    response = await client.post(
                        f"{self.base_url}{self.api_prefix}/knowledge/search",
                        json=payload,
                    )
                    logger.info(f"知识检索响应: status={response.status_code}, content_length={len(response.content)}")
                    response.raise_for_status()
                    response_data = response.json()
                    return KnowledgeSearchResult.from_response(response_data)

            except httpx.HTTPStatusError as e:
                return KnowledgeSearchResult(
                    code=e.response.status_code,
                    msg=f"HTTP错误: {e.response.status_code}",
                    products=[],
                    entries=[],
                    total_found=0
                )
            except (httpx.RequestError, Exception) as e:
                if attempt < max_retries:
                    import asyncio
                    await asyncio.sleep(1)
                    continue
                return KnowledgeSearchResult(
                    code=500,
                    msg=f"请求错误(重试{max_retries}次): {str(e)}",
                    products=[],
                    entries=[],
                    total_found=0
                )

    async def search_knowledge_raw(
        self,
        query: str,
        top_k: int = 10,
        search_mode: str = "hybrid",
        use_ann: bool = True,
        threshold: float = 0.3,
        search_type: str = "all",
        entities: List[Dict[str, Any]] = None,
        relations: List[Dict[str, Any]] = None,
    ) -> Dict:
        """
        搜索知识库（原始响应）

        Returns:
            Dict: 原始响应数据，未经过结构化处理

        Note:
            仅在需要访问未定义字段时使用，优先使用 search_knowledge()
        """
        request = KnowledgeSearchRequest(
            query=query,
            top_k=top_k,
            search_mode=search_mode,
            use_ann=use_ann,
            threshold=threshold,
            search_type=search_type,
            entities=entities,
            relations=relations,
        )
        payload = request.model_dump(exclude_none=True)

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}{self.api_prefix}/knowledge/search",
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
            except httpx.RequestError as e:
                return {"code": 500, "msg": f"搜索失败: {str(e)}", "data": {}}


knowledge_base_client = KnowledgeBaseClient()
