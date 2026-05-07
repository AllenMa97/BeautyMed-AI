# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
知识库路由
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import json
import csv
import io

from api.schemas.knowledge_schemas import (
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    ProductAddRequest,
    KnowledgeAddRequest
)
from core.services.knowledge_service import KnowledgeService
from core.services.knowledge_manager_service import KnowledgeManagerService
from core.layered_knowledge_manager import LayeredKnowledgeManager
from core.processors.knowledge_retriever import KnowledgeRetriever
from utils.logger import get_logger

router = APIRouter(prefix="/knowledge")
logger = get_logger(__name__)


# ========== 知识检索（供 /knowledge 页面和搜索功能使用） ==========

@router.post("/search", response_model=KnowledgeSearchResponse, tags=["知识检索"])
async def search_knowledge(request: KnowledgeSearchRequest):
    """
    知识库搜索

    前端知识库页面（/knowledge）的搜索框调用此接口。
    search_mode 参数支持四种检索模式：
    - **hybrid**（默认）：混合检索，结合向量检索和知识图谱检索
    - **vector**：纯向量检索，基于 HNSW 索引的近似最近邻搜索
    - **graph**：纯图谱检索，通过实体识别和关系推理检索相关知识
    - **keyword**：精准匹配，字符层面匹配，不走向量计算。可通过 keyword_field 指定匹配字段

    search_type 参数支持三种检索类型：
    - **all**（默认）：检索所有知识条目（包含产品和知识条目）
    - **products** 、 **entries**：分别检索产品和知识条目

    返回结果按相似度排序，可通过 threshold 过滤低分结果。
    """
    try:
        service = KnowledgeService()
        result = await service.search(
            query=request.query,
            top_k=request.top_k,
            search_mode=request.search_mode,
            use_ann=request.use_ann,
            threshold=request.threshold,
            search_type=request.search_type,
            keyword_field=request.keyword_field
        )
        return KnowledgeSearchResponse(msg="搜索完成", data=result)
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/list_all", response_model=KnowledgeSearchResponse, tags=["知识检索"])
async def list_all_data(
    page: int = 1,
    page_size: int = 50,
    group: str = None,
    brand: str = None
):
    """
    获取知识库全量数据（分页，给管理页面用）

    前端知识库页面（/knowledge）加载时调用此接口，返回分页产品、全部知识条目、筛选器选项（集团/品牌下拉列表）。

    如只需获取全部产品（不分页），请使用 GET /api/v1/knowledge/list_products。
    如只需获取全部知识条目（不分页），请使用 GET /api/v1/knowledge/list_entries。
    """
    service = KnowledgeService()
    result = await service.list_all_data(
        page=page,
        page_size=page_size,
        group=group,
        brand=brand
    )
    return KnowledgeSearchResponse(msg="数据列表获取成功", data=result)


@router.get("/list_products", response_model=KnowledgeSearchResponse, tags=["知识检索"])
async def list_products(limit: int = 0):
    """
    获取全部产品（仅产品，不含知识条目）

    供其他服务调用，返回去重后的全部产品列表。不分页。
    可通过 limit 参数限制返回数量，0 表示不限制。

    如需获取产品+条目的分页数据（给管理页面用），请使用 GET /api/v1/knowledge/list_all。
    """
    service = KnowledgeService()
    result = await service.list_products(limit=limit)
    return KnowledgeSearchResponse(msg="产品列表获取成功", data=result)


@router.get("/list_entries", response_model=KnowledgeSearchResponse, tags=["知识检索"])
async def list_entries(limit: int = 0):
    """
    获取全部知识条目（仅条目，不含产品）

    供其他服务调用，返回去重后的全部知识条目列表。不分页。
    可通过 limit 参数限制返回数量，0 表示不限制。

    如需获取产品+条目的分页数据（给管理页面用），请使用 GET /api/v1/knowledge/list_all。
    """
    service = KnowledgeService()
    result = await service.list_entries(limit=limit)
    return KnowledgeSearchResponse(msg="知识条目列表获取成功", data=result)


