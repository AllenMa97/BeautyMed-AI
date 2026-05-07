# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.api.schemas.feature_schemas.intent_clarify_schemas import (
    IntentClarifyRequest, IntentClarifyResponseData, IntentClarifyResponse
)
from algorithm_services.core.prompts.features.intent_clarify_prompt import get_intent_clarify_prompt
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)

# 可配置当前Service的默认服务商/模型（也可从配置文件读取）
DEFAULT_PROVIDER = "aliyun"
DEFAULT_MODEL = "qwen-flash"  # 快速
LLM_REQUEST_MAX_TOKENS = int(1000) # 32768是Qwen flash模型的输入+输出的总token上限


# DEFAULT_PROVIDER = "lansee"
# DEFAULT_MODEL = "Qwen/Qwen2.5-32B-Instruct-AWQ"
# LLM_REQUEST_MAX_TOKENS = int(512)

LLM_REQUEST_TEMPERATURE = float(0.5) # 中等温度，兼顾创造性和稳定性

class IntentClarifyService:
    """意图澄清Service"""
    async def clarify(self, request: IntentClarifyRequest) -> IntentClarifyResponse:
        """执行意图澄清"""
        # 1. 获取Prompt
        prompt = get_intent_clarify_prompt(
            user_input=request.user_input,
            recognized_intent=request.recognized_intent,
            recognized_entities=request.recognized_entities,
            context=request.context
        )
        # 2. 调用LLM（）
        llm_request = LLMRequest(
            system_prompt=prompt["system_prompt"],
            user_prompt=prompt["user_prompt"],
            temperature=LLM_REQUEST_TEMPERATURE,
            max_tokens=LLM_REQUEST_MAX_TOKENS,
            response_format={"type": "json_object"},
            provider=DEFAULT_PROVIDER,
            model=DEFAULT_MODEL
        )
        try:
            llm_result = await llm_client_singleton.call_llm(llm_request)
            logger.info(f"意图澄清LLM返回结果：{llm_result}")

            # 3. 结构化转换（容错处理）
            response_data = IntentClarifyResponseData(
                intent=llm_result.get("intent", request.recognized_intent),
                need_clarify=llm_result.get("need_clarify", False),
                clarify_question=llm_result.get("clarify_question", ""),
                clarify_suggestions=llm_result.get("clarify_suggestions", [])
            )
            return IntentClarifyResponse(
                code=200,
                msg="intent clarify success",
                data=response_data
            )

        except Exception as e:
            logger.error(f"意图澄清结果解析失败：{str(e)}")
            # 降级返回空数据
            tmp_data = IntentClarifyResponseData(
                intent=request.recognized_intent,
                need_clarify=False,
                clarify_question="",
                clarify_suggestions=[]
            )
            return IntentClarifyResponse(
                code=500,
                msg=f"intent clarify failed: {str(e)}",
                data=tmp_data
            )

