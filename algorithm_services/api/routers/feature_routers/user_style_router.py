"""用户风格学习路由"""
import asyncio
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from algorithm_services.utils.logger import get_logger
from algorithm_services.api.schemas.feature_schemas.user_style_schema import (
    UserStyleUpdateRequest,
    UserStyleResponse,
    UserStyleFeature,
    UserStyleAnalysisRequest,
    UserStyleAnalysisResponse,
    StylePromptConfig,
    StylePromptResponse,
)
from algorithm_services.core.services.feature_services.user_style_service import (
    user_style_learning_service
)


logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/feature/user_style", tags=["用户风格学习"])


@router.post("/update", response_model=dict)
async def update_user_style(request: UserStyleUpdateRequest):
    """
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

    异步更新用户风格
    
    这是一个非阻塞接口，将更新任务放入后台队列
    立即返回，实际更新在后台异步执行
    """
    try:
        logger.info(f"[用户风格路由] 接收风格更新请求: {request.user_id}")
        
        await user_style_learning_service.update_style_async(request)
        
        return {
            "success": True,
            "message": "风格更新任务已添加到队列",
            "user_id": request.user_id
        }
        
    except Exception as e:
        logger.error(f"[用户风格路由] 更新失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.get("/{user_id}", response_model=UserStyleResponse)
async def get_user_style(user_id: str):
    """
    获取用户风格特征
    """
    try:
        logger.info(f"[用户风格路由] 获取用户风格: {user_id}")
        
        style = await user_style_learning_service.get_user_style(user_id)
        
        if style is None:
            return UserStyleResponse(
                user_id=user_id,
                style=UserStyleFeature(
                    language_style="一般",
                    vocabulary_preferences=[],
                    sentence_patterns=[],
                    emotional_expressions=[],
                    common_topics=[],
                    interaction_style=""
                ),
                confidence=0.0,
                last_updated=""
            )
        
        return UserStyleResponse(
            user_id=user_id,
            style=style,
            confidence=0.8,
            last_updated=""
        )
        
    except Exception as e:
        logger.error(f"[用户风格路由] 获取失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.post("/analyze", response_model=UserStyleAnalysisResponse)
async def analyze_user_style(request: UserStyleAnalysisRequest):
    """
    分析用户风格
    
    一次性分析用户的语言风格特征
    适用于需要立即获取分析结果的场景
    """
    try:
        logger.info(f"[用户风格路由] 分析用户风格: {request.user_id}")
        
        result = await user_style_learning_service.analyze_user_style(request)
        
        return result
        
    except Exception as e:
        logger.error(f"[用户风格路由] 分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/generate_prompt", response_model=StylePromptResponse)
async def generate_style_prompt(
    user_id: str,
    base_prompt: str,
    user_profile_context: Optional[str] = None
):
    """
    生成风格适配的提示词
    
    合并用户画像上下文和用户风格指导
    用于Free Chat等需要个性化提示词的场景
    """
    try:
        logger.info(f"[用户风格路由] 生成个性化提示词: {user_id}")
        
        config = StylePromptConfig(
            user_id=user_id,
            base_prompt=base_prompt,
            user_profile_context=user_profile_context,
            include_style_guide=True
        )
        
        result = await user_style_learning_service.generate_style_prompt(config)
        
        return result
        
    except Exception as e:
        logger.error(f"[用户风格路由] 生成提示词失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/batch_generate_prompt")
async def batch_generate_style_prompt(
    requests: List[StylePromptConfig]
):
    """
    批量生成风格适配的提示词
    """
    try:
        logger.info(f"[用户风格路由] 批量生成提示词: {len(requests)} 个")
        
        tasks = [
            user_style_learning_service.generate_style_prompt(config)
            for config in requests
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if isinstance(r, StylePromptResponse))
        
        return {
            "success": True,
            "total": len(requests),
            "successful": successful,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"[用户风格路由] 批量生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量生成失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "user_style_learning",
        "description": "用户风格学习服务 - 异步增量更新"
    }
