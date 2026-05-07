# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.core.prompts.base_prompt import get_base_system_prompt, fill_prompt_template

# 标题生成专属规则
TITLE_GENERATION_RULES = """
1. 生成逻辑：
   - 严格基于用户输入生成编码相关标题，贴合用户意图；
   - 标题简洁凝练，控制在10-20字，无冗余修饰，符合日常场景；
   - 禁止脱离用户输入凭空创作，无明确意图时保留核心关键词，不强行拓展。
2. 输出格式（严格JSON，无额外内容）：
{
 "title": "生成的标题",
}
"""


# 标题生成用户Prompt模板
TITLE_GENERATION_USER_TEMPLATE = """
请为用户的输入生成的专属标题：
用户本次输入：{user_input}
"""


def get_title_generation_prompt(
    user_input: str,
) -> dict:
    """
    获取vibe coding平台的标题生成完整Prompt
    :param user_input: 用户本次输入的编码相关需求
    :return: Prompt字典，包含system_prompt和user_prompt
    """
    # 拼接基础系统prompt与标题生成专属规则
    system_prompt = get_base_system_prompt(TITLE_GENERATION_RULES)
    # 渲染用户模板，填充入参
    user_prompt = fill_prompt_template(
        TITLE_GENERATION_USER_TEMPLATE,
        user_input=user_input
    )
    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt
    }

