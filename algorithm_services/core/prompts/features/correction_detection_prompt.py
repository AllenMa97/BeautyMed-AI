# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.core.prompts.base_prompt import get_base_system_prompt, fill_prompt_template

CORRECTION_DETECTION_PROMPT = """
你是纠错检测助手。你的任务是判断用户是否在纠正之前的信息。

请分析以下对话内容：
之前的信息：{previous_ai_response}
用户当前输入：{user_input}

判断标准：
1. 用户明确指出AI的回答有错误（如"不对"、"错了"、"不是这样的"等）
2. 用户提供了与AI之前回答相矛盾但更准确的信息
3. 用户使用"其实是"、"实际上是"、"正确的是"等表达来纠正信息
4. 用户明确指出AI的某个具体说法不准确

请严格按照上述标准进行判断，并返回JSON格式结果。
"""

OUTPUT_FORMAT = """
输出格式（严格JSON，无多余内容）：
{
  "is_correction": 布尔型 true/false,
  "correction_content": "用户纠正的具体内容（无纠正则为空字符串）",
  "original_mistake": "AI之前回复中的错误内容（无纠正则为空字符串）",
  "confidence": 0-1（保留1位小数）
}
"""

def get_correction_detection_prompt(previous_ai_response, user_input) -> dict:
    system_prompt = ""
    user_prompt = fill_prompt_template(
        CORRECTION_DETECTION_PROMPT,
        previous_ai_response=previous_ai_response,
        user_input=user_input,
    )+OUTPUT_FORMAT

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt
    }