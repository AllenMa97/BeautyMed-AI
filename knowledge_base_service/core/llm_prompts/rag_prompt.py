# Developer: 马赫·马智?
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
RAG(检索增强生成)提示模板
"""

# RAG查询提示
RAG_QUERY_PROMPT = """
基于以下上下文信息回答用户的问题?

上下文信息:
{context}

用户问题?
{query}

请根据上述上下文信息,简洁明了地回答用户的问题。如果上下文信息不足以回答问题,请说明信息不足?
"""

# 知识整合提示
KNOWLEDGE_INTEGRATION_PROMPT = """
请将以下多个知识片段整合成一个连贯的回答?

知识片段?
{knowledge_fragments}

用户问题?
{query}

请基于以上知识片段,生成一个完整、连贯的回答?
"""

# 答案精炼提示
ANSWER_REFINEMENT_PROMPT = """
请对以下初步答案进行精炼和优化:

初步答案?
{initial_answer}

上下文信息:
{context}

请确保最终答案准确、简洁,并与上下文信息一致?
"""

def get_knowledge_base_rag_prompt(query: str, context: str):
    """
    获取知识库RAG系统的提?
    """
    system_prompt = RAG_QUERY_PROMPT.format(context=context, query=query)
    user_prompt = f"请基于以上上下文信息回答问题:{query}"
    
    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt
    }