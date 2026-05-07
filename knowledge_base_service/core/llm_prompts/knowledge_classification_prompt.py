# Developer: 马赫·马智?
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
知识分层分类提示模板
"""

KNOWLEDGE_CLASSIFICATION_PROMPT = """
请将以下内容分类到适当的知识层级:

查询: {query}
内容: {content}

知识层级定义?
- domain_background: 领域背景知识,通常是基础概念、理论框架、行业概况等
- specific: 具体知识,针对特定问题的具体解决方案、详细步骤、精确数据等
- associative: 关联知识,跨领域的连接性知识、类比、启发性信息等

请按以下JSON格式回复:
{{
  "layer": "domain_background|specific|associative",
  "reason": "分类理由"
}}
"""


def get_knowledge_classification_prompt(content: str, query: str = ""):
    """
    获取知识分层分类的提?
    """
    return KNOWLEDGE_CLASSIFICATION_PROMPT.format(content=content[:1000], query=query)