@router.get("/product/{product_id}", response_model=KnowledgeSearchResponse, tags=["知识检索"])
async def get_product(product_id: str):
    """
    获取单个产品详情

    根据产品 ID 获取产品的完整信息，包括名称、品牌、类别、功效等字段。
    """
    try:
        retriever = KnowledgeRetriever()
        product = await retriever.get_product_by_id(product_id)

        if product:
            return KnowledgeSearchResponse(msg="success", data=product)
        else:
            return KnowledgeSearchResponse(msg="产品不存在", data={})
    except Exception as e:
        logger.error(f"Failed to get product: {str(e)}")
        return KnowledgeSearchResponse(msg=f"获取产品失败: {str(e)}", data={})


@router.get("/entry/{entry_id}", response_model=KnowledgeSearchResponse, tags=["知识检索"])
async def get_entry(entry_id: str):
    """
    获取单个知识条目详情

    根据条目 ID 获取知识条目的完整信息，包括标题、类别、正文内容等。
    """
    try:
        retriever = KnowledgeRetriever()
        entry = await retriever.get_entry_by_id(entry_id)

        if entry:
            return KnowledgeSearchResponse(msg="success", data=entry)
        else:
            return KnowledgeSearchResponse(msg="知识条目不存在", data={})
    except Exception as e:
        logger.error(f"Failed to get entry: {str(e)}")
        return KnowledgeSearchResponse(msg=f"获取知识条目失败: {str(e)}", data={})


# ========== 知识管理（增删改） ==========

@router.post("/add_product", response_model=KnowledgeSearchResponse, tags=["知识管理"])
async def add_product(request: ProductAddRequest):
    """
    添加产品

    手动添加一个医美产品到知识库。添加后会自动生成向量嵌入并更新 HNSW 索引。
    """
    try:
        manager = KnowledgeManagerService()
        product_data = request.dict()
        product_id = await manager.add_product(product_data)

        logger.info(f"Product added successfully: {request.name} (ID: {product_id})")
        return KnowledgeSearchResponse(
            msg="success",
            data={"product_id": product_id, "name": request.name}
        )
    except Exception as e:
        logger.error(f"Failed to add product: {str(e)}")
        return KnowledgeSearchResponse(
            msg=f"添加产品失败: {str(e)}",
            data={}
        )


@router.post("/add_knowledge", response_model=KnowledgeSearchResponse, tags=["知识管理"])
async def add_knowledge(request: KnowledgeAddRequest):
    """
    添加知识条目

    手动添加一条知识条目到知识库。添加后会自动生成向量嵌入并更新索引。
    """
    try:
        manager = LayeredKnowledgeManager()
        success = await manager.add_knowledge(
            title=request.title,
            content=request.content,
            category=request.category,
            references=request.references,
            tags=request.tags
        )

        if success:
            logger.info(f"Knowledge added successfully: {request.title}")
            return KnowledgeSearchResponse(
                msg="success",
                data={"title": request.title, "category": request.category}
            )
        else:
            return KnowledgeSearchResponse(
                msg="知识添加失败：内容可能已存在或质量不足",
                data={}
            )
    except Exception as e:
        logger.error(f"Failed to add knowledge: {str(e)}")
        return KnowledgeSearchResponse(
            msg=f"添加知识失败: {str(e)}",
            data={}
        )


