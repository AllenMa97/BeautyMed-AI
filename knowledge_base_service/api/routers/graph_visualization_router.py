# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-21
# Copyright (c) 2026. All rights reserved.

"""
知识图谱可视化路由
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import json
from pathlib import Path

router = APIRouter(prefix="/graph", tags=["知识图谱"])


@router.get("/visualization_data")
async def get_graph_visualization_data(
    max_nodes: int = 100,
    max_relations: int = 200,
    entity_type: str = None
) -> Dict[str, Any]:
    """
    获取知识图谱可视化数据
    
    Args:
        max_nodes: 最大节点数量
        max_relations: 最大关系数量
        entity_type: 实体类型过滤（可选）
    
    Returns:
        可视化数据（nodes 和 edges）
    """
    try:
        graph_file = Path("data/knowledge_graph/knowledge_graph.json")
        
        if not graph_file.exists():
            raise HTTPException(status_code=404, detail="知识图谱文件不存在，请先构建知识图谱")
        
        with open(graph_file, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
        
        entities = graph_data.get("entities", {})
        relations = graph_data.get("relations", [])
        
        # 构建节点数据
        nodes = []
        entity_id_to_index = {}
        
        for idx, (entity_id, entity) in enumerate(entities.items()):
            if idx >= max_nodes:
                break
            
            # 实体类型过滤
            if entity_type and entity.get("entity_type") != entity_type:
                continue
            
            entity_id_to_index[entity_id] = idx
            
            # 根据实体类型设置颜色
            entity_type_colors = {
                "产品/服务": "#FF6B6B",
                "成分/原料": "#4ECDC4",
                "功效/作用": "#45B7D1",
                "品牌/厂商": "#FFA07A",
                "适用对象": "#98D8C8",
                "分类/类别": "#F7DC6F",
                "数值/参数": "#BB8FCE",
                "其他重要实体": "#85C1E9"
            }
            
            color = entity_type_colors.get(entity.get("entity_type", ""), "#85C1E9")
            
            nodes.append({
                "id": idx,
                "label": entity.get("entity_name", ""),
                "title": f"{entity.get('entity_name', '')}\n类型: {entity.get('entity_type', '未知')}",
                "color": color,
                "size": 20,
                "font": {"size": 14, "color": "#333"},
                "entity_type": entity.get("entity_type", ""),
                "entity_id": entity_id
            })
        
        # 构建边数据
        edges = []
        edge_count = 0
        
        for relation in relations:
            if edge_count >= max_relations:
                break
            
            source_id = relation.get("source_entity_id")
            target_id = relation.get("target_entity_id")
            
            # 只添加两个节点都存在的边
            if source_id in entity_id_to_index and target_id in entity_id_to_index:
                edges.append({
                    "from": entity_id_to_index[source_id],
                    "to": entity_id_to_index[target_id],
                    "label": relation.get("relation_type", ""),
                    "title": f"{relation.get('relation_type', '')}\n置信度: {relation.get('confidence', 0):.2f}",
                    "arrows": "to",
                    "color": {"color": "#999", "highlight": "#FF6B6B"},
                    "width": 1.5,
                    "font": {"size": 10, "align": "middle"}
                })
                edge_count += 1
        
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_entities": len(entities),
                "total_relations": len(relations),
                "displayed_nodes": len(nodes),
                "displayed_edges": len(edges)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识图谱数据失败: {str(e)}")


@router.get("/stats")
async def get_graph_stats() -> Dict[str, Any]:
    """
    获取知识图谱统计信息
    """
    try:
        graph_file = Path("data/knowledge_graph/knowledge_graph.json")
        
        if not graph_file.exists():
            return {
                "exists": False,
                "message": "知识图谱文件不存在，请先构建知识图谱"
            }
        
        with open(graph_file, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
        
        entities = graph_data.get("entities", {})
        relations = graph_data.get("relations", [])
        
        # 统计实体类型分布
        entity_type_distribution = {}
        for entity in entities.values():
            entity_type = entity.get("entity_type", "未知")
            entity_type_distribution[entity_type] = entity_type_distribution.get(entity_type, 0) + 1
        
        # 统计关系类型分布
        relation_type_distribution = {}
        for relation in relations:
            relation_type = relation.get("relation_type", "未知")
            relation_type_distribution[relation_type] = relation_type_distribution.get(relation_type, 0) + 1
        
        return {
            "exists": True,
            "total_entities": len(entities),
            "total_relations": len(relations),
            "entity_type_distribution": entity_type_distribution,
            "relation_type_distribution": relation_type_distribution,
            "chunks_with_entities": len(graph_data.get("chunk_to_entities", {}))
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/entity/{entity_id}")
async def get_entity_details(entity_id: str) -> Dict[str, Any]:
    """
    获取实体详细信息
    """
    try:
        graph_file = Path("data/knowledge_graph/knowledge_graph.json")
        
        if not graph_file.exists():
            raise HTTPException(status_code=404, detail="知识图谱文件不存在")
        
        with open(graph_file, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
        
        entities = graph_data.get("entities", {})
        relations = graph_data.get("relations", [])
        
        if entity_id not in entities:
            raise HTTPException(status_code=404, detail="实体不存在")
        
        entity = entities[entity_id]
        
        # 找到与该实体相关的所有关系
        related_relations = []
        for relation in relations:
            if relation.get("source_entity_id") == entity_id or relation.get("target_entity_id") == entity_id:
                related_relations.append(relation)
        
        # 找到相关的 chunks
        entity_to_chunks = graph_data.get("entity_to_chunks", {})
        related_chunks = entity_to_chunks.get(entity_id, [])
        
        return {
            "entity": entity,
            "related_relations": related_relations,
            "related_chunks": related_chunks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取实体详情失败: {str(e)}")
