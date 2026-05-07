# Developer: 马赫·马智?
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
下一步搜索行动提示模?
"""

NEXT_SEARCH_ACTION_PROMPT = """
请根据搜索进度决定下一步行动:

初始查询: {initial_query}
当前状? {results_info}
搜索历史: {history_info}

已收集结果示例(?个):
{results_examples}

请按以下JSON格式回复:
{{
  "continue_search": true/false,
  "reason": "继续或停止的原因",
  "new_queries": ["如果继续搜索,则提供新查询列?],
  "search_strategy": "broaden|narrow|diversify|deepen"
}}
"""


def get_next_search_action_prompt(initial_query: str, results_info: str, history_info: str, results_examples: str):
    """
    获取下一步搜索行动的提示
    """
    return NEXT_SEARCH_ACTION_PROMPT.format(
        initial_query=initial_query,
        results_info=results_info,
        history_info=history_info,
        results_examples=results_examples
    )
