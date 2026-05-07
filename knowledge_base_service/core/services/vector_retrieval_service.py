# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-22
# Copyright (c) 2026. All rights reserved.

"""
向量检索服务
负责从向量存储中检索相关 chunks
"""

from typing import List, Dict, Any, Optional
from pathlib import Path

from config.settings import get_embedding_dimension
from core.vector_store.chunk_vector_store import ChunkVectorStore
from core.vector_store.embedding_client import EmbeddingClient


class VectorRetrievalService:
    """向量检索服务"""
    
    def __init__(
        self,
        store_dir: str = "data/chunk_embeddings",
        embedding_dimension: int = None
    ):
        embedding_dimension = embedding_dimension or get_embedding_dimension()
        """
        初始化向量检索服务
        
        Args:
            store_dir: 向量存储目录
            embedding_dimension: 向量维度
        """
        self.store_dir = Path(store_dir)
        self.embedding_dimension = embedding_dimension
        
        self.vector_store = ChunkVectorStore(
            store_dir=store_dir,
            dimension=embedding_dimension
        )
        
        self.embedding_client = EmbeddingClient(dimension=embedding_dimension)
    
    async def load(self):
        """加载向量存储"""
        await self.vector_store.load()
        print(f"向量存储加载成功:{len(self.vector_store)} 个向量")
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        基于查询文本检索相关 chunks
        
        Args:
            query: 查询文本
            top_k: 返回的 chunk 数量
        
        Returns:
            检索结果列表
        """
        query_embedding = await self.embedding_client.embed(query)
        
        results = await self.vector_store.search(
            query_vector=query_embedding,
            top_k=top_k
        )
        
        return [
            {
                "id": r["id"],
                "content": r["content"],
                "metadata": r["metadata"],
                "score": r["score"],
                "source": "vector"
            }
            for r in results
        ]
    
    async def retrieve_by_embedding(
        self,
        embedding: List[float],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        基于向量检索相关 chunks
        
        Args:
            embedding: 查询向量
            top_k: 返回的 chunk 数量
        
        Returns:
            检索结果列表
        """
        results = await self.vector_store.search(
            query_vector=embedding,
            top_k=top_k
        )
        
        return [
            {
                "id": r["id"],
                "content": r["content"],
                "metadata": r["metadata"],
                "score": r["score"],
                "source": "vector"
            }
            for r in results
        ]
    
    async def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定 chunk
        
        Args:
            chunk_id: Chunk ID
        
        Returns:
            Chunk 数据
        """
        return await self.vector_store.get_by_id(chunk_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取向量存储统计信息"""
        return {
            "total_vectors": len(self.vector_store),
            "store_dir": str(self.store_dir),
            "embedding_dimension": self.embedding_dimension
        }