@router.post("/import", response_model=KnowledgeSearchResponse, tags=["知识管理"])
async def import_knowledge(files: List[UploadFile] = File(...)):
    """
    批量导入知识（文件上传）

    支持 JSON、CSV、Markdown 三种格式的文件导入。
    - JSON：数组格式，包含产品（name+description）或知识条目（title+content）
    - CSV：表头需包含 name/description（产品）或 title/content（知识条目）
    - Markdown：以 # 分隔的章节，每个章节作为一条知识条目
    """
    try:
        products_imported = 0
        knowledge_imported = 0
        errors = []

        retriever = KnowledgeRetriever()
        product_manager = KnowledgeManagerService()
        knowledge_manager = LayeredKnowledgeManager()

        for file in files:
            try:
                content = await file.read()
                filename = file.filename.lower()

                if filename.endswith('.json'):
                    data = json.loads(content.decode('utf-8'))

                    if isinstance(data, list):
                        for item in data:
                            if 'name' in item and 'description' in item:
                                product_id = await product_manager.add_product(item)
                                if product_id:
                                    products_imported += 1
                            elif 'title' in item and 'content' in item:
                                success = await knowledge_manager.add_knowledge(
                                    title=item.get('title'),
                                    content=item.get('content'),
                                    layer=item.get('layer', 'specific'),
                                    source_url=item.get('source_url', ''),
                                    tags=item.get('tags', [])
                                )
                                if success:
                                    knowledge_imported += 1

                elif filename.endswith('.csv'):
                    csv_reader = csv.DictReader(io.StringIO(content.decode('utf-8')))
                    for row in csv_reader:
                        if 'name' in row and 'description' in row:
                            if 'tags' in row and isinstance(row['tags'], str):
                                row['tags'] = [t.strip() for t in row['tags'].split(',')]
                            product_id = await product_manager.add_product(row)
                            if product_id:
                                products_imported += 1
                        elif 'title' in row and 'content' in row:
                            if 'tags' in row and isinstance(row['tags'], str):
                                row['tags'] = [t.strip() for t in row['tags'].split(',')]
                            success = await knowledge_manager.add_knowledge(
                                title=row.get('title'),
                                content=row.get('content'),
                                layer=row.get('layer', 'specific'),
                                source_url=row.get('source_url', ''),
                                tags=row.get('tags', [])
                            )
                            if success:
                                knowledge_imported += 1

                elif filename.endswith('.md') or filename.endswith('.txt'):
                    text_content = content.decode('utf-8')
                    sections = text_content.split('\n# ')

                    for section in sections:
                        if not section.strip():
                            continue

                        lines = section.strip().split('\n')
                        title = lines[0].replace('#', '').strip()

                        metadata = {}
                        content_lines = []
                        in_content = False

                        for line in lines[1:]:
                            if line.startswith('**') and ':**' in line:
                                key_value = line.replace('**', '').split(':**')
                                if len(key_value) == 2:
                                    key = key_value[0].strip().lower()
                                    value = key_value[1].strip()
                                    metadata[key] = value
                            elif line.startswith('## 内容'):
                                in_content = True
                            elif in_content or line.strip():
                                content_lines.append(line)

                        content_text = '\n'.join(content_lines).strip()

                        if title and content_text:
                            tags = []
                            if 'tags' in metadata:
                                tags = [t.strip() for t in metadata['tags'].split(',')]

                            success = await knowledge_manager.add_knowledge(
                                title=title,
                                content=content_text,
                                layer=metadata.get('层级', metadata.get('layer', 'specific')),
                                source_url=metadata.get('来源', metadata.get('source', '')),
                                tags=tags
                            )
                            if success:
                                knowledge_imported += 1

            except Exception as e:
                errors.append(f"{file.filename}: {str(e)}")
                logger.error(f"Error processing file {file.filename}: {str(e)}")

        result = {
            "products_imported": products_imported,
            "knowledge_imported": knowledge_imported,
            "total_imported": products_imported + knowledge_imported,
            "files_processed": len(files)
        }

        if errors:
            result["errors"] = errors

        logger.info(f"Import completed: {products_imported} products, {knowledge_imported} knowledge entries")
        return KnowledgeSearchResponse(msg="success", data=result)

    except Exception as e:
        logger.error(f"Import failed: {str(e)}")
        return KnowledgeSearchResponse(
            msg=f"导入失败: {str(e)}",
            data={}
        )


@router.put("/product/{product_id}", response_model=KnowledgeSearchResponse, tags=["知识管理"])
async def update_product(product_id: str, request: ProductAddRequest):
    """
    更新产品信息

    根据产品 ID 更新产品的名称、品牌、描述等字段。更新后会重新生成向量嵌入。
    """
    try:
        manager = KnowledgeManagerService()
        product_data = request.dict(exclude_unset=True)
        success = await manager.update_product(product_id, product_data)

        if success:
            logger.info(f"Product updated successfully: {product_id}")
            return KnowledgeSearchResponse(msg="更新成功", data={"product_id": product_id})
        else:
            return KnowledgeSearchResponse(msg="产品不存在或更新失败", data={})
    except Exception as e:
        logger.error(f"Failed to update product: {str(e)}")
        return KnowledgeSearchResponse(msg=f"更新产品失败: {str(e)}", data={})


