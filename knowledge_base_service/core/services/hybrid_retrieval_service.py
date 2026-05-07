# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-22
# Copyright (c) 2026. All rights reserved.

"""
混合检索服务
融合 KG 检索和向量检索,使用 RRF 合并结果
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from config.settings import get_embedding_dimension
from core.services.kg_retrieval_service import KGRetrievalService
from core.services.vector_retrieval_service import VectorRetrievalService
from core.llm_client import LLMClient
from core.vector_store.embedding_client import EmbeddingClient
from core.llm_prompts.keyword_extraction_prompt import get_keyword_extraction_prompt


class HybridRetrievalService:
    """混合检索服务"""
    
    def __init__(
        self,
        api_key: str,
        kg_storage_path: str = "data/knowledge_graph",
        vector_store_dir: str = "data/chunk_embeddings",
        embedding_dimension: int = None,
        llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        llm_model: str = "qwen-flash"
    ):
        embedding_dimension = embedding_dimension or get_embedding_dimension()
        """
        初始化混合检索服务
        
        Args:
            api_key: API 密钥
            kg_storage_path: 知识图谱存储路径
            vector_store_dir: 向量存储目录
            embedding_dimension: 向量维度
            llm_base_url: LLM API 基础 URL
            llm_model: LLM 模型名称
        """
        self.api_key = api_key
        self.llm_model = llm_model
        
        self.kg_service = KGRetrievalService(
            storage_path=kg_storage_path,
            embedding_dimension=embedding_dimension
        )
        
        self.vector_service = VectorRetrievalService(
            store_dir=vector_store_dir,
            embedding_dimension=embedding_dimension
        )
        
        self.llm_client = LLMClient(
            api_key=api_key,
            base_url=llm_base_url,
            default_model=llm_model
        )
        
        self.embedding_client = EmbeddingClient(dimension=embedding_dimension)
    
    async def initialize(self):
        """初始化服务"""
        await self.kg_service.load()
        await self.vector_service.load()
    
    async def _extract_keywords_from_query(
        self,
        query: str,
        domain: str = "medical_aesthetics"
    ) -> Tuple[List[str], List[str]]:
        """
        从查询中提取本地关键词和全局关键词
        
        Args:
            query: 用户查询
            domain: 领域
        
        Returns:
            (local_keywords, global_keywords) 元组
        """
        import json
        
        prompt = get_keyword_extraction_prompt(query, domain)
        
        try:
            content = await self.llm_client.chat(
                messages=[
                    {"role": "system", "content": "你是一个专业的关键词提取专家。请严格按照 JSON 格式返回结果。"},
                    {"role": "user", "content": prompt}
                ],
                model=self.llm_model,
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(content)
            local_keywords = result.get("local_keywords", [])
            global_keywords = result.get("global_keywords", [])
            
            return local_keywords, global_keywords
            
        except Exception as e:
            print(f"关键词提取失败: {e}")
            return [query], []
    
    async def retrieve(
        self,
        query: str,
        entities: Optional[List[str]] = None,
        relations: Optional[List[str]] = None,
        top_k: int = 20,
        kg_weight: float = 0.5,
        vector_weight: float = 0.5,
        use_kg: bool = True,
        use_vector: bool = True,
        rrf_k: int = 60
    ) -> Dict[str, Any]:
        """
        混合检索
        
        Args:
            query: 查询文本
            entities: 前端传入的实体列表(可选)
            relations: 前端传入的关系列表(可选)
            top_k: 返回的 chunk 数量
            kg_weight: KG 检索权重
            vector_weight: 向量检索权重
            use_kg: 是否使用 KG 检索
            use_vector: 是否使用向量检索
            rrf_k: RRF 参数
        
        Returns:
            检索结果
        """
        start_time = datetime.now()
        
        kg_chunks = []
        vector_chunks = []
        kg_error = None
        vector_error = None
        
        if use_kg:
            try:
                kg_chunks = await self._kg_retrieve(
                    query=query,
                    entities=entities,
                    relations=relations,
                    top_k=top_k
                )
            except Exception as e:
                kg_error = str(e)
                print(f"KG 检索失败: {e}")
        
        if use_vector:
            try:
                vector_chunks = await self._vector_retrieve(query, top_k)
            except Exception as e:
                vector_error = str(e)
                print(f"向量检索失败: {e}")
        
        merged_chunks = self._merge_results(
            kg_chunks=kg_chunks,
            vector_chunks=vector_chunks,
            kg_weight=kg_weight,
            vector_weight=vector_weight,
            rrf_k=rrf_k
        )
        
        merged_chunks = merged_chunks[:top_k]
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        return {
            "query": query,
            "chunks": merged_chunks,
            "kg_chunks_count": len(kg_chunks),
            "vector_chunks_count": len(vector_chunks),
            "merged_chunks_count": len(merged_chunks),
            "kg_error": kg_error,
            "vector_error": vector_error,
            "duration": duration
        }
    
    async def _kg_retrieve(
        self,
        query: str,
        entities: Optional[List[str]] = None,
        relations: Optional[List[str]] = None,
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        KG 检索
        
        Args:
            query: 查询文本
            entities: 前端传入的实体列表
            relations: 前端传入的关系列表
            top_k: 返回的 chunk 数量
        
        Returns:
            检索结果
        """
        if entities:
            local_keywords = entities
            global_keywords = relations or []
        else:
            local_keywords, global_keywords = await self._extract_keywords_from_query(query)
        
        chunk_results = await self.kg_service.retrieve_chunks_by_keywords(
            local_keywords=local_keywords,
            global_keywords=global_keywords,
            max_hops=1,
            top_k_chunks=top_k
        )
        
        chunks = []
        for chunk_id, score in chunk_results:
            chunk_data = await self.vector_service.get_chunk(chunk_id)
            if chunk_data:
                chunks.append({
                    "id": chunk_id,
                    "content": chunk_data.get("content", ""),
                    "metadata": chunk_data.get("metadata", {}),
                    "score": score,
                    "source": "kg"
                })
        
        return chunks
    
    async def _vector_retrieve(
        self,
        query: str,
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        向量检索
        
        Args:
            query: 查询文本
            top_k: 返回的 chunk 数量
        
        Returns:
            检索结果
        """
        return await self.vector_service.retrieve(query, top_k)
    
    def _merge_results(
        self,
        kg_chunks: List[Dict[str, Any]],
        vector_chunks: List[Dict[str, Any]],
        kg_weight: float = 0.5,
        vector_weight: float = 0.5,
        rrf_k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        使用 RRF 合并结果
        
        Args:
            kg_chunks: KG 检索结果
            vector_chunks: 向量检索结果
            kg_weight: KG 权重
            vector_weight: 向量权重
            rrf_k: RRF 参数
        
        Returns:
            合并后的结果
        """
        rrf_scores = {}
        chunk_data = {}
        
        for rank, chunk in enumerate(kg_chunks, 1):
            chunk_id = chunk["id"]
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + kg_weight / (rrf_k + rank)
            chunk_data[chunk_id] = chunk
        
        for rank, chunk in enumerate(vector_chunks, 1):
            chunk_id = chunk["id"]
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + vector_weight / (rrf_k + rank)
            if chunk_id not in chunk_data:
                chunk_data[chunk_id] = chunk
        
        sorted_chunks = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        merged = []
        for chunk_id, rrf_score in sorted_chunks:
            chunk = chunk_data[chunk_id].copy()
            chunk["rrf_score"] = rrf_score
            merged.append(chunk)
        
        return merged
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        kg_stats = self.kg_service.get_stats()
        vector_stats = self.vector_service.get_stats()
        
        return {
            "kg": kg_stats,
            "vector": vector_stats
        }
