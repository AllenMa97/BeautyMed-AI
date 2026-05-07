"""
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from typing import Dict, Any

ROUTING_DECISION_SYSTEM_PROMPT = """判断用户输入，返回JSON: {"need_plan":bool,"need_search":bool}

need_plan 判断规则：
- false: 仅限简单问候(你好/hi/hello)、确认(好的/OK)、感谢(谢谢)、纯闲聊(今天天气怎么样)
- true: 其他所有情况，特别是：
  * 需要专业知识回答的问题（医美/护肤/产品/成分/功效）
  * 需要产品推荐或建议
  * 需要多步骤完成的任务
  * 用户描述了具体问题或症状（如色斑、痘痘、皱纹等）
  * 用户追问（如"有什么好用的"、"哪个效果好"）
  * 任何涉及皮肤、美容、医美、护肤品的讨论

need_search: 实时信息/新闻/股价等需要联网搜索的问题=true，其他=false

重要规则：
1. 当不确定时，默认 need_plan=true，宁可多规划也不要漏掉需要专业知识的场景
2. 只要用户提到任何皮肤问题、医美项目、护肤成分、产品相关，need_plan=true
3. 用户追问或继续讨论某个话题时，need_plan=true
"""

ROUTING_DECISION_USER_PROMPT_TEMPLATE = "{user_input}"


def get_routing_decision_prompt(user_input: str) -> Dict[str, str]:
    """获取路由决策的 prompt"""
    return {
        "system_prompt": ROUTING_DECISION_SYSTEM_PROMPT,
        "user_prompt": ROUTING_DECISION_USER_PROMPT_TEMPLATE.format(user_input=user_input)
    }