@router.delete("/product/{product_id}", response_model=KnowledgeSearchResponse, tags=["知识管理"])
async def delete_product(product_id: str):
    """
    删除产品

    根据产品 ID 从知识库中删除产品及其向量数据。
    """
    try:
        manager = KnowledgeManagerService()
        success = await manager.delete_product(product_id)

        if success:
            logger.info(f"Product deleted successfully: {product_id}")
            return KnowledgeSearchResponse(msg="删除成功", data={"product_id": product_id})
        else:
            return KnowledgeSearchResponse(msg="产品不存在或删除失败", data={})
    except Exception as e:
        logger.error(f"Failed to delete product: {str(e)}")
        return KnowledgeSearchResponse(msg=f"删除产品失败: {str(e)}", data={})


@router.put("/entry/{entry_id}", response_model=KnowledgeSearchResponse, tags=["知识管理"])
async def update_entry(entry_id: str, request: KnowledgeAddRequest):
    """
    更新知识条目

    根据条目 ID 更新知识条目的标题、内容等字段。更新后会重新生成向量嵌入。
    """
    try:
        manager = KnowledgeManagerService()
        entry_data = request.dict(exclude_unset=True)
        success = await manager.update_entry(entry_id, entry_data)

        if success:
            logger.info(f"Entry updated successfully: {entry_id}")
            return KnowledgeSearchResponse(msg="更新成功", data={"entry_id": entry_id})
        else:
            return KnowledgeSearchResponse(msg="知识条目不存在或更新失败", data={})
    except Exception as e:
        logger.error(f"Failed to update entry: {str(e)}")
        return KnowledgeSearchResponse(msg=f"更新知识条目失败: {str(e)}", data={})


@router.delete("/entry/{entry_id}", response_model=KnowledgeSearchResponse, tags=["知识管理"])
async def delete_entry(entry_id: str):
    """
    删除知识条目

    根据条目 ID 从知识库中删除知识条目及其向量数据。
    """
    try:
        manager = KnowledgeManagerService()
        success = await manager.delete_entry(entry_id)

        if success:
            logger.info(f"Entry deleted successfully: {entry_id}")
            return KnowledgeSearchResponse(msg="删除成功", data={"entry_id": entry_id})
        else:
            return KnowledgeSearchResponse(msg="知识条目不存在或删除失败", data={})
    except Exception as e:
        logger.error(f"Failed to delete entry: {str(e)}")
        return KnowledgeSearchResponse(msg=f"删除知识条目失败: {str(e)}", data={})


# ========== 系统管理 ==========

@router.get("/index_status", response_model=KnowledgeSearchResponse, tags=["系统管理"])
async def get_index_status():
    """
    获取向量索引状态

    返回当前 HNSW 向量索引的向量数量和维度信息。
    索引数据存储在 data/chunk_embeddings/ 目录下。
    """
    try:
        from core.vector_store.chunk_vector_store import ChunkVectorStore
        store = ChunkVectorStore(store_dir="data/chunk_embeddings")
        await store.load()

        return KnowledgeSearchResponse(
            msg="success",
            data={
                "vector_count": len(store.id_list),
                "dimension": store.dimension,
                "status": "loaded"
            }
        )
    except Exception as e:
        logger.error(f"Failed to get index status: {str(e)}")
        return KnowledgeSearchResponse(msg=f"获取索引状态失败: {str(e)}", data={})


@router.get("/cache_stats", response_model=KnowledgeSearchResponse, tags=["系统管理"])
async def get_cache_stats():
    """
    获取查询缓存统计

    返回查询缓存的命中次数、缓存条目数等信息。
    缓存数据存储在 data/query_cache/ 目录下。
    """
    try:
        from core.cache.query_cache import get_query_cache

        cache = get_query_cache()
        stats = cache.get_stats()

        return KnowledgeSearchResponse(msg="success", data=stats)
    except Exception as e:
        logger.error(f"Failed to get cache stats: {str(e)}")
        return KnowledgeSearchResponse(msg=f"获取缓存统计失败: {str(e)}", data={})


@router.post("/clear_cache", response_model=KnowledgeSearchResponse, tags=["系统管理"])
async def clear_cache():
    """
    清除查询缓存

    清空所有已缓存的查询结果，下次搜索将重新计算。
    """
    try:
        from core.cache.query_cache import get_query_cache

        cache = get_query_cache()
        cache.invalidate()

        return KnowledgeSearchResponse(msg="缓存已清除", data={})
    except Exception as e:
        logger.error(f"Failed to clear cache: {str(e)}")
        return KnowledgeSearchResponse(msg=f"清除缓存失败: {str(e)}", data={})
