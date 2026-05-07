# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
RAG 路由 - 统一知识检索接口
"""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Literal

from core.processors.knowledge_retriever import KnowledgeRetriever
from core.vector_store.ann_index import ann_index_manager
from core.services.hybrid_retrieval_service import HybridRetrievalService
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG 检索"])

hybrid_service = None


async def get_hybrid_service():
    global hybrid_service
    if hybrid_service is None:
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY 未设置")
        
        hybrid_service = HybridRetrievalService(api_key=api_key)
        await hybrid_service.initialize()
    return hybrid_service


class RAGQueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 10
    search_mode: Optional[Literal["vector", "kg", "hybrid"]] = "hybrid"
    use_ann: Optional[bool] = True
    threshold: Optional[float] = 0.3
    intent: Optional[str] = None
    entities: Optional[List[str]] = None
    relations: Optional[List[str]] = None
    constraints: Optional[List[Dict[str, Any]]] = None
    rerank_top_k: Optional[int] = 10
    max_context_tokens: Optional[int] = 4000
    use_rerank: Optional[bool] = True
    use_dedup: Optional[bool] = True
    kg_weight: Optional[float] = 0.5
    vector_weight: Optional[float] = 0.5


class AddDocumentRequest(BaseModel):
    doc_id: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class RAGResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    data: Dict[str, Any] = {}


@router.post("/query", response_model=RAGResponse)
async def rag_query(request: RAGQueryRequest):
    """
    RAG 统一查询接口
    
    支持三种检索模式：
    - vector: 纯向量检索
    - kg: 纯知识图谱检索
    - hybrid: 混合检索（KG + 向量 + RRF 融合）
    
    前端可传入 entities 和 relations，跳过 LLM 关键词提取
    """
    try:
        use_kg = request.search_mode in ["kg", "hybrid"]
        use_vector = request.search_mode in ["vector", "hybrid"]
        
        service = await get_hybrid_service()
        
        result = await service.retrieve(
            query=request.query,
            entities=request.entities,
            relations=request.relations,
            top_k=request.top_k,
            kg_weight=request.kg_weight,
            vector_weight=request.vector_weight,
            use_kg=use_kg,
            use_vector=use_vector
        )
        
        chunks = result.get("chunks", [])
        
        if request.threshold > 0:
            chunks = [c for c in chunks if c.get("score", c.get("rrf_score", 1.0)) >= request.threshold]
        
        context_parts = []
        sources = []
        total_tokens = 0
        
        for i, chunk in enumerate(chunks):
            content = chunk.get("content", "")
            title = chunk.get("metadata", {}).get("name", chunk.get("id", "未知"))
            
            context_parts.append(f"【{i+1}】{title}\n{content}")
            sources.append({
                "id": chunk.get("id", ""),
                "title": title,
                "score": chunk.get("rrf_score", chunk.get("score", 0)),
                "source": chunk.get("source", "unknown")
            })
            
            total_tokens += len(content) // 2
        
        augmented_context = "\n\n".join(context_parts) if context_parts else ""
        
        return RAGResponse(
            msg="RAG查询完成",
            data={
                "augmented_context": augmented_context,
                "chunks": chunks,
                "total_chunks": len(chunks),
                "total_tokens": total_tokens,
                "sources": sources,
                "kg_chunks_count": result.get("kg_chunks_count", 0),
                "vector_chunks_count": result.get("vector_chunks_count", 0),
                "duration": result.get("duration", 0),
                "retrieval_metadata": {
                    "query": request.query,
                    "search_mode": request.search_mode,
                    "use_kg": use_kg,
                    "use_vector": use_vector,
                    "kg_weight": request.kg_weight,
                    "vector_weight": request.vector_weight,
                    "top_k": request.top_k,
                    "threshold": request.threshold,
                }
            },
        )
    except Exception as e:
        logger.error(f"RAG query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents", response_model=RAGResponse)
async def add_document(request: AddDocumentRequest):
    """
    添加文档到知识库
    
    自动执行: 分词 → 向量化 → 索引
    """
    try:
        from knowledge_base_service.core.layered_knowledge_manager import LayeredKnowledgeManager
        
        manager = LayeredKnowledgeManager()
        success = await manager.add_knowledge(
            title=request.doc_id,
            content=request.content,
            layer="specific",
            source_url=request.metadata.get("source", "") if request.metadata else "",
            tags=request.metadata.get("tags", []) if request.metadata else []
        )
        
        if success:
            return RAGResponse(
                msg="文档添加成功",
                data={"doc_id": request.doc_id},
            )
        else:
            return RAGResponse(
                msg="文档添加失败：内容可能已存在",
                data={},
            )
    except Exception as e:
        logger.error(f"Add document error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=RAGResponse)
async def get_stats():
    """
    获取知识库统计信息
    
    返回 KG 和向量存储的统计
    """
    try:
        service = await get_hybrid_service()
        stats = service.get_stats()
        
        return RAGResponse(
            msg="获取统计信息成功",
            data={
                "kg": stats.get("kg", {}),
                "vector": stats.get("vector", {})
            },
        )
    except Exception as e:
        logger.error(f"Get stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", tags=["系统管理"])
async def health_check():
    """
    RAG 子系统健康检查

    检查 RAG 检索服务是否正常运行。如需检查整体服务健康状态，请使用 GET /api/v1/health。
    """
    return {"status": "healthy", "service": "rag"}


@router.post("/build-ann-index", response_model=RAGResponse)
async def build_ann_index():
    """
    构建 ANN 索引
    
    使用 HNSW 算法构建近似最近邻索引，加速向量检索
    """
    try:
        retriever = KnowledgeRetriever(use_ann=True)
        stats = await retriever.build_ann_index()
        
        return RAGResponse(
            msg="ANN索引构建成功",
            data=stats,
        )
    except Exception as e:
        logger.error(f"Build ANN index error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ann-stats", response_model=RAGResponse, tags=["系统管理"])
async def get_ann_stats():
    """
    获取旧版 ANN 索引统计信息

    返回 data/indexes/ 目录下旧版 HNSW 索引的统计。
    当前核心检索使用 data/chunk_embeddings/ 下的索引，此接口仅用于兼容。
    """
    try:
        stats = ann_index_manager.get_stats()
        
        return RAGResponse(
            msg="获取ANN索引统计成功",
            data=stats,
        )
    except Exception as e:
        logger.error(f"Get ANN stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
