# Developer: 马赫·马智?
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
从HTML内容中提取有意义信息的提示模?
"""

# 从HTML提取内容的提?
EXTRACT_HTML_CONTENT_PROMPT = """
请从以下HTML内容中提取与主题"{topic}"相关的有意义的信息?
请忽略HTML标签,专注于提取纯文本内容?
请按照以下JSON格式返回结果?
{{
    "content": "提取的纯文本内容",
    "tags": ["标签1", "标签2"]
}}

HTML内容:
{html_content}
"""

def get_extract_html_content_prompt(html_content: str, topic: str):
    """
    获取从HTML提取内容的提?
    """
    # 限制HTML内容长度,避免超出token限制
    truncated_html = html_content[:3000]
    return EXTRACT_HTML_CONTENT_PROMPT.format(html_content=truncated_html, topic=topic)
