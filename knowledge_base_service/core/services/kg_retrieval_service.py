# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-22
# Copyright (c) 2026. All rights reserved.

"""
知识图谱检索服务
负责从知识图谱中检索相关实体、关系和 chunks
"""

import json
import math
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from core.vector_store.embedding_client import EmbeddingClient
from core.vector_store.ann_index import HNSWIndex
from core.services.entity_matcher import EntityMatcher
from api.schemas.joint_extraction_schemas import Entity, Relation
from config.settings import get_embedding_dimension


class KGRetrievalService:
    """知识图谱检索服务"""
    
    def __init__(
        self,
        storage_path: str = "data/knowledge_graph",
        embedding_dimension: int = None
    ):
        embedding_dimension = embedding_dimension or get_embedding_dimension()
        """
        初始化 KG 检索服务
        
        Args:
            storage_path: 知识图谱存储路径
            embedding_dimension: embedding 维度
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.embedding_client = EmbeddingClient(dimension=embedding_dimension)
        self.entity_matcher = EntityMatcher()
        
        self.knowledge_graph = {
            "entities": {},
            "relations": [],
            "chunk_to_entities": {},
            "entity_to_chunks": {}
        }
        
        self.entity_embeddings = {}
        self.relation_embeddings = {}
        
        self.entity_index = HNSWIndex(
            dimension=embedding_dimension,
            M=16,
            ef_construction=200,
            ef_search=50
        )
        self.relation_index = HNSWIndex(
            dimension=embedding_dimension,
            M=16,
            ef_construction=200,
            ef_search=50
        )
        self._index_built = False
    
    async def load(self):
        """加载知识图谱"""
        graph_file = self.storage_path / "knowledge_graph.json"
        
        if not graph_file.exists():
            print(f"知识图谱文件不存在: {graph_file}")
            return
        
        with open(graph_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.knowledge_graph["entities"] = {
            eid: Entity(**e) for eid, e in data.get("entities", {}).items()
        }
        self.knowledge_graph["relations"] = [
            Relation(**r) for r in data.get("relations", [])
        ]
        self.knowledge_graph["chunk_to_entities"] = data.get("chunk_to_entities", {})
        self.knowledge_graph["entity_to_chunks"] = data.get("entity_to_chunks", {})
        
        print(f"知识图谱加载成功:{len(self.knowledge_graph['entities'])} 个实体,"
              f"{len(self.knowledge_graph['relations'])} 个关系")
        
        embeddings_file = self.storage_path / "embeddings.json"
        if embeddings_file.exists():
            with open(embeddings_file, 'r', encoding='utf-8') as f:
                embeddings_data = json.load(f)
            self.entity_embeddings = embeddings_data.get("entity_embeddings", {})
            self.relation_embeddings = embeddings_data.get("relation_embeddings", {})
            print(f"Embedding 加载成功:{len(self.entity_embeddings)} 个实体,"
                  f"{len(self.relation_embeddings)} 个关系")
        else:
            print("Embedding 文件不存在,将在首次查询时计算...")
        
        await self._build_entity_matcher()
        
        if not self.load_indexes():
            self._build_hnsw_indexes()
    
    async def _build_entity_matcher(self):
        """构建实体匹配器"""
        self.entity_matcher.clear()
        
        for entity_id, entity in self.knowledge_graph["entities"].items():
            self.entity_matcher.add_entity(
                entity_id=entity_id,
                entity_name=entity.entity_name,
                entity_type=entity.entity_type,
                synonyms=getattr(entity, 'synonyms', []),
                aliases=getattr(entity, 'aliases', []),
                popularity=getattr(entity, 'popularity', 1.0)
            )
        
        self.entity_matcher.build_automaton()
        
        stats = self.entity_matcher.get_entity_stats()
        print(f"实体匹配器构建成功:{stats['total_entities']} 个实体,"
              f"{stats['total_names']} 个名称,"
              f"{stats['total_synonyms']} 个同义词")
    
    def _build_hnsw_indexes(self):
        """构建HNSW索引加速向量检索"""
        if self._index_built:
            return
        
        if self.entity_embeddings:
            for entity_id, embedding in self.entity_embeddings.items():
                self.entity_index.add_vector(entity_id, embedding)
            print(f"实体HNSW索引构建完成:{len(self.entity_embeddings)} 个向量")
        
        if self.relation_embeddings:
            for relation_id, embedding in self.relation_embeddings.items():
                self.relation_index.add_vector(relation_id, embedding)
            print(f"关系HNSW索引构建完成:{len(self.relation_embeddings)} 个向量")
        
        self._index_built = True
    
    async def _compute_entity_embeddings(self):
        """预先计算所有实体的 embedding"""
        if not self.knowledge_graph["entities"]:
            return
        
        entity_names = []
        entity_ids = []
        for entity_id, entity in self.knowledge_graph["entities"].items():
            entity_names.append(entity.entity_name)
            entity_ids.append(entity_id)
        
        embeddings = await self.embedding_client.embed_batch(entity_names)
        
        self.entity_embeddings = {
            entity_id: embedding
            for entity_id, embedding in zip(entity_ids, embeddings)
        }
    
    async def _compute_relation_embeddings(self):
        """预先计算所有关系的 embedding"""
        if not self.knowledge_graph["relations"]:
            return
        
        relation_types = []
        relation_ids = []
        for idx, relation in enumerate(self.knowledge_graph["relations"]):
            relation_types.append(relation.relation_type)
            relation_ids.append(f"relation_{idx}")
        
        embeddings = await self.embedding_client.embed_batch(relation_types)
        
        self.relation_embeddings = {
            relation_id: embedding
            for relation_id, embedding in zip(relation_ids, embeddings)
        }
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    async def retrieve_entities_by_embedding(
        self,
        keywords: List[str],
        top_k: int = 10,
        threshold: float = 0.7
    ) -> List[Tuple[str, float]]:
        """
        基于 embedding 检索实体(使用HNSW索引加速)
        
        Args:
            keywords: 关键词列表
            top_k: 返回的实体数量
            threshold: 相似度阈值
        
        Returns:
            [(entity_id, similarity), ...]
        """
        if not self.entity_embeddings:
            await self._compute_entity_embeddings()
            self._build_hnsw_indexes()
        
        if not self._index_built:
            self._build_hnsw_indexes()
        
        entity_scores = {}
        
        for keyword in keywords:
            keyword_embedding = await self.embedding_client.embed(keyword)
            
            results = self.entity_index.search(
                query_vector=keyword_embedding,
                top_k=top_k * 2,
                ef=max(50, top_k * 2)
            )
            
            for entity_id, similarity in results:
                if similarity >= threshold:
                    if entity_id not in entity_scores:
                        entity_scores[entity_id] = similarity
                    else:
                        entity_scores[entity_id] = max(entity_scores[entity_id], similarity)
        
        sorted_results = sorted(
            entity_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_results[:top_k]
    
    async def retrieve_relations_by_embedding(
        self,
        keywords: List[str],
        top_k: int = 10,
        threshold: float = 0.7
    ) -> List[Tuple[int, float]]:
        """
        基于 embedding 检索关系(使用HNSW索引加速)
        
        Args:
            keywords: 关键词列表
            top_k: 返回的关系数量
            threshold: 相似度阈值
        
        Returns:
            [(relation_index, similarity), ...]
        """
        if not self.relation_embeddings:
            await self._compute_relation_embeddings()
            self._build_hnsw_indexes()
        
        if not self._index_built:
            self._build_hnsw_indexes()
        
        relation_scores = {}
        
        for keyword in keywords:
            keyword_embedding = await self.embedding_client.embed(keyword)
            
            results = self.relation_index.search(
                query_vector=keyword_embedding,
                top_k=top_k * 2,
                ef=max(50, top_k * 2)
            )
            
            for relation_key, similarity in results:
                if similarity >= threshold:
                    relation_idx = int(relation_key.replace("relation_", ""))
                    if relation_idx not in relation_scores:
                        relation_scores[relation_idx] = similarity
                    else:
                        relation_scores[relation_idx] = max(relation_scores[relation_idx], similarity)
        
        sorted_results = sorted(
            relation_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_results[:top_k]
    
    async def retrieve_chunks_by_keywords(
        self,
        local_keywords: List[str],
        global_keywords: List[str],
        max_hops: int = 1,
        top_k_chunks: int = 10,
        entity_threshold: float = 0.7,
        relation_threshold: float = 0.7
    ) -> List[Tuple[str, float]]:
        """
        基于关键词检索相关 chunks(Light RAG 方式)
        
        Args:
            local_keywords: 本地关键词(用于匹配实体)
            global_keywords: 全局关键词(用于匹配关系)
            max_hops: 最大跳数
            top_k_chunks: 返回的 chunk 数量
            entity_threshold: 实体匹配阈值
            relation_threshold: 关系匹配阈值
        
        Returns:
            [(chunk_id, score), ...]
        """
        matched_entities = await self.retrieve_entities_by_embedding(
            local_keywords,
            top_k=20,
            threshold=entity_threshold
        )
        
        matched_relations = await self.retrieve_relations_by_embedding(
            global_keywords,
            top_k=20,
            threshold=relation_threshold
        )
        
        entity_ids = set([eid for eid, _ in matched_entities])
        
        for relation_idx, _ in matched_relations:
            if relation_idx < len(self.knowledge_graph["relations"]):
                relation = self.knowledge_graph["relations"][relation_idx]
                
                if relation.source_entity_id in entity_ids:
                    entity_ids.add(relation.target_entity_id)
                if relation.target_entity_id in entity_ids:
                    entity_ids.add(relation.source_entity_id)
        
        for hop in range(max_hops - 1):
            new_entity_ids = set()
            
            for relation in self.knowledge_graph["relations"]:
                if relation.source_entity_id in entity_ids:
                    new_entity_ids.add(relation.target_entity_id)
                if relation.target_entity_id in entity_ids:
                    new_entity_ids.add(relation.source_entity_id)
            
            entity_ids.update(new_entity_ids)
        
        chunk_scores = {}
        
        for entity_id in entity_ids:
            if entity_id in self.knowledge_graph["entity_to_chunks"]:
                chunk_ids = self.knowledge_graph["entity_to_chunks"][entity_id]
                for chunk_id in chunk_ids:
                    if chunk_id not in chunk_scores:
                        chunk_scores[chunk_id] = 0
                    chunk_scores[chunk_id] += 1
        
        sorted_chunks = sorted(
            chunk_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_chunks[:top_k_chunks]
    
    async def retrieve_chunks_by_entities(
        self,
        query_entities: List[str],
        max_hops: int = 2,
        top_k_chunks: int = 10,
        use_fuzzy_match: bool = True,
        fuzzy_threshold: float = 0.8
    ) -> List[Tuple[str, float]]:
        """
        基于实体检索相关 chunks(使用字符串匹配)
        
        Args:
            query_entities: 查询实体列表
            max_hops: 最大跳数
            top_k_chunks: 返回的 chunk 数量
            use_fuzzy_match: 是否使用模糊匹配
            fuzzy_threshold: 模糊匹配阈值
        
        Returns:
            [(chunk_id, score), ...]
        """
        entity_ids = set()
        
        for entity_name in query_entities:
            if use_fuzzy_match:
                matched_entities = self.entity_matcher.match_multi(
                    text=entity_name,
                    use_exact=True,
                    use_fuzzy=True,
                    use_automaton=True,
                    fuzzy_threshold=fuzzy_threshold,
                    max_results=3
                )
                
                for entity_id, _, score in matched_entities:
                    if score >= fuzzy_threshold:
                        entity_ids.add(entity_id)
            else:
                exact_matches = self.entity_matcher.match_exact(entity_name)
                for entity_id, _, _ in exact_matches:
                    entity_ids.add(entity_id)
        
        if not entity_ids:
            return []
        
        related_chunks = set()
        
        for entity_id in entity_ids:
            if entity_id in self.knowledge_graph["entity_to_chunks"]:
                related_chunks.update(
                    self.knowledge_graph["entity_to_chunks"][entity_id]
                )
        
        for hop in range(max_hops):
            new_entity_ids = []
            
            for relation in self.knowledge_graph["relations"]:
                if relation.source_entity_id in entity_ids:
                    if relation.target_entity_id not in entity_ids:
                        new_entity_ids.append(relation.target_entity_id)
                elif relation.target_entity_id in entity_ids:
                    if relation.source_entity_id not in entity_ids:
                        new_entity_ids.append(relation.source_entity_id)
            
            for new_entity_id in new_entity_ids:
                if new_entity_id in self.knowledge_graph["entity_to_chunks"]:
                    related_chunks.update(
                        self.knowledge_graph["entity_to_chunks"][new_entity_id]
                    )
            
            entity_ids.update(new_entity_ids)
        
        chunk_scores = {}
        for chunk_id in related_chunks:
            score = 0
            for entity_id in entity_ids:
                if chunk_id in self.knowledge_graph["entity_to_chunks"].get(entity_id, []):
                    score += 1
            chunk_scores[chunk_id] = score
        
        sorted_chunks = sorted(
            chunk_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_chunks[:top_k_chunks]
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """获取实体"""
        return self.knowledge_graph["entities"].get(entity_id)
    
    def get_relation(self, relation_idx: int) -> Optional[Relation]:
        """获取关系"""
        if 0 <= relation_idx < len(self.knowledge_graph["relations"]):
            return self.knowledge_graph["relations"][relation_idx]
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取知识图谱统计信息"""
        entity_types = {}
        for entity in self.knowledge_graph["entities"].values():
            etype = entity.entity_type
            entity_types[etype] = entity_types.get(etype, 0) + 1
        
        relation_types = {}
        for relation in self.knowledge_graph["relations"]:
            rtype = relation.relation_type
            relation_types[rtype] = relation_types.get(rtype, 0) + 1
        
        return {
            "total_entities": len(self.knowledge_graph["entities"]),
            "total_relations": len(self.knowledge_graph["relations"]),
            "entity_types": entity_types,
            "relation_types": relation_types,
            "chunks_with_entities": len(self.knowledge_graph["chunk_to_entities"]),
            "entity_embeddings": len(self.entity_embeddings),
            "relation_embeddings": len(self.relation_embeddings),
            "hnsw_index_built": self._index_built,
            "entity_index_stats": self.entity_index.get_stats() if self._index_built else None,
            "relation_index_stats": self.relation_index.get_stats() if self._index_built else None
        }
    
    def save_indexes(self):
        """保存HNSW索引到文件"""
        entity_index_file = self.storage_path / "entity_hnsw_index.json"
        relation_index_file = self.storage_path / "relation_hnsw_index.json"
        
        if self._index_built:
            self.entity_index.save(str(entity_index_file))
            self.relation_index.save(str(relation_index_file))
            print(f"HNSW索引已保存")
    
    def load_indexes(self) -> bool:
        """从文件加载HNSW索引"""
        entity_index_file = self.storage_path / "entity_hnsw_index.json"
        relation_index_file = self.storage_path / "relation_hnsw_index.json"
        
        entity_loaded = self.entity_index.load(str(entity_index_file))
        relation_loaded = self.relation_index.load(str(relation_index_file))
        
        if entity_loaded or relation_loaded:
            self._index_built = True
            print(f"HNSW索引加载成功")
            return True
        return False
