# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

# 对话摘要生成器

from fastapi import APIRouter
from algorithm_services.api.schemas.feature_schemas.dialog_summary_schema import DialogSummaryRequest, DialogSummaryResponse
from algorithm_services.core.services.feature_services.dialog_summary_service import DialogSummaryService

# 创建路由实例（命名规范：功能_router）
router = APIRouter(
    prefix="/api/v1/feature/dialog_summary",  # 接口前缀，配合main.py的/api/v1，最终路径：/api/v1/dialog_summary/
    tags=["对话摘要"],
)

service = DialogSummaryService()

# 定义接口（命名规范：router_功能_动作）
@router.post("/generate", response_model=DialogSummaryResponse, summary="生成对话摘要")
async def router_generate_dialog_summary(request: DialogSummaryRequest):
    """
    生成对话摘要接口
    - request: 对话内容、摘要长度、摘要类型
    - return: 标准化的摘要结果
    """
    summary_result = await service.generate_dialog_summary(request)
    return summary_result


