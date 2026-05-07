# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
知识库服务
"""
import json
import os
import re
from typing import Dict, Literal
from core.processors.knowledge_retriever import KnowledgeRetriever
from core.cache.query_cache import get_query_cache
from utils.logger import get_logger

logger = get_logger(__name__)


def _get_base_id(chunk_id: str) -> str:
    """从 chunk ID 提取基础 ID（去掉 _chunk_N 后缀）"""
    if "_chunk_" in chunk_id:
        return chunk_id.rsplit("_chunk_", 1)[0]
    return chunk_id


def _deduplicate_results(results: list) -> list:
    """按基础 ID 去重，保留分数最高的"""
    seen = {}
    for item in results:
        base_id = _get_base_id(item.get("id", ""))
        if base_id not in seen or item.get("vector_score", 0) > seen[base_id].get("vector_score", 0):
            seen[base_id] = item
    return list(seen.values())


def _parse_product_content(content: str) -> Dict:
    """将产品 content 文本解析为结构化字段"""
    result = {}
    field_map = {
        "产品名称": "name",
        "品牌": "brand",
        "类别": "category",
        "功效": "efficacy",
        "适用肤质": "applicable_skin",
        "容量": "capacity",
        "价格": "reference_price",
        "描述": "description",
    }
    labels = list(field_map.keys())
    for i, label in enumerate(labels):
        start_marker = f"{label}："
        start_idx = content.find(start_marker)
        if start_idx == -1:
            continue
        value_start = start_idx + len(start_marker)
        
        end_idx = len(content)
        for next_label in labels[i + 1:]:
            next_idx = content.find(f"{next_label}：", value_start)
            if next_idx != -1:
                end_idx = next_idx
                break
        
        result[field_map[label]] = content[value_start:end_idx].strip()

    tags_match = re.search(r"标签：(.+?)(?=\n|$)", content)
    if tags_match:
        result["tags"] = [t.strip() for t in tags_match.group(1).split(",")]

    return result


def _parse_entry_content(content: str) -> Dict:
    """将知识条目 content 文本解析为结构化字段"""
    result = {}
    field_map = {
        "标题": "title",
        "类别": "topic",
        "内容": "content_body",
        "来源": "source_url",
    }
    labels = list(field_map.keys())
    for i, label in enumerate(labels):
        start_marker = f"{label}："
        start_idx = content.find(start_marker)
        if start_idx == -1:
            continue
        value_start = start_idx + len(start_marker)
        
        end_idx = len(content)
        for next_label in labels[i + 1:]:
            next_idx = content.find(f"{next_label}：", value_start)
            if next_idx != -1:
                end_idx = next_idx
                break
        
        result[field_map[label]] = content[value_start:end_idx].strip()

    tags_match = re.search(r"标签：(.+?)(?=\n|$)", content)
    if tags_match:
        result["tags"] = [t.strip() for t in tags_match.group(1).split(",")]

    return result


class KnowledgeService:
    def __init__(self):
        self.retriever = KnowledgeRetriever()
        self.brand_group_map = {}
        self.group_info_map = {}
        self.group_brands_map = {}
        self.query_cache = get_query_cache()
        self._load_brand_group_mapping()
    
    def _load_brand_group_mapping(self):
        mapping_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data', 'brand_group_mapping.json'
        )
        try:
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.brand_group_map = data.get('brand_to_group', {})
                    self.group_info_map = data.get('group_info', {})
                    
                    self.group_brands_map = {}
                    for brand, group in self.brand_group_map.items():
                        if group not in self.group_brands_map:
                            self.group_brands_map[group] = []
                        self.group_brands_map[group].append(brand)
                    
                    for group in self.group_brands_map:
                        self.group_brands_map[group] = sorted(self.group_brands_map[group])
                        
        except Exception as e:
            logger.error(f"加载品牌集团映射失败: {e}")
    
    def _enrich_product_with_group(self, product: Dict) -> Dict:
        if product.get('group_name') or product.get('group_id'):
            return product
        
        brand = product.get('brand', '')
        if brand and brand in self.brand_group_map:
            group_name = self.brand_group_map[brand]
            product['group_name'] = group_name
            if group_name in self.group_info_map:
                product['group_description'] = self.group_info_map[group_name].get('description', '')
        
        return product
    
    async def search(
        self,
        query: str,
        top_k: int = 10,
        search_mode: Literal["hybrid", "vector", "graph", "keyword"] = "hybrid",
        use_ann: bool = True,
        threshold: float = 0.3,
        search_type: Literal["all", "products", "entries"] = "all",
        keyword_field: str = None
    ) -> Dict:
        """
        搜索知识库
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            search_mode: 搜索模式 (hybrid/vector/graph/keyword)
            use_ann: 是否使用 ANN 索引加速
            threshold: 相似度阈值
            search_type: 检索类型
                - all: 检索产品和知识条目
                - products: 仅检索产品
                - entries: 仅检索知识条目
            keyword_field: 精准匹配字段 (仅 keyword 模式)
        
        Raises:
            Exception: 搜索过程中的异常
        """
        if search_mode == "keyword":
            return await self._search_keyword(query, top_k, search_type, keyword_field)
        if search_mode == "graph":
            return await self._search_graph(query, top_k, threshold, search_type)
        
        cache_params = {
            'top_k': top_k,
            'search_mode': search_mode,
            'threshold': threshold,
            'search_type': search_type
        }
        
        cached_result = self.query_cache.get(query, **cache_params)
        if cached_result is not None:
            logger.debug(f"Query cache hit for: {query[:50]}...")
            cached_result['cache_hit'] = True
            return cached_result
        
        results = await self.retriever.search(
            query,
            top_k=top_k,
            search_type=search_type
        )
        
        for r in results:
            if r.get("type") == "product" and r.get("content"):
                parsed = _parse_product_content(r["content"])
                r.update(parsed)
            elif r.get("type") == "entry" and r.get("content"):
                parsed = _parse_entry_content(r["content"])
                r.update(parsed)
        
        results = _deduplicate_results(results)
        
        if threshold > 0:
            results = [r for r in results if r.get("vector_score", 1.0) >= threshold]
        
        result = {
            'query': query,
            'results': results,
            'total_found': len(results),
            'search_mode': search_mode,
            'search_type': search_type,
            'use_ann': use_ann,
            'threshold': threshold,
            'cache_hit': False
        }
        
        self.query_cache.set(query, result, **cache_params)
        
        return result
    
    async def _search_keyword(
        self,
        query: str,
        top_k: int,
        search_type: str,
        keyword_field: str = None
    ) -> Dict:
        """精准匹配模式 - 字符层面匹配，不走向量计算

        匹配字段：
          产品: name(名称), brand(品牌), category(类别), efficacy(功效), description(描述)
          知识条目: title(标题), topic(主题), content(正文)
        不传 keyword_field 则匹配所有字段。
        """
        query_lower = query.lower()
        all_products = await self.retriever.get_all_products()
        all_entries = await self.retriever.get_all_entries()

        product_fields = ["name", "brand", "category", "efficacy", "description"]
        entry_fields = ["title", "topic", "content"]

        results = []

        for p in all_products:
            if search_type == "entries":
                continue
            content = p.get("content", "")
            parsed = _parse_product_content(content)
            p.update(parsed)
            p = self._enrich_product_with_group(p)

            matched = False
            if keyword_field:
                field_value = parsed.get(keyword_field, "")
                if field_value and query_lower in field_value.lower():
                    matched = True
            else:
                for field in product_fields:
                    field_value = parsed.get(field, "")
                    if field_value and query_lower in field_value.lower():
                        matched = True
                        break

            if matched:
                p["vector_score"] = 1.0
                p["matched_field"] = keyword_field or "all"
                results.append(p)

        for e in all_entries:
            if search_type == "products":
                continue
            content = e.get("content", "")
            parsed = _parse_entry_content(content)
            e.update(parsed)

            matched = False
            if keyword_field:
                field_value = parsed.get(keyword_field, "")
                if field_value and query_lower in field_value.lower():
                    matched = True
            else:
                for field in entry_fields:
                    field_value = parsed.get(field, "")
                    if field_value and query_lower in field_value.lower():
                        matched = True
                        break

            if matched:
                e["vector_score"] = 1.0
                e["matched_field"] = keyword_field or "all"
                results.append(e)

        results = _deduplicate_results(results)
        results = results[:top_k]

        return {
            'query': query,
            'results': results,
            'total_found': len(results),
            'search_mode': 'keyword',
            'search_type': search_type,
            'use_ann': False,
            'threshold': 0,
            'cache_hit': False
        }

    async def _search_graph(
        self,
        query: str,
        top_k: int,
        threshold: float,
        search_type: str
    ) -> Dict:
        """图谱检索模式"""
        from core.services.graph_enhanced_rag_service import GraphEnhancedRAGService
        
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise Exception("DASHSCOPE_API_KEY not configured")
        
        service = GraphEnhancedRAGService(
            api_key=api_key,
            store_dir="data/chunk_embeddings"
        )
        await service.initialize()
        
        graph_result = await service.query(
            query=query,
            top_k=top_k,
            use_graph=True,
            use_vector=True,
            graph_weight=0.6,
            vector_weight=0.4
        )
        
        results = []
        raw_chunks = graph_result.get("chunks", [])
        for chunk in raw_chunks:
            item = {
                "content": chunk.get("content", ""),
                "vector_score": chunk.get("score", 0.0),
                "type": "entry",
                "source": "graph_rag"
            }
            if chunk.get("content"):
                parsed = _parse_entry_content(chunk["content"])
                item.update(parsed)
            results.append(item)
        
        if threshold > 0:
            results = [r for r in results if r.get("vector_score", 1.0) >= threshold]
        
        return {
            'query': query,
            'results': results,
            'total_found': len(results),
            'search_mode': 'graph',
            'search_type': search_type,
            'use_ann': True,
            'threshold': threshold,
            'cache_hit': False,
            'graph_entities': graph_result.get("entities", []),
            'graph_relations': graph_result.get("relations", [])
        }
    
    async def list_products(self, limit: int = 0) -> Dict:
        """列出所有产品（去重后）

        Args:
            limit: 返回数量限制，0 表示不限制
        """
        try:
            all_products = await self.retriever.get_all_products()
            for p in all_products:
                if p.get("content"):
                    parsed = _parse_product_content(p["content"])
                    p.update(parsed)
                p = self._enrich_product_with_group(p)
            all_products = _deduplicate_results(all_products)
            if limit > 0:
                all_products = all_products[:limit]
            return {
                'total_products': len(all_products),
                'products': all_products
            }
        except Exception as e:
            return {
                'total_products': 0,
                'products': [],
                'error': str(e)
            }

    async def list_entries(self, limit: int = 0) -> Dict:
        """列出所有知识条目（去重后）

        Args:
            limit: 返回数量限制，0 表示不限制
        """
        try:
            all_entries = await self.retriever.get_all_entries()
            for e in all_entries:
                if e.get("content"):
                    parsed = _parse_entry_content(e["content"])
                    e.update(parsed)
            all_entries = _deduplicate_results(all_entries)
            if limit > 0:
                all_entries = all_entries[:limit]
            return {
                'total_entries': len(all_entries),
                'entries': all_entries
            }
        except Exception as e:
            return {
                'total_entries': 0,
                'entries': [],
                'error': str(e)
            }
    
    async def list_all_data(
        self,
        page: int = 1,
        page_size: int = 50,
        group: str = None,
        brand: str = None
    ) -> Dict:
        """
        列出所有数据(产品和知识条目)
        
        Args:
            page: 页码,从1开始
            page_size: 每页数量
            group: 按集团筛选
            brand: 按品牌筛选
        """
        try:
            all_products = await self.retriever.get_all_products()
            entries = await self.retriever.get_all_entries()
            stats = await self.retriever.get_statistics()
            
            for p in all_products:
                if p.get("content"):
                    parsed = _parse_product_content(p["content"])
                    p.update(parsed)
                p = self._enrich_product_with_group(p)
            
            for e in entries:
                if e.get("content"):
                    parsed = _parse_entry_content(e["content"])
                    e.update(parsed)
            
            all_products = _deduplicate_results(all_products)
            entries = _deduplicate_results(entries)
            
            filtered_products = all_products
            if group:
                filtered_products = [
                    p for p in filtered_products
                    if p.get('group_name') == group or p.get('group_id') == group
                ]
            if brand:
                filtered_products = [
                    p for p in filtered_products
                    if p.get('brand') == brand
                ]
            
            total_products = len(filtered_products)
            total_pages = (total_products + page_size - 1) // page_size if total_products > 0 else 1
            
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paged_products = filtered_products[start_idx:end_idx]
            
            groups = set()
            brands = set()
            has_group_data = False
            
            for p in all_products:
                group_name = p.get('group_name') or p.get('group_id') or ''
                brand_name = p.get('brand') or ''
                
                if group_name:
                    groups.add(group_name)
                    has_group_data = True
                
                if brand_name:
                    brands.add(brand_name)
            
            if self.group_brands_map:
                groups = set(self.group_brands_map.keys())
                has_group_data = True
            
            return {
                'total_products': len(all_products),
                'total_entries': len(entries),
                'filtered_products': total_products,
                'products': paged_products,
                'entries': entries[:100],
                'statistics': stats,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                },
                'filters': {
                    'groups': sorted(list(groups)),
                    'brands': sorted(list(brands)),
                    'group_brands_map': self.group_brands_map,
                    'has_group_data': has_group_data
                }
            }
        except Exception as e:
            return {
                'total_products': 0,
                'total_entries': 0,
                'products': [],
                'entries': [],
                'error': str(e)
            }
