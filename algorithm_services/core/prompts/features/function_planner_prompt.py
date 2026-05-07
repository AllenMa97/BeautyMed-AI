# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import json

from typing import Dict, List, Any, Optional

from algorithm_services.core.prompts.base_prompt import get_base_system_prompt, fill_prompt_template
from algorithm_services.api.schemas.schema_kit import get_schema_by_func_name

PLANNER_BASIC_PROMPT = '''
你是智能规划器，负责决定调用哪些函数来处理用户输入。

之前函数执行结果：{intermediate_results_info}

会话状态标签(feature_stage)：
- COMPANIONSHIP_MODE 陪伴倾听
- ADVICE_MODE 提供建议
- CASUAL_CHAT_MODE 闲聊
- EMOTIONAL_SUPPORT_MODE 情感支持
- LEARNING_MODE 知识学习
- BEAUTY_CONSULTATION_MODE 美学咨询
- PRODUCT_CONSULTATION_MODE 产品咨询
- MEDICAL_CONSULTATION_MODE 医美咨询
- SKINCARE_CONSULTATION_MODE 护肤咨询
'''


PLANNER_FUNCTION_REGISTRATION_PROMPT = '''
### 可调用功能列表 与 调用时传入的参数规范
{
  # 知识检索 - 从知识库检索相关知识片段（医美/产品/成分/功效等）
  # 注意：实体和关系的抽取由服务内部自动完成，无需在此传入
  "knowledge_retrieval": {
    "user_input": "字符串 | 必填 | 用户本次输入",
    "intent": "字符串 | 非必填 | 用户意图",
    "top_k": "整数 | 非必填 | 检索结果数量，默认5",
    "search_type": "字符串 | 非必填 | 检索类型: all/products/entries"
  },
  # 意图澄清
  "intent_clarify": {
    "user_input": "字符串 | 必填 | 用户本次输入",
    "recognized_intent": "字符串 | 必填 | 已识别的意图（JSON 字符串）",
    "recognized_entities": "字符串 | 必填 | 已识别的实体（JSON 字符串）",
    "context": "字符串 | 非必填 | 对话上下文",
    "data": 其他参考信息
  },   
  # 文本摘要生成器
  "text_summary": {
    "user_input": "字符串 | 必填 | 用户本次输入",
    "data": 其他参考信息
  },
}

### 功能选择规则

## 医美/护肤/产品相关问题，必须调用 knowledge_retrieval
- 当用户明确询问产品推荐、品牌对比、产品功效时，search_type 设为 "products"
- 当用户询问疾病治疗、皮肤科普、成分知识等非产品问题时，search_type 设为 "entries"
- 其他情况 search_type 设为 "all"

### 调用 intent_clarify 的场景：
- 用户输入完全模糊，无法判断任何意图（如"那个"、"这个"、"嗯"）
- 用户输入与医美/护肤完全无关，且无法确定用户想要什么
### 重要提示
- 如果不需要任何功能调用，返回空的 function_calls: []
'''

_ENTITY_RELATION_EXTRACTION_REGISTRATION = '''
  # 实体与关系联合抽取（已内嵌为 knowledge_retrieval 的前置步骤，无需单独规划）
  # 恢复方式：将此变量拼接到 PLANNER_FUNCTION_REGISTRATION_PROMPT 的功能列表中
  "entity_relation_extraction": {
    "user_input": "字符串 | 必填 | 用户本次输入",
    "context": "字符串 | 非必填 | 对话上下文",
    "data": 其他参考信息
  },
'''

_DIALOG_SUMMARY_REGISTRATION = '''
  # 对话摘要生成器（已暂停：已在 generate_plan_result 中作为前置步骤自动执行）
  # 恢复方式：将此变量拼接到 PLANNER_FUNCTION_REGISTRATION_PROMPT 的功能列表中
  "dialog_summary": {
    "dialog_content": "列表【字符串】 | 必填 | 对话内容列表，每个项为一次用户输入和 Agent 回答",
    "summary_length": "整数 | 非必填 | 摘要长度限制",
    "summary_type": "字符串 | 非必填 | 摘要类型：brief(简洁)/detail(详细)",
    "data": 其他参考信息
  },
'''

PLANNER_OUTPUT_FORMAT_PROMPT = '''
### 输出格式（严格JSON）
{
  "feature_stage": "会话特征状态标签",
  "function_calls": [
      {
          "function_name": "功能名0",
          "function_params": {
            "参数名1": "参数值1",
            "参数名2": "参数值2",...
          }
        },
        {
          "function_name": "功能名1",
          "function_params": {
            "参数名1": "参数值1",
            "参数名2": "参数值2", ...
          }
        }, ...
  ],
  "execution_order": [0,1,2...], # 哪怕只调用一个函数，也要填入0
  "explanation": "函数调度逻辑说明" # 哪怕只调用一个函数，也要填入原因
}'''


PLANNER_RULES = PLANNER_BASIC_PROMPT + PLANNER_FUNCTION_REGISTRATION_PROMPT + PLANNER_OUTPUT_FORMAT_PROMPT


PLANNER_USER_TEMPLATE = """
会话ID：{session_id}
用户最新对话：{user_input}
对话上下文：{context}
已执行的函数及结果:{executed_functions_and_results}
已生成的函数调度逻辑说明：{explanation}
请根据上述信息，生成功能调度计划。
"""


def get_function_planner_prompt(
    session_id: str,
    user_input: str,
    context: str,
    executed_functions_and_results: Optional[List[Dict[str, Any]]],
    explanation: str,
    time_location_info: Optional[Dict[str, Any]] = None,
    trending_topics_info: Optional[Dict[str, Any]] = None,
    intermediate_results: Optional[Dict[str, Any]] = None
) -> dict:
    if intermediate_results is None:
        intermediate_results = {}

    try:
        intermediate_results_str = json.dumps(intermediate_results, ensure_ascii=False)
    except Exception as e:
        intermediate_results_str = str(intermediate_results)
    
    system_prompt_with_context = PLANNER_BASIC_PROMPT.format(
        intermediate_results_info=intermediate_results_str
    )
    
    full_prompt = system_prompt_with_context + PLANNER_FUNCTION_REGISTRATION_PROMPT + PLANNER_OUTPUT_FORMAT_PROMPT
    system_prompt = full_prompt

    try:
        executed_functions_and_results_str = json.dumps(
            executed_functions_and_results,
            ensure_ascii=False,
        )
    except Exception as e:
        executed_functions_and_results_str = ""

    user_prompt = fill_prompt_template(
            PLANNER_USER_TEMPLATE,
            session_id=session_id,
            user_input=user_input,
            context=context,
            executed_functions_and_results=executed_functions_and_results_str,
            explanation=explanation,
    )

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt
    }
