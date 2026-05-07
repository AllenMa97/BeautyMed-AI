# Developer: 马赫·马智?
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
文档信息提取提示模板
"""

# 文档信息提取提示
EXTRACT_DOCUMENT_INFORMATION_PROMPT = """
分析以下文档内容并提取关键信息?

文档: {filename}
内容: {content[:4000]}  # 限制内容长度

返回一个JSON对象,包含:
- "content": 文档中最重要的信?
- "tags": 相关标签/关键词数?
"""

def get_extract_document_information_prompt(filename: str, content: str):
    """
    获取文档信息提取的提?
    """
    return EXTRACT_DOCUMENT_INFORMATION_PROMPT.format(filename=filename, content=content)