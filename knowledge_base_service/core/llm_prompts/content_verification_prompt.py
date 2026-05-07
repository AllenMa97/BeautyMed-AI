# Developer: 马赫·马智?
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
内容验证提示模板
用于验证爬取的内容是否有?
"""

# 内容验证提示
CONTENT_VERIFICATION_PROMPT = """
请评估以下网页内容的质量和相关性:

网页URL: {url}
网页内容: {content}

请回答以下问题:
1. 内容是否为空或几乎为空?
2. 内容是否包含实际信息还是主要是错误消息?
3. 内容是否与预期主题相关?
4. 是否看起来像是反爬虫页面或验证码页面?

请按照以下JSON格式返回评估结果?
{{
    "is_valid": true/false,
    "quality_score": 0-100,
    "issues": ["issue1", "issue2"],
    "suggestions": ["suggestion1", "suggestion2"]
}}
"""

def get_content_verification_prompt(content: str, url: str):
    """
    获取内容验证提示
    """
    # 限制内容长度以避免超出token限制
    truncated_content = content[:2000] if len(content) > 2000 else content
    return CONTENT_VERIFICATION_PROMPT.format(content=truncated_content, url=url)
