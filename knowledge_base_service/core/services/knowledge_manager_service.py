# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-22
# Copyright (c) 2026. All rights reserved.

from typing import List, Dict, Optional
import json
from pathlib import Path
from utils.logger import get_logger
from core.vector_store.chunk_vector_store import ChunkVectorStore
from core.vector_store.embedding_client import EmbeddingClient

logger = get_logger(__name__)

EMBED_DIR = "data/chunk_embeddings"


class KnowledgeManagerService:
    """
    知识管理服务 - 负责增删改
    
    使用 EmbeddingClient，模型和维度从 config/env 统一读取
    """

    def __init__(self):
        self.store = ChunkVectorStore(store_dir=EMBED_DIR)
        self.embedding_client = EmbeddingClient()
        self.dimension = self.store.dimension
        self._loaded = False

    async def _ensure_loaded(self):
        if not self._loaded:
            await self.store.load()
            self._loaded = True

    async def add_product(self, product_data: Dict) -> str:
        await self._ensure_loaded()

        product_count = sum(1 for cid in self.store.id_list if cid.startswith("product_"))
        product_id = f"product_{product_count}"

        content_parts = []
        if product_data.get("name"):
            content_parts.append(f"产品名称：{product_data['name']}")
        if product_data.get("brand"):
            content_parts.append(f"品牌：{product_data['brand']}")
        if product_data.get("category"):
            content_parts.append(f"类别：{product_data['category']}")
        if product_data.get("efficacy"):
            content_parts.append(f"功效：{product_data['efficacy']}")
        if product_data.get("applicable_skin"):
            content_parts.append(f"适用肤质：{product_data['applicable_skin']}")
        if product_data.get("capacity"):
            content_parts.append(f"容量：{product_data['capacity']}")
        if product_data.get("reference_price"):
            content_parts.append(f"价格：{product_data['reference_price']}")
        if product_data.get("description"):
            content_parts.append(f"描述：{product_data['description']}")
        if product_data.get("tags"):
            content_parts.append(f"标签：{', '.join(product_data['tags'])}")

        content_text = "\n".join(content_parts)

        embedding = await self.embedding_client.embed(content_text)

        chunk_id = f"{product_id}_chunk_0"
        metadata = {
            "document_id": product_id,
            "chunk_type": "parent",
            "chunk_index": 0,
            "chunker_type": "manual",
            "authority_level": "general",
            "category": product_data.get("category", "general"),
            "similarity_threshold": 0.6,
            "parent_max_tokens": 512,
            "child_max_tokens": 128,
        }

        await self.store.add(chunk_id, embedding, content_text, metadata)

        embed_dir = Path(EMBED_DIR)
        embed_dir.mkdir(parents=True, exist_ok=True)
        chunk_file = embed_dir / f"{chunk_id}.json"
        chunk_file.write_text(json.dumps({
            "chunk_id": chunk_id,
            "document_id": product_id,
            "content": content_text,
            "embedding": embedding,
            "embedding_dimension": self.dimension,
            "metadata": metadata,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        await self.store.save()

        logger.info(f"产品添加成功: {product_data.get('name')} (ID: {product_id})")
        return product_id

    async def update_product(self, product_id: str, update_data: Dict) -> bool:
        await self._ensure_loaded()

        chunk_id = f"{product_id}_chunk_0"
        if chunk_id not in self.store.contents:
            logger.warning(f"产品不存在: {product_id}")
            return False

        old_content = self.store.contents.get(chunk_id, "")
        old_metadata = self.store.metadata.get(chunk_id, {})

        content_lines = old_content.split("\n") if old_content else []

        field_map = {
            "name": "产品名称",
            "brand": "品牌",
            "category": "类别",
            "efficacy": "功效",
            "applicable_skin": "适用肤质",
            "capacity": "容量",
            "reference_price": "价格",
            "description": "描述",
        }

        for field, label in field_map.items():
            if field in update_data:
                value = update_data[field]
                if field == "reference_price":
                    value = str(value)
                new_line = f"{label}：{value}"
                found = False
                for i, line in enumerate(content_lines):
                    if line.startswith(f"{label}："):
                        content_lines[i] = new_line
                        found = True
                        break
                if not found:
                    content_lines.append(new_line)

        if "tags" in update_data:
            tags_line = f"标签：{', '.join(update_data['tags'])}"
            found = False
            for i, line in enumerate(content_lines):
                if line.startswith("标签："):
                    content_lines[i] = tags_line
                    found = True
                    break
            if not found:
                content_lines.append(tags_line)

        new_content = "\n".join(content_lines)

        embedding = await self.embedding_client.embed(new_content)

        self.store.vectors[chunk_id] = embedding
        self.store.contents[chunk_id] = new_content
        self.store.metadata[chunk_id] = {**old_metadata, **update_data}

        embed_dir = Path(EMBED_DIR)
        chunk_file = embed_dir / f"{chunk_id}.json"
        if chunk_file.exists():
            chunk_file.write_text(json.dumps({
                "chunk_id": chunk_id,
                "document_id": product_id,
                "content": new_content,
                "embedding": embedding,
                "embedding_dimension": self.dimension,
                "metadata": self.store.metadata[chunk_id],
            }, ensure_ascii=False, indent=2), encoding="utf-8")

        await self.store.save()

        logger.info(f"产品更新成功: {product_id}")
        return True

    async def delete_product(self, product_id: str) -> bool:
        await self._ensure_loaded()

        if "_chunk_" in product_id:
            chunk_ids_to_delete = [product_id]
        else:
            chunk_ids_to_delete = [
                cid for cid in self.store.id_list
                if cid.startswith(f"{product_id}_chunk_")
            ]

        if not chunk_ids_to_delete:
            logger.warning(f"产品不存在: {product_id}")
            return False

        for chunk_id in chunk_ids_to_delete:
            self.store.vectors.pop(chunk_id, None)
            self.store.contents.pop(chunk_id, None)
            self.store.metadata.pop(chunk_id, None)
            self.store.id_list.remove(chunk_id)

            chunk_file = Path(EMBED_DIR) / f"{chunk_id}.json"
            if chunk_file.exists():
                chunk_file.unlink()

        self.store.hnsw_index = type(self.store.hnsw_index)(
            dimension=self.store.dimension,
            M=self.store.M,
            ef_construction=self.store.ef_construction,
            ef_search=50
        )
        self.store._build_hnsw_index()

        await self.store.save()

        logger.info(f"产品删除成功: {product_id}, 删除 {len(chunk_ids_to_delete)} 个分块")
        return True

    async def update_entry(self, entry_id: str, update_data: Dict) -> bool:
        await self._ensure_loaded()

        chunk_id = f"{entry_id}_chunk_0"
        if chunk_id not in self.store.contents:
            logger.warning(f"知识条目不存在: {entry_id}")
            return False

        old_content = self.store.contents.get(chunk_id, "")
        old_metadata = self.store.metadata.get(chunk_id, {})

        if "content" in update_data:
            new_content = update_data["content"]
        else:
            new_content = old_content

        if "title" in update_data:
            new_content = f"标题：{update_data['title']}\n{new_content}"

        if "tags" in update_data:
            tags_line = f"标签：{', '.join(update_data['tags'])}"
            lines = new_content.split("\n")
            found = False
            for i, line in enumerate(lines):
                if line.startswith("标签："):
                    lines[i] = tags_line
                    found = True
                    break
            if not found:
                lines.append(tags_line)
            new_content = "\n".join(lines)

        embedding = await self.embedding_client.embed(new_content)

        self.store.vectors[chunk_id] = embedding
        self.store.contents[chunk_id] = new_content
        self.store.metadata[chunk_id] = {**old_metadata, **update_data}

        embed_dir = Path(EMBED_DIR)
        chunk_file = embed_dir / f"{chunk_id}.json"
        if chunk_file.exists():
            chunk_file.write_text(json.dumps({
                "chunk_id": chunk_id,
                "document_id": entry_id,
                "content": new_content,
                "embedding": embedding,
                "embedding_dimension": self.dimension,
                "metadata": self.store.metadata[chunk_id],
            }, ensure_ascii=False, indent=2), encoding="utf-8")

        await self.store.save()

        logger.info(f"知识条目更新成功: {entry_id}")
        return True

    async def delete_entry(self, entry_id: str) -> bool:
        await self._ensure_loaded()

        base_id = entry_id.rsplit("_chunk_", 1)[0] if "_chunk_" in entry_id else entry_id
        chunk_ids_to_delete = [
            cid for cid in self.store.id_list
            if cid.startswith(f"{base_id}_chunk_")
        ]

        if not chunk_ids_to_delete:
            logger.warning(f"知识条目不存在: {entry_id}")
            return False

        for chunk_id in chunk_ids_to_delete:
            self.store.vectors.pop(chunk_id, None)
            self.store.contents.pop(chunk_id, None)
            self.store.metadata.pop(chunk_id, None)
            self.store.id_list.remove(chunk_id)

            chunk_file = Path(EMBED_DIR) / f"{chunk_id}.json"
            if chunk_file.exists():
                chunk_file.unlink()

        self.store.hnsw_index = type(self.store.hnsw_index)(
            dimension=self.store.dimension,
            M=self.store.M,
            ef_construction=self.store.ef_construction,
            ef_search=50
        )
        self.store._build_hnsw_index()

        await self.store.save()

        logger.info(f"知识条目删除成功: {entry_id}, 删除 {len(chunk_ids_to_delete)} 个分块")
        return True
