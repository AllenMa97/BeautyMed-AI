# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.core.prompts.base_prompt import get_base_system_prompt, fill_prompt_template

# 文本摘要专属规则
TEXT_SUMMARY_RULES = """
摘要规则（面向小白）：
- 仅提取用户输入的核心需求，忽略口语化冗余（如"能不能帮我"/"谢谢"）；
- 摘要长度控制在100字以内，语言口语化，无技术术语；
- 保留关键实体（页面名称/组件/操作），删除修饰词；
输出格式（严格JSON）：
{
 "summary": "字符串 | 核心摘要（100字以内，小白语言）",
 "key_points": 字符串列表[字符串1,字符串2, ...] | ["关键点1", "关键点2"...]（不超过5个）
}
"""

# 文本摘要用户Prompt模板
TEXT_SUMMARY_USER_TEMPLATE = """
请为以下用户输入生成核心摘要：
用户输入：{user_input}
"""

def get_text_summary_prompt(user_input: str) -> dict:
    """
    获取文本摘要完整Prompt
    :param user_input: 用户单次输入
    :return: Prompt字典
    """
    system_prompt = get_base_system_prompt(TEXT_SUMMARY_RULES)
    user_prompt = fill_prompt_template(
        TEXT_SUMMARY_USER_TEMPLATE,
        user_input=user_input
    )
    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt
    }