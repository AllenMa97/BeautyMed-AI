"""
根据 feature_stage 动态调整 free_chat prompt
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.session.session_factory import SessionFeatureStage


FEATURE_STAGE_PROMPTS = {
    SessionFeatureStage.COMPANIONSHIP_MODE: {
        "role": "陪伴者",
        "focus": "倾听、陪伴",
        "style": "温暖、体贴",
        "max_tokens": 80,
        "length_guide": "30-80字，简洁倾听",
    },
    
    SessionFeatureStage.ADVICE_MODE: {
        "role": "顾问",
        "focus": "提供建议",
        "style": "专业、实用",
        "max_tokens": 200,
        "length_guide": "80-150字，简明实用",
    },
    
    SessionFeatureStage.CASUAL_CHAT_MODE: {
        "role": "朋友",
        "focus": "日常闲聊",
        "style": "活泼、亲切",
        "max_tokens": 120,
        "length_guide": "50-100字，自然简短",
    },
    
    SessionFeatureStage.EMOTIONAL_SUPPORT_MODE: {
        "role": "安慰者",
        "focus": "情感安慰",
        "style": "温柔、支持",
        "max_tokens": 60,
        "length_guide": "20-60字，温暖简短",
    },
    
    SessionFeatureStage.LEARNING_MODE: {
        "role": "老师",
        "focus": "知识讲解",
        "style": "清晰、耐心里",
        "max_tokens": 200,
        "length_guide": "80-150字，清晰简洁",
    },
    
    SessionFeatureStage.BEAUTY_CONSULTATION_MODE: {
        "role": "美妆顾问",
        "focus": "美妆建议",
        "style": "专业、贴心",
        "max_tokens": 150,
        "length_guide": "50-100字，简明实用",
    },
}


def get_feature_stage_prompt_addition(feature_stage: str) -> dict:
    """
    根据 feature_stage 获取需要添加到 prompt 的内容
    """
    if not feature_stage:
        return {}
    
    stage_lower = feature_stage.lower()
    
    for stage_key, stage_info in FEATURE_STAGE_PROMPTS.items():
        if stage_key.lower() == stage_lower:
            return stage_info
    
    return {}


def apply_feature_stage_to_prompt(
    system_prompt: str,
    feature_stage: str,
    default_max_tokens: int = 200
) -> tuple[str, int]:
    """
    将 feature_stage 相关内容应用到 system prompt
    返回：(修改后的 prompt, max_tokens)
    """
    stage_info = get_feature_stage_prompt_addition(feature_stage)
    
    max_tokens = stage_info.get("max_tokens", default_max_tokens)
    length_guide = stage_info.get("length_guide", "")
    
    if not stage_info:
        return system_prompt, default_max_tokens
    
    role = stage_info.get('role', '朋友')
    focus = stage_info.get('focus', '自然交流')
    style = stage_info.get('style', '亲切自然')
    
    addition = f"""

【当前模式：{role}】
重点：{focus}
风格：{style}
回复长度：{length_guide}
"""
    
    return system_prompt + addition, max_tokens
