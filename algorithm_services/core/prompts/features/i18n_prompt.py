# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.core.prompts.base_prompt import get_base_system_prompt, fill_prompt_template


# 国际化翻译专属规则
I18N_TRANSLATION_RULES = """
1. 翻译规则：
   - 确保语义准确、语气匹配，保留原文格式（如标点、换行），技术术语翻译需符合行业规范；
   - 若上下文存在，需结合上下文优化翻译结果；
   - 目标语言遵循 BCP 47 规范（如zh-CN/en-US/ja-JP）；
2. 输出格式（严格JSON）：
   {
     "translated_text": "翻译后的文本",
   }
"""

# 翻译用户输入内容Prompt模板
I18N_TRANSLATION_USER_TEMPLATE = """
请完成文本的国际化翻译：
待翻译文本：{text}
目标语言：{target_lang}
翻译上下文：{context}
"""

def get_i18n_translation_prompt(
    text: str,
    target_lang: str,
    context: str,
) -> dict:
    """
    获取国际化翻译完整Prompt
    :param text: 待翻译文本
    :param target_lang: 目标语言
    :param context: 翻译上下文
    :return: Prompt字典
    """

    # system_prompt = get_base_system_prompt(I18N_TRANSLATION_RULES)
    system_prompt = I18N_TRANSLATION_RULES # 没必要太复杂的Prompt，节省Token消耗
    user_prompt = fill_prompt_template(
        I18N_TRANSLATION_USER_TEMPLATE,
        text=text,
        target_lang=target_lang,
        context=context
    )
    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt
    }

# 获取BCP47语言码专属规则
BCP47_DETECTION_RULES = """
你必须严格遵循以下规则识别BCP47语言码：
1. 仅从指定列表中返回值：[zh-CN,zh-TW,zh-HK,en-US,id-ID,ms-MY,th-TH,vi-VN,tl-PH,km-KH,lo-LA,my-MM,ta-SG,ja-JP,ko-KR,fr-FR,es-ES,pt-BR,de-DE,ru-RU]；
2. 处理特殊输入：
   - 若输入包含base64字符串，忽略base64部分，仅识别非base64文本的语言；
   - 若输入本身是列表内的BCP47码，直接返回该码值；
   - 若输入包含多种语言，按「字符占比最高」判定主要语言；
3. 兜底规则：无法精准识别时，必须返回zh-CN；
4. 输出约束（严格JSON）：
{
 "bcp47_tag": "BCP47码",
}
"""


# 获取用户输入内容BCP47码Prompt模板
BCP47_DETECTION_USER_TEMPLATE =  """
输入内容：{text}
"""

def get_i18n_bcp47_tag_prompt(
    text: str,
) -> dict:
    """
    获取国际化BCP47标签识别完整Prompt
    :param text: 待识别文本
    :return: Prompt字典
    """
    system_prompt = BCP47_DETECTION_RULES  # 没必要太复杂的Prompt，节省Token消耗
    user_prompt = fill_prompt_template(
        BCP47_DETECTION_USER_TEMPLATE,
        text=text,
    )
    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt
    }
