# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from typing import List, Dict, Optional
from utils.logger import get_logger
from core.vector_store.chunk_vector_store import ChunkVectorStore
from core.vector_store.embedding_client import EmbeddingClient

logger = get_logger(__name__)


class KnowledgeRetriever:
    """
    知识检索器 - 只负责检索
    
    使用 EmbeddingClient，模型和维度从 config/env 统一读取
    """

    def __init__(self, use_ann: bool = True):
        self.store = ChunkVectorStore(store_dir="data/chunk_embeddings")
        self.embedding_client = EmbeddingClient()
        self._loaded = False

    async def _ensure_loaded(self):
        if not self._loaded:
            await self.store.load()
            self._loaded = True

    async def search(self, query: str, top_k: int = 5, search_type: str = "all") -> List[Dict]:
        """
        向量检索

        Args:
            query: 查询文本
            top_k: 返回数量
            search_type: 检索类别 (all/products/entries)

        Returns:
            检索结果列表
        """
        await self._ensure_loaded()

        query_embedding = await self.embedding_client.embed(query)
        raw_results = await self.store.search(query_embedding, top_k=top_k * 3)

        results = []
        for item in raw_results:
            chunk_id = item.get("id", "")
            metadata = item.get("metadata", {})

            doc_type = "product" if chunk_id.startswith("product_") else "entry"

            if search_type == "products" and doc_type != "product":
                continue
            if search_type == "entries" and doc_type != "entry":
                continue

            results.append({
                "id": chunk_id,
                "content": item.get("content", ""),
                "vector_score": item.get("score", 0.0),
                "metadata": metadata,
                "type": doc_type,
            })

            if len(results) >= top_k:
                break

        return results

    async def get_all_products(self) -> List[Dict]:
        await self._ensure_loaded()
        results = []
        for chunk_id in self.store.id_list:
            if not chunk_id.startswith("product_"):
                continue
            content = self.store.contents.get(chunk_id, "")
            metadata = self.store.metadata.get(chunk_id, {})
            if content:
                results.append({
                    "id": chunk_id,
                    "content": content,
                    "metadata": metadata,
                    "type": "product",
                })
        return results

    async def get_all_entries(self) -> List[Dict]:
        await self._ensure_loaded()
        results = []
        for chunk_id in self.store.id_list:
            if not chunk_id.startswith("medical_"):
                continue
            content = self.store.contents.get(chunk_id, "")
            metadata = self.store.metadata.get(chunk_id, {})
            if content:
                results.append({
                    "id": chunk_id,
                    "content": content,
                    "metadata": metadata,
                    "type": "entry",
                })
        return results

    async def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        await self._ensure_loaded()
        chunk_id = f"{product_id}_chunk_0"
        content = self.store.contents.get(chunk_id, "")
        if not content:
            return None
        return {
            "id": product_id,
            "chunk_id": chunk_id,
            "content": content,
            "metadata": self.store.metadata.get(chunk_id, {}),
            "type": "product",
        }

    async def get_entry_by_id(self, entry_id: str) -> Optional[Dict]:
        await self._ensure_loaded()
        chunk_id = f"{entry_id}_chunk_0"
        content = self.store.contents.get(chunk_id, "")
        if not content:
            return None
        return {
            "id": entry_id,
            "chunk_id": chunk_id,
            "content": content,
            "metadata": self.store.metadata.get(chunk_id, {}),
            "type": "entry",
        }

    async def get_statistics(self) -> Dict:
        await self._ensure_loaded()
        product_count = sum(1 for cid in self.store.id_list if cid.startswith("product_"))
        entry_count = sum(1 for cid in self.store.id_list if cid.startswith("medical_"))
        return {
            "total_chunks": len(self.store.id_list),
            "total_products": product_count,
            "total_entries": entry_count,
            "total_vectors": len(self.store.vectors),
        }
