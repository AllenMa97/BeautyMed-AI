# Developer: 马赫·马智?
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
URL 识别提示模板
"""

URL_IDENTIFICATION_PROMPT = """
请分析以下URL列表,识别出哪些是医学、医美、美容领域的专业内容页面链接?
如学术论文、临床研究、医学指南、药品说明书、医疗器械信息、专业期刊文章?
政府医疗法规、行业协会指南、专利文献等?

URL列表:
{urls}

请返回一个JSON数组,只包含医学、医美、美容领域的专业内容页面URL?
[
    "https://medical-journal.org/article1",
    "https://clinicaltrials.gov/study1",
    ...
]

重要要求?
1. 只返回专业内容页面的URL,不要包含搜索结果页、广告页、导航页
2. 优先选择权威来源(如政府机构、学术期刊、专业协会)
3. 确保返回有效的JSON格式,不要包含任何额外文件
4. 如果没有找到专业内容页面,返回空数组 []
"""


def get_url_identification_prompt(urls: list):
    """
    获取 URL 识别的提?
    """
    urls_text = '\n'.join([f"- {url}" for url in urls])
    return URL_IDENTIFICATION_PROMPT.format(urls=urls_text)
