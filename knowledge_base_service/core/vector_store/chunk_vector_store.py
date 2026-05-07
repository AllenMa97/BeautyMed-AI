# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-17
# Copyright (c) 2026. All rights reserved.

"""
Chunk级别的向量存储,支持chunk级别的向量检索
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from config.settings import get_embedding_dimension, get_hnsw_m, get_hnsw_ef_construction, get_hnsw_ef_search

from core.vector_store.ann_index import HNSWIndex


class ChunkVectorStore:
    """Chunk级别的向量存储"""
    
    def __init__(
        self,
        store_dir: str = "data/chunk_embeddings",
        dimension: int = None,
        max_elements: int = 10000,
        ef_construction: int = None,
        M: int = None
    ):
        self.store_dir = Path(store_dir)
        self.dimension = dimension or get_embedding_dimension()
        self.max_elements = max_elements
        self.M = M or get_hnsw_m()
        self.ef_construction = ef_construction or get_hnsw_ef_construction()
        self.ef_search = get_hnsw_ef_search()
        
        self.vectors = {}
        self.contents = {}
        self.metadata = {}
        self.id_list = []
        
        self.hnsw_index = HNSWIndex(
            dimension=dimension,
            M=M,
            ef_construction=ef_construction,
            ef_search=50
        )
        self.ef_construction = ef_construction
        self.M = M
        
        self.index_file = self.store_dir / "hnsw_index.json"
        self.vectors_file = self.store_dir / "vectors.json"
        self.contents_file = self.store_dir / "contents.json"
        self.metadata_file = self.store_dir / "metadata.json"
        self.id_list_file = self.store_dir / "id_list.json"
    
    async def load(self):
        """加载向量存储"""
        if not self.store_dir.exists():
            self.store_dir.mkdir(parents=True, exist_ok=True)
            print(f"创建新的向量存储目录: {self.store_dir}")
            return
        
        try:
            if self.vectors_file.exists():
                with open(self.vectors_file, 'r', encoding='utf-8') as f:
                    self.vectors = json.load(f)
            
            if self.contents_file.exists():
                with open(self.contents_file, 'r', encoding='utf-8') as f:
                    self.contents = json.load(f)
            
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            
            if self.id_list_file.exists():
                with open(self.id_list_file, 'r', encoding='utf-8') as f:
                    self.id_list = json.load(f)
            
            if self.index_file.exists():
                self._load_hnsw_index()
            
            if not self.vectors:
                await self._load_from_individual_files()
            
            if self.vectors and len(self.hnsw_index.vectors) == 0:
                self._build_hnsw_index()
            
            print(f"向量存储加载成功: {len(self.vectors)} 个向量")
            
        except Exception as e:
            print(f"加载向量存储失败: {e}")
    
    async def _load_from_individual_files(self):
        """从单独的 JSON 文件加载向量"""
        json_files = list(self.store_dir.glob("*.json"))
        json_files = [f for f in json_files if f.name not in ["vectors.json", "contents.json", "metadata.json", "id_list.json", "hnsw_index.json"]]
        
        print(f"从 {len(json_files)} 个单独文件加载向量...")
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                chunk_id = data.get("chunk_id")
                if chunk_id:
                    self.vectors[chunk_id] = data.get("embedding", [])
                    self.contents[chunk_id] = data.get("content", "")
                    self.metadata[chunk_id] = data.get("metadata", {})
                    self.id_list.append(chunk_id)
            except Exception as e:
                print(f"加载文件 {json_file} 失败: {e}")
        
        print(f"加载完成: {len(self.vectors)} 个向量")
    
    def _load_hnsw_index(self):
        """加载HNSW索引"""
        try:
            if self.hnsw_index.load(str(self.index_file)):
                print("HNSW索引加载成功")
            else:
                print("HNSW索引文件不存在")
                self.hnsw_index = HNSWIndex(
                    dimension=self.dimension,
                    M=self.M,
                    ef_construction=self.ef_construction,
                    ef_search=50
                )
        except Exception as e:
            print(f"加载HNSW索引失败: {e}")
            self.hnsw_index = HNSWIndex(
                dimension=self.dimension,
                M=self.M,
                ef_construction=self.ef_construction,
                ef_search=50
            )
    
    def _build_hnsw_index(self):
        """构建HNSW索引"""
        if not self.vectors:
            return
        
        try:
            for chunk_id in self.id_list:
                if chunk_id in self.vectors:
                    self.hnsw_index.add_vector(chunk_id, self.vectors[chunk_id])
            
            self.hnsw_index.save(str(self.index_file))
            print(f"HNSW索引构建成功: {len(self.vectors)} 个向量")
            
        except Exception as e:
            print(f"构建HNSW索引失败: {e}")
    
    async def add(
        self,
        chunk_id: str,
        vector: List[float],
        content: str,
        metadata: Dict[str, Any] = None
    ):
        """
        添加向量
        
        Args:
            chunk_id: Chunk ID
            vector: 向量
            content: 内容
            metadata: 元数据
        """
        self.vectors[chunk_id] = vector
        self.contents[chunk_id] = content
        self.metadata[chunk_id] = metadata or {}
        
        if chunk_id not in self.id_list:
            self.id_list.append(chunk_id)
    
    async def add_batch(
        self,
        items: List[Dict[str, Any]]
    ):
        """
        批量添加向量
        
        Args:
            items: 项目列表,每个包含chunk_id, vector, content, metadata
        """
        for item in items:
            await self.add(
                chunk_id=item['chunk_id'],
                vector=item['vector'],
                content=item['content'],
                metadata=item.get('metadata', {})
            )
    
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        use_hnsw: bool = True
    ) -> List[Dict[str, Any]]:
        """
        向量搜索
        
        Args:
            query_vector: 查询向量
            top_k: 返回结果数量
            use_hnsw: 是否使用HNSW索引
        
        Returns:
            搜索结果
        """
        if not self.vectors:
            return []
        
        if use_hnsw and self.hnsw_index:
            return self._search_hnsw(query_vector, top_k)
        else:
            return self._search_brute_force(query_vector, top_k)
    
    def _search_hnsw(
        self,
        query_vector: List[float],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """使用HNSW索引搜索"""
        try:
            results = self.hnsw_index.search(query_vector, top_k=top_k)
            
            search_results = []
            for chunk_id, similarity in results:
                search_results.append({
                    'id': chunk_id,
                    'content': self.contents.get(chunk_id, ''),
                    'metadata': self.metadata.get(chunk_id, {}),
                    'score': similarity,
                    'distance': 1.0 - similarity
                })
            
            return search_results
            
        except Exception as e:
            print(f"HNSW搜索失败: {e}")
            return self._search_brute_force(query_vector, top_k)
    
    def _search_brute_force(
        self,
        query_vector: List[float],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """暴力搜索"""
        from sklearn.metrics.pairwise import cosine_similarity
        
        results = []
        query_array = np.array([query_vector])
        
        for chunk_id, vector in self.vectors.items():
            vector_array = np.array([vector])
            similarity = cosine_similarity(query_array, vector_array)[0][0]
            
            results.append({
                'id': chunk_id,
                'content': self.contents.get(chunk_id, ''),
                'metadata': self.metadata.get(chunk_id, {}),
                'score': float(similarity),
                'distance': 1.0 - float(similarity)
            })
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]
    
    async def get_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取chunk
        
        Args:
            chunk_id: Chunk ID
        
        Returns:
            Chunk数据
        """
        if chunk_id not in self.vectors:
            return None
        
        return {
            'id': chunk_id,
            'content': self.contents.get(chunk_id, ''),
            'metadata': self.metadata.get(chunk_id, {}),
            'vector': self.vectors.get(chunk_id, [])
        }
    
    async def save(self):
        """保存向量存储"""
        try:
            with open(self.vectors_file, 'w', encoding='utf-8') as f:
                json.dump(self.vectors, f, ensure_ascii=False, indent=2)
            
            with open(self.contents_file, 'w', encoding='utf-8') as f:
                json.dump(self.contents, f, ensure_ascii=False, indent=2)
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
            
            with open(self.id_list_file, 'w', encoding='utf-8') as f:
                json.dump(self.id_list, f, ensure_ascii=False, indent=2)
            
            if len(self.hnsw_index.vectors) == 0 and self.vectors:
                self._build_hnsw_index()
            elif len(self.hnsw_index.vectors) > 0:
                self.hnsw_index.save(str(self.index_file))
            
            print(f"向量存储已保存: {len(self.vectors)} 个向量")
            
        except Exception as e:
            print(f"保存向量存储失败: {e}")
    
    async def clear(self):
        """清空向量存储"""
        self.vectors = {}
        self.contents = {}
        self.metadata = {}
        self.id_list = []
        self.hnsw_index = HNSWIndex(
            dimension=self.dimension,
            M=self.M,
            ef_construction=self.ef_construction,
            ef_search=50
        )
        
        if self.index_file.exists():
            self.index_file.unlink()
        
        print("向量存储已清空")
    
    def __len__(self):
        """返回向量数量"""
        return len(self.vectors)
