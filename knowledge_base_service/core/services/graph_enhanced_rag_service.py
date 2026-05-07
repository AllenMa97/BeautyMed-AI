# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-17
# Copyright (c) 2026. All rights reserved.

"""
图谱增强的RAG服务
结合知识图谱检索和向量检索,提升检索效率和准确率
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from core.services.joint_extraction_service import JointExtractionService
from core.vector_store.chunk_vector_store import ChunkVectorStore
from core.vector_store.embedding_client import EmbeddingClient
from core.rerank.hybrid_reranker import HybridReranker
from core.augmentation.context_builder import ContextBuilder
from config.settings import get_embedding_dimension


class GraphEnhancedRAGService:
    """图谱增强的RAG服务"""
    
    def __init__(
        self,
        api_key: str,
        store_dir: str = "data/chunk_embeddings",
        embedding_dimension: int = None,
        max_context_tokens: int = 4000,
        graph_max_hops: int = 2,
        graph_top_k_chunks: int = 10,
        vector_top_k: int = 20
    ):
        embedding_dimension = embedding_dimension or get_embedding_dimension()
        """
        初始化图谱增强RAG服务
        
        Args:
            api_key: API密钥
            store_dir: 向量存储目录
            embedding_dimension: 向量维度
            max_context_tokens: 最大上下文token数
            graph_max_hops: 图检索最大跳数
            graph_top_k_chunks: 图检索返回的chunk数
            vector_top_k: 向量检索返回的chunk数
        """
        self.api_key = api_key
        self.graph_max_hops = graph_max_hops
        self.graph_top_k_chunks = graph_top_k_chunks
        self.vector_top_k = vector_top_k
        
        self.joint_extraction_service = JointExtractionService(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen-flash"
        )
        
        self.vector_store = ChunkVectorStore(
            store_dir=store_dir,
            dimension=embedding_dimension,
        )
        
        self.embedding_client = EmbeddingClient(dimension=embedding_dimension)
        
        self.reranker = HybridReranker()
        
        self.context_builder = ContextBuilder(
            max_tokens=max_context_tokens,
        )
    
    async def initialize(self):
        """初始化服务"""
        await self.vector_store.load()
        await self.joint_extraction_service.load_knowledge_graph()
    
    async def query(
        self,
        query: str,
        top_k: int = 10,
        use_graph: bool = True,
        use_vector: bool = True,
        graph_weight: float = 0.6,
        vector_weight: float = 0.4,
        entities: List[str] = None,
        relations: List[str] = None
    ) -> Dict[str, Any]:
        """
        图谱增强的查询(支持容错,确保至少一路可用)
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            use_graph: 是否使用图谱检索
            use_vector: 是否使用向量检索
            graph_weight: 图谱检索权重
            vector_weight: 向量检索权重
            entities: 前端传入的实体列表(NER 结果,可选)
            relations: 前端传入的关系列表(可选)
        
        Returns:
            查询结果
        """
        start_time = datetime.now()
        
        graph_chunks = []
        vector_chunks = []
        graph_error = None
        vector_error = None
        
        # 路径 1: KG 检索(独立 try-except)
        if use_graph:
            try:
                graph_chunks = await self._graph_retrieve(
                    query=query,
                    entities=entities,
                    relations=relations
                )
            except Exception as e:
                graph_error = str(e)
                print(f"⚠️ KG 检索失败: {e}")
                graph_chunks = []
        
        # 路径 2: 向量检索(独立 try-except)
        if use_vector:
            try:
                vector_chunks = await self._vector_retrieve(query)
            except Exception as e:
                vector_error = str(e)
                print(f"⚠️ 向量检索失败: {e}")
                vector_chunks = []
        
        # 容错检查:如果两路都失败,尝试降级策略
        if not graph_chunks and not vector_chunks:
            print("⚠️ 两路检索都失败,尝试降级策略...")
            
            # 降级策略 1: 尝试从向量存储直接检索
            try:
                if use_vector:
                    print("  → 降级策略:直接从向量存储检索")
                    query_embedding = await self.embedding_client.embed(query)
                    all_chunks = await self.vector_store.search(
                        query_vector=query_embedding,
                        top_k=top_k
                    )
                    if all_chunks:
                        vector_chunks = [{
                            "id": c.id,
                            "content": c.content,
                            "metadata": c.metadata,
                            "score": c.score,
                            "source": "vector_fallback"
                        } for c in all_chunks]
                        print(f"  ✓ 降级策略成功,检索到 {len(vector_chunks)} 个 chunks")
            except Exception as e:
                print(f"  ✗ 降级策略失败: {e}")
        
        # 合并结果
        merged_chunks = self._merge_results(
            graph_chunks=graph_chunks,
            vector_chunks=vector_chunks,
            graph_weight=graph_weight,
            vector_weight=vector_weight
        )
        
        final_chunks = merged_chunks[:top_k]
        
        context = await self._build_context(final_chunks)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 构建返回结果(包含错误信息)
        result = {
            "query": query,
            "chunks": final_chunks,
            "context": context,
            "graph_chunks_count": len(graph_chunks),
            "vector_chunks_count": len(vector_chunks),
            "merged_chunks_count": len(merged_chunks),
            "final_chunks_count": len(final_chunks),
            "duration": duration,
            "use_graph": use_graph,
            "use_vector": use_vector,
            "success": len(final_chunks) > 0
        }
        
        # 添加错误信息(如果有)
        if graph_error or vector_error:
            result["errors"] = {}
            if graph_error:
                result["errors"]["graph"] = graph_error
            if vector_error:
                result["errors"]["vector"] = vector_error
        
        return result
    
    async def _graph_retrieve(
        self,
        query: str,
        entities: List[str] = None,
        relations: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        基于知识图谱的检索(Light RAG 方式)
        
        Args:
            query: 查询文本
            entities: 前端传入的实体列表(NER 结果,可选)
            relations: 前端传入的关系列表(可选)
        
        Returns:
            相关chunks
        """
        try:
            # 步骤 1: 确定关键词
            if entities:
                # 前端已传入 NER 结果,直接使用
                local_keywords = entities
                print(f"使用前端传入的实体: {local_keywords}")
            else:
                # 前端未传入,调用 LLM 提取
                local_keywords, _ = await self.joint_extraction_service.extract_keywords_from_query(
                    query=query,
                    domain="medical_aesthetics"
                )
                print(f"LLM 提取的实体: {local_keywords}")
            
            # 步骤 2: 确定全局关键词(关系)
            if relations:
                # 前端已传入关系,直接使用
                global_keywords = relations
                print(f"使用前端传入的关系: {global_keywords}")
            else:
                # 前端未传入,尝试提取
                if not entities:
                    # 如果前端也没传 entities,则完整提取
                    _, global_keywords = await self.joint_extraction_service.extract_keywords_from_query(
                        query=query,
                        domain="medical_aesthetics"
                    )
                else:
                    # 如果前端传了 entities,但没有 relations,则不使用关系检索
                    global_keywords = []
                    print("前端未传入关系,跳过关系检索")
            
            if not local_keywords and not global_keywords:
                return []
            
            # 步骤 3: 基于关键词检索 chunks
            related_chunk_ids = await self.joint_extraction_service.retrieve_by_keywords(
                local_keywords=local_keywords,
                global_keywords=global_keywords,
                max_hops=self.graph_max_hops,
                top_k_chunks=self.graph_top_k_chunks,
                entity_threshold=0.7,
                relation_threshold=0.7
            )
            
            # 步骤 4: 获取 chunk 内容
            chunks = []
            for chunk_id in related_chunk_ids:
                chunk_data = await self.vector_store.get_by_id(chunk_id)
                if chunk_data:
                    chunks.append({
                        "id": chunk_id,
                        "content": chunk_data.get("content", ""),
                        "metadata": chunk_data.get("metadata", {}),
                        "score": 1.0,
                        "source": "graph",
                        "local_keywords": local_keywords,
                        "global_keywords": global_keywords
                    })
            
            return chunks
            
        except Exception as e:
            print(f"图谱检索失败: {e}")
            return []
    
    async def _vector_retrieve(self, query: str) -> List[Dict[str, Any]]:
        """
        基于向量的检索
        
        Args:
            query: 查询文本
        
        Returns:
            相关chunks
        """
        try:
            query_embedding = await self.embedding_client.embed(query)
            
            results = await self.vector_store.search(
                query_vector=query_embedding,
                top_k=self.vector_top_k
            )
            
            chunks = []
            for result in results:
                chunks.append({
                    "id": result["id"],
                    "content": result["content"],
                    "metadata": result["metadata"],
                    "score": result["score"],
                    "source": "vector"
                })
            
            return chunks
            
        except Exception as e:
            print(f"向量检索失败: {e}")
            return []
    
    def _merge_results(
        self,
        graph_chunks: List[Dict[str, Any]],
        vector_chunks: List[Dict[str, Any]],
        graph_weight: float,
        vector_weight: float
    ) -> List[Dict[str, Any]]:
        """
        使用 RRF(Reciprocal Rank Fusion)合并图谱和向量检索结果
        
        Args:
            graph_chunks: 图谱检索结果
            vector_chunks: 向量检索结果
            graph_weight: 图谱权重
            vector_weight: 向量权重
        
        Returns:
            合并后的结果
        """
        # RRF 参数
        k = 60  # RRF 常数
        
        # 计算 RRF 分数
        rrf_scores = {}
        
        # 图谱检索结果的 RRF 分数
        for rank, chunk in enumerate(graph_chunks, 1):
            chunk_id = chunk["id"]
            rrf_score = graph_weight / (k + rank)
            
            if chunk_id not in rrf_scores:
                rrf_scores[chunk_id] = {
                    "chunk": chunk,
                    "graph_rank": rank,
                    "vector_rank": None,
                    "rrf_score": 0.0
                }
            
            rrf_scores[chunk_id]["rrf_score"] += rrf_score
            rrf_scores[chunk_id]["graph_rank"] = rank
        
        # 向量检索结果的 RRF 分数
        for rank, chunk in enumerate(vector_chunks, 1):
            chunk_id = chunk["id"]
            rrf_score = vector_weight / (k + rank)
            
            if chunk_id not in rrf_scores:
                rrf_scores[chunk_id] = {
                    "chunk": chunk,
                    "graph_rank": None,
                    "vector_rank": rank,
                    "rrf_score": 0.0
                }
            
            rrf_scores[chunk_id]["rrf_score"] += rrf_score
            rrf_scores[chunk_id]["vector_rank"] = rank
        
        # 按 RRF 分数排序
        sorted_chunks = sorted(
            rrf_scores.values(),
            key=lambda x: x["rrf_score"],
            reverse=True
        )
        
        # 更新 chunk 的分数和元数据
        for idx, item in enumerate(sorted_chunks):
            chunk = item["chunk"]
            chunk["score"] = item["rrf_score"]
            chunk["metadata"]["graph_rank"] = item["graph_rank"]
            chunk["metadata"]["vector_rank"] = item["vector_rank"]
            chunk["metadata"]["rrf_score"] = item["rrf_score"]
        
        return [item["chunk"] for item in sorted_chunks]
    
    async def _build_context(self, chunks: List[Dict[str, Any]]) -> str:
        """
        构建上下文
        
        Args:
            chunks: chunks列表
        
        Returns:
            上下文字符串
        """
        if not chunks:
            return ""
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            content = chunk.get("content", "")
            metadata = chunk.get("metadata", {})
            source = chunk.get("source", "unknown")
            
            context_part = f"[{i}] {content}"
            if metadata:
                context_part += f"\n    来源: {source}"
                if "title" in metadata:
                    context_part += f" | 标题: {metadata['title']}"
                if "category" in metadata:
                    context_part += f" | 类别: {metadata['category']}"
            
            context_parts.append(context_part)
        
        return "\n\n".join(context_parts)
    
    async def get_retrieval_stats(self) -> Dict[str, Any]:
        """
        获取检索统计信息
        
        Returns:
            统计信息
        """
        kg_stats = await self.joint_extraction_service.get_knowledge_graph_stats()
        
        # 获取向量数量
        total_vectors = len(self.vector_store.vectors) if hasattr(self.vector_store, 'vectors') else 0
        
        return {
            "knowledge_graph": kg_stats.dict(),
            "vector_store": {
                "total_vectors": total_vectors,
                "dimension": self.vector_store.dimension
            }
        }
