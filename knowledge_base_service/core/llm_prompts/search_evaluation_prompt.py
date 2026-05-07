# Developer: 马赫·马智?
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
搜索结果评估提示模板
"""

SEARCH_EVALUATION_PROMPT = """
请评估以下搜索查询的结果质量,并提供建议?

搜索查询: {query}
目标结果数量: {target_count}
实际结果数量: {actual_count}
结果摘要:
{results_summary}

请按以下JSON格式回复:
{{
  "summary": "简要总结搜索结果质量",
  "relevance_score": 数字评分(1-100),
  "next_action": "process_results|refine_query|broaden_query|change_approach",
  "refined_query": "如果需要精炼查询,则提供新查询",
  "broadened_query": "如果需要扩展查询,则提供新查询",
  "alternative_queries": ["如果需要改变方法,则提供替代查询列?],
  "confidence_in_results": "high|medium|low"
}}
"""


def get_search_evaluation_prompt(query: str, target_count: int, actual_count: int, results_summary: str):
    """
    获取搜索结果评估的提?
    """
    return SEARCH_EVALUATION_PROMPT.format(
        query=query,
        target_count=target_count,
        actual_count=actual_count,
        results_summary=results_summary
    )
