# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.core.prompts.base_prompt import fill_prompt_template

SELF_EVOLUTION_PROMPT = """
你是自进化分析助手。你的任务是分析对话历史和用户反馈，提出系统改进建议。

当前系统信息：
- 用户画像：{user_profile}
- 错误记录：{error_records}
- 对话历史片段：{recent_dialogs}

请分析以下方面：
1. 回复质量如何？有哪些可以改进的地方？
2. 用户的反馈如何？有哪些需要调整的交互方式？
3. 基于错误记录，哪些方面容易出错？
4. 如何更好地满足用户需求？
"""
SELF_EVOLUTION_OUTPUT_FORMAT = """
输出格式（严格JSON，无多余内容）：
{
  "behavior_improvements": ["建议1", "建议2"],
  "knowledge_updates": ["知识更新1", "知识更新2"],
  "interaction_adjustments": ["交互调整1", "交互调整2"],
  "feature_enhancements": ["功能增强1", "功能增强2"],
  "analysis_summary": "总体分析总结"
}
"""

def get_self_evolution_prompt(user_profile, error_records, recent_dialogs) -> dict:
    user_prompt = fill_prompt_template(
        SELF_EVOLUTION_PROMPT,
        user_profile=user_profile,
        error_records=error_records,
        recent_dialogs=recent_dialogs,
    ) + SELF_EVOLUTION_OUTPUT_FORMAT
    return {
        "system_prompt": "",
        "user_prompt": user_prompt
    }


LEARN_FROM_CORRECTION_PROMPT = """
你的任务是从用户的纠正信息中学习，更新AI的知识库。

请分析以下用户纠正：
原始错误信息：{original_info}
用户纠正内容：{correction}

基于用户的纠正，更新正确的信息，并说明：
1. 原始信息哪里不准确
2. 正确的信息应该是什么
3. 这种类型的错误应该如何避免
"""
SLEARN_FROM_CORRECTION_OUTPUT_FORMAT = """
输出格式（严格JSON，无多余内容）：

{
  "original_mistake": "{original_info}",
  "corrected_information": "{correction}",
  "mistake_category": "错误类别",
  "learning_points": ["学习要点1", "学习要点2"],
  "prevention_strategy": "预防策略"
}
"""

def get_learn_from_correction_prompt(original_info, correction) -> dict:
    user_prompt = fill_prompt_template(
        SELF_EVOLUTION_PROMPT,
        original_info=original_info,
        correction=correction,
    ) + SLEARN_FROM_CORRECTION_OUTPUT_FORMAT
    return {
        "system_prompt": "",
        "user_prompt": user_prompt
    }
