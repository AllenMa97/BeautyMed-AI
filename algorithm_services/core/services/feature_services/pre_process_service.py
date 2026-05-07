# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.api.schemas.feature_schemas.function_planner_schemas import FunctionPlannerRequest
from algorithm_services.utils.logger import get_logger


logger = get_logger(__name__)

class PreProcessService:
    """预处理Service"""
    async def process(self, request: FunctionPlannerRequest) -> FunctionPlannerRequest:
        # TODO 1、语言识别并处理lang字段； 2、违规过滤； 3、攻击输入过滤； 4、错别输入纠正和正确推测；
        pass