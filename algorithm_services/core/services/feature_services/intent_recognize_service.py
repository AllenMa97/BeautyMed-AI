# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.api.schemas.feature_schemas.intent_recognize_schemas import (
    IntentRecognizeRequest,
    IntentRecognizeResponse,
    IntentRecognizeResponseData,
)
from algorithm_services.core.prompts.features.intent_recognize_prompt import get_yisia_intent_recognize_prompt
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)

# 可配置当前 Service 的默认服务商/模型（也可从配置文件读取）
DEFAULT_PROVIDER = "aliyun"
DEFAULT_MODEL = "qwen-flash"  # 快速
# LLM_REQUEST_MAX_TOKENS = int(32768) # 32768 是 Qwen flash 模型的输入 + 输出的总 token 上限
LLM_REQUEST_MAX_TOKENS = int(2048)  # 意图识别：输入约 1200 tokens + 输出约 10 tokens = 1210 tokens，2048 足够
LLM_REQUEST_TEMPERATURE = float(0.2)

class IntentRecognizeService:
    """意图识别Service"""
    description = "意图识别，分析用户输入的意图"
    
    async def recognize(self, request: IntentRecognizeRequest) -> IntentRecognizeResponse:
        """
        执行意图识别
        :param request: 意图识别请求
        :return: 结构化意图结果
        """
        # 1. 获取Prompt
        # 优化上下文长度，避免过长
        # 只保留最近 3 轮对话（约 1000 字符）
        context = request.context or ""
        if len(context) > 1000:
            # 截取最后 500 字符
            context = context[-1000:]
        
        prompt = get_yisia_intent_recognize_prompt(
            user_input=request.user_input,
            context=context
        )
        # logger.debug(f"意图识别Prompt：{prompt}")

        # 2. 调用LLM（低温度保证稳定性）
        llm_request = LLMRequest(
            system_prompt=prompt["system_prompt"],
            user_prompt=prompt["user_prompt"],
            temperature=LLM_REQUEST_TEMPERATURE,
            max_tokens=LLM_REQUEST_MAX_TOKENS,
            response_format={"type": "json_object"},  # 强制JSON输出
            provider = DEFAULT_PROVIDER,  # 指定服务商
            model = DEFAULT_MODEL,  # 指定模型（可传别名）
            enable_context_cache=True  # 启用阿里云Context Cache（Microcompact）
        )

        # 3. 转换为结构化数据（容错处理）
        try:
            llm_result = await llm_client_singleton.call_llm(llm_request)
            logger.info(f"意图识别LLM返回结果：{llm_result}")

            # 3. 结构化转换（容错处理）
            intent = llm_result.get("intent", "未明确")
            confidence = float(llm_result.get("confidence", 0.0))

            # 置信度<0.5强制标记为未明确
            if confidence < 0.5:
                intent = "未明确"

            response_data = IntentRecognizeResponseData(
                intent=intent,
                confidence=confidence
            )
            return IntentRecognizeResponse(
                code=200,
                msg="intent recognize success",
                data=response_data
            )
            return IntentRecognizeResponse(data=llm_result)

        except KeyError as e:
            logger.error(f"意图识别结果字段缺失：{e}")
            # 降级返回（保证服务可用）
            tmp_data = IntentRecognizeResponseData(
                intent="未明确",
                confidence=0.0,
            )
            return IntentRecognizeResponse(
                code=500,
                msg=f"意图识别结果字段缺失：{e}",
                data=tmp_data
            )
        except Exception as e:
            logger.error(f"意图识别执行异常：{str(e)}")
            tmp_data = IntentRecognizeResponseData(
                intent="未明确",
                confidence=0.0,
            )
            return IntentRecognizeResponse(
                code=500,
                msg=f"intent recognize failed: {str(e)}",
                data=tmp_data
            )
