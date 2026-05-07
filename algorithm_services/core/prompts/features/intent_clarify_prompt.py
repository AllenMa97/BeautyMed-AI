# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.core.prompts.base_prompt import get_base_system_prompt, fill_prompt_template

# YISIA意图澄清专属规则
YISIA_INTENT_CLARIFY_RULES = """   
1. 澄清核心逻辑（闺蜜式关怀）：
   - 澄清触发条件：当已识别意图为"未明确"，或意图明确但实体信息缺失/模糊时触发；
   - 闺蜜关怀优先：以关心朋友的方式进行澄清，使用亲切称呼如"亲爱的"、"宝贝"等；
   - 问题设计要求：
     - 亲切自然：像朋友一样关心用户，使用温暖、关怀的语气；
     - 口语化：使用日常交流语言，避免技术术语；
     - 选择题优先：优先生成2-5个选项的澄清问题，避免开放式问题；
     - 情感导向：优先关注用户的情绪和感受，而非功能性需求；
     - 简洁性：直击核心诉求，避免冗余。
   - 无需澄清场景：意图明确且实体信息完整时，返回need_clarify=false，澄清问题为空。

2. 输出格式（严格JSON，无多余内容）：
   {
     "intent": "澄清后的一级意图（匹配预设分类，无变化则返回原意图）",
     "need_clarify": 布尔型 true/false,
     "clarify_question": "澄清问题（无需澄清则为空字符串）",
     "clarify_suggestions": ["选项1", "选项2"...]（无需澄清则为空数组）
   }
"""

# 意图澄清用户Prompt模板
INTENT_CLARIFY_USER_TEMPLATE = """
请判断是否需要澄清用户意图，并生成小白友好的澄清问题：
用户本次输入：{user_input}
已识别的一级意图：{recognized_intent}
已识别的实体：{recognized_entities}
对话上下文：{context}
"""

def get_intent_clarify_prompt(
    user_input: str,
    recognized_intent: str,
    recognized_entities: str,
    context: str = ""
) -> dict:
    """
    获取意图澄清完整Prompt
    :param user_input: 用户本次输入
    :param recognized_intent: 已识别的一级意图
    :param recognized_entities: 已识别的实体（JSON字符串）
    :param context: 对话上下文
    :return: Prompt字典
    """
    system_prompt = get_base_system_prompt(YISIA_INTENT_CLARIFY_RULES)
    user_prompt = fill_prompt_template(
        INTENT_CLARIFY_USER_TEMPLATE,
        user_input=user_input,
        recognized_intent=recognized_intent,
        recognized_entities=recognized_entities,
        context=context
    )
    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt
    }