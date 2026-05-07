# Developer: 马赫·马智?
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
ANN (Approximate Nearest Neighbor) 索引
使用 HNSW (Hierarchical Navigable Small World) 算法加速向量检?

性能对比?
- 暴力搜索:O(N) - 遍历所有向?
- HNSW搜索:O(log N) - 近似最近邻,召回率 95%+

适用场景?
- 向量数量 > 1000 时显著提升性能
- 召回率要求不?100% 的场?
"""
import os
import json
import heapq
import numpy as np
from typing import List, Dict, Tuple, Optional, Set
from config.settings import get_embedding_dimension, get_hnsw_m, get_hnsw_ef_construction, get_hnsw_ef_search
from pathlib import Path
from collections import defaultdict
import random
import math

from utils.logger import get_logger

logger = get_logger(__name__)


class HNSWIndex:
    """
    HNSW (Hierarchical Navigable Small World) 索引
    
    核心思想
    1. 构建多层图结构,上层稀疏,下层密集
    2. 搜索时从上层开始,逐层向下逼近
    3. 每层使用贪心搜索找到最近邻
    
    参数说明
    - M: 每个节点的最大连接数(影响索引大小和召回率)
    - ef_construction: 构建时的候选列表大小(影响构建质量和速度)
    - ef_search: 搜索时的候选列表大小(影响召回率和速度)
    """
    
    def __init__(
        self,
        dimension: int = None,
        M: int = 16,
        ef_construction: int = None,
        ef_search: int = None,
        ml: float = None
    ):
        self.dimension = dimension or get_embedding_dimension()
        self.M = M or get_hnsw_m()
        self.M_max = self.M
        self.M_max0 = self.M * 2
        self.ef_construction = ef_construction or get_hnsw_ef_construction()
        self.ef_search = ef_search or get_hnsw_ef_search()
        
        self.ml = ml if ml else 1.0 / math.log(self.M)
        
        self.vectors: Dict[str, np.ndarray] = {}
        self.id_list: List[str] = []
        
        self.graphs: List[Dict[str, Set[str]]] = []
        self.entry_point: Optional[str] = None
        self.max_level: int = -1
        
        self.level_stats: Dict[int, int] = defaultdict(int)
    
    def _cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))
    
    def _distance(self, v1: np.ndarray, v2: np.ndarray) -> float:
        return 1.0 - self._cosine_similarity(v1, v2)
    
    def _random_level(self) -> int:
        """随机生成节点层级"""
        r = random.random()
        level = int(-math.log(r) * self.ml)
        return min(level, 50)
    
    def _get_neighbors(self, node_id: str, level: int) -> Set[str]:
        
        if level >= len(self.graphs):
            return set()
        return self.graphs[level].get(node_id, set())
    
    def _set_neighbors(self, node_id: str, level: int, neighbors: Set[str]):
        
        while level >= len(self.graphs):
            self.graphs.append({})
        self.graphs[level][node_id] = neighbors
    
    def _search_layer(
        self,
        query: np.ndarray,
        entry_points: Set[str],
        ef: int,
        level: int
    ) -> List[Tuple[float, str]]:
        """
        在指定层搜索最近邻
        
        使用贪心搜索 + 候选列表
        """
        visited = set(entry_points)
        
        candidates = []
        results = []
        
        for ep in entry_points:
            if ep in self.vectors:
                dist = self._distance(query, self.vectors[ep])
                heapq.heappush(candidates, (dist, ep))
                heapq.heappush(results, (-dist, ep))
        
        while candidates:
            dist_c, node_c = heapq.heappop(candidates)
            
            dist_f = -results[0][0] if results else float('inf')
            
            if dist_c > dist_f:
                break
            
            neighbors = self._get_neighbors(node_c, level)
            
            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    
                    if neighbor in self.vectors:
                        dist_n = self._distance(query, self.vectors[neighbor])
                        
                        if dist_n < dist_f or len(results) < ef:
                            heapq.heappush(candidates, (dist_n, neighbor))
                            heapq.heappush(results, (-dist_n, neighbor))
                            
                            if len(results) > ef:
                                heapq.heappop(results)
        
        result_list = [(-dist, node) for dist, node in results]
        result_list.sort()
        return result_list
    
    def _select_neighbors_simple(
        self,
        candidates: List[Tuple[float, str]],
        M: int
    ) -> List[str]:
        candidates.sort()
        return [node for _, node in candidates[:M]]
    
    def _select_neighbors_heuristic(
        self,
        query: np.ndarray,
        candidates: List[Tuple[float, str]],
        M: int,
        level: int,
        extend_candidates: bool = True
    ) -> List[str]:
        """
        启发式选择邻居
        
        考虑多样性,避免邻居之间过于相似
        """
        if len(candidates) <= M:
            return [node for _, node in candidates]
        
        candidates.sort()
        selected = []
        
        for dist, node in candidates:
            if len(selected) >= M:
                break
            
            if node not in self.vectors:
                continue
            
            node_vec = self.vectors[node]
            
            good = True
            for s in selected:
                if s in self.vectors:
                    dist_to_selected = self._distance(node_vec, self.vectors[s])
                    if dist_to_selected < dist:
                        good = False
                        break
            
            if good:
                selected.append(node)
        
        return selected
    
    def add_vector(self, item_id: str, vector: List[float]):
        vec = np.array(vector, dtype=np.float32)
        self.vectors[item_id] = vec
        self.id_list.append(item_id)
        
        if self.entry_point is None:
            self.entry_point = item_id
            self.max_level = 0
            self._set_neighbors(item_id, 0, set())
            self.level_stats[0] += 1
            return
        
        level = self._random_level()
        self.level_stats[level] += 1
        
        while level >= len(self.graphs):
            self.graphs.append({})
        
        query = vec
        
        curr_entry = {self.entry_point}
        curr_level = self.max_level
        
        for lc in range(curr_level, level, -1):
            results = self._search_layer(query, curr_entry, ef=1, level=lc)
            if results:
                curr_entry = {results[0][1]}
        
        for lc in range(min(level, curr_level), -1, -1):
            results = self._search_layer(query, curr_entry, ef=self.ef_construction, level=lc)
            
            M_max = self.M_max0 if lc == 0 else self.M_max
            neighbors = self._select_neighbors_heuristic(query, results, M_max, lc)
            
            self._set_neighbors(item_id, lc, set(neighbors))
            
            for neighbor in neighbors:
                neighbor_neighbors = self._get_neighbors(neighbor, lc)
                neighbor_neighbors.add(item_id)
                
                M_max_neighbor = self.M_max0 if lc == 0 else self.M_max
                if len(neighbor_neighbors) > M_max_neighbor:
                    neighbor_vec = self.vectors[neighbor]
                    neighbor_candidates = [
                        (self._distance(neighbor_vec, self.vectors[n]), n)
                        for n in neighbor_neighbors if n in self.vectors
                    ]
                    new_neighbors = self._select_neighbors_simple(neighbor_candidates, M_max_neighbor)
                    self._set_neighbors(neighbor, lc, set(new_neighbors))
                else:
                    self._set_neighbors(neighbor, lc, neighbor_neighbors)
            
            if results:
                curr_entry = {r[1] for r in results}
        
        if level > self.max_level:
            self.entry_point = item_id
            self.max_level = level
    
    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        ef: int = None
    ) -> List[Tuple[str, float]]:
        if self.entry_point is None or len(self.vectors) == 0:
            return []
        
        query = np.array(query_vector, dtype=np.float32)
        ef = ef or max(self.ef_search, top_k)
        
        curr_entry = {self.entry_point}
        
        for level in range(self.max_level, 0, -1):
            results = self._search_layer(query, curr_entry, ef=1, level=level)
            if results:
                curr_entry = {results[0][1]}
        
        results = self._search_layer(query, curr_entry, ef=ef, level=0)
        
        return [(node, 1.0 - dist) for dist, node in results[:top_k]]
    
    def get_stats(self) -> Dict:
        """获取索引统计信息"""
        total_connections = 0
        for level, graph in enumerate(self.graphs):
            for node, neighbors in graph.items():
                total_connections += len(neighbors)
        
        return {
            "total_vectors": len(self.vectors),
            "dimension": self.dimension,
            "max_level": self.max_level,
            "entry_point": self.entry_point,
            "M": self.M,
            "ef_construction": self.ef_construction,
            "ef_search": self.ef_search,
            "total_connections": total_connections,
            "avg_connections": total_connections / max(len(self.vectors), 1),
            "level_distribution": dict(self.level_stats)
        }
    
    def save(self, filepath: str):
        data = {
            "dimension": self.dimension,
            "M": self.M,
            "M_max": self.M_max,
            "M_max0": self.M_max0,
            "ef_construction": self.ef_construction,
            "ef_search": self.ef_search,
            "ml": self.ml,
            "entry_point": self.entry_point,
            "max_level": self.max_level,
            "id_list": self.id_list,
            "vectors": {k: v.tolist() for k, v in self.vectors.items()},
            "graphs": [
                {k: list(v) for k, v in graph.items()}
                for graph in self.graphs
            ],
            "level_stats": dict(self.level_stats)
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        
        logger.info(f"HNSW索引已保存 {filepath}")
    
    def load(self, filepath: str):
        
        if not os.path.exists(filepath):
            logger.warning(f"索引文件不存在 {filepath}")
            return False
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.dimension = data["dimension"]
        self.M = data["M"]
        self.M_max = data["M_max"]
        self.M_max0 = data["M_max0"]
        self.ef_construction = data["ef_construction"]
        self.ef_search = data["ef_search"]
        self.ml = data["ml"]
        self.entry_point = data["entry_point"]
        self.max_level = data["max_level"]
        self.id_list = data["id_list"]
        self.vectors = {k: np.array(v, dtype=np.float32) for k, v in data["vectors"].items()}
        self.graphs = [
            {k: set(v) for k, v in graph.items()}
            for graph in data["graphs"]
        ]
        self.level_stats = defaultdict(int, data.get("level_stats", {}))
        
        logger.info(f"HNSW索引已加载 {len(self.vectors)} 个向量 ")
        return True


class ANNIndexManager:
    """
    ANN索引管理
    
    管理产品和知识条目的向量索引
    """
    
    def __init__(self, storage_dir: str = "data/indexes"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.product_index = HNSWIndex()
        self.entry_index = HNSWIndex()
        
        self.product_index_file = self.storage_dir / "products_hnsw.json"
        self.entry_index_file = self.storage_dir / "medical_hnsw.json"
        
        self._loaded = False
    
    def load_indexes(self) -> bool:
        """加载索引"""
        product_loaded = self.product_index.load(str(self.product_index_file))
        entry_loaded = self.entry_index.load(str(self.entry_index_file))
        self._loaded = product_loaded or entry_loaded
        return self._loaded
    
    def save_indexes(self):
        """保存索引"""
        self.product_index.save(str(self.product_index_file))
        self.entry_index.save(str(self.entry_index_file))
    
    def add_product(self, product_id: str, vector: List[float]):
        """添加产品向量"""
        self.product_index.add_vector(product_id, vector)
    
    def add_entry(self, entry_id: str, vector: List[float]):
        """添加知识条目向量"""
        self.entry_index.add_vector(entry_id, vector)
    
    def search_products(
        self,
        query_vector: List[float],
        top_k: int = 10,
        ef: int = None
    ) -> List[Tuple[str, float]]:
        """搜索产品"""
        return self.product_index.search(query_vector, top_k, ef)
    
    def search_entries(
        self,
        query_vector: List[float],
        top_k: int = 10,
        ef: int = None
    ) -> List[Tuple[str, float]]:
        """搜索知识条目"""
        return self.entry_index.search(query_vector, top_k, ef)
    
    def search_all(
        self,
        query_vector: List[float],
        top_k: int = 10,
        ef: int = None
    ) -> List[Tuple[str, float]]:
        """搜索所有(产品+知识条目)"""
        product_results = self.search_products(query_vector, top_k * 2, ef)
        entry_results = self.search_entries(query_vector, top_k * 2, ef)
        
        all_results = product_results + entry_results
        all_results.sort(key=lambda x: x[1], reverse=True)
        
        return all_results[:top_k]
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "product_index": self.product_index.get_stats(),
            "entry_index": self.entry_index.get_stats()
        }
    
    def is_loaded(self) -> bool:
        """检查索引是否已加载"""
        return self._loaded
    
    def get_vector_count(self) -> int:
        """获取向量总数"""
        return len(self.product_index.vectors) + len(self.entry_index.vectors)


ann_index_manager = ANNIndexManager()
