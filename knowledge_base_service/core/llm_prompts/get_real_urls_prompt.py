# Developer: 马赫·马智?
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
获取真实URL提示模板
"""

# 获取真实URL的提?
GET_REAL_URLS_PROMPT = """
根据以下搜索查询,提?{max_results} 个最相关的真实网站URL和标题?
搜索查询: {query}

请严格按照以下JSON格式返回结果?
[
  {{"url": "https://example.com", "title": "网站标题"}},
  {{"url": "https://example.com", "title": "网站标题"}}
]

重要要求?
1. 只返回真实存在的网站,不要编造URL
2. 避免返回example.com、test.com等示例域?
3. 优先推荐中国大陆可访问的网站
4. 确保返回的URL格式正确,包含http://或https://
5. 确保返回有效的JSON格式,不要包含任何额外文件
6. 选择权威、高质量的网站,如百度百科、知乎、维基百科、学术网站、官方网站等
7. 确保URL是可访问的,避免返回已失效的链接
8. 如果查询涉及具体领域,优先返回该领域的专业网?
9. 生成多样化的URL,包括问答类(知乎、百度知道)、百科类(百度百科、维基百科)、新闻类、博客类?
10. 如果找不到完全匹配的内容,返回相关主题的页面
11. 如果不确定,请返回空数组 []

示例输出?
[
  {{"url": "https://baike.baidu.com/item/{query}", "title": "百度百科 - {query}"}},
  {{"url": "https://www.zhihu.com/search?q={query}", "title": "知乎 - {query}相关问题"}},
  {{"url": "https://zh.wikipedia.org/wiki/{query}", "title": "维基百科 - {query}"}},
  {{"url": "https://www.so.com/s?q={query}", "title": "360搜索 - {query}"}},
  {{"url": "https://www.sogou.com/web?query={query}", "title": "搜狗搜索 - {query}"}}
]
"""

def get_real_urls_prompt(query: str, max_results: int):
    """
    获取获取真实URL的提?
    """
    return GET_REAL_URLS_PROMPT.format(max_results=max_results, query=query)