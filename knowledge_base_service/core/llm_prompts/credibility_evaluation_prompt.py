# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
内容可信度评估提示模板
"""

CREDIBILITY_EVALUATION_PROMPT = """
评估以下内容的可信度:

内容:{content}
来源 URL: {source_url}
评估层次:{layer}
评估重点:{evaluation_focus}

请返回一个 JSON 对象:
{{
    "credibility_score": 0.0-1.0,
    "reasons": ["理由 1", "理由 2"]
}}
"""

def get_credibility_evaluation_prompt(content: str, source_url: str, layer: str = "specific"):
    """
    获取内容可信度评估的提示
    """
    if layer == "domain_background":
        evaluation_focus = "基础概念的准确性、理论框架的完整性、背景信息的可靠性"
    elif layer == "specific":
        evaluation_focus = "具体信息的精确性、解决方案的可行性、数据的准确性"
    else:
        evaluation_focus = "关联性的合理性、启发性、跨领域连接的价值"
    
    return CREDIBILITY_EVALUATION_PROMPT.format(
        content=content[:1000],
        source_url=source_url,
        layer=layer,
        evaluation_focus=evaluation_focus
    )
