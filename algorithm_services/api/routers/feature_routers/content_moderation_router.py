"""内容检测路由器"""
from fastapi import APIRouter, HTTPException
from typing import List
import asyncio

from algorithm_services.api.schemas.feature_schemas.content_moderation_schemas import (
    ModerationRequest,
    ModerationResponse,
    BatchModerationRequest,
    BatchModerationResponse,
)
from algorithm_services.core.moderation import get_moderation_coordinator
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/feature/content_moderation", tags=["内容检测"])
coordinator = get_moderation_coordinator()


@router.post("/moderate", response_model=ModerationResponse)
async def moderate_content(request: ModerationRequest):
    """
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

    单个内容检测接口
    
    支持三种检测模式：
    - fast: 快速检测（仅关键词）
    - accurate: 精确检测（仅LLM）
    - parallel: 并行检测（关键词+LLM）
    """
    try:
        # 根据模式选择检测方式
        if request.mode == "fast":
            result = coordinator.detect_fast(request.text)
        elif request.mode == "accurate":
            result = coordinator.detect_accurate(request.text)
        elif request.mode == "parallel":
            result = await coordinator.detect_parallel(
                text=request.text,
                use_keyword=request.use_keyword,
                use_llm=request.use_llm,
                categories=request.categories
            )
        else:
            raise HTTPException(status_code=400, detail=f"不支持的检测模式: {request.mode}")
        
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
        
        return ModerationResponse(
            is_violation=result.is_violation,
            violation_categories=result.violation_categories,
            confidence=result.confidence,
            processing_time=result.processing_time,
            details=details
        )
    
    except Exception as e:
        logger.error(f"内容检测失败: {e}")
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


@router.post("/batch_moderate", response_model=BatchModerationResponse)
async def batch_moderate_content(request: BatchModerationRequest):
    """
    批量内容检测接口
    
    支持同时检测多个文本，提高效率
    """
    try:
        import time
        start_time = time.time()
        
        # 并行处理多个请求
        tasks = []
        for req in request.requests:
            if req.mode == "fast":
                task = asyncio.to_thread(coordinator.detect_fast, req.text)
            elif req.mode == "accurate":
                task = asyncio.to_thread(coordinator.detect_accurate, req.text)
            elif req.mode == "parallel":
                task = coordinator.detect_parallel(
                    text=req.text,
                    use_keyword=req.use_keyword,
                    use_llm=req.use_llm,
                    categories=req.categories
                )
            else:
                continue
            
            tasks.append(task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # 处理异常结果
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"第{i+1}个检测失败: {result}")
                # 创建一个默认的错误响应
                valid_results.append(ModerationResponse(
                    is_violation=False,
                    violation_categories=[],
                    confidence=0.0,
                    processing_time=0.0,
                    details=[]
                ))
            else:
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
                
                valid_results.append(ModerationResponse(
                    is_violation=result.is_violation,
                    violation_categories=result.violation_categories,
                    confidence=result.confidence,
                    processing_time=result.processing_time,
                    details=details
                ))
        
        # 统计结果
        violation_count = sum(1 for r in valid_results if r.is_violation)
        pass_count = len(valid_results) - violation_count
        
        return BatchModerationResponse(
            results=valid_results,
            total_count=len(valid_results),
            violation_count=violation_count,
            pass_count=pass_count,
            total_time=total_time
        )
    
    except Exception as e:
        logger.error(f"批量内容检测失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量检测失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "content_moderation",
        "description": "内容检测服务 - 支持黄赌毒暴政等7大类违规内容检测"
    }


@router.get("/categories")
async def get_categories():
    """获取支持的检测类别"""
    return {
        "categories": [
            {
                "name": "political",
                "description": "政治敏感",
                "details": "领土主权、领导人相关、分裂国家言论等"
            },
            {
                "name": "violence",
                "description": "暴力血腥",
                "details": "暴力行为、血腥内容、自残自杀等"
            },
            {
                "name": "pornography",
                "description": "色情低俗",
                "details": "黄色内容、低俗笑话、擦边内容等"
            },
            {
                "name": "gambling",
                "description": "赌博诈骗",
                "details": "赌博网站、诈骗电话、非法集资等"
            },
            {
                "name": "drug",
                "description": "毒品犯罪",
                "details": "毒品交易、非法武器、黑客攻击等"
            },
            {
                "name": "hate",
                "description": "仇恨言论",
                "details": "种族歧视、地域歧视、性别歧视等"
            },
            {
                "name": "fake",
                "description": "虚假信息",
                "details": "谣言传播、伪科学、恶意造谣等"
            }
        ]
    }


@router.get("/modes")
async def get_modes():
    """获取支持的检测模式"""
    return {
        "modes": [
            {
                "name": "fast",
                "description": "快速检测",
                "details": "仅使用关键词检测，速度快，适用于实时场景",
                "processing_time": "0.05-0.15ms",
                "accuracy": "高"
            },
            {
                "name": "accurate",
                "description": "精确检测",
                "details": "仅使用LLM检测，理解上下文，适用于准确性要求高的场景",
                "processing_time": "100-500ms",
                "accuracy": "极高"
            },
            {
                "name": "parallel",
                "description": "并行检测",
                "details": "同时使用关键词和LLM检测，综合判断",
                "processing_time": "0.11ms + 异步LLM",
                "accuracy": "极高"
            }
        ]
    }
