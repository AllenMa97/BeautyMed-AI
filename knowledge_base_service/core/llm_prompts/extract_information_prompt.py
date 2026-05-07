# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
信息提取提示模板
"""

# 信息提取提示
EXTRACT_INFORMATION_PROMPT = """
从以下内容中提取与主题和要求相关的信息:

主题:{topic}
要求:{requirements}
内容:{content[:4000]}  # 限制内容长度

返回一个 JSON 对象,包含:
- "content": 提取的相关内容
- "tags": 相关标签/关键词数组
"""

def get_extract_information_prompt(topic: str, requirements: str, content: str):
    """
    获取信息提取的提示
    """
    return EXTRACT_INFORMATION_PROMPT.format(topic=topic, requirements=requirements, content=content)
