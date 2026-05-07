# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.core.prompts.features.dialog_summary_prompt import get_dialog_summary_prompt
from algorithm_services.api.schemas.feature_schemas.dialog_summary_schema import DialogSummaryRequest, DialogSummaryResponseData, DialogSummaryResponse
from algorithm_services.utils.logger import get_logger
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest

logger = get_logger(__name__)


# 可配置当前Service的默认服务商/模型（也可从配置文件读取）
DEFAULT_PROVIDER = "aliyun"
DEFAULT_MODEL = "qwen-flash"  # 视觉模型，qwen-vl-max不存在
LLM_REQUEST_MAX_TOKENS = int(4096) # 32768是Qwen flash模型的输入+输出的总token上限


# DEFAULT_PROVIDER = "lansee"
# DEFAULT_MODEL = "Qwen/Qwen2.5-32B-Instruct-AWQ"
# LLM_REQUEST_MAX_TOKENS = int(512)


LLM_REQUEST_TEMPERATURE = float(0.3) # 优先准确性，降低随机性



class DialogSummaryService:
    """适配Agent调用的对话摘要工具类"""
    description = "对话摘要，生成会话历史摘要"
    
    async def generate_dialog_summary(
            self,
            request: DialogSummaryRequest
    ) -> DialogSummaryResponse:
        """
        Agent内部调用的对话摘要异步入口
        :param request: 对话摘要请求体（含对话内容、摘要长度、摘要类型）
        :return: 结构化的摘要响应数据
        """
        try:
            # 1. 获取标准化提示词（复用原有逻辑）
            user_prompt = get_dialog_summary_prompt(
                dialog_content=request.dialog_content,
                summary_length=request.summary_length,
                summary_type=request.summary_type
            )
            llm_request = LLMRequest(
                system_prompt='',
                user_prompt=user_prompt,
                temperature=LLM_REQUEST_TEMPERATURE,
                max_tokens=LLM_REQUEST_MAX_TOKENS,
                provider=DEFAULT_PROVIDER,
                model=DEFAULT_MODEL,
                enable_context_cache=True  # 启用阿里云Context Cache（Microcompact）
            )
            # 2. 调用LLM生成摘要（复用原有逻辑，补充参数注释）
            llm_response = await llm_client_singleton.call_llm(llm_request)

            # 3. 处理响应结果并封装结构化数据
            summary_result = request.dialog_content  # 保底
            if 'raw_content' in llm_response:
                summary_result = llm_response['raw_content'].strip()
            logger.info(f"对话摘要结果：{summary_result}")

            response_data =  DialogSummaryResponseData(
                dialog_summary=summary_result,
                raw_length=len(request.dialog_content),
                summary_length=len(summary_result)
            )

            return DialogSummaryResponse(
                code=200,
                msg="dialog summary service success",
                data=response_data
            )

        except Exception as e:
            # 异常兜底（Agent调用时需明确异常处理，避免崩溃）
            response_data = DialogSummaryResponseData(dialog_summary=request.dialog_content,
                                                      raw_length=request.summary_length,
                                                      summary_length=request.summary_length)
            return DialogSummaryResponse(
                code=500,
                msg=f"dialog summary service error, error message: {str(e)} ",
                data=response_data
            )