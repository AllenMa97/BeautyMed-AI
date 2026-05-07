# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.api.schemas.feature_schemas.text_summary_schemas import TextSummaryRequest, TextSummaryResponseData, TextSummaryResponse
from algorithm_services.core.prompts.features.text_summary_prompt import get_text_summary_prompt
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)


# 可配置当前Service的默认服务商/模型（也可从配置文件读取）
DEFAULT_PROVIDER = "aliyun"
DEFAULT_MODEL = "qwen-plus" 
LLM_REQUEST_MAX_TOKENS = int(512) # 摘要不需要太长
LLM_REQUEST_TEMPERATURE = float(0.3)

class TextSummaryService:
    """文本摘要Service"""
    description = "文本摘要，对用户输入进行摘要总结"
    
    async def generate(self, request: TextSummaryRequest) -> TextSummaryResponse:
        """生成文本摘要"""
        # 1. 获取Prompt
        prompt = get_text_summary_prompt(user_input=request.user_input)

        # 2. 调用LLM（指定服务商和模型，低温度保证稳定性）
        llm_request = LLMRequest(
            system_prompt=prompt["system_prompt"],
            user_prompt=prompt["user_prompt"],
            temperature=LLM_REQUEST_TEMPERATURE,
            max_tokens=LLM_REQUEST_MAX_TOKENS,
            response_format={"type": "json_object"},
            provider=DEFAULT_PROVIDER,
            model=DEFAULT_MODEL
        )

        llm_result = await llm_client_singleton.call_llm(llm_request)
        logger.info(f"文本摘要结果：{llm_result}")

        # 3. 转换为结构化数据
        try:
            data = TextSummaryResponseData(
                summary=llm_result.get("summary", ""),
                key_points=llm_result.get("key_points", [])[:5]  # 限制最多5个要点
            )
            return TextSummaryResponse(data=data)
        except Exception as e:
            logger.error(f"文本摘要结果解析失败：{e}")
            # 降级：直接截取用户输入前50字
            data = TextSummaryResponseData(
                summary=request.user_input[:50],
                key_points=[request.user_input[:20]]
            )
            return TextSummaryResponse(
                code=500,
                msg=f"文本摘要结果解析失败：{e}， 直接截取用户输入前50字作为摘要，前20字作为关键点",
                data=data
            )