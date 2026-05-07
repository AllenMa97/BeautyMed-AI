# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from fastapi import APIRouter
from algorithm_services.api.schemas.feature_schemas.function_planner_schemas import (
    FunctionPlannerRequest, FunctionPlannerResponse
)
from algorithm_services.core.services.feature_services.function_planner_service import FunctionPlannerService

router = APIRouter(prefix="/api/v1/feature/function_planner", tags=["功能执行规划器"])
service = FunctionPlannerService()

@router.post("/plan", response_model=FunctionPlannerResponse)
async def plan_functions(request: FunctionPlannerRequest):
    result = await service.plan(request) # result是一个FunctionPlannerResponseData对象
    return FunctionPlannerResponse(
        code=200,
        msg="success",
        data=result
    )