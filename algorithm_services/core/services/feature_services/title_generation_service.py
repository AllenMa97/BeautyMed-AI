# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.api.schemas.feature_schemas.title_generation_schemas import (
    TitleGenerationRequest, TitleGenerationResponse, TitleGenerationResponseData
)
from algorithm_services.core.prompts.features.title_generation_prompt import get_title_generation_prompt
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)

class TitleGenerationService:
    """标题生成Service"""
    async def generation(self, request: TitleGenerationRequest) -> TitleGenerationResponse:
        # 1. 获取Prompt
        prompt = get_title_generation_prompt(
            user_input=request.user_input,
        )
        # 2. 调用LLM（中等温度，兼顾创造性和稳定性）
        llm_request = LLMRequest(
            system_prompt=prompt["system_prompt"],
            user_prompt=prompt["user_prompt"],
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        llm_result = await llm_client_singleton.call_llm(llm_request)  # 得到的 TitleGenerationResponseData
        logger.info(f"标题生成结果：{llm_result}")
        # 3. 转换为结构化数据
        try:
            return TitleGenerationResponse(data=llm_result)
        except Exception as e:
            llm_str_result = await llm_client_singleton.free_call_llm('帮我润色一下这句话（觉得不用润色就直接返回，不用废话）：你的个人应用', temperature=0.5)
            tmp_data =  TitleGenerationResponseData(
                title=llm_str_result
            )
            return TitleGenerationResponse(
                data=tmp_data
            )
