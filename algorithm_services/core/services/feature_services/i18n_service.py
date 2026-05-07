# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

# 国际化语言转换
from algorithm_services.core.prompts.features.i18n_prompt import get_i18n_translation_prompt, get_i18n_bcp47_tag_prompt
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)

# 可配置当前Service的默认服务商/模型（也可从配置文件读取）
DEFAULT_PROVIDER = "aliyun"
DEFAULT_MODEL = "qwen-flash"  # 快速
LLM_REQUEST_MAX_TOKENS = int(4096) # 32768是Qwen flash模型的输入+输出的总token上限


# DEFAULT_PROVIDER = "lansee"
# DEFAULT_MODEL = "Qwen/Qwen2.5-32B-Instruct-AWQ"
# LLM_REQUEST_MAX_TOKENS = int(512)

LLM_REQUEST_TEMPERATURE = float(0.1) # 翻译场景优先准确性，降低随机性


async def I18N_Get_BCP47_Tag(
    text: str,
) -> dict:
    """
    执行语言识别（纯函数式实现，无Schema依赖）
    :param text: 待翻译文本
    :return: 原生字典格式的翻译结果
             成功示例: {"code":200, "msg":"success", "data":{"bcp47_tag":"xxx""}}
             失败示例: {"code":500, "msg":"error info", "data":{"bcp47_tag":"zh-CN",}}
    """

    # 1. 构建Prompt（兼容原prompt函数的入参格式）
    prompt = get_i18n_bcp47_tag_prompt(
        text=text,
    )

    # 2. 调用LLM
    llm_request = LLMRequest(
        system_prompt=prompt["system_prompt"],
        user_prompt=prompt["user_prompt"],
        max_tokens=LLM_REQUEST_MAX_TOKENS,
        temperature=LLM_REQUEST_TEMPERATURE,  # 优先准确性，降低随机性
        response_format={"type": "json_object"},
        provider=DEFAULT_PROVIDER,  # 指定服务商
        model=DEFAULT_MODEL  # 指定模型（别名/真实名均可）
    )

    try:
        llm_result = await llm_client_singleton.call_llm(llm_request)
        # 统一返回格式（原生字典）
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "bcp47_tag": llm_result.get("bcp47_tag", "zh-CN"),
            }
        }
    except Exception as e:
        logger.error(f"获取bcp47_tag失败：{e}, 返回默认值zh-CN", exc_info=True)
        # 异常兜底返回（原生字典）
        return {
            "code": 500,
            "msg": f"i18n translation failed: {str(e)}",
            "data": {
                "bcp47_tag": "zh-CN",
            }
        }

async def I18N_Translate(
    text: str,
    target_lang: str,
    context: str = None
) -> dict:
    """
    执行国际化翻译（纯函数式实现，无Schema依赖）
    :param text: 待翻译文本
    :param target_lang: 目标语言（如zh/en/ja）
    :param context: 翻译上下文（可选，提升翻译准确性）
    :return: 原生字典格式的翻译结果
             成功示例: {"code":200, "msg":"success", "data":{"translated_text":"xxx", "source_lang":"xxx", "target_lang":"xxx"}}
             失败示例: {"code":500, "msg":"error info", "data":{"translated_text":"", "source_lang":"xxx", "target_lang":"xxx"}}
    """

    # 1. 构建Prompt（兼容原prompt函数的入参格式）
    prompt = get_i18n_translation_prompt(
        text=text,
        target_lang=target_lang,
        context=context
    )

    # 2. 调用LLM（低温度，保证翻译准确性）
    llm_request = LLMRequest(
        system_prompt=prompt["system_prompt"],
        user_prompt=prompt["user_prompt"],
        max_tokens=LLM_REQUEST_MAX_TOKENS,
        temperature=LLM_REQUEST_TEMPERATURE,  # 翻译场景优先准确性，降低随机性
        response_format={"type": "json_object"},
        provider=DEFAULT_PROVIDER,  # 指定服务商
        model=DEFAULT_MODEL  # 指定模型（别名/真实名均可）
    )

    try:
        llm_result = await llm_client_singleton.call_llm(llm_request)
        # logger.info(f"国际化翻译结果：{llm_result}")
        # 统一返回格式（原生字典）
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "translated_text": llm_result.get("translated_text", ""),
            }
        }
    except Exception as e:
        logger.error(f"国际化翻译失败：{e}", exc_info=True)
        # 异常兜底返回（原生字典）
        return {
            "code": 500,
            "msg": f"i18n translation failed: {str(e)}",
            "data": {
                "translated_text": "",
            }
        }