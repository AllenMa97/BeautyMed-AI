# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
搜索查询生成提示模板
"""

# 生成搜索查询的提示
GENERATE_SEARCH_QUERIES_PROMPT = """
输入主题:{topic}
要求:{requirements}

以 JSON 数组字符串格式返回查询。
"""

def get_generate_search_queries_prompt(topic: str, requirements: str, num_queries: int = 5):
    """
    获取生成搜索查询的提示
    """
    return GENERATE_SEARCH_QUERIES_PROMPT.format(topic=topic, requirements=requirements, num_queries=num_queries)
