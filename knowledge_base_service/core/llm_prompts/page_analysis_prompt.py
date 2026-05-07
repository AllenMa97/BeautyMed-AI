# Developer: 马赫·马智?
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
页面分析提示模板
"""

PAGE_ANALYSIS_PROMPT = """
请分析以下网页是内容页面还是搜索结果页面?

URL: {url}

网页HTML片段:
{html_content}

请回答以下问题:
1. 这是一个内容页面吗?(如文章、教程、产品说明、研究报告等?
2. 这是一个搜索结果页面吗?(列出多个链接供用户选择?
3. 这是一个导航页面吗?(如首页、菜单页等)

请按以下JSON格式回复:
{{
  "is_content_page": true/false,
  "confidence": 0-100之间的置信度分数,
  "reason": "简要说明判断理?,
  "page_type": "内容页|搜索结果页|导航页|其他",
  "has_meaningful_content": true/false
}}
"""


def get_page_analysis_prompt(url: str, html_content: str):
    """
    获取页面分析的提?
    """
    return PAGE_ANALYSIS_PROMPT.format(
        url=url,
        html_content=html_content[:2000]
    )
