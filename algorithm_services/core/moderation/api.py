"""内容检测API接口"""
import asyncio
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from algorithm_services.core.moderation import (
    get_moderation_coordinator,
    OverallModerationResult,
)
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)


class ModerationRequest(BaseModel):
    """内容检测请求"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

    text: str
    use_keyword: bool = True
    use_llm: bool = True
    categories: Optional[List[str]] = None


class ModerationResponse(BaseModel):
    """内容检测响应"""
    is_violation: bool
    violation_categories: List[str]
    confidence: float
    processing_time: float
    details: List[Dict]


# 创建FastAPI应用
app = FastAPI(title="内容检测API", version="1.0.0")


@app.post("/moderate", response_model=ModerationResponse)
async def moderate_content(request: ModerationRequest):
    """
    内容检测接口
    
    支持三种检测模式：
    1. 并行检测：同时使用关键词和LLM（默认）
    2. 快速检测：仅使用关键词
    3. 精确检测：仅使用LLM
    """
    logger.info(f"[内容检测-API] 接收到检测请求，文本长度: {len(request.text)}, 使用关键词: {request.use_keyword}, 使用LLM: {request.use_llm}")
    
    try:
        coordinator = get_moderation_coordinator()
        
        # 根据参数选择检测方式
        if request.use_keyword and request.use_llm:
            # 并行检测
            logger.info(f"[内容检测-API] 执行并行检测")
            result = await coordinator.detect_parallel(
                text=request.text,
                use_keyword=True,
                use_llm=True,
                categories=request.categories
            )
        elif request.use_keyword:
            # 快速检测
            logger.info(f"[内容检测-API] 执行快速检测")
            result = coordinator.detect_fast(request.text)
        elif request.use_llm:
            # 精确检测
            logger.info(f"[内容检测-API] 执行精确检测")
            result = coordinator.detect_accurate(request.text)
        else:
            logger.error(f"[内容检测-API] 请求参数错误：至少选择一种检测方式")
            raise HTTPException(status_code=400, detail="至少选择一种检测方式")
        
        # 转换为响应格式
        details = []
        for r in result.results:
            details.append({
                'category': r.category,
                'method': r.method,
                'is_violation': r.is_violation,
                'confidence': r.confidence,
                'details': r.details
            })
        
        logger.info(f"[内容检测-API] 检测完成，结果: {'违规' if result.is_violation else '正常'}, 处理时间: {result.processing_time:.2f}s")
        
        return ModerationResponse(
            is_violation=result.is_violation,
            violation_categories=result.violation_categories,
            confidence=result.confidence,
            processing_time=result.processing_time,
            details=details
        )
    
    except Exception as e:
        logger.error(f"[内容检测-API] 检测过程发生异常: {e}")
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


@app.post("/batch_moderate", response_model=List[ModerationResponse])
async def batch_moderate_content(requests: List[ModerationRequest]):
    """
    批量内容检测接口
    
    支持同时检测多个文本，提高效率
    """
    try:
        coordinator = get_moderation_coordinator()
        
        # 并行处理多个请求
        tasks = []
        for req in requests:
            if req.use_keyword and req.use_llm:
                task = coordinator.detect_parallel(
                    text=req.text,
                    use_keyword=True,
                    use_llm=True,
                    categories=req.categories
                )
            elif req.use_keyword:
                task = asyncio.to_thread(coordinator.detect_fast, req.text)
            elif req.use_llm:
                task = asyncio.to_thread(coordinator.detect_accurate, req.text)
            else:
                continue
            
            tasks.append(task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks)
        
        # 转换为响应格式
        responses = []
        for result in results:
            details = []
            for r in result.results:
                details.append({
                    'category': r.category,
                    'method': r.method,
                    'is_violation': r.is_violation,
                    'confidence': r.confidence,
                    'details': r.details
                })
            
            responses.append(ModerationResponse(
                is_violation=result.is_violation,
                violation_categories=result.violation_categories,
                confidence=result.confidence,
                processing_time=result.processing_time,
                details=details
            ))
        
        return responses
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量检测失败: {str(e)}")


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": "content_moderation"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
