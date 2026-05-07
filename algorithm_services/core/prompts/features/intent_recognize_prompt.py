# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.core.prompts.base_prompt import get_base_system_prompt, fill_prompt_template

# YISIA意图分类体系（闺蜜式社交导向）
YISIA_INTENT_RECOGNIZE_RULES = """
# 用户意图
1. 一级意图分类（唯一且互斥，严格匹配以下分类，禁止自定义）：
   - 情感分享：用户表达情绪、分享生活经历、讲述个人故事或心情；
   - 美妆咨询：用户关于护肤、美妆、医美等自然询问，寻求建议或意见；
   - 日常闲聊：用户问候、寒暄、轻松话题、生活趣事等日常交流；
   - 生活建议：用户寻求穿搭、生活方式、健康习惯等方面的建议；
   - 陪伴倾听：用户需要倾诉、寻求安慰或情感支持；
   - 知识学习：用户想了解新知识、技能或感兴趣的话题；

2. 识别核心规则：
   - 社交视角：完全站在朋友视角理解输入，注重情感和关系建立；
   - 自然对话：忽略口语化表达，专注于理解用户的真实意图；
   - 上下文关联：结合对话上下文判断意图，避免孤立解析单句；
   - 亲近感营造：即使用户询问功能性问题，也要识别为寻求建议或帮助；

3. 输出格式（严格JSON，无多余内容）：
   {
     "intent": "匹配的一级意图名称",
     "confidence": 0-1（保留1位小数）
   }
"""



# 意图识别用户Prompt模板（无改动，保留上下文适配）
INTENT_RECOGNIZE_USER_TEMPLATE = """
请识别以下用户对话的一级意图：
用户对话：{user_input}
对话上下文：{context}
"""

def get_yisia_intent_recognize_prompt(user_input: str, context: str = "") -> dict:
    """
    获取YISIA意图识别完整Prompt
    :param user_input: 用户本次输入
    :param context: 对话上下文（可选）
    :return: {"system_prompt": "...", "user_prompt": "..."}
    """
    # system_prompt = get_base_system_prompt(YISIA_INTENT_RECOGNIZE_RULES)
    system_prompt = YISIA_INTENT_RECOGNIZE_RULES # 简化系统规则，压缩上下文
    user_prompt = fill_prompt_template(
        INTENT_RECOGNIZE_USER_TEMPLATE,
        user_input=user_input,
        context=context
    )
    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt
    }

