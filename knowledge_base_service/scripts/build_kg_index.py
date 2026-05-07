# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-22
# Copyright (c) 2026. All rights reserved.

"""
构建知识图谱HNSW索引

功能：
1. 加载已有的embeddings.json
2. 构建实体和关系的HNSW索引
3. 保存索引文件供后续检索使用

使用方法：
    python scripts/build_kg_index.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.vector_store.ann_index import HNSWIndex
from core.services.kg_retrieval_service import KGRetrievalService


async def build_kg_index():
    """构建知识图谱HNSW索引"""
    print("=" * 60)
    print("构建知识图谱HNSW索引")
    print("=" * 60)
    
    storage_path = Path("data/knowledge_graph")
    embeddings_file = storage_path / "embeddings.json"
    
    if not embeddings_file.exists():
        print(f"错误: embeddings文件不存在: {embeddings_file}")
        print("请先运行知识抽取流程生成embeddings")
        return
    
    print(f"\n1. 加载embeddings: {embeddings_file}")
    with open(embeddings_file, 'r', encoding='utf-8') as f:
        embeddings_data = json.load(f)
    
    entity_embeddings = embeddings_data.get("entity_embeddings", {})
    relation_embeddings = embeddings_data.get("relation_embeddings", {})
    
    print(f"   - 实体embeddings: {len(entity_embeddings)} 个")
    print(f"   - 关系embeddings: {len(relation_embeddings)} 个")
    
    if not entity_embeddings:
        print("错误: 没有实体embeddings")
        return
    
    print("\n2. 构建实体HNSW索引...")
    entity_index = HNSWIndex()
    
    for entity_id, embedding in entity_embeddings.items():
        entity_index.add_vector(entity_id, embedding)
    
    entity_stats = entity_index.get_stats()
    print(f"   - 向量数量: {entity_stats['total_vectors']}")
    print(f"   - 最大层级: {entity_stats['max_level']}")
    print(f"   - 平均连接数: {entity_stats['avg_connections']:.2f}")
    
    print("\n3. 构建关系HNSW索引...")
    relation_index = HNSWIndex()
    
    for relation_id, embedding in relation_embeddings.items():
        relation_index.add_vector(relation_id, embedding)
    
    relation_stats = relation_index.get_stats()
    print(f"   - 向量数量: {relation_stats['total_vectors']}")
    print(f"   - 最大层级: {relation_stats['max_level']}")
    print(f"   - 平均连接数: {relation_stats['avg_connections']:.2f}")
    
    print("\n4. 保存索引文件...")
    entity_index_file = storage_path / "entity_hnsw_index.json"
    relation_index_file = storage_path / "relation_hnsw_index.json"
    
    entity_index.save(str(entity_index_file))
    relation_index.save(str(relation_index_file))
    
    print(f"   - 实体索引: {entity_index_file}")
    print(f"   - 关系索引: {relation_index_file}")
    
    print("\n5. 验证索引...")
    kg_service = KGRetrievalService()
    await kg_service.load()
    
    stats = kg_service.get_stats()
    print(f"   - 索引已构建: {stats.get('hnsw_index_built', False)}")
    print(f"   - 实体索引统计: {stats.get('entity_index_stats', {})}")
    
    print("\n" + "=" * 60)
    print("知识图谱HNSW索引构建完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(build_kg_index())
